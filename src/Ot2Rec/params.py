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


        

def new_master_yaml(args):
    """
    Subroutine to create yaml file for processing master metadata

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """

    master_yaml_name = args.project_name + '_proj.yaml'
    
    proj_yaml_dict = {
        'source_folder': args.source_folder,
        'TS_folder_prefix': args.folder_prefix,
        'file_prefix': args.project_name if args.file_prefix is None else args.file_prefix,
        'image_stack_field': args.stack_field,
        'image_tiltangle_field': args.tiltangle_field,
        'source_TIFF': args.tiffs,
    }

    with open(master_yaml_name, 'w') as f:
        yaml.dump(proj_yaml_dict, f, indent=4, sort_keys=False) 


def new_mc2_yaml(args):
    """
    Subroutine to create yaml file for motioncorr

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """

    mc2_yaml_name = args.project_name + '_mc2.yaml'

    mc2_yaml_dict = {
        'System': {
            'process_list': None,
            'output_path': args.output_folder,
            'output_prefix': args.file_prefix if args.file_prefix is not None else args.project_name,
            'use_gpu': 'auto' if not args.no_gpu else False,
            'jobs_per_gpu': args.jobs_per_gpu,
            'gpu_memory_usage': args.gpu_mem_usage,
            'source_TIFF': None,
        },
        'MC2': {
            'MC2_path': args.exec_path,
            'gain_reference': 'nogain' if args.gain is None else args.gain,
            'pixel_size': args.pixel_size,
            'desired_pixel_size': args.pixel_size*2 if args.super_res else args.pixel_size,
            'discard_frames_top': args.discard_top,
            'discard_frames_bottom': args.discard_bottom,
            'tolerance': args.tolerance,
            'max_iterations': args.max_iter,
            'patch_size': args.patch_size,
            'use_subgroups': args.no_subgroups,
        },
    }
        
    with open(mc2_yaml_name, 'w') as f:
        yaml.dump(mc2_yaml_dict, f, indent=4, sort_keys=False) 


def new_ctffind_yaml(args):
    """
    Subroutine to create yaml file for ctffind

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """

    ctf_yaml_name = args.project_name + '_ctffind.yaml'

    ctf_yaml_dict = {
        'System': {
            'process_list': 'all',
            'output_path': args.output_folder,
            'output_prefix': args.file_prefix if args.file_prefix is not None else args.project_name,
        },
        'ctffind': {
            'ctffind_path': args.exec_path,
            'pixel_size': None,
            'voltage': args.voltage,
            'spherical_aberration': args.spherical_aberration,
            'amp_contrast': args.amp_contrast,
            'amp_spec_size': args.spec_size,
            'resolution_min': max(args.res_range),
            'resolution_max': min(args.res_range),
            'defocus_min': args.defocus_range[0],
            'defocus_max': args.defocus_range[1],
            'defocus_step': args.defocus_range[2],
            'astigm_type': args.astigm_type,
            'exhaustive_search': args.exhaustive_search,
            'astigm_restraint': args.astigm_restraint if args.astigm_restraint is not None else False,
            'phase_shift': args.phase_shift,
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
            'output_rootname' : 'TS',
            'output_suffix' : '',
        },
        
        'BatchRunTomo': {
            'setup': {
                'use_rawtlt': True,
                'pixel_size': 'default',
                'rot_angle': 86.,
                'gold_size': 0.,
                'adoc_template': '/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc',
                'stack_bin_factor': 8,
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
        }
    }
                
    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_yaml_dict, f, indent=4, sort_keys=False)


def new_recon_yaml(project_name: str):
    """
    Subroutine to create yaml file for batchtomo (continuing from aligned stacks to full reconstruction)

    ARGS:
    project_name :: Name of current project
    """

    recon_yaml_name = project_name + '_recon.yaml'

    recon_yaml_dict = {
        'System' : {
            'process_list' : 'all',
            'output_path' : './stacks/',
            'output_rootname' : 'TS',
            'output_suffix' : '',
        },
        
        'BatchRunTomo': {
            'setup': {
                'use_rawtlt': True,
                'pixel_size': 'default',
                'rot_angle': 86.,
                'gold_size': 0.,
                'adoc_template': '/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc',
            },

            'positioning': {
                'do_positioning': False,
                'unbinned_thickness': 3600,
            },

            'aligned_stack': {
                'correct_ctf': False,
                'erase_gold': False,
                '2d_filtering': False,
                'bin_factor': 8,
            },

            'reconstruction': {
                'thickness': 3600,
            },

            'postprocessing': {
                'run_trimvol': True,
                'trimvol_reorient': 'rotate',
            },
        }
    }
                
    with open(recon_yaml_name, 'w') as f:
        yaml.dump(recon_yaml_dict, f, indent=4, sort_keys=False)


def new_savurecon_yaml(project_name: str):
    """
    Subroutine to create yaml file for savurecon (continuing from aligned stacks to full reconstruction)

    ARGS:
    project_name :: Name of current project
    """

    savurecon_yaml_name = project_name + '_savurecon.yaml'

    savurecon_yaml_dict = {
        'System' : {
            'process_list' : 'all',
            'output_path' : './savurecon/',
            'output_rootname' : 'TS',
            'output_suffix' : '',
        },
        
        'Savu': {
            'setup': {
                'tilt_angles': '.tlt',
                'aligned_projections': '*_ali.mrc',
                'algorithm': 'CGLS_CUDA',
                'centre_of_rotation': '0.0',
            }
        }
    }
                
    with open(savurecon_yaml_name, 'w') as f:
        yaml.dump(savurecon_yaml_dict, f, indent=4, sort_keys=False)

        
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
