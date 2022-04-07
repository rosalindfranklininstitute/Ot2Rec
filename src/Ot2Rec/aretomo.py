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

from . import align
from . import logger as logMod
from . import params as prmMod
from . import user_args as uaMod


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
        kwargs = self.params["AreTomo_kwargs"].keys()
        for kwarg in kwargs:
            cmd.append(kwarg)
            cmd.append(self.params["AreTomo_kwargs"][kwarg])

        # Add AreTomo command and out_mrc to md_out
        if "aretomo_cmd" not in list(self.md_out.keys()):
            self.md_out["aretomo_cmd"] = {}
        self.md_out["aretomo_cmd"][curr_ts] = " ".join(cmd)

        # Run aretomo
        aretomo_run = subprocess.run(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     encoding='ascii',
                                     check=True,
        )
        print(aretomo_run.stdout)
   

    def run_aretomo_all(self):
        """
        Method to run AreTomo for all ts in process list
        """
        for i, curr_ts in enumerate(self.params['System']['process_list']):
            self._run_aretomo(i)
            print(f"Ran AreTomo on {self.proj_name}_{curr_ts}")
        self.export_metadata()

    
    def export_metadata(self):
        """
        Method to export metadata as yaml
        """

        yaml_file = self.proj_name + "_aretomo_mdout.yaml"

        with open(yaml_file, 'w') as f:
            yaml.dump(self.md_out, f, indent=4, sort_keys=False)


# Plugin functions

def update_yaml(args, kwargs):
    """
    Method to update yaml file for AreTomo

    Args:
    args (Namespace) :: Namespace containing user inputs
    kwargs (list) :: List of extra inputs, used for extra AreTomo arguments
                     beyond those implemented here
    """
    # Read in YAML, set mundane things
    rootname    = args.project_name if args.rootname is None else args.rootname
    suffix      = args.suffix

    aretomo_yaml_names = {0: args.project_name + "_aretomo_align.yaml",
                         1: args.project_name + "_aretomo_recon.yaml",
                         2: args.project_name + "_aretomo_align-recon.yaml"}

    aretomo_yaml_name = aretomo_yaml_names[int(args.aretomo_mode)]
    aretomo_params = prmMod.read_yaml(
        project_name=args.project_name,
        filename=aretomo_yaml_name
    )

    # Check that AreTomo Mode is 0-3
    if (args.aretomo_mode < 0) or (args.aretomo_mode > 3):
        raise ValueError("AreTomo mode must be 0, 1, 2, or 3")

    # Add optional kwargs
    aretomo_params.params['AreTomo_kwargs'] = kwargs
    
    if args.aretomo_mode != 1: # for workflows with alignment
        # Uses align to create the InMrc and AngFile in correct form
        try:
            align.create_yaml([
                args.project_name, 
                str(args.rot_angle),
                '-o',
                args.output_path])
            align.run(
                newstack=True, 
                do_align=False, 
                args_pass=[args.project_name])
            print("Created stacks for input to AreTomo")
        except:
            print("IMOD might not be loaded")
        
        # Set InMrc
        st_file_list = glob(f'{args.output_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.st')
        aretomo_params.params["AreTomo_setup"]["input_mrc"] = st_file_list

        # Set AngFile
        if args.tilt_angles is None:
            tlt_file_list = glob(f'{args.output_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.rawtlt')
        else:
            tlt_file_list = args.tilt_angles
        aretomo_params.params["AreTomo_setup"]["tilt_angles"] = tlt_file_list

        # Set process list
        ts_list = [int(file.split('/')[-1].replace(f'{rootname}_', '').replace(f'{suffix}.st', ''))
                   for file in st_file_list]
        aretomo_params.params["System"]["process_list"] = ts_list
    
    if args.aretomo_mode == 1:
        # Set InMrc
        st_file_list = glob(f'{args.input_mrc_folder}/{rootname}_*{suffix}/{rootname}_*{suffix}_ali.mrc')
        aretomo_params.params["AreTomo_setup"]["input_mrc"] = st_file_list

        # Set process list
        ts_list = [int(file.split('/')[-1].replace(f'{rootname}_', '').replace(f'{suffix}_ali.mrc', ''))
                   for file in st_file_list]
        aretomo_params.params["System"]["process_list"] = ts_list
        
        # Set AngFile
        if args.tilt_angles is None:
            tlt_file_list = glob(f'{args.output_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.tlt')
        else:
            tlt_file_list = args.tilt_angles
        aretomo_params.params["AreTomo_setup"]["tilt_angles"] = tlt_file_list

    # Set OutputMrc
    if args.aretomo_mode == 0:
        out_file_list = [f"{os.path.splitext(file)[0]}_ali.mrc" for file in st_file_list]
    elif args.aretomo_mode > 0:
        out_file_list = [f"{os.path.splitext(file)[0]}_rec.mrc" for file in st_file_list]
    aretomo_params.params["AreTomo_setup"]["output_mrc"] = out_file_list

    # Add the rest of the argparse values to aretomo_params
    aretomo_params.params["AreTomo_setup"]["aretomo_mode"] = args.aretomo_mode
    aretomo_params.params["AreTomo_setup"]["output_binning"] = args.output_binning
    aretomo_params.params["AreTomo_recon"]["volz"] = args.volz
    aretomo_params.params["AreTomo_recon"]["sample_thickness"] = args.sample_thickness
    aretomo_params.params["AreTomo_recon"]["pixel_size"] = args.pixel_size
    aretomo_params.params["AreTomo_recon"]["recon_algo"] = args.recon_algo

    # for workflows with reconstruction, set VolZ unless already overwritten
    if args.aretomo_mode > 0:
        if args.volz == -1:
            if args.sample_thickness < 0:
                raise ValueError("Please set sample thickness in nm to automatically calculate VolZ")
            if args.pixel_size < 0:
                raise ValueError("Please set pixel size in nm to automatically calculate VolZ")
            aretomo_params.params["AreTomo_recon"]["volz"] = int(
                (args.sample_thickness * args.pixel_size) + 200)


    # update and write yaml file
    with open(aretomo_yaml_name, "w") as f:
        yaml.dump(aretomo_params.params, f, indent=4, sort_keys=False)


