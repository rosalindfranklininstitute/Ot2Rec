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
import sys
from glob import glob

import yaml

from . import logger as logMod
from . import metadata as mdMod
from . import params as prmMod
from . import user_args as uaMod


def get_proj_name():
    """
    Function to get project name from user
    """

    project_name = sys.argv[1]
    # Check input validity
    for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        if project_name.find(char) != -1:
            raise ValueError(f"Error in Ot2Rec.main.new_proj: Illegal character ({char}) found in input project name.")

    return project_name


def new_proj():
    """
    Method to create a new project and get master metadata from raw images
    """
    # Parse user inputs
    parser = uaMod.get_args_new_proj()
    args = parser.parse_args()
    
    # Create master yaml config file
    prmMod.new_master_yaml(args)

    # Create empty Metadata object
    # Master yaml file will be read automatically
    meta = mdMod.Metadata(project_name=args.project_name,
                          job_type='master')

    # Create master metadata and serialise it as yaml file
    meta.create_master_metadata()
    if not args.no_mdoc:
        meta.get_mc2_temp()

    master_md_name = args.project_name + '_master_md.yaml'
    with open(master_md_name, 'w') as f:
        yaml.dump(meta.metadata, f, indent=4)


def cleanup():
    """
    Method to clean up project folder to save space
    """

    project_name = get_proj_name()

    mc2_yaml = project_name + '_mc2.yaml'
    recon_yaml = project_name + '_recon.yaml'

    # Create Logger object
    logger = logMod.Logger()

    if os.path.isfile(mc2_yaml):
        mc2_config = prmMod.read_yaml(project_name=project_name,
                                      filename=mc2_yaml)
        mc2_path = mc2_config.params['System']['output_path']
        if os.path.isdir(mc2_path):
            logger(f"Deleting {mc2_path} folder and its contents...")
            cmd = ['rm', '-rf', mc2_path]
            del_mc2 = subprocess.run(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

    if os.path.isfile(recon_yaml):
        recon_config = prmMod.read_yaml(project_name=project_name,
                                        filename=recon_yaml)
        recon_path = recon_config.params['System']['output_path']
        if os.path.isdir(recon_path):
            logger(f"Deleting intermediary IMOD files...")
            files = glob(recon_path + 'stack*/*.*~') + \
                glob(recon_path + 'stack*/*_full_rec.*')
            cmd = ['rm', *files]
            del_recon = subprocess.run(cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)


def run_all():
    """
    Method to run all four processes in one go using default settings.
    """

    logger = logMod.Logger()

    # Collect raw images and produce master metadata
    logger("Collecting raw images...")
    get_master_metadata()

    # Motion correction
    logger("Motion correction in progress...")
    create_mc2_yaml()
    run_mc2()

    # CTF estimation
    logger("CTF estimation in progress...")
    create_ctffind_yaml()
    run_ctffind()

    # Alignment
    logger("Alignment in progress...")
    create_align_yaml()
    run_align()

    # Reconstruction
    logger("Reconstruction in progress...")
    create_recon_yaml()
    run_recon()


def update_aretomo_yaml(args, kwargs):
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

    aretomo_yaml_name = args.project_name + "_aretomo.yaml"
    aretomo_params = prmMod.read_yaml(
        project_name=args.project_name,
        filename=aretomo_yaml_name
    )

    # Check that AreTomo Mode is 0-3
    if (args.aretomo_mode < 0) or (args.aretomo_mode > 3):
        raise ValueError("AreTomo mode must be 0, 1, 2, or 3")

    # Add optional kwargs
    for param in kwargs:
        aretomo_params.params["AreTomo_kwargs"][param] = vars(args).get(param)


    # Uses align to create the InMrc and AngFile in correct form
    create_align_yaml([
        args.project_name, 
        str(args.rot_angle),
        '-o',
        args.output_path])
    run_align(full_align=False, args_to_pass=[args.project_name])
    print("Created stacks for input to AreTomo")
    
    # Set InMrc
    st_file_list = glob(f'{args.output_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.st')
    aretomo_params.params["AreTomo_setup"]["input_mrc"] = st_file_list

    # Set AngFile
    tlt_file_list = glob(f'{args.output_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.rawtlt')
    aretomo_params.params["AreTomo_setup"]["tilt_angles"] = tlt_file_list

    # Set OutputMrc
    if args.aretomo_mode == 0:
        out_file_list = ["{}_ali.mrc".format(os.path.splitext(file)[0]) for file in st_file_list]
    elif args.aretomo_mode > 0:
        out_file_list = ["{}_rec.mrc".format(os.path.splitext(file)[0]) for file in st_file_list]
    aretomo_params.params["AreTomo_setup"]["output_mrc"] = out_file_list

    # Set process list
    ts_list = [int(file.split('/')[-1].replace(f'{rootname}_', '').replace(f'{suffix}.st', '')) for file in st_file_list]
    aretomo_params.params["System"]["process_list"] = ts_list

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


def create_aretomo_yaml():
    """
    Subroutine to create new yaml file for AreTomo
    """

    # Parse user inputs
    parser, kwargs = uaMod.get_args_aretomo()
    args = parser.parse_args()

    # Create the yaml file, then automatically update it
    prmMod.new_aretomo_yaml(args)
    update_aretomo_yaml(args, kwargs)


def run_aretomo():
    """ 
    Method to run AreTomo
    """                 
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")    
    args = parser.parse_args()

    # Check if prerequisite files exist
    aretomo_yaml = args.project_name + "_aretomo.yaml"
    if not os.path.isfile(aretomo_yaml):
        raise IOError("Error in Ot2Rec.main.run_aretomo: AreTomo yaml file not found.")

    # Read in config and metadata
    aretomo_config = prmMod.read_yaml(
        project_name=args.project_name,
        filename=aretomo_yaml
    )

    # Create logger object
    logger = logMod.Logger()

    # Create AreTomo object
    aretomo_obj = aretomoMod.AreTomo(
        project_name=args.project_name,
        params_in=aretomo_config,
        logger_in=logger
    )

    # Run AreTomo commands
    aretomo_obj.run_aretomo_all()
