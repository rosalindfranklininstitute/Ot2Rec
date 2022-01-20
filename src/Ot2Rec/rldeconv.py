# Copyright 2021 Rosalind Franklin Institute
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import RedLionfishDeconv as rlf
import numpy as np
from scipy.signal import convolve as conv

from icecream import ic


itick = 0
def tickCallBack(self):
    """
    Function defining the tick callback
    Note: Needs to be outside the class
    """
    global itick
    ic(f'itick = {itick}')
    itick += 1

            
class RLF_deconv():
    """
    Class encapsulating an RLF_deconv object
    """
    
    def __init__(self, orig, kernel, params_dict):
        """
        Initialise the RLF_deconv object

        ARGS:
        orig (ndarray)     :: original image to be deconvolved
        kernel (ndarray)   :: kernel with which the image is to be deconvolved
        params_dict (dict) :: dictionary containing all parameters used in RLF
        """

        self.orig = orig
        self.kernel = kernel
        self.params = params_dict

        
    def __call__(self):
        """
        Method to start deconvolution
        """
        self._validate_params()
        out = self._deconv_array()
        return out


    def _validate_params(self):
        """
        Method to validate parameters
        """
        if 'niter' not in self.params:
            self.params['niter'] = 10
        else:
            assert (isinstance(self.params['niter'], int)), \
                'Error in RFL_deconv._validate_params: niter must be an integer.'

        if 'method' not in self.params:
            self.params['method'] = 'gpu'
        else:
            assert (self.params['method'] in ['cpu', 'gpu']), \
                'Error in RFL_deconv._validate_params: method must be either gpu or cpu.'

        if 'useBlockAlgorithm' not in self.params:
            self.params['useBlockAlgorithm'] = False
        else:
            assert (isinstance(self.params['useBlockAlgorithm'], bool)), \
                'Error in RFL_deconv._validate_params: useBlockAlgorithm must be a boolean.'

        if 'resAsUint8' not in self.params:
            self.params['resAsUint8'] = False
        else:
            assert (isinstance(self.params['resAsUint8'], bool)), \
                'Error in RFL_deconv._validate_params: resAsUint8 must be a boolean.'

        if 'callbkTickFunc' not in self.params:
            self.params['callbkTickFunc'] = None
            

    def _deconv_array(self):
        """
        Method to use RLF to deconvolve image
        """

        image_deconvolved = rlf.doRLDeconvolutionFromNpArrays(
            self.orig, self.kernel,
            niter=self.params['niter'],
            method=self.params['method'],
            useBlockAlgorithm=self.params['useBlockAlgorithm'],
            callbkTickFunc=tickCallBack if self.params['callbkTickFunc'] else None,
            resAsUint8=self.params['resAsUint8']
        )

        return image_deconvolved
