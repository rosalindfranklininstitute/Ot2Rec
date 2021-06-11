"""
Ot2Rec.params.py

Copyright (C) Rosalind Franklin Institute 2021

Author: Neville B.-y. Yee
Date: 10-Jun-2021

Version: 0.0.2
"""

import os
from glob import glob
import yaml
import pandas as pd
import multiprocess as mp
import datetime as dt


class Params:
    """
    Class encapsulating Params objects
    """

    def __init__(self,
                 project_name: str,
                 params_in=None):
        """
        Initialise Params object
       
        ARGS:
        project_name :: Name of current project
        params_in    :: Parameters being read in
        """

        self.project_name = project_name
        self.params = params_in


        

def new_master_yaml(project_name: str):
    """
    Subroutine to create yaml file for processing master metadata

    ARGS:
    project_name :: Name of current project
    """

    master_yaml_name = project_name + '_proj.yaml'
    
    proj_yaml_dict = {
        'source_folder': '../raw/',
        'TS_folder_prefix': '*',
        'image_stack_field': 1,
        'image_tiltangle_field': 3,
        'source_TIFF': True,
    }

    with open(master_yaml_name, 'w') as f:
        yaml.dump(proj_yaml_dict, f, indent=4, sort_keys=False) 

            
def read_yaml(project_name: str,
              filename: str):
    """
    Function to read in config file

    ARGS:
    project_name :: name of current project
    filename     :: config file name

    RETURNS:
    Params object
    """

    # Check if file exists
    if not os.path.isfile(filename):
        raise IOError("Error in Ot2Rec.params.read_yaml: File not found.")

    with open(filename, 'r') as f:
        params = yaml.load(f, Loader=yaml.FullLoader)

    return Params(project_name, params)
