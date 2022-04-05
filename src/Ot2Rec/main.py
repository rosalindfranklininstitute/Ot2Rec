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


import sys
import os
import argparse
from glob import glob, glob1
import yaml
import pandas as pd
from icecream import ic
from beautifultable import BeautifulTable as bt
from tqdm import tqdm
import skimage.transform as skt

import re
import subprocess
import numpy as np
import mrcfile

from . import user_args as uaMod
from . import params as prmMod
from . import metadata as mdMod
from . import motioncorr as mc2Mod
from . import logger as logMod
from . import ctffind as ctfMod
from . import align as alignMod
from . import recon as reconMod
from . import ctfsim as ctfsimMod
from . import savurecon as savuMod
from . import rlf_deconv as rlfMod


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


def update_recon_yaml(args):
    """
    Subroutine to update yaml file for IMOD reconstruction

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """
    # Check if recon and align yaml files exist
    recon_yaml_name = args.project_name + '_recon.yaml'
    align_yaml_name = args.project_name + '_align.yaml'
    if not os.path.isfile(recon_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_recon_yaml: reconstruction config file not found.")
    if not os.path.isfile(align_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_recon_yaml: alignment config file not found.")

    # Read in alignment metadata (as Pandas dataframe)
    align_md_name = args.project_name + '_align_mdout.yaml'
    with open(align_md_name, 'r') as f:
        align_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]

    # Read in previous alignment output metadata (as Pandas dataframe) for old projects
    recon_md_name = args.project_name + '_recon_mdout.yaml'
    if os.path.isfile(recon_md_name):
        is_old_project = True
        with open(recon_md_name, 'r') as f:
            recon_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]
    else:
        is_old_project = False

    # Diff the two dataframes to get numbers of tilt-series with unprocessed data
    if is_old_project:
        merged_md = align_md.merge(recon_md,
                                   how='outer',
                                   indicator=True)
        unprocessed_images = merged_md.loc[lambda x: x['_merge']=='left_only']
    else:
        unprocessed_images = align_md
    unique_ts_numbers = unprocessed_images['ts'].sort_values(ascending=True).unique().tolist()

    # Read in reconstruction yaml file, modify, and update
    # read in alignment yaml as well (some parameters depend on alignment settings)
    recon_params = prmMod.read_yaml(project_name=args.project_name,
                                    filename=recon_yaml_name)
    align_params = prmMod.read_yaml(project_name=args.project_name,
                                  filename=align_yaml_name)

    recon_params.params['System']['output_rootname'] = align_params.params['System']['output_rootname']
    recon_params.params['System']['output_suffix'] = align_params.params['System']['output_suffix']
    recon_params.params['System']['process_list'] = unique_ts_numbers

    recon_params.params['BatchRunTomo']['setup'] = {key: value for key, value in align_params.params['BatchRunTomo']['setup'].items() \
                                                    if key != 'stack_bin_factor'}
    
    with open(recon_yaml_name, 'w') as f:
        yaml.dump(recon_params.params, f, indent=4, sort_keys=False)


def create_recon_yaml():
    """
    Subroutine to create new yaml file for IMOD reconstruction
    """
    # Parse user inputs
    parser = uaMod.get_args_recon()
    args = parser.parse_args()
    
    # Create the yaml file, then automatically update it
    prmMod.new_recon_yaml(args)
    update_recon_yaml(args)


