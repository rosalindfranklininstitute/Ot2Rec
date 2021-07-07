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


import yaml
import os
from glob import glob
import pandas as pd
from icecream import ic

from . import params as prmMod


class Metadata:
    """
    Class encapsulating Metadata objects
    """

    # First define conversion table between job (module) name and file suffixes
    suffix_dict = {
        'master': 'proj',
        'motioncorr': 'mc2',
        'ctffind': 'ctffind',
        'align': 'align',
        'reconstruct': 'recon',
    }


    def __init__(self,
                 project_name: str,
                 job_type: str,
                 md_in=None,
    ):
        """
        Initialise Metadata object

        ARGS:
        project_name :: name of the current project
        job_type     :: what job is being done (motioncorr/ctffind/align/reconstruct)
        md_in        :: dictionary read from yaml file containing existing metadata
        """

        self.project_name = project_name
        self.job_type = job_type
        self.metadata = md_in

        # Obtain parameters first
        self.get_param()


    def get_param(self):
        """
        Subroutine to get parameters for current job
        """

        param_file = self.project_name + '_' + Metadata.suffix_dict[self.job_type] + '.yaml'
        self.prmObj = prmMod.read_yaml(project_name=self.project_name,
                                       filename=param_file)
        self.params = self.prmObj.params
        

    def create_master_metadata(self):
        """
        Subroutine to create master metadata from raw data.
        Metadata include: image paths, tilt series indices, tilt angles
        """

        # Define criteria for searching subfolders (tilt series) within source folder
        if self.params['TS_folder_prefix'] == '*':
            ts_subfolder_criterion = '*'
        elif self.params['TS_folder_prefix'] != '*' and \
             len(self.params['TS_folder_prefix']) > 0:
            ts_subfolder_criterion = self.params['TS_folder_prefix'] + '_*'
            
        if self.params['source_TIFF']:
            source_extension = 'tif'
        else:
            source_extension = 'mrc'

        # Source folder should not end with forward slash so remove them
        while self.params['source_folder'].endswith('/'):
            self.params['source_folder'] = self.params['source_folder'][:-1]
        
        # Find files and check
        raw_images_list = glob("{}/{}/*.{}".format(self.params['source_folder'],
                                                   ts_subfolder_criterion,
                                                   source_extension)
        )
        if (len(raw_images_list) == 0):
            raise IOError("Error in Ot2Rec.metadata.Metadata.create_master_metadata: No vaild files found using given criteria.")

        # Convert potentially relative file paths to absolute paths
        raw_images_list = [os.path.abspath(image) for image in raw_images_list]

        # Extract information from image file names
        self.image_paths, self.tilt_series, self.tilt_angles = [], [], []
        for curr_image in raw_images_list:
            self.image_paths.append(curr_image)

            # Extract tilt series number
            split_path_name = curr_image.split('/')[-1].split('_')
            try:
                ts_index = int(''.join(i for i in split_path_name[self.params['image_stack_field']] if i.isdigit()))
            except IndexError or ValueError:
                raise IndexError(f"Error in Ot2Rec.metadata.Metadata.create_master_metadata. Failed to get tilt series number from file path {curr_image}.")
            self.tilt_series.append(ts_index)

            # Extract tilt angle
            try:
                tilt_angle = float(split_path_name[self.params['image_tiltangle_field']].replace(
                    f'.{source_extension}', '').replace('[', '').replace(']', ''))
            except IndexError or ValueError as ierr:
                raise IndexError(f"Error in Ot2Rec.metadata.Metadata.create_master_metadata. Failed to get tilt angle from file path {curr_image}.")
            self.tilt_angles.append(tilt_angle)

        # Save metadata as a dictionary --- easier to dump as yaml
        self.metadata = dict(file_paths=self.image_paths,
                             ts=int(self.tilt_series),
                             angles=self.tilt_angles)

        
def read_md_yaml(project_name: str,
                 job_type: str,
                 filename: str,
):
    """
    Function to read in YAML file containing metadata

    ARGS:
    project_name :: Name of current project
    job_type     :: what job is being done (motioncorr/ctffind/align/reconstruct)
    filename     :: Name of the YAML file to be read

    RETURNS:
    Metadata object
    """

    # Check if file exists
    if not os.path.isfile(filename):
        raise IOError("Error in Ot2Rec.metadata.read_md_yaml: File not found.")

    with open(filename, 'r') as f:
        md = yaml.load(f, Loader=yaml.FullLoader)

    return Metadata(project_name=project_name,
                    job_type=job_type,
                    md_in=md)
