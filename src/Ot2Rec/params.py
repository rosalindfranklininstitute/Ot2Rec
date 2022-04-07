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
import yaml


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
        'image_index_field': args.index_field,
        'image_tiltangle_field': args.tiltangle_field,
        'filetype': args.ext,
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
            'use_subgroups': not args.no_subgroups,
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


def new_align_yaml(args):
    """
    Subroutine to create yaml file for stack creation and BatchTomo (up till alignment)

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """

    align_yaml_name = args.project_name + '_align.yaml'

    align_yaml_dict = {
        'System' : {
            'process_list' : 'all',
            'output_path' : args.output_folder,
            'output_rootname' : args.file_prefix if args.file_prefix is not None else args.project_name,
            'output_suffix' : args.file_suffix,
        },
        
        'BatchRunTomo': {
            'setup': {
                'use_rawtlt': not args.no_rawtlt,
                'pixel_size': None,
                'rot_angle': args.rot_angle,
                'gold_size': args.fiducial_size,
                'adoc_template': args.adoc_template,
                'stack_bin_factor': args.stack_bin_factor,
            },

            'preprocessing': {
                'delete_old_files': args.delete_old_files,
                'remove_xrays': args.remove_xrays,
            },

            'coarse_align': {
                'bin_factor': args.coarse_align_bin_factor,
            },

            'patch_track': {
                'size_of_patches': args.patch_sizes,
                'num_of_patches': args.num_patches,
                'num_iterations': args.num_iter,
                'limits_on_shift': args.limits_on_shift,
                'adjust_tilt_angles': args.adjust_tilt_angles,
            },

            'fine_align': {
                'num_surfaces': args.num_surfaces,
                'mag_option': args.mag_option,
                'tilt_option': args.tilt_option,
                'rot_option': args.rot_option,
                'beam_tilt_option': args.beam_tilt_option,
                'use_robust_fitting': not args.no_robust_fitting,
                'weight_all_contours': not args.no_weight_contours,
            },
        }
    }
                
    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_yaml_dict, f, indent=4, sort_keys=False)


def new_recon_yaml(args):
    """
    Subroutine to create yaml file for batchtomo (continuing from aligned stacks to full reconstruction)

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """
    recon_yaml_name = args.project_name + '_recon.yaml'

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
                'do_positioning': args.do_positioning,
                'unbinned_thickness': args.unbinned_thickness,
            },

            'aligned_stack': {
                'correct_ctf': args.correct_ctf,
                'erase_gold': args.erase_gold,
                '2d_filtering': args.filtering,
                'bin_factor': args.bin_factor,
            },

            'reconstruction': {
                'thickness': args.thickness,
            },

            'postprocessing': {
                'run_trimvol': not args.no_trimvol,
                'trimvol_reorient': args.trimvol_reorient,
            },
        }
    }
                
    with open(recon_yaml_name, 'w') as f:
        yaml.dump(recon_yaml_dict, f, indent=4, sort_keys=False)


def new_savurecon_yaml(args):
    """
    Subroutine to create yaml file for savurecon (continuing from aligned stacks to full reconstruction)

    ARGS:
    args (Namespace) :: Namespace containing user parameter inputs
    """

    savurecon_yaml_name = args.project_name + '_savurecon.yaml'

    savurecon_yaml_dict = {
        'System' : {
            'process_list' : None,
            'output_path' : args.output_path,
            'output_rootname' : args.project_name if args.rootname is None else args.rootname,
            'output_suffix' : args.suffix,
        },
        
        'Savu': {
            'setup': {
                'tilt_angles': None,
                'aligned_projections': None,
                'algorithm': 'CGLS_CUDA',
                'centre_of_rotation': 'autocenter',
            }
        }
    }
                
    with open(savurecon_yaml_name, 'w') as f:
        yaml.dump(savurecon_yaml_dict, f, indent=4, sort_keys=False)


def new_aretomo_yaml(args):
    """
    Subroutine to create yaml file for aretomo

    ARGS:
    args (Namespace) :: Namespace containing user parameter inputs
    """

    aretomo_yaml_names = {0: args.project_name + "_aretomo_align.yaml",
                         1: args.project_name + "_aretomo_recon.yaml",
                         2: args.project_name + "_aretomo_align-recon.yaml"}

    aretomo_yaml_name = aretomo_yaml_names[int(args.aretomo_mode)]
    print("{} created".format(aretomo_yaml_name))

    aretomo_yaml_dict = {
        "System" : {
            "process_list" : None,
            "output_path" : args.output_path,
            "output_rootname" : args.project_name if args.rootname is None else args.rootname,
            "output_suffix" : args.suffix,
        },

        "AreTomo_setup" : {
            "aretomo_mode" : args.aretomo_mode,
            "rot_angle" : args.rot_angle,
            "input_mrc" : None,
            "output_mrc" :None,
            "tilt_angles" : None,
            "output_binning" : None
        },

        "AreTomo_recon" : {
            "volz" : None,
            "sample_thickness" : None,
            "pixel_size" : args.pixel_size,
            "recon_algo" : None,
        },

        "AreTomo_kwargs" : {
            # placeholder for extra kwargs
        },
    }

    with open(aretomo_yaml_name, "w") as f:
        yaml.dump(aretomo_yaml_dict, f, indent=4, sort_keys=False)

        
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
