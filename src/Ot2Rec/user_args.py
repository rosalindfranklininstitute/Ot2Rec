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


import argparse


def get_args_new_proj():
    """
    Function to add arguments to parser for new project

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("-s", "--source_folder",
                        type=str,
                        default='../raw/',
                        help="Path to folder with raw images (Default: ../raw/)")
    parser.add_argument("-fp", "--folder_prefix",
                        type=str,
                        default='',
                        help="Common prefix of raw tilt series folder(s). Don't use this flag if all images are in the parent folder.")
    parser.add_argument("-p", "--file_prefix",
                        type=str,
                        help="Common prefix of raw image files (Default: project name).")
    parser.add_argument("-e", "--ext",
                        type=str,
                        default='mrc',
                        help="Extension of raw image files (Default: mrc).")
    parser.add_argument("--stack_field",
                        type=int,
                        default=0,
                        help="Field number of tilt series indices (Default: 0).")
    parser.add_argument("--index_field",
                        type=int,
                        default=1,
                        help="Field number of image indices (Default: 1).")
    parser.add_argument("--tiltangle_field",
                        type=int,
                        default=2,
                        help="Field number of tilt angles (Default: 2).")
    parser.add_argument("--no_mdoc",
                        action="store_true",
                        help="Use this flag if no MDOC file provided.")

    return parser


def get_args_mc2():
    """
    Function to add arguments to parser for MotionCor

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("pixel_size",
                        type=float,
                        help="Image pixel size in Angstroms.")
    parser.add_argument("-o", "--output_folder",
                        type=str,
                        default='./motioncor/',
                        help="Path to folder for storing motion-corrected images (Default: ./motioncor/)")
    parser.add_argument("-p", "--file_prefix",
                        type=str,
                        help="Common prefix of image files (Default: project name).")
    parser.add_argument("--no_gpu",
                        action="store_true",
                        help="Use CPU only for motion-correction.")
    parser.add_argument("-jpg", "--jobs_per_gpu",
                        type=int,
                        default=2,
                        help="Number of job instance(s) per GPU. Only valid when --no_gpu is off.")
    parser.add_argument("-m", "--gpu_mem_usage",
                        type=float,
                        default=1,
                        help="MotionCor2 memory usage.")
    parser.add_argument("--exec_path",
                        type=str,
                        default='/opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110',
                        help="Path to MotionCor2 executable. (Default: /opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110)")
    parser.add_argument("--gain",
                        type=str,
                        help="Path to gain reference file. (Default: None)")
    parser.add_argument("--super_res",
                        action="store_true",
                        help="Use flag if images are super-resolution.")
    parser.add_argument("-dt", "--discard_top",
                        type=int,
                        default=0,
                        help="Number of frames discarded from top per image. (Default: 0)")
    parser.add_argument("-db", "--discard_bottom",
                        type=int,
                        default=0,
                        help="Number of frames discarded from bottom per image. (Default: 0)")
    parser.add_argument("-tol", "--tolerance",
                        type=float,
                        default=0.5,
                        help="Threshold of alignment errors in pixels. (Default: 0.5)")
    parser.add_argument("--max_iter",
                        type=int,
                        default=10,
                        help="Maximum number of iterations performed by MotionCor2.")
    parser.add_argument("-ps", "--patch_size",
                        nargs=3,
                        type=int,
                        default=[5, 5, 20],
                        help="Size of patches used in alignment.")
    parser.add_argument("--no_subgroups",
                        action="store_true",
                        help="Do not use subgroups in alignment.")

    return parser


