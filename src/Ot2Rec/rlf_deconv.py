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


from glob import glob
import mrcfile
import tifffile

import RedLionfishDeconv as rlf

from . import user_args as uaMod
from . import magicgui as mgMod
from . import logger as logMod


itick = 0
def tickCallBack():
    global itick
    print(f"{itick}")
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

        # Initiating variables for later use
        self.orig = None
        self.kernel = None

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
            callbkTickFunc=tickCallBack(), # if self.params['callbkTickFunc'] else None,
            resAsUint8=self.params['resAsUint8']
        )

        print(
            self.orig.shape,
            self.kernel.shape,
            self.params
        )
        print(type(image_deconvolved))
        return image_deconvolved


"""
PLUGIN METHODS
"""


def run():
    """
    Method to deconvolve image using a given kernel (point-spread function)
    """
    # Parse user inputs
    args = mgMod.get_args_rldeconv.show(run=True)

    # Create logger object
    logger = logMod.Logger()

    # Check provided files are present
    # try:
    #     assert (len(glob(str(args.image_path.value))) > 0)
    # except:
    #     logger("Error in rlf_deconv:run: Raw image doesn't exist. Aborting...")
    #     return

    # try:
    #     assert (len(glob(args.psf_path)) > 0)
    # except:
    #     logger("Error in rlf_deconv:run: PSF image doesn't exist. Aborting...")
    #     return

    # Define deconvolution parameters and object
    deconv_params = dict({
        'method': args.device.value,
        'niter': args.niter.value,
        'useBlockAlgorithm': args.block.value,
        'callbkTickFunc': True,
        'resAsUint8': args.uint.value,
    })

    my_deconv = RLF_deconv(orig_path=str(args.image_path.value),
                           kernel_path=str(args.psf_path.value),
                           params_dict=deconv_params,
                           orig_mrc=args.image_type.value == 'mrc',
                           kernel_mrc=args.psf_type.value == 'mrc')

    deconvd_image = my_deconv()
    print(type(deconvd_image)); exit()

    # Save results
    with mrcfile.new(str(args.output_path.value), overwrite=True) as f:
        f.set_data(deconvd_image)
