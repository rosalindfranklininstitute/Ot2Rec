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

from Ot2Rec import params as prmMod
from Ot2Rec import metadata as mdMod
from Ot2Rec import motioncorr as mc2Mod
from Ot2Rec import logger as logMod
from Ot2Rec import ctffind as ctfMod
from Ot2Rec import align as alignMod
from Ot2Rec import recon as reconMod
from Ot2Rec import ctfsim as ctfsimMod
from Ot2Rec import savurecon as savuMod
from Ot2Rec import rlf_deconv as rlfMod
from Ot2Rec import user_args as uaMod


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


def update_mc2_yaml(args):
    """
    Subroutine to update yaml file for motioncorr

    ARGS:
    args (Namespace) :: Arguments obtained from user
    """

    # Check if MC2 yaml exists
    mc2_yaml_name = args.project_name + '_mc2.yaml'
    if not os.path.isfile(mc2_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_mc2_yaml: File not found.")

    # Read in master yaml
    master_yaml = args.project_name + '_proj.yaml'
    with open(master_yaml, 'r') as f:
        master_config = yaml.load(f, Loader=yaml.FullLoader)

    # Read in master metadata (as Pandas dataframe)
    master_md_name = args.project_name + '_master_md.yaml'
    with open(master_md_name, 'r') as f:
        master_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]

    # Read in previous MC2 output metadata (as Pandas dataframe) for old projects
    mc2_md_name = args.project_name + '_mc2_md.yaml'
    if os.path.isfile(mc2_md_name):
        is_old_project = True
        with open(mc2_md_name, 'r') as f:
            mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]
    else:
        is_old_project = False

    # Diff the two dataframes to get numbers of tilt-series with unprocessed data
    if is_old_project:
        merged_md = master_md.merge(mc2_md,
                                    how='outer',
                                    indicator=True)
        unprocessed_images = merged_md.loc[lambda x: x['_merge']=='left_only']
    else:
        unprocessed_images = master_md

    unique_ts_numbers = unprocessed_images['ts'].sort_values(ascending=True).unique().tolist()

    # Read in MC2 yaml file, modify, and update
    mc2_params = prmMod.read_yaml(project_name=args.project_name,
                                  filename=mc2_yaml_name)
    mc2_params.params['System']['process_list'] = unique_ts_numbers
    mc2_params.params['System']['filetype'] = master_config['filetype']

    with open(mc2_yaml_name, 'w') as f:
        yaml.dump(mc2_params.params, f, indent=4, sort_keys=False)


def create_mc2_yaml():
    """
    Subroutine to create new yaml file for motioncorr
    """

    # Parse user inputs
    parser = uaMod.get_args_mc2()
    args = parser.parse_args()

    # Create the yaml file, then automatically update it
    prmMod.new_mc2_yaml(args)
    update_mc2_yaml(args)