def get_args_ctffind():
    """
    Function to add arguments to parser for CTFFind

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("-o", "--output_folder",
                        type=str,
                        default='./ctffind/',
                        help="Path to folder for storing motion-corrected images (Default: ./ctffind/)")
    parser.add_argument("-p", "--file_prefix",
                        type=str,
                        help="Common prefix of image files (Default: project name).")
    parser.add_argument("--exec_path",
                        type=str,
                        default='/opt/lmod/modules/ctffind/4.1.14/bin/ctffind',
                        help="Path to CTFFind4 executable. (Default: /opt/lmod/modules/ctffind/4.1.14/bin/ctffind)")
    parser.add_argument("-v", "--voltage",
                        type=float,
                        default=300.0,
                        help="Electron beam voltage in keV. (Default: 300.0)")
    parser.add_argument("-cs", "--spherical_aberration",
                        type=float,
                        default=2.7,
                        help="Spherical aberration of objective lens in mrad. (Default: 2.7)")
    parser.add_argument("-ac", "--amp_contrast",
                        type=float,
                        default=0.8,
                        help="Relative amplitude contrast w1, range=(0, 1). (Default: 0.8)")
    parser.add_argument("-ss", "--spec_size",
                        type=int,
                        default=512,
                        help="Size of amplitude spectrum in pixels. (Default: 512)")
    parser.add_argument("-res", "--res_range",
                        type=float,
                        nargs=2,
                        default=[30, 5],
                        help="Range of resolutions in target function in Angstroms. (Default: 30, 5)")
    parser.add_argument("-d", "--defocus_range",
                        type=float,
                        nargs=3,
                        default=[5000, 50000, 500],
                        help="Min, max and step size of initial defocus search in Angstroms. (Default: 5000, 50000, 500)")
    parser.add_argument("-at", "--astigm_type",
                        type=str,
                        help="Type of astigmatism. FLAG USE NOT RECOMMENDED.")
    parser.add_argument("-e", "--exhaustive_search",
                        action="store_true",
                        help="Use exhaustive search algorithm for defocus. Use flag if True.")
    parser.add_argument("-ar", "--astigm_restraint",
                        type=int,
                        help="Restraint on astigmatism in Angstroms.")
    parser.add_argument("-ps", "--phase_shift",
                        action="store_true",
                        help="Estimate phase shift. Use flag if True.")
    
    return parser


def get_args_align():
    """
    Function to add arguments to parser for IMOD alignment

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("rot_angle",
                        type=float,
                        help="Rotational angle of electron beam. Can be obtained from MDOC files.")
    parser.add_argument("-o", "--output_folder",
                        type=str,
                        default='./stacks/',
                        help="Path to folder for storing motion-corrected images (Default: ./stacks/)")
    parser.add_argument("-p", "--file_prefix",
                        type=str,
                        help="Common prefix of image files (Default: project name).")
    parser.add_argument("-s", "--file_suffix",
                        type=str,
                        default='',
                        help="Extra information attached as suffix to output filenames.")
    parser.add_argument("--no_rawtlt",
                        action="store_true",
                        help="Use information in filenames to determine tilt angles (rather than using .rawtlt files).")
    parser.add_argument("-fs", "--fiducial_size",
                        type=float,
                        default=0.0,
                        help="Size (in nm) of gold fiducial particles. Ignore flag if no fiducial.")
    parser.add_argument("--adoc_template",
                        type=str,
                        default="/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc",
                        help="Path to template file of BatchRunTomo directives. (Default: /opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc)")
    parser.add_argument("-b", "--stack_bin_factor",
                        type=int,
                        default=4,
                        help="Stack: Raw image stacks downsampling factor. (Default: 4)")
    parser.add_argument("--delete_old_files",
                        action="store_true",
                        help="Preprocessing: Remove original stack when excluding views. Use flag if True.")
    parser.add_argument("--remove_xrays",
                        action="store_true",
                        help="Preprocessing: Attempt to remove X-rays and other artefacts. Use flag if True.")
    parser.add_argument("-ba", "--coarse_align_bin_factor",
                        type=int,
                        default=4,
                        help="Coarse-alignment: Coarse aligned stack binning. (Default: 4)")
    parser.add_argument("--patch_sizes",
                        type=int,
                        nargs=2,
                        default=[200, 200],
                        help="Patch-tracking: Size (in pixels) in X and Y of patches to track. (Default: 200, 200)")
    parser.add_argument("--num_patches",
                        type=int,
                        nargs=2,
                        default=[24, 24],
                        help="Patch-tracking: Number of patches to track in X and Y. (Default: 24, 24)")
    parser.add_argument("--num_iter",
                        type=int,
                        choices=[1, 2, 3, 4],
                        default=4,
                        help="Patch-tracking: Number of iterations. (Max. 4, Default: 4)")
    parser.add_argument("--limits_on_shift",
                        type=int,
                        nargs=2,
                        default=[2, 2],
                        help="Patch-tracking: Maximum extent (in pixels) to which patches are allowed to move during alignment. (Default: 2, 2)")
    parser.add_argument("--adjust_tilt_angles",
                        action="store_true",
                        help="Patch-tracking: Rerun patch-tracking procedure with tilt-angle offset. Use flag if True.")
    parser.add_argument("--num_surfaces",
                        type=int,
                        choices=[1, 2],
                        default=1,
                        help="Fine-alignment: Number of surface(s) for angle analysis. (1|2, Default: 1)")
    parser.add_argument("--mag_option",
                        type=str,
                        choices=['all', 'group', 'fixed'],
                        default='fixed',
                        help="Fine-alignment: Type of magnification solution. (all|group|fixed, Default: fixed)")
    parser.add_argument("--tilt_option",
                        type=str,
                        choices=['all', 'group', 'fixed'],
                        default='fixed',
                        help="Fine-alignment: Type of tilt-angle solution. (all|group|fixed, Default: fixed)")
    parser.add_argument("--rot_option",
                        type=str,
                        choices=['all', 'group', 'one', 'fixed'],
                        default='group',
                        help="Fine-alignment: Type of rotation solution. (all|group|one|fixed, Default: group)")
    parser.add_argument("--beam_tilt_option",
                        type=str,
                        choices=['fixed', 'search'],
                        default='fixed',
                        help="Fine-alignment: Type of beam-tilt solution. (fixed|search, Default: fixed)")
    parser.add_argument("--no_robust_fitting",
                        action="store_true",
                        help="Fine-alignment: Do not use robust fitting. Use flag if True.")
    parser.add_argument("--no_weight_contours",
                        action="store_true",
                        help="Fine-alignment: Do not apply weighting to entire contours from patch-tracking. Use flag if True.")

    return parser