def run_recon():
    """
    Method to run IMOD reconstruction
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")

    args = parser.parse_args()

    # Check if prerequisite files exist
    recon_yaml = args.project_name + '_recon.yaml'
    align_md_file = args.project_name + '_align_mdout.yaml'

    # Read in config and metadata
    recon_config = prmMod.read_yaml(project_name=args.project_name,
                                    filename=recon_yaml)
    align_md = mdMod.read_md_yaml(project_name=args.project_name,
                                  job_type='reconstruct',
                                  filename=align_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create Recon object
    recon_obj = reconMod.Recon(project_name=args.project_name,
                               md_in=align_md,
                               params_in=recon_config,
                               logger_in=logger,
    )

    # Run IMOD
    if not recon_obj.no_processes:
        recon_obj.recon_stack()


def run_savurecon():
    project_name = get_proj_name()

    # Check if prerequisite files exist
    savurecon_yaml = project_name + '_savurecon.yaml'

    # Read in config and metadata
    savurecon_params = prmMod.read_yaml(project_name=project_name,
                                        filename=savurecon_yaml)

    # Create Logger object
    logger = logMod.Logger()

    # Create SavuRecon object
    savurecon_obj = savuMod.SavuRecon(project_name=project_name,
                                  params_in=savurecon_params,
                                  logger_in=logger,
                                 )

    # Run Savu
    savurecon_obj.run_savu_all()


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


def update_savurecon_yaml(args):
    """
    Method to update yaml file for savu reconstruction --- if stacks already exist

    Args:
    args (Namespace) :: Namespace containing user inputs
    """

    parent_path = args.stacks_folder
    rootname    = args.project_name if args.rootname is None else args.rootname
    suffix      = args.suffix
    ext         = args.extension
    imod_suffix = args.imod_suffix
    
    # Find stack files
    st_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}*_{suffix}{imod_suffix}.{ext}')

    # Find rawtlt files
    rawtlt_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.rawtlt')

    # Extract tilt series number
    ts_list = [int(i.split('/')[-1].replace(f'{rootname}_', '').replace(f'_{suffix}{imod_suffix}.{ext}', '')) for i in st_file_list]

    # Read in and update YAML parameters
    recon_yaml_name = args.project_name + '_savurecon.yaml'
    recon_params = prmMod.read_yaml(project_name=args.project_name,
                                    filename=recon_yaml_name)

    recon_params.params['System']['process_list'] = ts_list
    recon_params.params['Savu']['setup']['tilt_angles'] = rawtlt_file_list
    recon_params.params['Savu']['setup']['aligned_projections'] = st_file_list

    # Change centre of rotation to centre of image by default
    centre_of_rotation = []
    for image in recon_params.params['Savu']['setup']['aligned_projections']:
        mrc = mrcfile.open(image)
        centre_of_rotation.append(float(mrc.header["nx"]/2)) # xdim/2
    recon_params.params['Savu']['setup']['centre_of_rotation'] = centre_of_rotation

    # Write out YAML file
    with open(recon_yaml_name, 'w') as f:
        yaml.dump(recon_params.params, f, indent=4, sort_keys=False)


def create_savurecon_yaml():
    """
    Subroutine to create new yaml file for Savu reconstruction
    """

    # Parse user inputs
    parser = uaMod.get_args_savurecon()
    args = parser.parse_args()

    # Create the yaml file, then automatically update it
    prmMod.new_savurecon_yaml(args)
    update_savurecon_yaml(args)


def run_recon_ext():
    """
    Method to run IMOD reconstruction
    """

    project_name = get_proj_name()

    # Check if prerequisite files exist
    recon_yaml = project_name + '_recon.yaml'

    # Read in config and metadata
    recon_config = prmMod.read_yaml(project_name=project_name,
                                    filename=recon_yaml)

    # Create Logger object
    logger = logMod.Logger()

    # Create Align object
    recon_obj = reconMod.Recon(project_name=project_name,
                               md_in=None,
                               params_in=recon_config,
                               logger_in=logger,
    )

    # Run IMOD
    if not recon_obj.no_processes:
        recon_obj.recon_stack(ext=True)


def run_rlf_deconv():
    """
    Method to deconvolve image using a given kernel (point-spread function)
    """
    # Parse user inputs
    parser = uaMod.get_args_rldeconv()
    args = parser.parse_args()

    # Create logger object
    logger = logMod.Logger()
    
    # Check provided files are present
    try:
        assert (len(glob(args.image_path)) > 0)
    except:
        logger("Error in main:run_rlf_deconv: Raw image doesn't exist. Aborting...")
        return

    try:
        assert (len(glob(args.psf_path)) > 0)
    except:
        logger("Error in main:run_rlf_deconv: PSF image doesn't exist. Aborting...")
        return

    # Define deconvolution parameters and object
    deconv_params = dict({
        'method': args.device,
        'niter': args.niter,
        'useBlockAlgorithm': args.block,
        'callbkTickFunc': True,
        'resAsUint8': args.uint,
    })

    my_deconv = rlfMod.RLF_deconv(orig_path=args.image_path,
                                  kernel_path=args.psf_path,
                                  params_dict=deconv_params,
                                  orig_mrc=args.image_type=='mrc',
                                  kernel_mrc=args.psf_type=='mrc')

    deconvd_image = my_deconv()
    
    # Save results
    with mrcfile.new(args.output_path, overwrite=True) as f:
        f.set_data(deconvd_image)

    
