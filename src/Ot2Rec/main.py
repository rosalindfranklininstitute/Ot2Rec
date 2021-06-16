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

import Ot2Rec.params as prmMod
import Ot2Rec.metadata as mdMod
import Ot2Rec.motioncorr as mc2Mod


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

    unique_ts_numbers = unprocessed_images['ts'].unique().tolist()

    # Read in MC2 yaml file, modify, and update
    mc2_params = prmMod.read_yaml(project_name=project_name,
                                  filename=mc2_yaml_name)
    mc2_params.params['System']['process_list'] = unique_ts_numbers
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
    master_md = project_name + '_master_md.yaml'

    if not os.path.isfile(mc2_yaml):
        raise IOError("Error in Ot2Rec.main.run_mc2: MC2 yaml config not found.")
    if not os.path.isfile(master_md):
        raise IOError("Error in Ot2Rec.main.run_mc2: Master metadata not found.")

    # Read in config and metadata
    mc2_config = prmMod.read_yaml(project_name=project_name,
                                  filename=mc2_yaml)
    master_md = mdMod.read_md_yaml(project_name=project_name,
                                   job_type='motioncorr',
                                   filename=master_md)

    # Create Motioncorr object
    mc2_obj = mc2Mod.Motioncorr(project_name=project_name,
                                mc2_params=mc2_config,
                                md_in=master_md)

    # Run MC2 recursively (and update input/output metadata) until nothing is left in the input metadata list
    while len(mc2_obj.meta) > 0:
        mc2_obj.run_mc2()
        mc2_obj.update_mc2_metadata()

    # Once all specified images are processed, export output metadata
    mc2_obj.export_metadata()