def get_args_align_ext():
    """
    Function to add arguments to parser for IMOD alignment (with external image stacks)

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("rot_angle",
                        type=float,
                        help="Rotational angle of electron beam. Can be obtained from MDOC files.")
    parser.add_argument("pixel_size",
                        type=float,
                        help="Image pixel size in Angstroms.")
    parser.add_argument("-i", "--input_folder",
                        type=str,
                        default='./stacks/',
                        help="Path to folder for storing motion-corrected images (Default: ./stacks/)")
    parser.add_argument("-o", "--output_folder",
                        type=str,
                        default='./stacks/',
                        help="Path to folder for storing motion-corrected images (Default: ./stacks/)")
    parser.add_argument("-p", "--file_prefix",
                        type=str,
                        help="Common prefix of image files (Default: project name).")
    parser.add_argument("-s", "--file_suffix",
                        type=str,
                        default='',
                        help="Extra information attached as suffix to output filenames.")
    parser.add_argument("--no_rawtlt",
                        action="store_true",
                        help="Use information in filenames to determine tilt angles (rather than using .rawtlt files).")
    parser.add_argument("-fs", "--fiducial_size",
                        type=float,
                        default=0.0,
                        help="Size (in nm) of gold fiducial particles. Ignore flag if no fiducial.")
    parser.add_argument("--adoc_template",
                        type=str,
                        default="/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc",
                        help="Path to template file of BatchRunTomo directives. (Default: /opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc)")
    parser.add_argument("-b", "--stack_bin_factor",
                        type=int,
                        default=4,
                        help="Stack: Raw image stacks downsampling factor. (Default: 4)")
    parser.add_argument("--delete_old_files",
                        action="store_true",
                        help="Preprocessing: Remove original stack when excluding views. Use flag if True.")
    parser.add_argument("--remove_xrays",
                        action="store_true",
                        help="Preprocessing: Attempt to remove X-rays and other artefacts. Use flag if True.")
    parser.add_argument("-ba", "--coarse_align_bin_factor",
                        type=int,
                        default=4,
                        help="Coarse-alignment: Coarse aligned stack binning. (Default: 4)")
    parser.add_argument("--patch_sizes",
                        type=int,
                        nargs=2,
                        default=[200, 200],
                        help="Patch-tracking: Size (in pixels) in X and Y of patches to track. (Default: 200, 200)")
    parser.add_argument("--num_patches",
                        type=int,
                        nargs=2,
                        default=[24, 24],
                        help="Patch-tracking: Number of patches to track in X and Y. (Default: 24, 24)")
    parser.add_argument("--num_iter",
                        type=int,
                        choices=[1, 2, 3, 4],
                        default=4,
                        help="Patch-tracking: Number of iterations. (Max. 4, Default: 4)")
    parser.add_argument("--limits_on_shift",
                        type=int,
                        nargs=2,
                        default=[2, 2],
                        help="Patch-tracking: Maximum extent (in pixels) to which patches are allowed to move during alignment. (Default: 2, 2)")
    parser.add_argument("--adjust_tilt_angles",
                        action="store_true",
                        help="Patch-tracking: Rerun patch-tracking procedure with tilt-angle offset. Use flag if True.")
    parser.add_argument("--num_surfaces",
                        type=int,
                        choices=[1, 2],
                        default=1,
                        help="Fine-alignment: Number of surface(s) for angle analysis. (1|2, Default: 1)")
    parser.add_argument("--mag_option",
                        type=str,
                        choices=['all', 'group', 'fixed'],
                        default='fixed',
                        help="Fine-alignment: Type of magnification solution. (all|group|fixed, Default: fixed)")
    parser.add_argument("--tilt_option",
                        type=str,
                        choices=['all', 'group', 'fixed'],
                        default='fixed',
                        help="Fine-alignment: Type of tilt-angle solution. (all|group|fixed, Default: fixed)")
    parser.add_argument("--rot_option",
                        type=str,
                        choices=['all', 'group', 'one', 'fixed'],
                        default='group',
                        help="Fine-alignment: Type of rotation solution. (all|group|one|fixed, Default: group)")
    parser.add_argument("--beam_tilt_option",
                        type=str,
                        choices=['fixed', 'search'],
                        default='fixed',
                        help="Fine-alignment: Type of beam-tilt solution. (fixed|search, Default: fixed)")
    parser.add_argument("--no_robust_fitting",
                        action="store_true",
                        help="Fine-alignment: Do not use robust fitting. Use flag if True.")
    parser.add_argument("--no_weight_contours",
                        action="store_true",
                        help="Fine-alignment: Do not apply weighting to entire contours from patch-tracking. Use flag if True.")


    return parser


def get_args_recon():
    """
    Function to add arguments to parser for IMOD reconstruction

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("--do_positioning",
                        action="store_true",
                        help="Positioning: Perform positioning for the stack. Use flag if True.")
    parser.add_argument("unbinned_thickness",
                        type=int,
                        help="Positioning: Unbinned thickness (in pixels) for samples or whole tomogram.")
    parser.add_argument("--correct_ctf",
                        action="store_true",
                        help="Aligned stack: Correct CTF for aligned stacks. Use flag if True.")
    parser.add_argument("--erase_gold",
                        action="store_true",
                        help="Aligned stack: Erase gold fiducials. Use flag if True.")
    parser.add_argument("--filtering",
                        action="store_true",
                        help="Aligned stack: Perform 2D filtering. Use flag if True.")
    parser.add_argument("-b", "--bin_factor",
                        type=int,
                        default=1,
                        help="Aligned stack: Binning factor for aligned stack.")
    parser.add_argument("thickness",
                        type=int,
                        help="Reconstruction: Thickness (in pixels) for reconstruction.")
    parser.add_argument("--no_trimvol",
                        action="store_true",
                        help="Postprocessing: Do not run Trimvol on reconstruction. Use flag if True.")
    parser.add_argument("--trimvol_reorient",
                        type=str,
                        choices=['none', 'flip', 'rotate'],
                        default='rotate',
                        help="Reorientation in Trimvol. (none|flip|rotate, Default: rotate)")

    return parser


