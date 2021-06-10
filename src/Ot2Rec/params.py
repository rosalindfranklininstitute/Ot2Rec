"""
Ot2Rec.params.py

Copyright (C) Rosalind Franklin Institute 2021

Author: Neville B.-y. Yee
Date: 10-Jun-2021

Version: 0.0.1
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

    def __init__(self, project_name):
        """
        Initialise Params object
       
        ARGS:
        project_name (str) :: Name of current project
        """

        self.project_name = project_name


    def new_master_yaml(self):
        """
        Subroutine to create yaml file for processing master metadata
        """

        master_yaml_name = self.project_name + '_proj.yaml'

        proj_yaml_dict - {
            'source_folder': '../raw/',
            'TS_folder_prefix': '*',
            'image_stack_field': 1,
            'image_tiltangle_field': 3,
            'source_TIFF': True,
        }

        with open(master_yaml_name, 'w') as f:
            yaml.dump(proj_yaml_dict, f, indent=4, sort_keys=False) 