def create_yaml():
    """
    Subroutine to create new yaml file for AreTomo
    """

    # Parse user inputs
    parser = uaMod.get_args_aretomo()
    args, kwargs = parser.parse_known_args()

    # Create the yaml file, then automatically update it
    prmMod.new_aretomo_yaml(args)
    update_yaml(args, kwargs)


def run():
    """ 
    Method to run AreTomo
    """                 
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("aretomo_mode",
                        type=int,
                        help=
                        "Processes to be run in AreTomo, must be set."
                        " 0: alignment only,"
                        " 1: reconstruction only,"
                        " 2: alignment + reconstruction"
                        )    
    args = parser.parse_args()

    # Check if prerequisite files exist
    aretomo_yaml_names = {0: args.project_name + "_aretomo_align.yaml",
                         1: args.project_name + "_aretomo_recon.yaml",
                         2: args.project_name + "_aretomo_align-recon.yaml"}

    aretomo_yaml_name = aretomo_yaml_names[int(args.aretomo_mode)]
    if not os.path.isfile(aretomo_yaml_name):
        raise IOError("Error in Ot2Rec.main.run_aretomo: AreTomo yaml file not found.")

    # Read in config and metadata
    aretomo_config = prmMod.read_yaml(
        project_name=args.project_name,
        filename=aretomo_yaml_name
    )

    # Create logger object
    logger = logMod.Logger()

    # Create AreTomo object
    aretomo_obj = AreTomo(
        project_name=args.project_name,
        params_in=aretomo_config,
        logger_in=logger
    )

    # Run AreTomo commands
    aretomo_obj.run_aretomo_all()
