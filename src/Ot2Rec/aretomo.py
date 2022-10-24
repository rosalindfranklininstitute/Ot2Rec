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
import warnings
from icecream import ic
from pathlib import Path

import yaml

from . import align
from . import logger as logMod
from . import magicgui as mgMod
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
            subfolder = (f"{self.basis_folder}/"
                         f"{self.rootname}_{curr_ts:04d}{self.suffix}")
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

        if self.params['AreTomo_recon']['recon_algo'] == "WBP":
            # WBP
            cmd.append('-Wbp')
            cmd.append('1')
        elif self.params['AreTomo_recon']['recon_algo'] == "SART":
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

def _update_volz(args, aretomo_params):
    # for workflows with reconstruction, set VolZ unless already overwritten
    args["volz"] = int(args["volz"])
    if args["aretomo_mode"] > 0:
        if args["volz"] == -1:
            if (args["sample_thickness"] <= 0) or (args["pixel_size"] <= 0):
                raise ValueError(
                    f"Please set sample thickness and pixel size \
                    in nm to automatically calculate VolZ. Currently sample_thickness \
                    = {args['sample_thickness']} and pixel_size = {args['pixel_size']}")
            aretomo_params.params["AreTomo_recon"]["volz"] = int(
                (args["sample_thickness"] * args["pixel_size"] * 0.1) + 200   # factor of 0.1 because pixel_size in A
            )

    # Reject volz and sample thickness values which are not -1 or >0
        elif (args["volz"] == 0) or (args["volz"] < -1):
            raise ValueError(
                "VolZ should be at least 1, unless sample thickness and pixel size are set"
            )


def _create_stacks_with_imod(args):
    # Uses align to create the InMrc and AngFile in correct form
        try:
            align.create_yaml([
                args["project_name"],
                str(args["rot_angle"]),
                '-o',
                args["output_path"]])
            align.run(
                newstack=True,
                do_align=False,
                args_pass=[args["project_name"]])
            print("Created stacks for input to AreTomo")
        except:
            print("IMOD might not be loaded")


def _find_files_with_ext(ext, rootname, suffix, directory):
    search_term = (f"{directory}/{rootname}_*{suffix}/"
                   f"{rootname}_*{suffix}{ext}")
    file_list = glob(search_term)

    if len(file_list) == 0:
        warnings.warn(
            f"Files matching {search_term} were not found")

    return file_list


def _get_yaml_filename(aretomo_mode, project_name):
    aretomo_yaml_names = {
        0: f"{project_name}_aretomo_align.yaml",
        1: f"{project_name}_aretomo_recon.yaml",
        2: f"{project_name}_aretomo_align-recon.yaml"
    }
    return aretomo_yaml_names[aretomo_mode]


def _get_process_list(file_list, rootname, suffix, ext):
    ts_list = []
    for st in file_list:
        st_bn = os.path.basename(st)
        if suffix != "":
            ts_list.append(
                int(st_bn.split(f"{rootname}_")[1].split(f"_{suffix}{ext}")[0])
            )
        else:
            ts_list.append(
                int(st_bn.split(f"{rootname}_")[1].split(ext)[0])
            )
    return ts_list

