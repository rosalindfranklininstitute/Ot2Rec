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

from Ot2Rec import aretomo as atMod
from Ot2Rec import logger as logMod
from Ot2Rec import metadata as mdMod
from Ot2Rec import mgui_aretomo as atMGUI
from Ot2Rec import mgui_import as importMGUI
from Ot2Rec import mgui_mc2 as mc2MGUI
from Ot2Rec import motioncorr as mcMod
from Ot2Rec import params as prmMod
from Ot2Rec.utils import rename


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


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
    at_params.input_mrc_folder = Path("./AreTomo")
    at_params.input_ext = "st"
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
    ot2rec_report_args.to_slides.value = True
    ot2rec_report_args.to_html.value = True

    o2r_report.main(args=ot2rec_report_args)

    log_general.logger.info("Report generation successful.")
    log_general.logger.info("All Ot2Rec-Previewer tasks finished.")


def run_previewer_with_mgui():
    run_previewer.show(run=True)