def get_args_ctfsim():
    """
    Function to add arguments to parser for O2R-CTFsim

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("pixel_res",
                        type=float,
                        help="Pixel resolution of motion-corrected images (in Angstroms)")
    parser.add_argument("ds_factor",
                        type=int,
                        help="Downsampling factor (must be same as alignment/reconstruction)")
    parser.add_argument("-rn", "--rootname",
                        type=str,
                        help="Rootname of current project (required if different from project name)")
    parser.add_argument("-d", "--dims",
                        nargs=2,
                        type=int,
                        default=[100, 100],
                        help="Dimensions of simulated CTF in pixels (Default: [100, 100])")

    return parser


def get_args_savurecon():
    """
    Function to add arguments to parser for Savu reconstruction

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("--stacks_folder",
                        type=str,
                        default='./stacks',
                        help="Path to parent folder with stacks")
    parser.add_argument("-rn", "--rootname",
                        type=str,
                        help="Rootname of current project (required if different from project name)")
    parser.add_argument("-s", "--suffix",
                        type=str,
                        default='',
                        help="Suffix of project files")
    parser.add_argument("-e", "--extension",
                        type=str,
                        default='mrc',
                        help="File extension of stacks (Default: mrc)")
    parser.add_argument("-is", "--imod_suffix",
                        type=str,
                        default='ali',
                        help="IMOD file suffix")
    parser.add_argument("-o", "--output_path",
                        type=str,
                        default="./savurecon/",
                        help="Path to output folder (Default: ./savurecon/)")

    return parser