def update_yaml(args):
    """
    Method to update yaml file for AreTomo

    Args:
    args (Namespace) :: Namespace containing user inputs
    kwargs (list) :: List of extra inputs, used for extra AreTomo arguments
                     beyond those implemented here
    """
    # Read in YAML, set mundane things
    if args["rootname"] == "":
        rootname = args["project_name"]
    else:
        rootname = args["rootname"]
    suffix = args["suffix"]

    aretomo_yaml_name = _get_yaml_filename(
        args["aretomo_mode"],
        args["project_name"]
    )

    aretomo_params = prmMod.read_yaml(
        project_name=args["project_name"],
        filename=aretomo_yaml_name
    )

    # Check that AreTomo Mode is 0-3
    if (args["aretomo_mode"] < 0) or (args["aretomo_mode"] > 2):
        raise ValueError("AreTomo mode must be 0, 1, 2")

    # Add optional kwargs TODO: Implement
    # aretomo_params.params['AreTomo_kwargs'] = kwargs

    if args["aretomo_mode"] != 1:  # for workflows with alignment
        # Create input stacks from motioncor images
        _create_stacks_with_imod(args)

        # Set InMrc
        st_file_list = _find_files_with_ext(
            ".st",
            rootname,
            suffix,
            str(args["input_mrc_folder"])
        )
        aretomo_params.params["AreTomo_setup"]["input_mrc"] = st_file_list

        # Set AngFile
        if args["tilt_angles"] == "":
            tlt_file_list = _find_files_with_ext(
                ".rawtlt",
                rootname,
                suffix,
                str(args["input_mrc_folder"])
            )
            aretomo_params.params["AreTomo_setup"]["tilt_angles"] = tlt_file_list
        else:
            tlt_file_list = args["tilt_angles"]
            aretomo_params.params["AreTomo_setup"]["tilt_angles"] = tlt_file_list

        # Set process list
        ts_list = _get_process_list(st_file_list, rootname, suffix, ".st")
        aretomo_params.params["System"]["process_list"] = ts_list

        # Set output mrc
        output_lookup = {0: "_ali.mrc", 2: "_rec.mrc"}
        # out_file_list = [
        #     (f"{os.path.splitext(file)[0]}"
        #      f"{output_lookup[args['aretomo_mode']]}") for file in st_file_list]
        out_file_list = [
            (f"{aretomo_params.params['System']['output_path']}/"
             f"{os.path.splitext(os.path.basename(file))[0]}/"
             f"{os.path.splitext(os.path.basename(file))[0]}"
             f"{output_lookup[args['aretomo_mode']]}") for file in st_file_list
        ]


        aretomo_params.params["AreTomo_setup"]["output_mrc"] = out_file_list

    elif args["aretomo_mode"] == 1: # for reconstruction only
        # Set InMrc
        st_file_list = _find_files_with_ext(
            "_ali.mrc",
            rootname,
            suffix,
            str(args["input_mrc_folder"])
        )
        aretomo_params.params["AreTomo_setup"]["input_mrc"] = st_file_list

        # Set AngFile
        if args["tilt_angles"] == "":
            tlt_file_list = _find_files_with_ext(
                ".tlt",
                rootname,
                suffix,
                str(args["input_mrc_folder"])
            )
            aretomo_params.params["AreTomo_setup"]["tilt_angles"] = tlt_file_list
        else:
            tlt_file_list = args["tilt_angles"]
        aretomo_params.params["AreTomo_setup"]["tilt_angles"] = tlt_file_list

        # Set process list
        ts_list = _get_process_list(st_file_list, rootname, suffix, "_ali.mrc")
        aretomo_params.params["System"]["process_list"] = ts_list

        # Set output mrc
        out_file_list = [
            f"{os.path.splitext(file)[0]}_rec.mrc" for file in st_file_list
        ]
        aretomo_params.params["AreTomo_setup"]["output_mrc"] = out_file_list

    # Add the rest of the argparse values to aretomo_params
    aretomo_params.params["AreTomo_setup"]["aretomo_mode"] = args["aretomo_mode"]
    aretomo_params.params["AreTomo_setup"]["output_binning"] = args["output_binning"]
    aretomo_params.params["AreTomo_recon"]["volz"] = args["volz"]
    aretomo_params.params["AreTomo_recon"]["sample_thickness"] = args["sample_thickness"]
    aretomo_params.params["AreTomo_recon"]["pixel_size"] = args["pixel_size"]
    aretomo_params.params["AreTomo_recon"]["recon_algo"] = args["recon_algo"]

    _update_volz(args, aretomo_params)

    # update and write yaml file
    with open(Path(aretomo_yaml_name), "w") as f:
        yaml.dump(aretomo_params.params, f, indent=4, sort_keys=False)


def create_yaml(input_mgNS=None):
    """
    Subroutine to create new yaml file for AreTomo
    """

    # Parse user inputs
    if input_mgNS is None:
        args = mgMod.get_args_aretomo.show(run=True).asdict()
    else:
        args = input_mgNS

    # Create the yaml file, then automatically update it
    prmMod.new_aretomo_yaml(args)
    update_yaml(args)


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
                        help="Processes to be run in AreTomo, must be set."
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
