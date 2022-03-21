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

import mrcfile
import tifffile

from icecream import ic


itick = 0
def tickCallBack():
    global itick
    itick += 1

    
class RLF_deconv():
    """
    Class encapsulating an RLF_deconv object
    """
    
    def __init__(self, orig_path, kernel_path, params_dict, orig_mrc, kernel_mrc):
        """
        Initialise the RLF_deconv object

        ARGS:
        orig_path (ndarray)   :: path to original image to be deconvolved
        kernel_path (ndarray) :: path to kernel with which the image is to be deconvolved
        params_dict (dict)    :: dictionary containing all parameters used in RLF
        orig_mrc (bool)       :: whether the original image is in MRC format (TIFF if false)
        kernel_mrc (bool)     :: whether the kernel is in MRC format (TIFF if false)
        """

        self.orig_path = orig_path
        self.kernel_path = kernel_path
        self.params = params_dict
        self.orig_mrc = orig_mrc
        self.kernel_mrc = kernel_mrc

        
    def __call__(self):
        """
        Method to start deconvolution
        """
        # Read in raw image and kernel files
        if self.orig_mrc:
            self.orig = self.read_mrc(self.orig_path)
        else:
            self.orig = self.read_tiff(self.orig_path)

        if self.kernel_mrc:
            self.kernel = self.read_mrc(self.kernel_path)
        else:
            self.kernel = self.read_tiff(self.kernel_path)

        # Deconvolve image
        out = self._deconv_array()

        return out


    @staticmethod
    def read_mrc(path):
        """
        Method to read an MRC file and return a numpy array

        Returns:
        ndarray
        """
        with mrcfile.open(path) as image:
            data = image.data
            
        return data


    @staticmethod
    def read_tiff(path):
        """
        Method to read a TIFF file and return a numpy array

        Returns:
        ndarray
        """
        data = tifffile.imread(path)

        return data
    
    
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
