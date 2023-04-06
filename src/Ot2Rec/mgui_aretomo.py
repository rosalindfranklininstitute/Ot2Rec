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
from . import aretomo as atMod


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=False,
    project_name={"label": "Project name *"},
    aretomo_mode={
        "label": "AreTomo Mode*. 0: align, 1: recon, 2: align + recon",
        "min": 0,
        "max": 2,
        "step": 1,
    },
    rot_angle={
        "label": "Rotation angle of electron beam, can be obtained from mdoc",
        "min": -180.0000,
        "max": 180.0000,
    },
    pixel_size={
        "label": "Pixel size in A",
        "min": 0.001,
    },
    rootname={
        "label": "Rootname of current project (required if different from project name"
    },
    suffix={"label": "Suffix of project files"},
    input_mrc_folder={
        "label": "Folder containing input mrc's",
        "mode": "d",
    },
    input_ext={
        "label": "Extension of input mrc files",
        "tooltip": ".st or .mrc usually",
    },
    output_path={
        "label": "Path to output folder",
        "mode": "d",
    },
    tilt_angles={"label": "Path to text file containing tilt angles, usually .tlt"},
    volz={
        "label": "Z-height of reconstructed volume in unbinned voxels.",
        "min": -1,
        "max": 50000,
        "step": 1,
    },
    sample_thickness={
        "label": "Sample thickness in nm, used to set volz automatically",
        "min": -1,
        "max": 50000,
        "step": 1,
    },
    output_binning={
        "label": "Binning to be applied to saved .mrc",
        "min": 1,
        "step": 1,
    },
    recon_algo={"label": "Reconstruction algorithm", "choices": ["WBP", "SART"]},
    out_imod={
        "label": "Produce STA output for",
        "choices": ["N/A", "RELION4", "Warp", "Local alignment"],
    },
    dark_tol={
        "label": "Tolerance to remove dark images",
        "tooltip": "Default 0.7, low number = fewer images removed",
    },
    aretomo_path={
        "label": "Path to AreTomo executable (leave blank if module loaded)",
        "tooltip": "Ensure the path is to the correct version to match CUDA",
    },
    return_only={
        "label": "Only return parameters without file creation (not recommended)"
    },
)
def get_args_aretomo(
    project_name="",
    aretomo_mode=0,
    rot_angle=0.001,
    pixel_size=0.00,
    rootname="",
    suffix="",
    input_mrc_folder=Path("./aretomo"),
    input_ext=".st",
    output_path=Path("./aretomo"),
    tilt_angles="",
    volz=-1,
    sample_thickness=-1,
    output_binning=4,
    recon_algo="SART",
    out_imod="N/A",
    dark_tol=0.7,
    aretomo_path="",
    *,
    return_only=False
):
    if return_only:
        return locals()

    logger = logMod.Logger(log_path="o2r_aretomo.log")

    args = asObject(locals())
    prmMod.new_aretomo_yaml(args)
    atMod.update_yaml(args)

    logger(level="info", message=" metadata file created.")

    return
