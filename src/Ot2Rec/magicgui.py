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


from pathlib import Path

from magicgui import magicgui as mg


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=False,

    project_name={"label": "Project name *"},
    source_folder={"widget_type": "FileEdit",
                   "label": "Source folder *",
                   "mode": "d"},
    folder_prefix={"label": "Folder prefix (if tilt series in subfolders)"},
    file_prefix={"label": "File prefix (if different from project name)"},
    ext={"widget_type": "ComboBox",
         "label": "Image file extension",
         "choices": ["mrc", "tif", "eer"]},
    stack_field={"min": 0,
                 "label": "Stack index field #"},
    index_field={"min": 0,
                 "label": "Image index field #"},
    tiltangle_field={"min": 0,
                     "label": "Tilt angle field #"},
    no_mdoc={"label": "No MDOCs"}
)
def get_args_new_proj(
        project_name="",
        source_folder=Path("../raw/"),
        folder_prefix="",
        file_prefix="",
        ext="mrc",
        stack_field=0,
        index_field=1,
        tiltangle_field=2,
        no_mdoc=False,
):
    """
    Function to add arguments to parser for new project

    ARGS:
    project_name (str)    :: Name of current project
    source_folder (str)   :: Path to folder with raw images (Default: ../raw/)
    folder_prefix (str)   :: Common prefix of raw tilt series folder(s)
    file_prefix (str)     :: Common prefix of raw image files (Default: project)
    ext (str)             :: Extension of raw image files (Default: mrc)
    stack_field (int)     :: Field number of tilt series indices (Default: 0)
    index_field (int)     :: Field number of image indices (Default: 1)
    tiltangle_field (int) :: Field number of tilt angles (Default: 2)
    no_mdoc (bool)        :: True if no MDOC file provided (Default: False)

    OUTPUTs:
    Namespace
    """

    return locals()


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=False,

    project_name={"label": "Project name *"},
    pixel_size={"label": "Pixel size (A) *",
                "step": 0.001},
    output_folder={"label": "MC2 output folder"},
    file_prefix={"label": "File prefix (if different from project name)"},
    exec_path={"label": "Path to MC2 executable"},
    no_gpu={"label": "CPU only?"},
    jobs_per_gpu={"label": "Jobs per GPU",
                  "min": 1},
    gpu_mem_usage={"label": "GPU memory usage (if applicable)",
                   "widget_type": "FloatSlider",
                   "min": 0.1,
                   "max": 2.0},
    use_gain={"label": "Use gain reference?"},
    gain={"label": "Gain reference file (if applicable)",
          "widget_type": "FileEdit",
          "mode": "w"},
    super_res={"label": "Super-resolution images?"},
    discard_top={"label": "# Frames discarded FROM TOP of images",
                 "min": 0},
    discard_bottom={"label": "# Frames discarded FROM BOTTOM of images",
                    "min": 0},
    tolerance={"label": "Alignment error threshold (in pixels)",
               "min": 0},
    max_iter={"label": "Maximum MC2 iterations",
              "min": 1},
    patch_size={"widget_type": "LiteralEvalLineEdit",
                "label": "Patch configurations (Nx, Ny, %overlap)"},
    use_subgroups={"label": "Use subgroups in alignments"}
)
def get_args_mc2(
        project_name="",
        pixel_size=0.0,
        output_folder=Path(Path.cwd() / "motioncor"),
        file_prefix="",
        exec_path=Path("/opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110"),
        no_gpu=False,
        jobs_per_gpu=2,
        gpu_mem_usage=1.0,
        use_gain=False,
        gain="",
        super_res=False,
        discard_top=0,
        discard_bottom=0,
        tolerance=0.5,
        max_iter=10,
        patch_size=[5,5,20],
        use_subgroups=True,
):
    """
    Function to add arguments to parser for MotionCor

    ARGS:
    project_name (str)    :: Name of current project
    pixel_size (float)    :: Image pixel size in Angstroms
    output_folder (str)   :: Path to folder for storing motion-corrected images (Default: ./motioncor/)
    file_prefix (str)     :: Common prefix of raw image files (Default: project)
    no_gpu (bool)         :: Use CPU only for motion-correction
    jobs_per_gpu (int)    :: Number of job instance(s) per GPU
    gpu_mem_usage (float) :: MotionCor2 GPU memory usage
    exec_path (str)       :: Path to MotionCor2 executable
    use_gain (bool)       :: Whether to use gain reference file
    gain (str)            :: Path to gain reference file (leave blank if use_gain==False)
    super_res (bool)      :: True if super-resolution images used
    discard_top (int)     :: Number of frames discarded from top per image
    discard_bottom (int)  :: Number of frames discarded from bottom per image
    tolerance (float)     :: Threshold of alignment errors in pixels
    max_iter (int)        :: Maximum number of iterations performed by MotionCor2
    patch_size (int)      :: Size of patches used in alignment
    use_subgroups (bool)  :: Use subgroups in alignment

    OUTPUTs:
    Namespace
    """
    return locals()


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=False,

    project_name={"label": "Project name *"},
    output_folder={"label": "CTFFind4 output folder",
                   "mode": "d"},
    file_prefix={"label": "File prefix (if different from project name)"},
    exec_path={"label": "Path to CTFFind4 executable"},
    voltage={"label": "Electron beam voltage (in keV)"},
    spherical_aberration={"label": "Objective lens spherical aberration (in mrad)",
                          "step": 0.1},
    amp_contrast={"widget_type": "FloatSlider",
                  "min": 0.0,
                  "max": 1.0,
                  "label": "Relative amplitude constrast w1"},
    spec_size={"label": "Size of amplitude spectrum (in pixels)"},
    res_range={"label": "Target function resolution range (in Angstroms)"},
    defocus_range={"widget_type": "RangeEdit",
                   "label": "Initial defocus search range (in Angstroms) [min, max, step]",
                   "step": 100},
    astigm_type={"label": "Type of astigmatism. USE NOT RECOMMENDED"},
    exhaustive_search={"label": "Use exhaustive search"},
    astigm_restraint={"label": "Restraint on astigmatism (in Angstroms)",
                      "min": 0},
    phase_shift={"label": "Estimate phase shift"}
)
def get_args_ctffind(
        project_name="",
        output_folder=Path(Path.cwd() / "ctffind"),
        file_prefix="",
        exec_path=Path("/opt/lmod/modules/ctffind/4.1.14/bin/ctffind"),
        voltage=300.0,
        spherical_aberration=2.7,
        amp_contrast=0.8,
        spec_size=512,
        res_range=[30, 5],
        defocus_range=range(5000, 50000, 500),
        astigm_type="",
        exhaustive_search=False,
        astigm_restraint=0,
        phase_shift=False,
):
    """
    Function to add arguments to parser for CTFFind

    ARGS:
    project_name (str)           :: Name of current project
    output_folder (str)          :: Path to folder for storing CTFFind4 outputs
    file_prefix (str)            :: Common prefix of raw image files (Default: project)
    exec_path (str)              :: Path to IMOD executable
    voltage (float)              :: Electron beam voltage in keV
    spherical_aberration (float) :: Spherical aberration of objective lens in mrad
    amp_contrast (float)         :: Relative amplitude contrast w1
    res_range (float)            :: Range of resolutions in target function in Angstroms
    defocus_range (float)        :: Min, max and step size of initial defocus search in Angstroms
    astigm_type (str)            :: Type of astigmatism. FLAG USE NOT RECOMMENDED
    exhaustive_search (bool)     :: Use exhaustive search algorithm for defocus
    astigm_restraint (int)       :: Restraint on astigmatism in Angstroms
    phase_shift (bool)           :: Estimate phase shift

    OUTPUTs:
    Namespace
    """

    return locals()


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=False,

    project_name={"label": "Project name *"},
    rot_angle={"label": "Beam rotation angle *",
               "min": -180.00,
               "max": 180.00,
               "step": 0.01},
    image_dims={"widget_type": "LiteralEvalLineEdit",
                "label": "Image dimensions (in pixels) *"},
    output_folder={"label": "IMOD output folder",
                   "mode": "d"},
    file_prefix={"label": "File prefix (if different from project name)"},
    file_suffix={"label": "IMOD file suffix (if applicable)"},
    no_rawtlt={"label": "Ignore .rawtlt files?"},
    fiducial_size={"label": "Size of fiducial particles in nm (0.0 if fiducial-free)",
                   "min": 0.0,
                   "step": 0.01},
    adoc_template={"label": "Path to BatchRunTomo directives template"},
    stack_bin_factor={"label": "Stack: Raw image stacks downsampling factor",
                      "min": 1},
    delete_old_files={"label": "Preprocessing: Remove original stack when excluding views"},
    remove_xrays={"label": "Preprocessing: Remove X-rays and other artefacts"},
    coarse_align_bin_factor={"label": "Coarse-alignment: Coarse aligned stack binning",
                             "min": 1},
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
        rot_angle=0.00,
        image_dims=[1000, 1000],
        output_folder=Path("./stacks"),
        file_prefix="",
        file_suffix="",
        no_rawtlt=False,
        fiducial_size=0.0,
        adoc_template=Path("/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc"),
        stack_bin_factor=4,
        delete_old_files=False,
        remove_xrays=True,
        coarse_align_bin_factor=4,
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

    return locals()
