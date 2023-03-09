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
import yaml

from . import logger as logMod
from . import params as prmMod
from . import metadata as mdMod
from . import motioncorr as mcMod


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=True,

    project_name={"label": "Project name *"},
    pixel_size={"label": "Pixel size (A) *",
                "step": 0.001},
    output_folder={"label": "MC2 output folder"},
    file_prefix={"label": "File prefix (if different from project name)"},
    exec_path={"widget_type": "FileEdit",
               "mode": "w",
               "label": "Path to MC2 executable (Default: MotionCor2_1.4.0_Cuda110)"},
    gpu_mem_usage={"label": "GPU memory usage (if applicable)",
                   "min": 0.0,
                   "max": 1.0,
                   "step": 0.05,
    },
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
        exec_path="",
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
    logger = logMod.Logger(log_path="o2r_motioncor2.log")
    args = asObject(locals())

    if locals()['exec_path'] == Path("."):
        args.exec_path = "MotionCor2_1.4.0_Cuda110"

    prmMod.new_mc2_yaml(args)
    mcMod.update_yaml(args)

    logger(message="MotionCor2 metadata file created.")

    return "Done. You can close this window now."
