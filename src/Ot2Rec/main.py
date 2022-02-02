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

from . import params as prmMod
from . import metadata as mdMod
from . import motioncorr as mc2Mod
from . import logger as logMod
from . import ctffind as ctfMod
from . import align as alignMod
from . import recon as reconMod
from . import ctfsim as ctfsimMod
from . import savurecon as savuMod


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
    Subroutine executing actions when a new project has been initiated
    """

    # Parse user inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("-s", "--source_folder",
                        type=str,
                        default='../raw/',
                        help="Path to folder with raw images (Default: ../raw/)")
    parser.add_argument("-fp", "--folder_prefix",
                        type=str,
                        default='',
                        help="Common prefix of raw tilt series folder(s). Don't use this flag if all images are in the parent folder.")
    parser.add_argument("-p", "--file_prefix",
                        type=str,
                        help="Common prefix of raw image files (Default: project name).")
    parser.add_argument("-t", "--tiffs",
                        action="store_true",
                        help="Use this flag if the raw images are TIFFs.")
    parser.add_argument("--stack_field",
                        type=int,
                        default=0,
                        help="Field number of tilt series indices (Default: 0).")
    parser.add_argument("--tiltangle_field",
                        type=int,
                        default=2,
                        help="Field number of tilt angles (Default: 2).")


    args = parser.parse_args()
    
    # Create master yaml config file
    prmMod.new_master_yaml(args)


def get_master_metadata():
    """
    Subroutine to get master metadata from raw images
    """

    # Parse user inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    args = parser.parse_args()

    # Create empty Metadata object
    # Master yaml file will be read automatically
    meta = mdMod.Metadata(project_name=args.project_name,
                          job_type='master')

    # Create master metadata and serialise it as yaml file
    meta.create_master_metadata()

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
    mc2_params.params['System']['source_TIFF'] = master_config['source_TIFF']

    with open(mc2_yaml_name, 'w') as f:
        yaml.dump(mc2_params.params, f, indent=4, sort_keys=False)


def create_mc2_yaml():
    """
    Subroutine to create new yaml file for motioncorr
    """

    # Parse user inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("-o", "--output_folder",
                        type=str,
                        default='./motioncor/',
                        help="Path to folder for storing motion-corrected images (Default: ./motioncor/)")
    parser.add_argument("-p", "--file_prefix",
                        type=str,
                        help="Common prefix of image files (Default: project name).")
    parser.add_argument("--no_gpu",
                        action="store_true",
                        help="Use CPU only for motion-correction.")
    parser.add_argument("-jpg", "--jobs_per_gpu",
                        type=int,
                        default=2,
                        help="Number of job instance(s) per GPU. Only valid when --no_gpu is off.")
    parser.add_argument("-m", "--gpu_mem_usage",
                        type=float,
                        default=1,
                        help="MotionCor2 memory usage.")
    parser.add_argument("--mc2_path",
                        type=str,
                        default='/opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110',
                        help="Path to MotionCor2 executable. (Default: /opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110)")
    parser.add_argument("--gain",
                        type=str,
                        help="Path to gain reference file. (Default: None)")
    parser.add_argument("pixel_size",
                        type=float,
                        help="Image pixel size in Angstroms.")
    parser.add_argument("-sr", "--super_res",
                        action="store_true",
                        help="Use flag if images are super-resolution.")
    parser.add_argument("-dt", "--discard_top",
                        type=int,
                        default=0,
                        help="Number of frames discarded from top per image. (Default: 0)")
    parser.add_argument("-db", "--discard_bottom",
                        type=int,
                        default=0,
                        help="Number of frames discarded from bottom per image. (Default: 0)")
    parser.add_argument("-tol", "--tolerance",
                        type=float,
                        default=0.5,
                        help="Threshold of alignment errors in pixels. (Default: 0.5)")
    parser.add_argument("--max_iter",
                        type=int,
                        default=10,
                        help="Maximum number of iterations performed by MotionCor2.")
    parser.add_argument("-ps", "--patch_size",
                        nargs=3,
                        type=int,
                        default=[5, 5, 20],
                        help="Size of patches used in alignment.")
    parser.add_argument("--no_subgroups",
                        action="store_false",
                        help="Do not use subgroups in alignment.")
    
    args = parser.parse_args()

    # Create the yaml file, then automatically update it
    prmMod.new_mc2_yaml(args)
    update_mc2_yaml(args)


def run_mc2():
    """
    Method to run motioncorr
    """

    project_name = get_proj_name()

    # Check if prerequisite files exist
    mc2_yaml = project_name + '_mc2.yaml'
    master_md_file = project_name + '_master_md.yaml'

    if not os.path.isfile(mc2_yaml):
        raise IOError("Error in Ot2Rec.main.run_mc2: MC2 yaml config not found.")
    if not os.path.isfile(master_md_file):
        raise IOError("Error in Ot2Rec.main.run_mc2: Master metadata not found.")

    # Read in config and metadata
    mc2_config = prmMod.read_yaml(project_name=project_name,
                                  filename=mc2_yaml)
    master_md = mdMod.read_md_yaml(project_name=project_name,
                                   job_type='motioncorr',
                                   filename=master_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create Motioncorr object
    mc2_obj = mc2Mod.Motioncorr(project_name=project_name,
                                mc2_params=mc2_config,
                                md_in=master_md,
                                logger=logger
    )

    if not mc2_obj.no_processes:
        # Run MC2 recursively (and update input/output metadata) until nothing is left in the input metadata list
        mc2_obj.run_mc2()

        # Once all specified images are processed, export output metadata
        mc2_obj.export_metadata()


def update_ctffind_yaml():
    """
    Subroutine to update yaml file for ctffind
    """

    project_name = get_proj_name()

    # Check if ctffind and motioncorr yaml files exist
    ctf_yaml_name = project_name + '_ctffind.yaml'
    mc2_yaml_name = project_name + '_mc2.yaml'
    if not os.path.isfile(ctf_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_ctffind_yaml: ctffind config file not found.")
    if not os.path.isfile(mc2_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_ctffind_yaml: motioncorr config file not found.")

    # Read in MC2 metadata (as Pandas dataframe)
    # We only need the TS number and the tilt angle for comparisons at this stage
    mc2_md_name = project_name + '_mc2_mdout.yaml'
    with open(mc2_md_name, 'r') as f:
        mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]

    # Read in previous ctffind output metadata (as Pandas dataframe) for old projects
    ctf_md_name = project_name + '_ctffind_mdout.yaml'
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
    ctf_params = prmMod.read_yaml(project_name=project_name,
                                  filename=ctf_yaml_name)
    mc2_params = prmMod.read_yaml(project_name=project_name,
                                  filename=mc2_yaml_name)

    ctf_params.params['System']['output_prefix'] = project_name
    ctf_params.params['System']['process_list'] = unique_ts_numbers
    ctf_params.params['ctffind']['pixel_size'] = mc2_params.params['MC2']['desired_pixel_size']

    with open(ctf_yaml_name, 'w') as f:
        yaml.dump(ctf_params.params, f, indent=4, sort_keys=False)


def create_ctffind_yaml():
    """
    Subroutine to create new yaml file for ctffind
    """

    project_name = get_proj_name()

    # Create the yaml file, then automatically update it
    prmMod.new_ctffind_yaml(project_name)
    update_ctffind_yaml()


def run_ctffind():
    """
    Method to run ctffind
    """

    project_name = get_proj_name()

    # Check if prerequisite files exist
    ctffind_yaml = project_name + '_ctffind.yaml'
    mc2_md_file = project_name + '_mc2_mdout.yaml'

    if not os.path.isfile(ctffind_yaml):
        raise IOError("Error in Ot2Rec.main.run_ctffind: ctffind yaml config not found.")
    if not os.path.isfile(mc2_md_file):
        raise IOError("Error in Ot2Rec.main.run_ctffind: MC2 output metadata not found.")

    # Read in config and metadata
    ctffind_config = prmMod.read_yaml(project_name=project_name,
                                      filename=ctffind_yaml)
    mc2_md = mdMod.read_md_yaml(project_name=project_name,
                                job_type='ctffind',
                                filename=mc2_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create ctffind object
    ctffind_obj = ctfMod.ctffind(project_name=project_name,
                                 md_in=mc2_md,
                                 params_in=ctffind_config,
                                 logger_in=logger,
    )

    if not ctffind_obj.no_processes:
        ctffind_obj.run_ctffind()


def update_align_yaml():
    """
    Subroutine to update yaml file for IMOD newstack / alignment
    """

    project_name = get_proj_name()

    # Check if align and motioncorr yaml files exist
    align_yaml_name = project_name + '_align.yaml'
    mc2_yaml_name = project_name + '_mc2.yaml'
    if not os.path.isfile(align_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_align_yaml: alignment config file not found.")
    if not os.path.isfile(mc2_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_align_yaml: motioncorr config file not found.")

    # Read in MC2 metadata (as Pandas dataframe)
    # We only need the TS number and the tilt angle for comparisons at this stage
    mc2_md_name = project_name + '_mc2_mdout.yaml'
    with open(mc2_md_name, 'r') as f:
        mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]

    # Read in previous alignment output metadata (as Pandas dataframe) for old projects
    align_md_name = project_name + '_align_mdout.yaml'
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
    align_params = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml_name)
    mc2_params = prmMod.read_yaml(project_name=project_name,
                                  filename=mc2_yaml_name)

    align_params.params['System']['output_rootname'] = project_name
    align_params.params['System']['process_list'] = unique_ts_numbers
    align_params.params['BatchRunTomo']['setup']['pixel_size'] = mc2_params.params['MC2']['desired_pixel_size'] * 0.1

    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_params.params, f, indent=4, sort_keys=False)


def update_align_yaml_stacked():
    """
    Method to update yaml file for IMOD newstack / alignment --- if stacks already exist
    """

    # Parse user inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("parent_path",
                        type=str,
                        help="Path to parent folder with stacks in")
    parser.add_argument("pixel_res",
                        type=float,
                        help="Pixel resolution of motion-corrected images (in Angstroms)")
    parser.add_argument("-rn", "--rootname",
                        type=str,
                        help="Rootname of current project (required if different from project name)")
    parser.add_argument("-s", "--suffix",
                        type=str,
                        help="Suffix of project files")

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


def create_align_yaml():
    """
    Subroutine to create new yaml file for IMOD newstack / alignment
    """

    project_name = get_proj_name()

    # Create the yaml file, then automatically update it
    prmMod.new_align_yaml(project_name)
    update_align_yaml()


def create_align_yaml_stacked():
    """
    Subroutine to create new yaml file for IMOD newstack / alignment
    prestack (bool) :: if stacks already exist
    """

    project_name = get_proj_name()

    # Create the yaml file, then automatically update it
    prmMod.new_align_yaml(project_name)
    update_align_yaml_stacked()


def run_align():
    """
    Method to run IMOD newstack / alignment
    """

    project_name = get_proj_name()

    # Check if prerequisite files exist
    align_yaml = project_name + '_align.yaml'
    mc2_md_file = project_name + '_mc2_mdout.yaml'

    # Read in config and metadata
    align_config = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml)
    mc2_md = mdMod.read_md_yaml(project_name=project_name,
                                job_type='align',
                                filename=mc2_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create Align object
    align_obj = alignMod.Align(project_name=project_name,
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



def update_recon_yaml():
    """
    Subroutine to update yaml file for IMOD reconstruction
    """

    project_name = get_proj_name()

    # Check if recon and align yaml files exist
    recon_yaml_name = project_name + '_recon.yaml'
    align_yaml_name = project_name + '_align.yaml'
    if not os.path.isfile(recon_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_recon_yaml: reconstruction config file not found.")
    if not os.path.isfile(align_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_recon_yaml: alignment config file not found.")

    # Read in alignment metadata (as Pandas dataframe)
    align_md_name = project_name + '_align_mdout.yaml'
    with open(align_md_name, 'r') as f:
        align_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]

    # Read in previous alignment output metadata (as Pandas dataframe) for old projects
    recon_md_name = project_name + '_recon_mdout.yaml'
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
    recon_params = prmMod.read_yaml(project_name=project_name,
                                    filename=recon_yaml_name)
    align_params = prmMod.read_yaml(project_name=project_name,
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

    project_name = get_proj_name()

    # Create the yaml file, then automatically update it
    prmMod.new_recon_yaml(project_name)
    update_recon_yaml()


def run_recon():
    """
    Method to run IMOD reconstruction
    """

    project_name = get_proj_name()

    # Check if prerequisite files exist
    recon_yaml = project_name + '_recon.yaml'
    align_md_file = project_name + '_align_mdout.yaml'

    # Read in config and metadata
    recon_config = prmMod.read_yaml(project_name=project_name,
                                    filename=recon_yaml)
    align_md = mdMod.read_md_yaml(project_name=project_name,
                                  job_type='reconstruct',
                                  filename=align_md_file)

    # Create Logger object
    logger = logMod.Logger()

    # Create Recon object
    recon_obj = reconMod.Recon(project_name=project_name,
                               md_in=align_md,
                               params_in=recon_config,
                               logger_in=logger,
    )

    # Run IMOD
    if not recon_obj.no_processes:
        recon_obj.recon_stack()


def update_savurecon_yaml():
    """
    Subroutine to update yaml file for savu reconstruction
    """

    project_name = get_proj_name()

    # Check if savurecon, align, and align_mdout yaml files exist
    savurecon_yaml_name = project_name + '_savurecon.yaml'
    align_yaml_name = project_name + '_align.yaml'
    align_md_name = project_name + '_align_mdout.yaml'
    if not os.path.isfile(savurecon_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_savurecon_yaml: reconstruction config file not found.")
    if not os.path.isfile(align_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_savurecon_yaml: align.yaml file not found")
    if not os.path.isfile(align_md_name):
        raise IOError("Error in Ot2Rec.main.update_savurecon_yaml: alignment mdout file not found.")

    # Read in alignment metadata (as Pandas dataframe)
    with open(align_md_name, 'r') as f:
        align_md_df = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))
        align_md_ts = align_md_df['ts']
        align_output = align_md_df['align_output']

    savurecon_params = prmMod.read_yaml(project_name=project_name,
                                    filename=savurecon_yaml_name)
    align_params = prmMod.read_yaml(project_name=project_name,
                                  filename=align_yaml_name)

    # Get tilt angle files
    align_tilt_files = []
    for f in align_md_df['stack_output']:
        align_tilt_files.append(f.replace('.st', '.tlt'))

    # Update savurecon yaml
    savurecon_params.params['System']['process_list'] = align_md_ts.sort_values(ascending=True).unique().tolist()
    savurecon_params.params['System']['output_rootname'] = align_params.params['System']['output_rootname']
    savurecon_params.params['System']['output_suffix'] = align_params.params['System']['output_suffix']
    savurecon_params.params['Savu']['setup']['tilt_angles'] = align_tilt_files
    savurecon_params.params['Savu']['setup']['aligned_projections'] = align_output.sort_values(ascending=True).unique().tolist()


    # Change centre of rotation to centre of image by default
    centre_of_rotation = []
    for image in savurecon_params.params['Savu']['setup']['aligned_projections']:
        mrc = mrcfile.open(image)
        centre_of_rotation.append(float(mrc.header["ny"]/2)) # ydim/2
    savurecon_params.params['Savu']['setup']['centre_of_rotation'] = centre_of_rotation

    
def create_savurecon_yaml():
    """
    Creates yaml for savu reconstruction
    """
    project_name = get_proj_name()

    # Create savurecon yaml file and automatically update it
    prmMod.new_savurecon_yaml(project_name)
    update_savurecon_yaml()


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


def run_ctfsim():
    """
    Method to run simulator for CTF from CTFFIND4 outputs
    """

    # Parse user inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("pixel_res",
                        type=float,
                        help="Pixel resolution of motion-corrected images (in Angstroms)")
    parser.add_argument("ds_factor",
                        type=int,
                        help="Downsampling factor (must be same as alignment/reconstruction)")
    parser.add_argument("-rn", "--rootname",
                        type=str,
                        help="Rootname of current project (required if different from project name)")
    parser.add_argument("-d", "--dims",
                        type=str,
                        help="Dimensions of simulated CTF in pixels (default: same as downsampled raw data)")

    args = parser.parse_args()
    project_name = args.project_name

    rootname = project_name
    if args.rootname is not None:
        while args.rootname.endswith('/'):
            rootname = args.rootname[:-1]

    pixel_size = args.pixel_res * 1e-10
    ds_factor = args.ds_factor

    if args.dims is not None:
        ctf_dims = [int(item) for item in args.dims.split(',')]

    
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
            if args.dims is not None:
                ctf_dims = [int(item) for item in args.dims.split(',')]
                (xmin, ymin) = (
                    (source_dim[-2]-ctf_dims[0]) // 2,
                    (source_dim[-1]-ctf_dims[1]) // 2)
                (xmax, ymax) = (xmin+ctf_dims[0], ymin+ctf_dims[1])

                f.set_data(full_psf[:, xmin:xmax, ymin:ymax])
            else:
                f.set_data(full_psf)


        # Write out rawtlt file
        with open(subfolder_path + f'/{rootname}_{curr_ts:02}.rawtlt', 'w') as f:
            for angle in sorted(angle_list):
                f.writelines(str(angle) + '\n')


def update_recon_yaml_stacked(project_name, param_dict):
    """
    Method to update yaml file for savu reconstruction --- if stacks already exist

    Args:
    project_name (str) :: Name of current project
    param_dict (dict)  :: Dictionary containing params
    """

    parent_path = param_dict['parent_path']
    rootname    = param_dict['rootname']
    suffix      = param_dict['suffix']
    ext         = param_dict['ext']
    imod_suffix = param_dict['imod_suffix']
    out_folder  = param_dict['out_folder']
    
    # Find stack files
    st_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}_*{suffix}{imod_suffix}.{ext}')

    # Find rawtlt files
    rawtlt_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.rawtlt')

    # Extract tilt series number
    ts_list = [int(i.split('/')[-1].replace(f'{rootname}_', '').replace(f'{suffix}{imod_suffix}.{ext}', '')) for i in st_file_list]

    # Read in and update YAML parameters
    recon_yaml_name = project_name + '_savurecon.yaml'
    recon_params = prmMod.read_yaml(project_name=project_name,
                                    filename=recon_yaml_name)

    recon_params.params['System']['process_list'] = ts_list
    recon_params.params['System']['output_rootname'] = rootname
    recon_params.params['System']['output_path'] = out_folder
    recon_params.params['System']['output_suffix'] = suffix
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


def create_recon_yaml_stacked():
    """
    Subroutine to create new yaml file for IMOD reconstruction
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
                        help="Suffix of project files")
    parser.add_argument("-e", "--extension",
                        type=str,
                        help="File extension of stacks (Default: mrc)")
    parser.add_argument("-is", "--imod_suffix",
                        type=str,
                        help="IMOD file suffix")
    parser.add_argument("-o", "--output_path",
                        type=str,
                        help="Path to output folder (Default: ./savurecon/)")

    args = parser.parse_args()
    project_name = args.project_name
    parent_path = args.stacks_folder

    rootname = project_name
    if args.rootname is not None:
        while args.rootname.endswith('/'):
            rootname = args.rootname[:-1]

    suffix = ''
    if args.suffix is not None:
        suffix = args.suffix

    imod_suffix = ''
    if args.imod_suffix is not None:
        imod_suffix = '_' + args.imod_suffix
        
    ext = 'mrc'
    if args.extension is not None:
        ext = args.extension

    out_folder = './savurecon/'
    if args.output_path is not None:
        out_folder = args.output_path

    savu_params = dict({
        'parent_path'  : parent_path,
        'rootname'     : rootname,
        'suffix'       : suffix,
        'ext'          : ext,
        'imod_suffix'  : imod_suffix,
        'out_folder'   : out_folder
    })
        
        
    # Create the yaml file, then automatically update it
    prmMod.new_savurecon_yaml(project_name)
    update_recon_yaml_stacked(project_name=project_name,
                              param_dict=savu_params)



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
