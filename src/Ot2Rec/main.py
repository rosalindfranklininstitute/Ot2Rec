"""
Ot2Rec.main.py

Copyright (C) Rosalind Franklin Institute 2021

Author  : Neville B.-y. Yee
Date    : 11-Jun-2021
Version : 0.0.2
"""

import sys
import os
from glob import glob
import yaml
import pandas as pd

from icecream import ic

import Ot2Rec.params as prmMod
import Ot2Rec.metadata as mdMod
import Ot2Rec.motioncorr as mc2Mod
import Ot2Rec.logger as logMod


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
        master_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader)).drop(columns=['file_paths'])

    # Read in previous MC2 output metadata (as Pandas dataframe) for old projects
    mc2_md_name = project_name + '_mc2_md.yaml'
    if os.path.isfile(mc2_md_name):
        is_old_project = True
        with open(mc2_md_name, 'r') as f:
            mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader)).drop(columns=['file_paths'])
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
    ctf_md_name = project_name + '_ctf_mdout.yaml'
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
