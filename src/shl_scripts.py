#!/usr/bin/env python3
""" shl_scripts """
# -*- coding: utf-8 -*

import time
import sys

toolbar_width = 40



import matplotlib
import time

import matplotlib.pyplot as plt
import numpy as np


from sklearn.decomposition import SparseHebbianLearning
# from sklearn.decomposition import MiniBatchDictionaryLearning
# from sklearn.decomposition import DictionaryLearning
from sklearn.feature_extraction.image import extract_patches_2d

from SLIP import Image
import numpy as np

class SHL(object):
    """
    Base class to define SHL experiments:
        - intializing
        - running learning
        - visualization
        - quantitative analysis

    """
    def __init__(self,
                 height=256,
                 width=256,
                 patch_size=(10, 10),
                 n_components=11**2,
                 learning_algorithm='omp',
                 alpha=None,
                 transform_n_nonzero_coefs=20,
                 n_iter=50000,
                 eta=1./25,
                 eta_homeo=0.005,
                 alpha_homeo=0.02,
                 max_patches=10000,
                 batch_size=100,
                 n_image=200,
                 DEBUG_DOWNSCALE=1, # set to 10 to perform a rapid experiment<D-d>
                 verbose=20,
                 ):
        self.height = height
        self.width = width
        self.patch_size = patch_size
        self.n_components = n_components
        self.n_iter = int(n_iter/DEBUG_DOWNSCALE)
        self.max_patches = int(max_patches/DEBUG_DOWNSCALE)
        self.n_image = int(n_image/DEBUG_DOWNSCALE)
        self.batch_size = batch_size
        self.learning_algorithm = learning_algorithm
        self.alpha=alpha

        self.transform_n_nonzero_coefs = transform_n_nonzero_coefs
        self.eta = eta
        self.eta_homeo = eta_homeo
        self.alpha_homeo = alpha_homeo

        self.verbose = verbose
        # Load natural images and extract patches
        self.slip = Image({'N_X':height, 'N_Y':width, 
                                        'white_n_learning' : 0,
                                        'seed': None,
                                        'white_N' : .07,
                                        'white_N_0' : .0, # olshausen = 0.
                                        'white_f_0' : .4, # olshausen = 0.2
                                        'white_alpha' : 1.4,
                                        'white_steepness' : 4.,
                                        'datapath': '/Users/lolo/pool/science/PerrinetBednar15/database/',
                                        'do_mask':True,
                                        'N_image': n_image})


    def get_data(self, name_database='serre07_distractors', seed=None):
        if self.verbose:
            # setup toolbar
            sys.stdout.write('Extracting data...')
            sys.stdout.flush()
            sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['
            t0 = time.time()
        imagelist = self.slip.make_imagelist(name_database=name_database)#, seed=seed)
        for filename, croparea in imagelist:
            # whitening
            image, filename_, croparea_ = self.slip.patch(name_database, filename=filename, croparea=croparea, center=False)#, , seed=seed)
            image = self.slip.whitening(image)
            # Extract all reference patches
            data_ = extract_patches_2d(image, self.patch_size, max_patches=int(self.max_patches))#, seed=seed)
            data_ = data_.reshape(data_.shape[0], -1)
            data_ -= np.mean(data_, axis=0)
            data_ /= np.std(data_, axis=0)
            try:
                data = np.vstack((data, data_))
            except:
                data = data_.copy()
            if self.verbose:
                # update the bar
                sys.stdout.write(filename + ", ")
                sys.stdout.flush()
        if self.verbose:
            dt = time.time() - t0
            sys.stdout.write("\n")
            sys.stdout.write("Data is of shape : "+ str(data.shape))
            sys.stdout.write('done in %.2fs.' % dt)
            sys.stdout.flush()
        return data


    def learn_dico(self, name_database='serre07_distractors', **kwargs):
        data = self.get_data(name_database)
        # Learn the dictionary from reference patches
        if self.verbose: print('Learning the dictionary...', end=' ')
        t0 = time.time()
        dico = SparseHebbianLearning(eta=self.eta,
                                     n_components=self.n_components, n_iter=self.n_iter,
                                     gain_rate=self.eta_homeo, alpha_homeo=self.alpha_homeo,
                                     transform_n_nonzero_coefs=self.transform_n_nonzero_coefs,
                                     batch_size=self.batch_size, verbose=self.verbose, n_jobs=1,
                                     transform_algorithm=self.learning_algorithm, transform_alpha=self.alpha, **kwargs)
        if self.verbose: print('Training on %d patches' % len(data), end='... ')
        dico.fit(data)
        if self.verbose:
            dt = time.time() - t0
            print('done in %.2fs.' % dt)
        return dico

    def show_dico(self, dico, title=None):
        subplotpars = matplotlib.figure.SubplotParams(left=0., right=1., bottom=0., top=1., wspace=0.05, hspace=0.05,)
        fig = plt.figure(figsize=(10, 10), subplotpars=subplotpars)
        for i, comp in enumerate(dico.components_):
            ax = fig.add_subplot(np.sqrt(self.n_components), np.sqrt(self.n_components), i + 1)
            cmax = np.max(np.abs(comp))
            ax.imshow(comp.reshape(self.patch_size), cmap=plt.cm.gray_r, vmin=-cmax, vmax=+cmax,
                    interpolation='nearest')
            ax.set_xticks(())
            ax.set_yticks(())
        if title is not None:
            fig.suptitle(title, fontsize=12, backgroundcolor = 'white', color = 'k')
        #fig.tight_layout(rect=[0, 0, .9, 1])
        return fig, ax

    def code(self, data, dico, intercept, coding_algorithm='omp', **kwargs):
        if self.verbose:
            print('Coding data...', end=' ')
            t0 = time.time()
        dico.set_params(transform_algorithm=coding_algorithm, **kwargs)
        code = dico.transform(data)
        V = dico.components_

        patches = np.dot(code, V)
        if coding_algorithm == 'threshold':
            patches -= patches.min()
            patches /= patches.max()

        patches += intercept
        patches = patches.reshape(len(data), *self.patch_size)
        if coding_algorithm == 'threshold':
            patches -= patches.min()
            patches /= patches.max()
        if self.verbose:
            dt = time.time() - t0
            print('done in %.2fs.' % dt)
        return patches