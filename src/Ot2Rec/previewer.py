# Copyright 2023 Rosalind Franklin Institute
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
import time
from pathlib import Path

import yaml
from magicgui import magicgui
from ot2rec_report import main as o2r_report
from importlib.metadata import version

from Ot2Rec import aretomo as atMod
from Ot2Rec import logger as logMod
from Ot2Rec import metadata as mdMod
from Ot2Rec import mgui_aretomo as atMGUI
from Ot2Rec import mgui_import as importMGUI
from Ot2Rec import mgui_mc2 as mc2MGUI
from Ot2Rec import motioncorr as mcMod
from Ot2Rec import params as prmMod
from Ot2Rec.utils import rename
import shutil
import subprocess


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


def _get_gpu_nvidia_smi():
    """
    TEMPORARY: will move to somewhere else later.
    Subroutine to get visible GPU ID(s) from nvidia-smi
    """

    nv_uuid = subprocess.run(
        ["nvidia-smi", "--list-gpus"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="ascii",
        check=True,
    )
    nv_processes = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=gpu_uuid", "--format=csv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="ascii",
        check=True,
    )

    # catch the visible GPUs
    if nv_uuid.returncode != 0 or nv_processes.returncode != 0:
        self.logObj.logger.critical(
            msg=f"nvidia-smi returned an error: {nv_uuid.stderr}",
        )
        raise AssertionError(
            f"Error in Ot2Rec.Motioncorr._get_gpu_from_nvidia_smi: "
            f"nvidia-smi returned an error: {nv_uuid.stderr}"
        )

    nv_uuid = nv_uuid.stdout.strip("\n").split("\n")
    nv_processes = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=gpu_uuid", "--format=csv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="ascii",
        check=True,
    )
    visible_gpu = []
    for gpu in nv_uuid:
        id_idx = gpu.find("GPU ")
        uuid_idx = gpu.find("UUID")

        gpu_id = gpu[id_idx + 4 : id_idx + 6].strip(" ").strip(":")
        gpu_uuid = gpu[uuid_idx + 5 : -1].strip(" ")

        # discard the GPU hosting a process
        if gpu_uuid not in nv_processes.stdout.split("\n"):
            visible_gpu.append(gpu_id)

    if not visible_gpu:
        self.logObj.logger.critical(
            f"{len(nv_uuid)} GPU detected, but none of them is free.",
        )
        raise ValueError(
            f"Error in metadata._get_gpu_from_nvidia_smi: {len(nv_uuid)} GPU detected, "
            "but none of them is free."
        )
    return visible_gpu