def get_args_rldeconv():
    """
    Function to add arguments to parser for RedLionfish deconvolution

    ARGS:
    None

    OUTPUTs:
    Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path",
                        type=str,
                        help="Path to raw image.")
    parser.add_argument("psf_path",
                        type=str,
                        help="Path to PSF for deconvolving raw image.")
    parser.add_argument("--image_type",
                        type=str,
                        choices=['mrc', 'tiff'],
                        default='mrc',
                        help="File type of raw image. (mrc/tiff, Default: mrc)")
    parser.add_argument("--psf_type",
                        type=str,
                        choices=['mrc', 'tiff'],
                        default='mrc',
                        help="File type of PSF image. (mrc/tiff, Default: mrc)")
    parser.add_argument("output_path",
                        type=str,
                        help="Path to output (deconvolved) image.")
    parser.add_argument("-d", "--device",
                        type=str,
                        choices=['gpu', 'cpu'],
                        default='gpu',
                        help="Device to be used for deconvolution. (gpu/cpu, Default: gpu)")
    parser.add_argument("-n", "--niter",
                        type=int,
                        default=10,
                        help="Max number of iterations used in deconvolution.")
    parser.add_argument("--block",
                        action="store_true",
                        help="Use block-iterative algorithm for deconvolution. Use flag if True.")
    parser.add_argument("--uint",
                        action="store_true",
                        help="Store results as UInt8. Use flag if True.")
    
    return parser


def get_args_aretomo():
    """
    Function to add arguments to parser for AreTomo

    ARGS:
    None

    OUTPUTs:
    Namespace
    kwargs (list) : list of extra parameters to pass to AreTomo, empty if none are passed

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")
    parser.add_argument("aretomo_mode",
                        type=int,
                        help=
                            "Processes to be run in AreTomo, must be set."
                            " 0: alignment only,"
                            " 1: reconstruction only,"
                            " 2: alignment + reconstruction")
    parser.add_argument("rot_angle",
                        type=float,
                        help="Rotational angle of electron beam. Can be obtained from MDOC files.")
    parser.add_argument("--pixel_size",
                        type=float,
                        help="Image pixel size in nm.")
    parser.add_argument("-rn", "--rootname",
                        type=str,
                        help="Rootname of current project (required if different from project name)")
    parser.add_argument("-s", "--suffix",
                        type=str,
                        default='',
                        help="Suffix of project files")
    parser.add_argument("-in", "--input_mrc_folder",
                        type=str,
                        default='./aretomo/',
                        help=
                            "Folder containing input mrcs (Default: ./aretomo)")
    parser.add_argument("-o", "--output_path",
                        type=str,
                        default="./aretomo/",
                        help="Path to output folder (Default: ./aretomo)")
    parser.add_argument("-ta", "--tilt_angles",
                        type=str,
                        help=
                            "Path to text file containing tilt angles, usually .tlt."
                            " Defaults to <project_name>_<suffix>.tlt")
    parser.add_argument("--volz",
                        type=int,
                        default=-1,
                        help=
                            "Z-height of reconstructed volume in voxels (unbinned),"
                            " ignored if only alignment is performed."
                            " Defaults to -1, where this will be set automatically"
                            " by the rule of thumb."
                            " VolZ = 200 + sample_thickness * pixel_size"
                            " Setting value > 0 overrides automatic setting")
    parser.add_argument("--sample_thickness",
                        type=float,
                        default=-1,
                        help=
                            "Sample thickness in nm, used to set VolZ automatically."
                            " Ignored if VolZ is set to >0, or only alignment is done")
    parser.add_argument("--output_binning",
                        type=int,
                        default=4,
                        help=
                            "Binning to be applied to saved .mrc file."
                            " Default = 4")
    parser.add_argument("--recon_algo",
                        type=int,
                        default=0,
                        help=
                            "Reconstruction algorithm to be used."
                            " 0: WBP (default),"
                            " 1: SART")
    
    return parser