def run_mc2():
    """
    Method to run motioncorr
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    args = parser.parse_args()

    # Check if prerequisite files exist
    mc2_yaml = args.project_name + '_mc2.yaml'
    master_md_file = args.project_name + '_master_md.yaml'

    if not os.path.isfile(mc2_yaml):
        raise IOError("Error in Ot2Rec.main.run_mc2: MC2 yaml config not found.")
    if not os.path.isfile(master_md_file):
        raise IOError("Error in Ot2Rec.main.run_mc2: Master metadata not found.")

    # Read in config and metadata
    mc2_config = prmMod.read_yaml(project_name=args.project_name,
                                  filename=mc2_yaml)
    master_md = mdMod.read_md_yaml(project_name=args.project_name,
                                   job_type='motioncorr',
                                   filename=master_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create Motioncorr object
    mc2_obj = mc2Mod.Motioncorr(project_name=args.project_name,
                                mc2_params=mc2_config,
                                md_in=master_md,
                                logger=logger
    )

    if not mc2_obj.no_processes:
        # Run MC2 recursively (and update input/output metadata) until nothing is left in the input metadata list
        mc2_obj.run_mc2()

        # Once all specified images are processed, export output metadata
        mc2_obj.export_metadata()


def update_ctffind_yaml(args):
    """
    Subroutine to update yaml file for ctffind

    ARGS:
    args (Namespace) :: Arguments obtained from user
    """
    # Check if ctffind and motioncorr yaml files exist
    ctf_yaml_name = args.project_name + '_ctffind.yaml'
    mc2_yaml_name = args.project_name + '_mc2.yaml'
    if not os.path.isfile(ctf_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_ctffind_yaml: ctffind config file not found.")
    if not os.path.isfile(mc2_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_ctffind_yaml: motioncorr config file not found.")

    # Read in MC2 metadata (as Pandas dataframe)
    # We only need the TS number and the tilt angle for comparisons at this stage
    mc2_md_name = args.project_name + '_mc2_mdout.yaml'
    with open(mc2_md_name, 'r') as f:
        mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]

    # Read in previous ctffind output metadata (as Pandas dataframe) for old projects
    ctf_md_name = args.project_name + '_ctffind_mdout.yaml'
    if os.path.isfile(ctf_md_name):
        is_old_project = True
        with open(ctf_md_name, 'r') as f:
            ctf_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]
    else:
        is_old_project = False

    # Diff the two dataframes to get numbers of tilt-series with unprocessed data
    if is_old_project:
        merged_md = mc2_md.merge(ctf_md,
                                 how='outer',
                                 indicator=True)
        unprocessed_images = merged_md.loc[lambda x: x['_merge']=='left_only']
    else:
        unprocessed_images = mc2_md

    unique_ts_numbers = unprocessed_images['ts'].sort_values(ascending=True).unique().tolist()

    # Read in ctffind yaml file, modify, and update
    # read in MC2 yaml as well (some parameters depend on MC2 settings)
    ctf_params = prmMod.read_yaml(project_name=args.project_name,
                                  filename=ctf_yaml_name)
    mc2_params = prmMod.read_yaml(project_name=args.project_name,
                                  filename=mc2_yaml_name)

    ctf_params.params['System']['process_list'] = unique_ts_numbers
    ctf_params.params['ctffind']['pixel_size'] = mc2_params.params['MC2']['desired_pixel_size']

    with open(ctf_yaml_name, 'w') as f:
        yaml.dump(ctf_params.params, f, indent=4, sort_keys=False)


def create_ctffind_yaml():
    """
    Subroutine to create new yaml file for ctffind
    """
    # Parse user inputs
    parser = uaMod.get_args_ctffind()
    args = parser.parse_args()

    # Create the yaml file, then automatically update it
    prmMod.new_ctffind_yaml(args)
    update_ctffind_yaml(args)


def run_ctffind():
    """
    Method to run ctffind
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")

    args = parser.parse_args()

    # Check if prerequisite files exist
    ctffind_yaml = args.project_name + '_ctffind.yaml'
    mc2_md_file = args.project_name + '_mc2_mdout.yaml'

    if not os.path.isfile(ctffind_yaml):
        raise IOError("Error in Ot2Rec.main.run_ctffind: ctffind yaml config not found.")
    if not os.path.isfile(mc2_md_file):
        raise IOError("Error in Ot2Rec.main.run_ctffind: MC2 output metadata not found.")

    # Read in config and metadata
    ctffind_config = prmMod.read_yaml(project_name=args.project_name,
                                      filename=ctffind_yaml)
    mc2_md = mdMod.read_md_yaml(project_name=args.project_name,
                                job_type='ctffind',
                                filename=mc2_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create ctffind object
    ctffind_obj = ctfMod.ctffind(project_name=args.project_name,
                                 md_in=mc2_md,
                                 params_in=ctffind_config,
                                 logger_in=logger,
    )

    if not ctffind_obj.no_processes:
        ctffind_obj.run_ctffind()


def update_align_yaml(args):
    """
    Subroutine to update yaml file for IMOD newstack / alignment

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """

    # Check if align and motioncorr yaml files exist
    align_yaml_name = args.project_name + '_align.yaml'
    mc2_yaml_name = args.project_name + '_mc2.yaml'
    if not os.path.isfile(align_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_align_yaml: alignment config file not found.")
    if not os.path.isfile(mc2_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_align_yaml: motioncorr config file not found.")

    # Read in MC2 metadata (as Pandas dataframe)
    # We only need the TS number and the tilt angle for comparisons at this stage
    mc2_md_name = args.project_name + '_mc2_mdout.yaml'
    with open(mc2_md_name, 'r') as f:
        mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]

    # Read in previous alignment output metadata (as Pandas dataframe) for old projects
    align_md_name = args.project_name + '_align_mdout.yaml'
    if os.path.isfile(align_md_name):
        is_old_project = True
        with open(align_md_name, 'r') as f:
            align_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]
    else:
        is_old_project = False

    # Diff the two dataframes to get numbers of tilt-series with unprocessed data
    if is_old_project:
        merged_md = mc2_md.merge(align_md,
                                 how='outer',
                                 indicator=True)
        unprocessed_images = merged_md.loc[lambda x: x['_merge']=='left_only']
    else:
        unprocessed_images = mc2_md

    unique_ts_numbers = unprocessed_images['ts'].sort_values(ascending=True).unique().tolist()

    # Read in ctffind yaml file, modify, and update
    # read in MC2 yaml as well (some parameters depend on MC2 settings)
    align_params = prmMod.read_yaml(project_name=args.project_name,
                                    filename=align_yaml_name)
    mc2_params = prmMod.read_yaml(project_name=args.project_name,
                                  filename=mc2_yaml_name)

    align_params.params['System']['process_list'] = unique_ts_numbers
    align_params.params['BatchRunTomo']['setup']['pixel_size'] = mc2_params.params['MC2']['desired_pixel_size'] * 0.1

    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_params.params, f, indent=4, sort_keys=False)


