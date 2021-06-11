"""
Ot2Rec.main.py

Copyright (C) Rosalind Franklin Institute 2021

Author  : Neville B.-y. Yee
Date    : 11-Jun-2021
Version : 0.0.1
"""

import Ot2Rec.params as prmMod



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
