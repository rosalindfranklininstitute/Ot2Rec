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
from glob import glob
import yaml
import pandas as pd
from icecream import ic
from beautifultable import BeautifulTable as bt
import re
import subprocess
import numpy as np

from . import params as prmMod
from . import metadata as mdMod
from . import motioncorr as mc2Mod
from . import logger as logMod
from . import ctffind as ctfMod
from . import align as alignMod
from . import recon as reconMod
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

    project_name = get_proj_name()
    
    # Create master yaml config file
    prmMod.new_master_yaml(project_name)


def get_master_metadata():
    """
    Subroutine to get master metadata from raw images
    """

    project_name = get_proj_name()

    # Create empty Metadata object
    # Master yaml file will be read automatically
    meta = mdMod.Metadata(project_name=project_name,
                          job_type='master')

    # Create master metadata and serialise it as yaml file
    meta.create_master_metadata()

    master_md_name = project_name + '_master_md.yaml'
    with open(master_md_name, 'w') as f:
        yaml.dump(meta.metadata, f, indent=4)
    

def update_mc2_yaml():
    """
    Subroutine to update yaml file for motioncorr
    """

    project_name = get_proj_name()
    
    # Check if MC2 yaml exists
    mc2_yaml_name = project_name + '_mc2.yaml'
    if not os.path.isfile(mc2_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_mc2_yaml: File not found.")

    # Read in master metadata (as Pandas dataframe)
    master_md_name = project_name + '_master_md.yaml'
    with open(master_md_name, 'r') as f:
        master_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]

    # Read in previous MC2 output metadata (as Pandas dataframe) for old projects
    mc2_md_name = project_name + '_mc2_md.yaml'
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
    mc2_params = prmMod.read_yaml(project_name=project_name,
                                  filename=mc2_yaml_name)
    mc2_params.params['System']['process_list'] = unique_ts_numbers
    mc2_params.params['System']['output_prefix'] = project_name
    
    if mc2_params.params['MC2']['desired_pixel_size'] == 'ps_x2':
        mc2_params.params['MC2']['desired_pixel_size'] = mc2_params.params['MC2']['pixel_size'] * 2
    else:
        mc2_params.params['MC2']['desired_pixel_size'] = mc2_params.params['MC2']['pixel_size']

    with open(mc2_yaml_name, 'w') as f:
        yaml.dump(mc2_params.params, f, indent=4, sort_keys=False) 

        
def create_mc2_yaml():
    """
    Subroutine to create new yaml file for motioncorr
    """

    project_name = get_proj_name()
    
    # Create the yaml file, then automatically update it
    prmMod.new_mc2_yaml(project_name)
    update_mc2_yaml()
    

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

    project_name = get_proj_name()

    # User prompt for file specifications
    parent_path = input('Enter path of parent folder with stacks in: \n')
    assert (os.path.isdir(parent_path)), \
        "Error in main.update_align_yaml_stacked: IMOD parent folder not found."
    while parent_path.endswith('/'):
        parent_path = parent_path[:-1]

    rootname = input('Enter rootname of project (remove final underscore): \n')
    while rootname.endswith('_'):
        rootname = rootname[:-1]

    suffix = input('Enter file suffix (leave empty if not applicable): \n')
    pixel_size = input('Enter desired pixel size (in angstroms): \n')

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
        align_obj.align_stack()
        

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
    recon_params.params['BatchRunTomo']['setup'] = align_params.params['BatchRunTomo']['setup']
    
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
    
    # Create Align object
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
    
    with open(savurecon_yaml_name, 'w') as f:
        yaml.dump(savurecon_params.params, f, indent=4, sort_keys=False) 


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