def create_align_yaml():
    """
    Subroutine to create new yaml file for IMOD newstack / alignment
    """
    # Parse user inputs
    parser = uaMod.get_args_align()
    args = parser.parse_args()
    
    # Create the yaml file, then automatically update it
    prmMod.new_align_yaml(args)
    update_align_yaml(args)

    
def update_align_yaml_stacked():
    """
    Method to update yaml file for IMOD newstack / alignment --- if stacks already exist
    """

    # Parse user inputs
    parser = uaMod.get_args_align_ext()
    args = parser.parse_args()

    project_name = args.project_name
    parnet_path = args.parent_path
    assert (os.path.isdir(parent_path)), \
        "Error in main.update_align_yaml_stacked: IMOD parent folder not found."
    while parent_path.endswith('/'):
        parent_path = parent_path[:-1]
    
    rootname = project_name
    if args.rootname is not None:
        while args.rootname.endswith('/'):
            rootname = args.rootname[:-1]

    pixel_size = args.pixel_res
    suffix = args.suffix if args.suffix is not None else ''
    
    
    # Find stack files
    st_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.st')

    # Extract tilt series number
    ts_list = [int(i.split('/')[-1].replace(f'{rootname}_', '').replace(f'{suffix}.st', '')) for i in st_file_list]

    # Read in and update YAML parameters
    align_yaml_name = project_name + '_align.yaml'
    align_params = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml_name)

    align_params.params['System']['output_path'] = parent_path
    align_params.params['System']['output_rootname'] = rootname
    align_params.params['System']['output_suffix'] = suffix
    align_params.params['System']['process_list'] = ts_list
    align_params.params['BatchRunTomo']['setup']['pixel_size'] = float(pixel_size) * 0.1

    # Write out YAML file
    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_params.params, f, indent=4, sort_keys=False)


def create_align_yaml_stacked():
    """
    Subroutine to create new yaml file for IMOD newstack / alignment
    prestack (bool) :: if stacks already exist
    """

    project_name = get_proj_name()

    # Create the yaml file, then automatically update it
    prmMod.new_align_yaml(project_name)
    update_align_yaml_stacked()


def create_stacks():
    """
    Method to only create stacks using IMOD but omit alignment.
    Separated from the rest of alignment so users can continue processing with other program.
    """
    run_align(full_align=False)


