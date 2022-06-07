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
    patch_size={"label": "Patch configurations (Nx, Ny, %overlap)"},
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
    project_name (str) :: Name of current project
    pixel_size (float) :: Image pixel size in Angstroms
    output_folder (str) :: Path to folder for storing motion-corrected images (Default: ./motioncor/)
    file_prefix (str)     :: Common prefix of raw image files (Default: project)
    no_gpu (bool) :: Use CPU only for motion-correction
    jobs_per_gpu (int) :: Number of job instance(s) per GPU
    gpu_mem_usage (float) :: MotionCor2 GPU memory usage
    exec_path (str) :: Path to MotionCor2 executable
    use_gain (bool) :: Whether to use gain reference file
    gain (str) :: Path to gain reference file (leave blank if use_gain==False)
    super_res (bool) :: True if super-resolution images used
    discard_top (int) :: Number of frames discarded from top per image
    discard_bottom (int) :: Number of frames discarded from bottom per image
    tolerance (float) :: Threshold of alignment errors in pixels
    max_iter (int) :: Maximum number of iterations performed by MotionCor2
    patch_size (int) :: Size of patches used in alignment
    use_subgroups (bool) :: Use subgroups in alignment

    OUTPUTs:
    Namespace
    """
    return locals()
