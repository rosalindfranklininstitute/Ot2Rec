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


from pathlib import Path, PosixPath
from magicgui import magicgui as mg

import yaml

from . import logger as logMod
from . import params as prmMod
from . import metadata as mdMod
from . import align


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=True,
    scrollable=True,

    project_name={"label": "Project name *"},
    newstack_path={"widget_type": "FileEdit",
                   "mode": "w",
                   "label": "Path to IMOD-newstack executable (Default: newstack)"},
    brt_path={"widget_type": "FileEdit",
              "mode": "w",
              "label": "Path to IMOD-batchruntomo executable (Default: batchruntomo)"},
    rot_angle={"label": "Beam rotation angle *",
               "min": -180.00,
               "max": 180.00,
               "step": 0.01},
    image_dims={"widget_type": "LiteralEvalLineEdit",
                "label": "Image dimensions (in pixels) *"},
    excl_views={"widget_type": "LiteralEvalLineEdit",
                "label": "Excluded views"},
    output_folder={"label": "IMOD output folder",
                   "mode": "d"},
    file_prefix={"label": "File prefix (if different from project name)"},
    file_suffix={"label": "IMOD file suffix (if applicable)"},
    file_ext={"label": "Image file extension"},
    no_rawtlt={"label": "Ignore .rawtlt files?"},
    fiducial_size={"label": "Size of fiducial particles in nm (-1 if fiducial-free)",
                   "min": -1.0,
                   "step": 0.01},
    num_beads={"label": "# of beads to track"},
    adoc_template={"label": "Path to BatchRunTomo directives template"},
    stack_bin_factor={"label": "Stack: Raw image stacks downsampling factor",
                      "min": 1},
    aligned_bin_factor={"label": "Stack: Aligned stack binning factor",
                        "min": 1},
    delete_old_files={"label": "Preprocessing: Remove original stack when excluding views"},
    remove_xrays={"label": "Preprocessing: Remove X-rays and other artefacts"},
    num_patches={"widget_type": "LiteralEvalLineEdit",
                 "label": "Patch-tracking: Number of patches to track in X and Y (Nx, Ny)"},
    patch_overlap={"label": "Patch-tracking: % overlap between patches",
                   "min": 0,
                   "max": 100},
    num_iter={"label": "Patch-tracking: Number of iterations (1-4)",
              "min": 1,
              "max": 4},
    limits_on_shift={"widget_type": "LiteralEvalLineEdit",
                     "label": "Patch-tracking: Limits on shifts (in pixels)"},
    adjust_tilt_angles={"label": "Patch-tracking: Rerun patch-tracking with tilt-angle offset"},
    num_surfaces={"widget_type": "RadioButtons",
                  "label": "Fine-alignment: Number of surface(s) for angle analysis.",
                  "choices": [1, 2]},
    mag_option={"widget_type": "ComboBox",
                "label": "Fine-alignment: Type of magnification solution",
                "choices": ['all', 'group', 'fixed']},
    tilt_option={"widget_type": "ComboBox",
                 "label": "Fine-alignment: Type of tilt-angle solution",
                 "choices": ['all', 'group', 'fixed']},
    rot_option={"widget_type": "ComboBox",
                "label": "Fine-alignment: Type of rotation solution",
                "choices": ['all', 'group', 'one', 'fixed']},
    beam_tilt_option={"widget_type": "ComboBox",
                      "label": "Fine-alignment: Type of beam tilt-angle solution",
                      "choices": ['fixed', 'search']},
    robust_fitting={"label": "Fine-alignment: Use robust fitting?"},
    weight_contours={"label": "Fine-alignment: Apply weighting to entire contours from patch-tracking"},
)
def get_args_align(
        project_name="",
        newstack_path="newstack",
        brt_path="batchruntomo",
        rot_angle=0.00,
        image_dims=[100, 100],
        excl_views=[0],
        output_folder=Path("./stacks"),
        file_prefix="",
        file_suffix="",
        file_ext="mrc",
        no_rawtlt=False,
        fiducial_size=-1,
        num_beads=0,
        adoc_template=Path("/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc"),
        stack_bin_factor=1,
        aligned_bin_factor=4,
        delete_old_files=False,
        remove_xrays=True,
        num_patches=[24, 24],
        patch_overlap=25,
        num_iter=4,
        limits_on_shift=[2, 2],
        adjust_tilt_angles=True,
        num_surfaces=1,
        mag_option="fixed",
        tilt_option="fixed",
        rot_option="group",
        beam_tilt_option="fixed",
        robust_fitting=True,
        weight_contours=True,
):
    """
    Function to add arguments to parser for IMOD alignment

    ARGS:
    project_name (str)            :: Name of current project
    rot_angle (float)             :: Rotational angle of electron beam. Can be obtained from MDOC files
    image_dims (int)              :: Image dimensions (in pixels)
    excl_views (int)              :: Indices of micrographes to be excluded
    output_folder (str)           :: Path to folder for storing IMOD outputs
    file_prefix (str)             :: Common prefix of raw image files (Default: project)
    file_suffix (str)             :: Extra information attached as suffix to output filenames
    no_rawtlt (bool)              :: Use information in filenames to determine tilt angles (rather than using .rawtlt files)
    fiducial_size (float)         :: Size (in nm) of gold fiducial particles
    adoc_template (str)           :: Path to template file of BatchRunTomo directives
    stack_bin_factor (int)        :: Stack: Raw image stacks downsampling factor
    delete_old_files (bool)       :: Preprocessing: Remove original stack when excluding views
    remove_xrays (bool)           :: Preprocessing: Attempt to remove X-rays and other artefacts
    coarse_align_bin_factor (int) :: Coarse-alignment: Coarse aligned stack binning
    num_patches (int)             :: Patch-tracking: Number of patches to track in X and Y
    patch_overlap (int)           :: Patch-tracking: % overlap between patches
    num_iter (int)                :: Patch-tracking: Number of iterations. (Max. 4)
    limits_on_shift (int)         :: Patch-tracking: Maximum extent (in pixels) to which patches are allowed to move during alignment
    adjust_tilt_angles (bool)     :: Patch-tracking: Rerun patch-tracking procedure with tilt-angle offset
    num_surfaces (int)            :: Fine-alignment: Number of surface(s) for angle analysis
    mag_option (str)              :: Fine-alignment: Type of magnification solution
    tilt_option (str)             :: Fine-alignment: Type of tilt-angle solution
    rot_option (str)              :: Fine-alignment: Type of rotation solution
    beam_tilt_option (str)        :: Fine-alignment: Type of beam-tilt solution
    robust_fitting (bool)         :: Fine-alignment: Use robust fitting
    weight_contours (bool)        :: Fine-alignment: Apply weighting to entire contours from patch-tracking

    OUTPUTs:
    Namespace
    """
    logger = logMod.Logger(log_path="o2r_imod_align.log")
    args = asObject(locals())

    if locals()['newstack_path'] == Path("."):
        args.newstack_path = "newstack"

    if locals()['brt_path'] == Path("."):
        args.brt_path = "batchruntomo"

    # Create the yaml file, then automatically update it
    prmMod.new_align_yaml(args)
    align.update_yaml(args, logger)

    return "Done. You can close this window now."
