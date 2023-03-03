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
from pathlib import Path
from icecream import ic


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

    master_yaml_name = args.project_name.value + '_proj.yaml'

    proj_yaml_dict = {
        'source_folder': str(args.source_folder.value),
        'TS_folder_prefix': args.folder_prefix.value,
        'file_prefix': args.project_name.value if args.file_prefix.value=="" else args.file_prefix.value,
        'image_stack_field': args.stack_field.value,
        'image_index_field': args.index_field.value,
        'image_tiltangle_field': args.tiltangle_field.value,
        'filetype': args.ext.value,
    }

    with open(master_yaml_name, 'w') as f:
        yaml.dump(proj_yaml_dict, f, indent=4, sort_keys=False)


def new_mc2_yaml(args):
    """
    Subroutine to create yaml file for motioncorr

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """

    mc2_yaml_name = args.project_name.value + '_mc2.yaml'

    mc2_yaml_dict = {
        'System': {
            'process_list': None,
            'output_path': str(args.output_folder.value),
            'output_prefix': args.file_prefix.value if args.file_prefix.value != "" else args.project_name.value,
            'use_gpu': 'auto', # if not args.no_gpu.value else False,
            'jobs_per_gpu': args.jobs_per_gpu.value,
            'gpu_memory_usage': args.gpu_mem_usage.value,
        },
        'MC2': {
            'MC2_path': str(args.exec_path.value),
            'gain_reference': 'nogain' if not args.use_gain.value else str(args.gain.value),
            'pixel_size': args.pixel_size.value,
            'desired_pixel_size': args.pixel_size.value * 2 if args.super_res.value else args.pixel_size.value,
            'discard_frames_top': args.discard_top.value,
            'discard_frames_bottom': args.discard_bottom.value,
            'tolerance': args.tolerance.value,
            'max_iterations': args.max_iter.value,
            'patch_size': args.patch_size.value,
            'use_subgroups': args.use_subgroups.value,
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

    ctf_yaml_name = args.project_name.value + '_ctffind.yaml'

    ctf_yaml_dict = {
        'System': {
            'process_list': 'all',
            'output_path': str(args.output_folder.value),
            'output_prefix': args.file_prefix.value if args.file_prefix.value != "" else args.project_name.value,
        },
        'ctffind': {
            'ctffind_path': str(args.exec_path.value),
            'pixel_size': None,
            'voltage': args.voltage.value,
            'spherical_aberration': args.spherical_aberration.value,
            'amp_contrast': args.amp_contrast.value,
            'amp_spec_size': args.spec_size.value,
            'resolution_min': max(args.res_range.value),
            'resolution_max': min(args.res_range.value),
            'defocus_min': args.defocus_range.value[0],
            'defocus_max': args.defocus_range.value[1],
            'defocus_step': args.defocus_range.value[2],
            'astigm_type': args.astigm_type.value,
            'exhaustive_search': args.exhaustive_search.value,
            'astigm_restraint': args.astigm_restraint.value if args.astigm_restraint.value > 0 else False,
            'phase_shift': args.phase_shift.value,
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

    # Calculate patch sizes
    import numpy as np
    image_dims = np.array(args.image_dims.value)
    n_patches = np.array(args.num_patches.value)
    overlap = args.patch_overlap.value * 0.01
    denom = n_patches - n_patches*overlap + overlap
    patch_dims = (image_dims / denom).astype(int)

    align_yaml_name = args.project_name.value + '_align.yaml'

    align_yaml_dict = {
        'System': {
            'process_list': 'all',
            'output_path': str(args.output_folder.value),
            'output_rootname': args.file_prefix.value if args.file_prefix.value != "" else args.project_name.value,
            'output_suffix': args.file_suffix.value,
        },

        'BatchRunTomo': {
            'setup': {
                'excluded_views': list(args.excl_views.value),
                'use_rawtlt': not args.no_rawtlt.value,
                'pixel_size': None,
                'rot_angle': args.rot_angle.value,
                'gold_size': args.fiducial_size.value,
                'num_beads': args.num_beads.value,
                'adoc_template': str(args.adoc_template.value),
                'stack_bin_factor': args.stack_bin_factor.value,
            },

            'preprocessing': {
                'delete_old_files': args.delete_old_files.value,
                'remove_xrays': args.remove_xrays.value,
            },

            'coarse_align': {
                'bin_factor': args.coarse_align_bin_factor.value,
            },

            'patch_track': {
                'size_of_patches': patch_dims.tolist(),
                'num_of_patches': list(args.num_patches.value),
                'num_iterations': args.num_iter.value,
                'limits_on_shift': list(args.limits_on_shift.value),
                'adjust_tilt_angles': args.adjust_tilt_angles.value,
            },

            'fine_align': {
                'num_surfaces': args.num_surfaces.value,
                'mag_option': args.mag_option.value,
                'tilt_option': args.tilt_option.value,
                'rot_option': args.rot_option.value,
                'beam_tilt_option': args.beam_tilt_option.value,
                'use_robust_fitting': args.robust_fitting.value,
                'weight_all_contours': args.weight_contours.value,
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
    recon_yaml_name = args.project_name.value + '_recon.yaml'

    recon_yaml_dict = {
        'System': {
            'process_list': 'all',
            'output_path': './stacks/',
            'output_rootname': 'TS',
            'output_suffix': '',
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
                'do_positioning': args.do_positioning.value,
                'unbinned_thickness': args.unbinned_thickness.value,
            },

            'aligned_stack': {
                'correct_ctf': args.correct_ctf.value,
                'erase_gold': args.erase_gold.value,
                '2d_filtering': args.filtering.value,
                'bin_factor': args.bin_factor.value,
            },

            'reconstruction': {
                'thickness': args.thickness.value,
                'use_sirt': args.use_sirt.value,
                'sirt_iter': args.sirt_iter.value,
            },

            'postprocessing': {
                'run_trimvol': args.trimvol.value,
                'trimvol_reorient': args.trimvol_reorient.value,
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

    savurecon_yaml_name = args.project_name.value + '_savurecon.yaml'

    savurecon_yaml_dict = {
        'System': {
            'process_list': None,
            'output_path': str(args.output_path.value),
            'output_rootname': args.project_name.value if args.rootname.value is None else args.rootname.value,
            'output_suffix': args.suffix.value,
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

    aretomo_yaml_names = {0: args["project_name"] + "_aretomo_align.yaml",
                          1: args["project_name"] + "_aretomo_recon.yaml",
                          2: args["project_name"] + "_aretomo_align-recon.yaml"}

    aretomo_yaml_name = aretomo_yaml_names[int(args["aretomo_mode"])]
    print(f"{aretomo_yaml_name} created")

    aretomo_yaml_dict = {
        "System": {
            "process_list": None,
            "output_path": str(args["output_path"]),
            "output_rootname": args["project_name"] if args["rootname"] == "" else args["rootname"],
            "output_suffix": args["suffix"],
        },

        "AreTomo_setup": {
            "aretomo_mode": args["aretomo_mode"],
            "rot_angle": args["rot_angle"],
            "input_mrc": None,
            "output_mrc": None,
            "tilt_angles": None,
            "output_binning": None,
            "out_imod": args["out_imod"],
            "dark_tol": args["dark_tol"]
        },

        "AreTomo_recon": {
            "volz": None,
            "sample_thickness": None,
            "pixel_size": args["pixel_size"],
            "recon_algo": args["recon_algo"],
        },

        "AreTomo_kwargs": {
            # placeholder for extra kwargs
        },
    }

    with open(aretomo_yaml_name, "w") as f:
        yaml.dump(aretomo_yaml_dict, f, indent=4, sort_keys=False)


def new_exclude_bad_tilts_yaml(args):
    """
    Subroutine to create yaml file for excluding bad tilts

    ARGS:
    args (Namespace) :: Namespace containing user parameter inputs
    """

    ebt_yaml_name = f"{args.project_name.value}_exclude_bad_tilts.yaml"
    print(f"{ebt_yaml_name} created")

    ebt_yaml_dict = {
        "System": {
            "process_list": None,
        },

        "EBT_setup": {
            "input_mrc": None,
            "min_percentile": None,
            "max_percentile": None,
        },
    }

    with open(ebt_yaml_name, "w") as f:
        yaml.dump(ebt_yaml_dict, f, indent=4, sort_keys=False)


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
        params = yaml.load(f.read(), Loader=yaml.FullLoader)

    return Params(project_name, params)
