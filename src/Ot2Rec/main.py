"""
Ot2Rec.main.py

Copyright (C) Rosalind Franklin Institute 2021

Author  : Neville B.-y. Yee
Date    : 11-Jun-2021
Version : 0.0.2
"""

from glob import glob
import yaml

import Ot2Rec.params as prmMod
import Ot2Rec.metadata as mdMod


def new_proj():
    """
    Subroutine executing actions when a new project has been initiated
    """

    # Ask for name of project from user
    project_name = input("Project name? ")

    # Check input validity
    for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        if project_name.find(char) != -1:
            raise ValueError(f"Error in Ot2Rec.main.new_proj: Illegal character ({char}) found in input project name.")
    
    # Create master yaml config file
    prmMod.new_master_yaml(project_name)


def get_master_metadata():
    """
    Subroutine to get master metadata from raw images
    """

    # Ask for name of project from user
    project_name = input("Project name? ")

    # Create empty Metadata object
    # Master yaml file will be read automatically
    meta = mdMod.Metadata(project_name=project_name,
                          job_type='master')

    # Create master metadata and serialise it as yaml file
    meta.create_master_metadata()

    master_md_name = project_name + '_master_md.yaml'
    with open(master_md_name, 'w') as f:
        yaml.dump(meta.metadata, f, indent=4)
    
