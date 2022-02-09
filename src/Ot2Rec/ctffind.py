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


import os
import subprocess
import yaml
import pandas as pd
from icecream import ic

from . import metadata as mdMod


class ctffind():
    """
    Class encapsulating a ctffind object
    """

    def __init__(self,
                 project_name,
                 md_in,
                 params_in,
                 logger_in,
    ):
        """
        Initialising a ctffind object

        ARGS:
        project_name (str) :: name of current project
        md_in (Metadata)   :: metadata containing information of tilt-series to be processed
        params_in (Params) :: params object containing configurations for ctffind
        logger_in (Logger) :: logger object for recording ctffind process
        """

        self.proj_name = project_name
        
        self.prmObj = params_in
        self.params = self.prmObj.params

        self.logObj = logger_in
        self.log = []

        self._process_list = self.params['System']['process_list']
        self.meta = pd.DataFrame(md_in.metadata)
        self.meta = self.meta[self.meta['ts'].isin(self._process_list)]

        self._get_images()
        self.no_processes = False
        self._check_processed_images()
        self._set_output_path()

        # Check if output folder exists, create if not
        if not os.path.isdir(self.params['System']['output_path']):
            subprocess.run(['mkdir', self.params['System']['output_path']],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           encoding='ascii')
        
        
    def _get_images(self):
        """
        Method to extract images for ctffind
        Note: one image per tilt-series, criterion: image closest to 0 tilt angle
        """

        self.ctf_images = pd.DataFrame(columns=self.meta.columns)
        for curr_ts in self._process_list:
            temp = self.meta[self.meta['ts']==curr_ts]
            self.ctf_images = pd.concat([self.ctf_images, temp],
                                        ignore_index=True)
        

    def _set_output_path(self):
        """
        Subroutine to set input and output path for "ctffound" images
        """
        # copy values from output column to file_paths (input) column
        self.ctf_images['file_paths'] = self.ctf_images.apply(lambda df: df['output'], axis=1)

        # update output column
        self.ctf_images['output'] = self.ctf_images.apply(
            lambda row: f"{self.params['System']['output_path']}"
            f"{self.params['System']['output_prefix']}_{row['ts']:03}_{row['angles']}_ctffind.mrc", axis=1)
        

    def _check_processed_images(self):
        """
        Method to check images which have already been processed before
        """
        # Create new empty internal output metadata if no record exists
        if not os.path.isfile(self.proj_name + '_ctffind_mdout.yaml'):
            self.meta_out = pd.DataFrame(columns=self.meta.columns)
            
        # Read in serialised metadata and turn into DataFrame if record exists
        else:
            _meta_record = mdMod.read_md_yaml(project_name=self.proj_name,
                                              job_type='ctffind',
                                              filename=self.proj_name + '_ctffind_mdout.yaml')
            self.meta_out = pd.DataFrame(_meta_record.metadata)
        self.meta_out.drop_duplicates(inplace=True)

        # Compare output metadata and output folder
        # If a file (in specified TS) is in record but missing, remove from record
        if len(self.meta_out) > 0:
            self._missing = self.meta_out.loc[~self.meta_out['output'].apply(lambda x: os.path.isfile(x))]
            self._missing_specified = pd.DataFrame(columns=self.meta.columns)
        
            for curr_ts in self.params['System']['process_list']:
                _to_append = self._missing[self._missing['ts']==curr_ts]
                self._missing_specified = pd.concat([self._missing_specified, _to_append],
                                                    ignore_index=True,
                )
            self._merged = self.meta_out.merge(self._missing_specified, how='left', indicator=True)
            self.meta_out = self.meta_out[self._merged['_merge']=='left_only']

            if len(self._missing_specified) > 0:
                self.logObj(f"Info: {len(self._missing_specified)} images in record missing in folder. Will be added back for processing.")
            
        # Drop the items in input metadata if they are in the output record 
        _ignored = self.ctf_images[self.ctf_images.output.isin(self.meta_out.file_paths)]
        if len(_ignored) > 0 and len(_ignored) < len(self.ctf_images):
            self.logObj(f"Info: {len(_ignored)} images had been processed and will be omitted.")
        elif len(_ignored) == len(self.ctf_images):
            self.logObj(f"Info: All specified images had been processed. Nothing will be done.")
            self.no_processes = True

        self._merged = self.ctf_images.merge(_ignored, how='left', indicator=True)
        self.ctf_images = self.ctf_images[self._merged['_merge']=='left_only']
        self._process_list = self.ctf_images['ts'].sort_values(ascending=True).unique().tolist()
        

    def _get_ctffind_command(self, image):
        """
        Function to return command for CTFfind

        ARGS:
        ts (int) :: index of curent tilt-series
        """

        self.cmd = [self.params['ctffind']['ctffind_path']]
        input_dict = [image['file_paths'],
                      image['output'],
                      str(self.params['ctffind']['pixel_size']),
                      str(self.params['ctffind']['voltage']),
                      str(self.params['ctffind']['spherical_aberration']),
                      str(self.params['ctffind']['amp_contrast']),
                      str(self.params['ctffind']['amp_spec_size']),
                      str(self.params['ctffind']['resolution_min']),
                      str(self.params['ctffind']['resolution_max']),
                      str(self.params['ctffind']['defocus_min']),
                      str(self.params['ctffind']['defocus_max']),
                      str(self.params['ctffind']['defocus_step']),
                      str(self.params['ctffind']['astigm_type']) if self.params['ctffind']['astigm_type'] else 'no',
                      'yes' if self.params['ctffind']['exhaustive_search'] else 'no',
                      'yes' if self.params['ctffind']['astigm_restraint'] else 'no',
                      'yes' if self.params['ctffind']['phase_shift'] else 'no',
                      'no']
        self.input_string = '\n'.join(input_dict)

    
    def run_ctffind(self):
        """
        Method to run ctffind on tilt-series sequentially
        """

        for index, curr_image in self.ctf_images.iterrows():
            # Get the command and inputs for current tilt-series
            self._get_ctffind_command(curr_image)
            ctffind_run = subprocess.run(self.cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT,
                                         input=self.input_string,
                                         encoding='ascii')

            if ctffind_run.stderr:
                raise ValueError(f'Ctffind: An error has occurred ({ctffind_run.returncode}) '
                                 f'on stack{stack_padded}.')
            else:
                self.stdout = ctffind_run.stdout
                self.update_ctffind_metadata()
                self.export_metadata()

                
    def update_ctffind_metadata(self):
        """
        Subroutine to update metadata after one set of runs
        """

        # Search for files with output paths specified in the metadata
        # If the files don't exist, keep the line in the input metadata
        # If they do, move them to the output metadata

        _to_append = self.ctf_images.loc[self.ctf_images['output'].apply(lambda x: os.path.isfile(x))]
        self.meta_out = pd.concat([self.meta_out, _to_append],
                                  ignore_index=True)
        self.ctf_images = self.ctf_images.loc[~self.ctf_images['output'].apply(lambda x: os.path.isfile(x))]

        # Sometimes data might be duplicated (unlikely) -- need to drop the duplicates
        self.meta_out.drop_duplicates(inplace=True)

        
    def export_metadata(self):
        """
        Method to serialise output metadata, export as yaml
        """

        yaml_file = self.proj_name + '_ctffind_mdout.yaml'

        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False) 