@magicgui(
    call_button="Preview Ot2Rec Tomograms",
    layout="vertical",
    mdocs_directory={
        "widget_type": "FileEdit",
        "label": "Directory where mdocs are stored*",
        "mode": "d",
    },
    micrograph_directory={
        "widget_type": "FileEdit",
        "label": "Directory where raw micrographs are stored*",
        "mode": "d",
    },
    update_dates_for_warp={"label": "Convert mdoc dates to yy-mmm-dd for Warp?"},
    tomogram_thickness={
        "min": 0,
        "step": 0.1,
        "label": "Thickness of tomogram in nm",
    },
    binning={
        "min": 1,
        "label": "Tomogram binning factor",
    },
    aretomo_path={
        "widget_type": "FileEdit",
        "label": "AreTomo executable (optional)",
        "tooltip": "Leave as AreTomo to use module loaded version.",
        "mode": "r",
    },
)
def run_previewer(
    mdocs_directory: Path,
    micrograph_directory: Path,
    update_dates_for_warp: bool = False,
    tomogram_thickness: float = 300,
    binning: int = 4,
    aretomo_path: Path = "AreTomo",
):
    log_general = logMod.Logger(name="general", log_path="o2r_general.log")
    log_general.logger.info("Ot2Rec-Previewer started.")

    # Check that motioncor2 and AreTomo and IMOD are on the path
    if shutil.which("MotionCor2_1.4.0_Cuda110") is None:
        raise ImportError(
            "MotionCor2_1.4.0_Cuda110 unavailable, try module load motioncor2"
        )
    if shutil.which(aretomo_path) is None:
        raise ImportError(f"{aretomo_path} is not available, try module load aretomo")
    if shutil.which("imod") is None:
        raise ImportError(f"IMOD is unavailable, try module load imod")
    visible_gpu = _get_gpu_nvidia_smi()
    if len(visible_gpu) < 1:
        raise RuntimeError("GPU unavailable so motioncor cannot proceed. Aborting now.")

    # Rename files according to mdocs
    rename.rename_all(
        mdocs_directory=mdocs_directory,
        micrograph_directory=micrograph_directory,
        update_dates_for_warp=update_dates_for_warp,
    )

    # Collect raw images and produce main metadata
    new_proj_params = asObject(importMGUI.get_args_new_proj(return_only=True))
    new_proj_params.source_folder = micrograph_directory
    new_proj_params.mdocs_folder = "./ot2rec_mdocs"
    new_proj_params.stack_field = -3
    new_proj_params.index_field = -2
    new_proj_params.tiltangle_field = -1

    # Get proj name and ext
    micrograph_name = os.listdir(micrograph_directory)[0]
    new_proj_params.project_name = "_".join(micrograph_name.rsplit("_")[0:-3])
    new_proj_params.ext = os.path.splitext(micrograph_name)[-1][1:]

    prmMod.new_master_yaml(new_proj_params)

    # Create empty Metadata object
    # Master yaml file will be read automatically
    log_general.logger.info("Aggregating metadata...")
    meta = mdMod.Metadata(project_name=new_proj_params.project_name, job_type="master")
    meta.params["mdocs_folder"] = "./ot2rec_mdocs"

    # Get master metadata and acquisition settings from mdocs and save as yaml
    meta.create_master_metadata_from_mdocs(mdocs_folder="./ot2rec_mdocs")
    if not new_proj_params.no_mdoc:
        meta.get_mc2_temp()
        meta.get_acquisition_settings()

    master_md_name = f"{new_proj_params.project_name}_master_md.yaml"
    acqui_md_name = f"{new_proj_params.project_name}_acquisition_md.yaml"
    with open(master_md_name, "w") as f:
        yaml.dump(meta.metadata, f, indent=4)
    with open(acqui_md_name, "w") as g:
        yaml.dump(meta.acquisition, g, indent=4)

    log_general.logger.info("All metadata successfully aggregated.")

    # Motion correction with MotionCor2
    mc2_params = asObject(mc2MGUI.get_args_mc2(return_only=True))
    mc2_params.project_name = new_proj_params.project_name
    mc2_params.pixel_size = meta.acquisition["pixel_spacing"]
    mc2_params.exec_path = "MotionCor2_1.4.0_Cuda110"
    prmMod.new_mc2_yaml(mc2_params)
    mcMod.update_yaml(mc2_params)

    log_general.logger.info("Motion correction started.")
    mcMod.run(exclusive=False, args_in=mc2_params)
    log_general.logger.info("Motion correction successful.")

    time.sleep(2)

    # Set up AreTomo Mode 2
    at_params_dict = atMGUI.get_args_aretomo(return_only=True)
    at_params = asObject(at_params_dict)
    at_params.project_name = new_proj_params.project_name
    at_params.aretomo_mode = 2
    at_params.pixel_size = meta.acquisition["pixel_spacing"]
    at_params.rot_angle = meta.acquisition["rotation_angle"]
    at_params.input_mrc_folder = Path("./aretomo")
    at_params.input_ext = ".st"
    at_params.sample_thickness = tomogram_thickness
    at_params.output_binning = binning
    at_params.aretomo_path = str(aretomo_path)

    log_aretomo = logMod.Logger(name="aretomo", log_path="o2r_aretomo_align-recon.log")
    prmMod.new_aretomo_yaml(at_params)
    log_aretomo.logger.info("AreTomo metadata file created.")
    atMod.update_yaml(at_params_dict)

    log_general.logger.info("Alignment and reconstruction (AreTomo) started.")

    aretomo_config = prmMod.read_yaml(
        project_name=new_proj_params.project_name,
        filename=f"{new_proj_params.project_name}_aretomo_align-recon.yaml",
    )

    aretomo_obj = atMod.AreTomo(
        project_name=new_proj_params.project_name,
        params_in=aretomo_config,
        logger_in=log_aretomo,
    )

    # Run AreTomo commands
    aretomo_obj.run_aretomo_all()
    log_general.logger.info("Alignment and reconstruction (AreTomo) successful.")

    # Run Ot2Rec Report
    log_general.logger.info("Report generation started.")
    ot2rec_report_args = o2r_report.get_args_o2r_report
    ot2rec_report_args.project_name.value = new_proj_params.project_name
    ot2rec_report_args.processes.value = [
        o2r_report.Choices.motioncor2,
        o2r_report.Choices.aretomo_align,
        o2r_report.Choices.aretomo_recon,
    ]
    ot2rec_report_args.notes.value = f"""
    This version of Ot2Rec: {version('Ot2Rec')}
    MotionCor2 version: MotionCor2_1.4.0_Cuda110
    AreTomo version: {aretomo_path}
    """
    ot2rec_report_args.to_slides.value = True
    ot2rec_report_args.to_html.value = True

    o2r_report.main(args=ot2rec_report_args)

    log_general.logger.info("Report generation successful.")
    log_general.logger.info("All Ot2Rec-Previewer tasks finished.")


def run_previewer_with_mgui():
    run_previewer.show(run=True)
