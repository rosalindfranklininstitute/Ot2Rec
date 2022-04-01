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
import subprocess


class AreTomo:
    """
    Class encapsulating a AreTomo object
    """


    def __init__(self,
                 project_name,
                 params_in,
                 logger_in,
    ):
        """
        Initialising a AreTomo object

        ARGS:
        project_name (str) :: name of current project
        params_in (Params) :: parameters for stack creation
        logger_in (Logger) :: logger object to keep record of progress and errors
        """

        self.proj_name = project_name

        self.pObj = params_in
        self.params = self.pObj.params

        self.logObj = logger_in

        self.md_out = dict()

        self._get_internal_metadata()


    def _get_internal_metadata(self):
        """
        Method to prepare internal metadata for processing and checking
        """
        self.basis_folder = self.params['System']['output_path']
        if self.basis_folder.endswith('/'):
            self.basis_folder = self.basis_folder[:-1]
        
        self.rootname = self.params['System']['output_rootname']
        if self.rootname.endswith('_'):
            self.rootname = self.rootname[:-1]
        
        self.suffix = self.params['System']['output_suffix']
        if self.suffix.endswith('_'):
            self.suffix = self.suffix[:-1]
        
        # Create the folders and dictionary for future reference
        self._path_dict = dict()
        for curr_ts in self.params['System']['process_list']:
            subfolder = f"{self.basis_folder}/{self.rootname}_{curr_ts:02d}{self.suffix}"
            os.makedirs(subfolder, exist_ok=True)
            # self._path_dict[curr_ts] = subfolder
            if "aretomo_output_dir" not in list(self.md_out.keys()):
                self.md_out["aretomo_output_dir"] = {}
            self.md_out["aretomo_output_dir"][curr_ts] = subfolder
        

    def _get_aretomo_align_command(self, i):
        """
        Method to get command to set up AreTomo align

        ARGS:
        i (int): The i-th tilt series to process
        """
        cmd = [
            'AreTomo',
            '-InMrc',
            self.params['AreTomo_setup']['input_mrc'][i],
            '-OutMrc',
            self.params['AreTomo_setup']['output_mrc'][i],
            '-AngFile',
            self.params['AreTomo_setup']['tilt_angles'][i],
            '-VolZ',
            '0',
            '-OutBin',
            str(self.params['AreTomo_setup']['output_binning']),
            ]
        
        return cmd
    

    def _get_aretomo_recon_command(self, i):
        """
        Method to get command to set up AreTomo reconstruction

        ARGS:
        i (int): The i-th tilt series to process
        """
        cmd = [
            'AreTomo',
            '-InMrc',
            self.params['AreTomo_setup']['input_mrc'][i],
            '-OutMrc',
            self.params['AreTomo_setup']['output_mrc'][i],
            '-AngFile',
            self.params['AreTomo_setup']['tilt_angles'][i],
            '-VolZ',
            str(self.params['AreTomo_recon']['volz']),
            '-OutBin',
            str(self.params['AreTomo_setup']['output_binning']),
            '-Align',
            '0'
        ]

        if self.params['AreTomo_recon']['recon_algo'] == 0:
            # WBP
            cmd.append('-Wbp')
            cmd.append('1')
        elif self.params['AreTomo_recon']['recon_algo'] == 1:
            # SART
            cmd.append('-Wbp')
            cmd.append('0')

        return cmd


    def _run_aretomo(self, i):
        """
        Method to run AreTomo workflows
        """
        curr_ts = self.params['System']['process_list'][i]

        # check AreTomo mode
        if self.params['AreTomo_setup']['aretomo_mode'] == 0:
            align_cmd = self._get_aretomo_align_command(i)
            cmd = align_cmd
        else:
            recon_cmd = self._get_aretomo_recon_command(i)
            cmd = recon_cmd

        # Add extra kwargs
        

        # Run aretomo
        aretomo_run = subprocess.run(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     encoding='ascii',
                                     )
        print(aretomo_run.stdout)
   

    def run_aretomo_all(self):
        """
        Method to run AreTomo for all ts in process list
        """
        for i, curr_ts in enumerate(self.params['System']['process_list']):
            self._run_aretomo(i)
            print("Ran AreTomo on {}_{}".format(self.proj_name, curr_ts))
        self.export_metadata()

    
    def export_metadata(self):
        """
        Method to export metadata as yaml
        """

        yaml_file = self.proj_name + "_aretomo_mdout.yaml"

        with open(yaml_file, 'w') as f:
            yaml.dump(self.md_out, f, indent=4, sort_keys=False)
