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


class SavuRecon:
    """
    Class encapsulating a SavuRecon object
    """


    def __init__(self,
                 project_name,
                 params_in,
    ):
        """
        Initialising a SavuRecon object

        ARGS:
        project_name (str) :: name of current project
        params_in (Params) :: parameters for stack creation
        """

        self.proj_name = project_name

        self.pObj = params_in
        self.params = self.pObj.params

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
            if "savu_output_dir" not in list(self.md_out.keys()):
                self.md_out["savu_output_dir"] = {}
            self.md_out["savu_output_dir"][curr_ts] = subfolder
        

    def _get_savuconfig_recon_command(self, i):
        """
        Method to get command to set up Savu process list

        ARGS:
        i (int): The i-th tilt series to process
        """
        
        curr_ts = self.params['System']['process_list'][i]
        # Get tilt angles .tlt file for this iteration
        ts_name = os.path.splitext(
                    os.path.basename(
                        self.params['Savu']['setup']['tilt_angles'][i]))[0]

        # Get reconstruction algorithm and check that it is a valid choice
        algo = self.params['Savu']['setup']['algorithm']
        algo_choices = ["FBP_CUDA", "SIRT_CUDA", "SART_CUDA", "CGLS_CUDA", "BP_CUDA", "SIRT3D_CUDA", "CGLS3D_CUDA"]
        if algo not in algo_choices:
            raise ValueError(
                "Algorithm not supported. Please amend algorithm in savurecon.yaml to one of {}".format(algo_choices)
                )
        
        subfolder = os.path.abspath(self.md_out["savu_output_dir"][curr_ts])

        cmd = ['add MrcLoader\n',
                'mod 1.2 {}\n'.format(self.params['Savu']['setup']['tilt_angles'][i]),
                'add AstraReconGpu\n',
                'mod 2.2 {}\n'.format(algo),
                'add TiffSaver\n',
                'mod 3.1 VOLUME_YZ\n',
                'save {}/{}_{}.nxs\n'.format(subfolder, ts_name, algo),
                'y\n',
                'exit\n',
                'y\n'
                ]
        if self.params['Savu']['setup']['algorithm'] != "FBP_CUDA":
            cmd.insert(4, "mod 2.2 5\n")
        
        # Add location of .nxs file to metadata
        if "savu_process_lists" not in list(self.md_out.keys()):
            self.md_out['savu_process_lists'] = {}
        self.md_out['savu_process_lists'][curr_ts] = '{}/{}_{}.nxs'.format(subfolder, ts_name, algo)
        
        return cmd
    

    def savurecon_stack(self, i):
        """
        Method to generate savu_config process list and run savu for the i-th ts
        """
        curr_ts = self.params['System']['process_list'][i]
        cmd = self._get_savuconfig_recon_command(i)
        savu_config = subprocess.Popen('savu_config',
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     encoding='ascii',
                                     )
        
        # Feed commands to savu_config to make process list
        for command in cmd:
            savu_config.stdin.write(command)
        # print(savu_config.communicate()[0])

        # Run savu
        savu_run = subprocess.run(['savu',
                                   self.params['Savu']['setup']['aligned_projections'][i],
                                   self.md_out['savu_process_lists'][curr_ts],
                                   self.md_out['savu_output_dir'][curr_ts]],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   encoding='ascii',
                                   )
        # print(savu_run.stdout)


    def dummy_runner(self, i):
        """
        Temp method to test locally that commands are created correctly
        """
        curr_ts = self.params['System']['process_list'][i]
        cmd = self._get_savuconfig_recon_command(i)
        print(cmd)
        print(['savu',
                self.params['Savu']['setup']['aligned_projections'][i],
                self.md_out['savu_process_lists'][curr_ts],
                self.md_out['savu_output_dir'][curr_ts]],
        )
    

    def run_savu_all(self):
        """
        Method to run savurecon_stack for all ts in process list
        """
        for i, curr_ts in enumerate(self.params['System']['process_list']):
            self.savurecon_stack(i)
            # self.dummy_runner(i)
        print("Savu reconstruction complete for {}_{}".format(self.proj_name, curr_ts))
        self.export_metadata()

    
    def export_metadata(self):
        """
        Method to export metadata as yaml
        """

        yaml_file = self.proj_name + "_savurecon_mdout.yaml"

        with open(yaml_file, 'w') as f:
            yaml.dump(self.md_out, f, indent=4, sort_keys=False)
