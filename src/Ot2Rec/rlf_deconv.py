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
import os
import numpy as np
from icecream import ic
from tqdm import tqdm
import pandas as pd
import yaml

import mrcfile
import tifffile

import RedLionfishDeconv as rlf

from . import user_args as uaMod
from . import magicgui as mgMod
from . import logger as logMod


itick = 0
def tickCallBack():
    global itick
    itick += 1


class RLF_deconv():
    """
    Class encapsulating an RLF_deconv object
    """
    def __init__(self, rootname, suffix, raw_folder, kernel_folder, out_folder, params_dict, orig_mrc, kernel_mrc):
        """
        Initialise the RLF_deconv object

        ARGS:
        rootname (str)          :: rootname of project
        orig_folder (ndarray)   :: parent folder containing original images to be deconvolved
        kernel_folder (ndarray) :: parent folder containing kernel with which the image is to be deconvolved
        out_folder (ndarray)    :: output parent folder for deconvolved tomograms
        params_dict (dict)      :: dictionary containing all parameters used in RLF
        orig_mrc (bool)         :: whether the original image is in MRC format (TIFF if false)
        kernel_mrc (bool)       :: whether the kernel is in MRC format (TIFF if false)
        """
        self.rootname = rootname
        self.suffix = suffix
        self.raw_folder = raw_folder
        self.kernel_folder = kernel_folder
        self.out_folder = out_folder
        self.params = params_dict
        self.orig_mrc = orig_mrc
        self.kernel_mrc = kernel_mrc

        # Initiating variables for later use
        self.orig = None
        self.kernel = None

        self._get_internal_metadata()


    def __call__(self):
        """
        Method to start deconvolution
        """
        self.out_files = []
        tqdm_iter = tqdm(range(len(self.plist)), ncols=100)

        for idx in tqdm_iter:
            self.orig_path = self.raw_files[idx]
            self.kernel_path = self.psf_files[idx]
            self.out_path = f"{self.out_folder}/{self.plist[idx]}/{self.plist[idx]}_deconv.mrc"

            # Read in raw image and kernel files
            if self.orig_mrc:
                self.orig = self.read_mrc(self.orig_path)
            else:
                self.orig = self.read_tiff(self.orig_path)

            self.orig = 256 * (self.orig-np.min(self.orig)) / np.ptp(self.orig)

            if self.kernel_mrc:
                self.kernel = np.flip(self.read_mrc(self.kernel_path))
            else:
                self.kernel = np.flip(self.read_tiff(self.kernel_path))

            # Deconvolve image
            out = self._deconv_array()

            # Save results
            with mrcfile.new(self.out_path, overwrite=True) as f:
                f.set_data(out)

            # Update output list
            self.out_files.append(self.out_path)

        # Update and export output metadata
        self.meta_out.outputs = self.out_files

        yaml_file = self.rootname + '_rlf_deconv_mdout.yaml'
        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False)



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
            method=self.params['method'].lower(),
            useBlockAlgorithm=self.params['useBlockAlgorithm'],
            callbkTickFunc=tickCallBack(), # if self.params['callbkTickFunc'] else None,
            resAsUint8=self.params['resAsUint8']
        )

        return image_deconvolved


    def _get_internal_metadata(self):
        """
        Method to prepare internal metadata for processing and checking
        """
        # Get process list
        raw_subfolders = (f"{self.raw_folder}/"
                          f"{self.rootname}_*{self.suffix}")
        psf_subfolders = (f"{self.kernel_folder}/"
                          f"{self.rootname}_*{self.suffix}")
        raw_set = set([i.split("/")[-1] for i in glob(raw_subfolders)])
        psf_set = set([i.split("/")[-1] for i in glob(psf_subfolders)])
        self.plist = sorted(list(raw_set & psf_set))

        self.raw_files = []
        self.psf_files = []
        for proc in self.plist:
            # Create the folders and dictionary for future reference
            out_subfolders = f"{self.out_folder}/{proc}"
            os.makedirs(out_subfolders, exist_ok=True)

            # Find relevant files
            search = f"{self.raw_folder}/{proc}/*_rec.mrc"
            exclude = f"{self.raw_folder}/{proc}/*_full_rec.mrc"
            file_clean = list(set(glob(search))-set(glob(exclude)))[0]

            self.raw_files.append(file_clean)
            self.psf_files.append(glob(f"{self.kernel_folder}/{proc}/*_PSF.mrc")[0])

        assert(len(self.raw_files)==len(self.psf_files)), \
            "ERROR: lengths of raw and PSF file list not equal. File missing?"

        self.meta_out = pd.DataFrame(columns=['raw_files', 'psf_files', 'outputs'])
        self.meta_out.raw_files = self.raw_files
        self.meta_out.psf_files = self.psf_files


"""
PLUGIN METHODS
"""
def run():
    """
    Method to deconvolve image using a given kernel (point-spread function)
    """
    logger = logMod.Logger(log_path="o2r_rlf_deconv.log")

    # Parse user inputs
    args = mgMod.get_args_rldeconv.show(run=True)

    # Define deconvolution parameters and object
    deconv_params = dict({
        'method': args.device.value,
        'niter': args.niter.value,
        'useBlockAlgorithm': args.block.value,
        'callbkTickFunc': True,
        'resAsUint8': args.uint.value,
    })

    logger(level="info",
           message="Ot2Rec-RLFDeconv started.")

    my_deconv = RLF_deconv(
        rootname = args.project_name.value,
        suffix = args.file_suffix.value,
        raw_folder=str(args.raw_folder.value),
        kernel_folder=str(args.psf_folder.value),
        out_folder=str(args.output_folder.value),
        params_dict=deconv_params,
        orig_mrc=args.image_type.value == 'mrc',
        kernel_mrc=args.psf_type.value == 'mrc'
    )

    deconvd_image = my_deconv()
