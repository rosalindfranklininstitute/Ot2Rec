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


import argparse
import os
import subprocess
from glob import glob

import yaml
import mrcfile

from . import metadata as mdMod
from . import user_args as uaMod
from . import magicgui as mgMod
from . import logger as logMod
from . import params as prmMod


class SavuRecon:
    """
    Class encapsulating a SavuRecon object
    """

    def __init__(self,
                 project_name,
                 params_in,
                 logger_in,
                 ):
        """
        Initialising a SavuRecon object
        ARGS:
        project_name (str) :: name of current project
        params_in (Params) :: parameters for stack creation
        logger_in (Logger) :: logger object to keep record of progress and errors
        """

        self.proj_name = project_name

        self.pObj = params_in
        self.params = self.pObj.params

        self.logObj = logger_in

        self.md_out = {}

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
        self._path_dict = {}
        for curr_ts in self.params['System']['process_list']:
            subfolder = f"{self.basis_folder}/{self.rootname}_{curr_ts:04d}{self.suffix}"
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
            os.path.basename(self.params['Savu']['setup']['tilt_angles'][i]))[0]

        # Get reconstruction algorithm and check that it is a valid choice
        algo = self.params['Savu']['setup']['algorithm']
        algo_choices = ["FBP_CUDA", "SIRT_CUDA", "SART_CUDA", "CGLS_CUDA", "BP_CUDA", "SIRT3D_CUDA", "CGLS3D_CUDA"]
        if algo not in algo_choices:
            raise ValueError("Algorithm not supported. "
                             f"Please amend algorithm in savurecon.yaml to one of {algo_choices}")

        # Get centre of rotation
        # Set centre of rotation to centre if centre_of_rotation is autocenter
        if self.params['Savu']['setup']['centre_of_rotation'][i] == 'autocenter':
            mrc = mrcfile.open(self.params['Savu']['setup']['aligned_projections'][i])
            cor = float(mrc.header["ny"] / 2)  # ydim/2

        # Else if the centre of rotation is a single value to be used for all ts:
        else:
            try:
                cor = float(self.params['Savu']['setup']['centre_of_rotation'][i])
            except ValueError:
                raise ValueError("Centre of rotation must be 'autocenter' or a float")

        subfolder = os.path.abspath(self.md_out["savu_output_dir"][curr_ts])
        cmd = [
            'add MrcLoader\n',
            'mod 1.2 {}\n'.format(self.params['Savu']['setup']['tilt_angles'][i]),
            'add AstraReconGpu\n',
            'mod 2.1 {}\n'.format(cor),
            'mod 2.2 {}\n'.format(algo),
            'add MrcSaver\n',
            'mod 3.1 VOLUME_YZ\n',
            'save {}/{}_{}.nxs\n'.format(subfolder, ts_name, algo),
            'y\n',
            'exit\n',
            'y\n'
        ]
        if algo in ("SIRT_CUDA", "SART_CUDA", "CGLS_CUDA"):
            cmd.insert(4, "mod 2.2 5\n")

        # Add location of .nxs file to metadata
        if "savu_process_lists" not in list(self.md_out.keys()):
            self.md_out['savu_process_lists'] = {}
        self.md_out['savu_process_lists'][curr_ts] = '{}/{}_{}.nxs'.format(subfolder, ts_name, algo)

        return cmd

    def _create_savurecon_process_list(self, i):
        """
        Method to generate savu_config process lists
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
        # Check that the process list was created with no stderr
        # For some reason, if you call savu_config.communicate in any way at the end of this
        # we don't have the problem of moving on to running process lists before they exist
        if savu_config.communicate()[1] is None:
            print(f"Process list created: {self.md_out['savu_process_lists'][curr_ts]}.")

    def _run_savurecon(self, i):
        """
        Method to run savu process lists
        """
        curr_ts = self.params['System']['process_list'][i]
        # Run savu
        savu_run = subprocess.run(['savu',
                                   self.params['Savu']['setup']['aligned_projections'][i],
                                   self.md_out['savu_process_lists'][curr_ts],
                                   self.md_out['savu_output_dir'][curr_ts]],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  encoding='ascii',
                                  check=True,
                                  )
        print(savu_run.stdout)

    def _dummy_runner(self, i):
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
            self._create_savurecon_process_list(i)
            self._run_savurecon(i)
            # self._dummy_runner(i)
            print(f"Savu reconstruction complete for {self.proj_name}_{curr_ts}")
        self.export_metadata()

    def export_metadata(self):
        """
        Method to export metadata as yaml
        """
        yaml_file = self.proj_name + "_savurecon_mdout.yaml"

        with open(yaml_file, 'w') as f:
            yaml.dump(self.md_out, f, indent=4, sort_keys=False)


"""
PLUGIN METHODS
"""


def create_yaml():
    """
    Subroutine to create new yaml file for Savu reconstruction
    """
    logger = logMod.Logger(log_path="o2r_savu.log")

    # Parse user inputs
    args = mgMod.get_args_savurecon.show(run=True)

    # Create the yaml file, then automatically update it
    prmMod.new_savurecon_yaml(args)
    update_yaml(args)

    logger(message="Savu metadata file created.")


def update_yaml(args):
    """
    Method to update yaml file for savu reconstruction --- if stacks already exist
    Args:
    args (Namespace) :: Namespace containing user inputs
    """
    logger = logMod.Logger(log_path="o2r_savu.log")

    # Check if SavuRecon yaml exists
    savu_yaml_name = args.project_name.value + '_savurecon.yaml'
    if not os.path.isfile(savu_yaml_name):
        logger(level="error",
               message="Savu metadata file not found.")
        raise IOError("Error in Ot2Rec.main.update_savu_yaml: File not found.")    

    parent_path = args.stacks_folder.value
    rootname = args.project_name.value if args.rootname.value is "" else args.rootname.value
    suffix = args.suffix.value
    ext = args.extension.value
    imod_suffix = args.imod_suffix.value

    # Find stack files
    st_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}*_{suffix}{imod_suffix}.{ext}')

    # Find tlt files
    # tlt_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.tlt')
    tlt_file_list = [st_file.replace(f'_{imod_suffix}.{ext}', '.tlt') for st_file in st_file_list]

    # Extract tilt series number
    ts_list = [int(i.split('/')[-1].replace(f'{rootname}_', '').replace(f'_{suffix}{imod_suffix}.{ext}', ''))
               for i in st_file_list]

    # Read in and update YAML parameters
    savu_yaml_name = args.project_name.value + '_savurecon.yaml'
    recon_params = prmMod.read_yaml(project_name=args.project_name.value,
                                    filename=savu_yaml_name)

    recon_params.params['System']['process_list'] = ts_list
    recon_params.params['Savu']['setup']['tilt_angles'] = tlt_file_list
    recon_params.params['Savu']['setup']['aligned_projections'] = st_file_list
    logger(message=f"Search term is {parent_path}/{rootname}_*{suffix}/{rootname}*_{suffix}{imod_suffix}.{ext}")

    # Change centre of rotation to centre of image by default
    centre_of_rotation = []
    for image in recon_params.params['Savu']['setup']['aligned_projections']:
        mrc = mrcfile.open(image)
        centre_of_rotation.append(float(mrc.header["nx"] / 2))  # xdim/2
    recon_params.params['Savu']['setup']['centre_of_rotation'] = centre_of_rotation

    # Set algorithm
    recon_params.params['Savu']['setup']['algorithm'] = args.algorithm.value

    # Write out YAML file
    with open(savu_yaml_name, 'w') as f:
        yaml.dump(recon_params.params, f, indent=4, sort_keys=False)
    logger(message="Savu metadata updated.")


def run():
    """
    Method to run SavuRecon
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    args = parser.parse_args()

    # Check if prerequisite files exist
    savurecon_yaml = args.project_name + '_savurecon.yaml'

    # Read in config and metadata
    savurecon_params = prmMod.read_yaml(project_name=args.project_name,
                                        filename=savurecon_yaml)

    # Create Logger object
    log_path = "./o2r_savurecon.log"
    try:
        os.remove(log_path)
    except:
        pass
    logger = logMod.Logger(log_path=log_path)

    # Create SavuRecon object
    savurecon_obj = SavuRecon(project_name=args.project_name,
                              params_in=savurecon_params,
                              logger_in=logger,
                              )

    # Run Savu
    savurecon_obj.run_savu_all()