def run_align(full_align=True):
    """
    Method to run IMOD newstack / alignment
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")

    args = parser.parse_args()

    # Check if prerequisite files exist
    align_yaml = args.project_name + '_align.yaml'
    mc2_md_file = args.project_name + '_mc2_mdout.yaml'

    # Read in config and metadata
    align_config = prmMod.read_yaml(project_name=args.project_name,
                                    filename=align_yaml)
    mc2_md = mdMod.read_md_yaml(project_name=args.project_name,
                                job_type='align',
                                filename=mc2_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create Align object
    align_obj = alignMod.Align(project_name=args.project_name,
                               md_in=mc2_md,
                               params_in=align_config,
                               logger_in=logger,
    )

    # Run IMOD
    # Create the stacks and rawtlt files first
    if not align_obj.no_processes:
        align_obj.create_stack_folders()
        align_obj.create_rawtlt()
        align_obj.create_stack()
        if full_align:
            align_obj.align_stack()


def run_align_ext():
    """
    Method to run IMOD alignment with existing stacks
    """

    project_name = get_proj_name()

    # Check if prerequisite files exist
    align_yaml = project_name + '_align.yaml'

    # Read in config and metadata
    align_config = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml)

    # Create Logger object
    logger = logMod.Logger()

    # Create Align object
    align_obj = alignMod.Align(project_name=project_name,
                               md_in=None,
                               params_in=align_config,
                               logger_in=logger,
    )

    # Run IMOD
    # Create the stacks and rawtlt files first
    if not align_obj.no_processes:
        align_obj.align_stack(ext=True)


def get_align_stats():
    """
    Method to extract statistics from alignment
    """

    project_name = get_proj_name()

    # Check if align metadata file exists
    align_md_name = project_name + '_align_mdout.yaml'
    if not os.path.isfile(align_md_name):
        raise IOError("Error in Ot2Rec.main.get_align_stats: alignment metadata file not found.")

    # Get stacks folder path from config
    align_yaml = project_name + '_align.yaml'
    align_config = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml)

    folder_path = align_config.params['System']['output_path']
    while folder_path.endswith('/'):
        folder_path = folder_path[:-1]

    rootname = align_config.params['System']['output_rootname']
    while rootname.endswith('_'):
        rootname = rootname[:-1]

    suffix = align_config.params['System']['output_suffix']

    # Read metadata to extract aligned TS numbers
    with open(align_md_name, 'r') as f:
        aligned_ts = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))['ts'].values.tolist()

    # Create pandas dataframe
    stats_df = pd.DataFrame(
        {'Tilt series': [],
         'Error mean (nm)': [],
         'Error SD (nm)': [],
         'Error weighted mean (nm)': [],
         }
    )

    # Loop through folders, find data and append to dataframe
    for curr_ts in aligned_ts:
        target_file_path = f"{folder_path}/{rootname}_{curr_ts:02d}{suffix}/align.log"
        if not os.path.isfile(target_file_path):
            raise IOError("Error in Ot2Rec.main.get_align_stats: alignment log file not found.")

        with open(target_file_path, 'r') as f:
            lines = f.readlines()

        mean_sd_criterion = re.compile('^\s*Residual error mean')
        filtered = list(filter(mean_sd_criterion.match, lines))
        filter_split = re.split('\s+', filtered[0])

        get_mean_sd = re.compile('[0-9]+.[0-9]+')
        mean = float(list(filter(get_mean_sd.match, filter_split))[0])
        sd = float(list(filter(get_mean_sd.match, filter_split))[1])

        weighted_mean_criterion = re.compile('^\s*Residual error weighted mean')
        filtered = list(filter(weighted_mean_criterion.match, lines))
        filter_split = re.split('\s+', filtered[0])

        get_weighted_crit = re.compile('[0-9]+.[0-9]+')
        weighted_error = float(list(filter(get_weighted_crit.match, filter_split))[0])

        stats_df.loc[len(stats_df.index)] = [curr_ts, mean, sd, weighted_error]

    stats_df.sort_values(by='Error weighted mean (nm)',
                         inplace=True)

    # Create table object and append data from dataframe
    stats = bt()
    stats.columns.headers = ['Tilt series', 'Error mean (nm)', 'Error SD (nm)', 'Error weighted mean (nm)']
    stats.rows.append(stats.columns.headers)
    for i in stats_df.values.tolist():
        stats.rows.append([int(i[0]), *i[1:]])

    # Print out stats
    print(stats)


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
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("stacks_folder",
                        type=str,
                        help="Path to parent folder with stacks")
    parser.add_argument("-rn", "--rootname",
                        type=str,
                        help="Rootname of current project (required if different from project name)")
    parser.add_argument("-s", "--suffix",
                        type=str,
                        default='',
                        help="Suffix of project files")
    parser.add_argument("-e", "--extension",
                        type=str,
                        default='mrc',
                        help="File extension of stacks (Default: mrc)")
    parser.add_argument("-is", "--imod_suffix",
                        type=str,
                        default='',
                        help="IMOD file suffix")
    parser.add_argument("-o", "--output_path",
                        type=str,
                        default="./savurecon/",
                        help="Path to output folder (Default: ./savurecon/)")

    args = parser.parse_args()

    # Create the yaml file, then automatically update it
    prmMod.new_savurecon_yaml(args)
    update_savurecon_yaml(args)


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


def run_ctfsim():
    """
    Method to run simulator for CTF from CTFFIND4 outputs
    """

    # Parse user inputs
    parser = uaMod.get_args_ctfsim()
    args = parser.parse_args()

    project_name = args.project_name
    rootname = project_name
    if args.rootname is not None:
        while args.rootname.endswith('/'):
            rootname = args.rootname[:-1]

    pixel_size = args.pixel_res * 1e-10
    ds_factor = args.ds_factor

    # Read in metadata from ctffind
    ctffind_md_file = project_name + '_ctffind_mdout.yaml'
    ctffind_obj = mdMod.read_md_yaml(project_name=project_name,
                                    job_type='ctfsim',
                                    filename=ctffind_md_file)
    ctffind_md = pd.DataFrame(ctffind_obj.metadata)

    # Read image to get dimensions
    sample_image = ctffind_md.iloc[0].file_paths
    with mrcfile.open(sample_image) as source:
        source_dim = skt.downscale_local_mean(source.data, (ds_factor, ds_factor)).shape

    # Generate point source
    ps = np.zeros(source_dim[-2:], dtype=np.float32)
    ps[ps.shape[0]//2, ps.shape[1]//2] = 1
    ps_k = np.fft.fft2(ps).astype(np.cdouble)

    # Calculate the grids in reciprocal space
    k2_grid, alpha_g_grid = ctfsimMod.calculate_k_grids(source_dim, pixel_size*ds_factor)

    # Grab tilt series numbers and tilt angles from metadata
    ts_list = sorted(pd.Series(ctffind_md['ts']).unique())
    tqdm_iter = tqdm(ts_list, ncols=100)

    for curr_ts in tqdm_iter:
        # Create folders and subfolders
        subfolder_path = f'PSF/{rootname}_{curr_ts:02}'
        os.makedirs(subfolder_path, exist_ok=True)

        # Find txt files from ctffind
        glob_list = glob1('./ctffind/', f'{rootname}_{curr_ts:03}_*ctffind.txt')

        angle_list = [float(i.split('/')[-1].split('_')[2]) for i in glob_list]
        angle_index = [sorted(angle_list).index(i) for i in angle_list]

        full_psf = np.empty(shape=(len(angle_list), *source_dim[-2:]),
                            dtype=np.float32)
        for index in range(len(angle_index)):
            full_psf[angle_index[index], ...] = ctfsimMod.get_psf(ctffile='./ctffind/' + glob_list[index],
                                                                  point_source_recip=ps_k,
                                                                  k2_grid=k2_grid,
                                                                  alpha_g=alpha_g_grid)

        # Write out psf stack
        with mrcfile.new(subfolder_path + f'/{rootname}_{curr_ts:02}.mrc', overwrite=True) as f:
            (xmin, ymin) = (
                (source_dim[-2]-args.dims[0]) // 2,
                (source_dim[-1]-args.dims[1]) // 2)
            (xmax, ymax) = (xmin+args.dims[0], ymin+args.dims[1])

            f.set_data(full_psf[:, xmin:xmax, ymin:ymax])


        # Write out rawtlt file
        with open(subfolder_path + f'/{rootname}_{curr_ts:02}.rawtlt', 'w') as f:
            for angle in sorted(angle_list):
                f.writelines(str(angle) + '\n')


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
    """ Placeholder 
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

    # Add optional kwargs
    for param in kwargs:
        aretomo_params.params["AreTomo_kwargs"][param] = vars(args).get(param)


    # set process list, InMrc, OutMrc, AngFile

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
    """ Placeholder """                 
    pass