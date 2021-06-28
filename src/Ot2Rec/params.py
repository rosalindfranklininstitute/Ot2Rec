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


def new_mc2_yaml(project_name: str):
    """
    Subroutine to create yaml file for motioncorr

    ARGS:
    project_name :: Name of current project
    """

    mc2_yaml_name = project_name + '_mc2.yaml'

    mc2_yaml_dict = {
        'System': {
            'process_list': 'all',
            'output_path': './motioncor/',
            'output_prefix': 'TS',
            'use_gpu': 'auto',
            'jobs_per_gpu': 2,
            'gpu_memory_usage': 1,
            'source_TIFF': True,
        },
        'MC2': {
            'MC2_path': '/opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110',
            'gain_reference': 'nogain',
            'pixel_size': 0.815,
            'desired_pixel_size': 'ps_x2',
            'discard_frames_top': 1,
            'discard_frames_bottom': 0,
            'tolerance': 0.5,
            'max_iterations': 10,
            'patch_size': [5, 5, 20],
            'use_subgroups': True,
        },
    }
        
    with open(mc2_yaml_name, 'w') as f:
        yaml.dump(mc2_yaml_dict, f, indent=4, sort_keys=False) 


def new_ctffind_yaml(project_name: str):
    """
    Subroutine to create yaml file for ctffind

    ARGS:
    project_name :: Name of current project
    """

    ctf_yaml_name = project_name + '_ctffind.yaml'

    ctf_yaml_dict = {
        'System': {
            'process_list': 'all',
            'output_path': './ctffind/',
            'output_prefix': 'TS',
        },
        'ctffind': {
            'ctffind_path': '/opt/lmod/modules/ctffind/4.1.14/bin/ctffind',
            'pixel_size': None,
            'voltage': 300.,
            'spherical_aberration': 2.7,
            'amp_contrast': 0.8,
            'amp_spec_size': 512,
            'resolution_min': 30.,
            'resolution_max': 5.,
            'defocus_min': 5000.,
            'defocus_max': 50000.,
            'defocus_step': 500.,
            'astigm_type': None,
            'exhaustive_search': False,
            'astigm_restraint': False,
            'phase_shift': False,
        },
    }
        
    with open(ctf_yaml_name, 'w') as f:
        yaml.dump(ctf_yaml_dict, f, indent=4, sort_keys=False)


def new_align_yaml(project_name: str):
    """
    Subroutine to create yaml file for stack creation and BatchTomo (up till alignment)

    ARGS:
    project_name :: Name of current project
    """

    align_yaml_name = project_name + '_align.yaml'

    align_yaml_dict = {
        'System' : {
            'process_list' : 'all',
            'output_path' : './stacks/',
            'output_prefix' : 'TS',
        },
        
        'BatchRunTomo': {
            'general': {
                'align_images_brt': True,
                'adoc_file': 'default',
                'step_start': 0,
                'step_end': 6,
            },
            
            'setup': {
                'use_rawtlt': True,
                'pixel_size': 'default',
                'rot_angle': 86.,
                'gold_size': 0.,
                'adoc_template': '/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc',
            },

            'preprocessing': {
                'delete_old_files': False,
                'remove_xrays': True,
            },

            'coarse_align': {
                'bin_factor': 8,
            },

            'patch_track': {
                'size_of_patches': [300, 200],
                'num_of_patches': [12, 8],
                'num_iterations': 4,
                'limits_on_shift': [2, 2],
                'adjust_tilt_angles': True,
            },

            'fine_align': {
                'num_surfaces': 1,
                'mag_option': 'fixed',
                'tilt_option': 'fixed',
                'rot_option': 'group',
                'beam_tilt_option': 'fixed',
                'use_robust_fitting': True,
                'weight_all_contours': True,
            },

            'positioning': {
                'do_positioning': False,
                'unbinned_thickness': 3600,
            },
        }
    }
                
    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_yaml_dict, f, indent=4, sort_keys=False)

        
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
        raise IOError(f"Error in Ot2Rec.params.read_yaml: {filename}: File not found.")

    with open(filename, 'r') as f:
        params = yaml.load(f, Loader=yaml.FullLoader)

    return Params(project_name, params)
