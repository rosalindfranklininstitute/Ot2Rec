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
import time
import subprocess
import sys
from glob import glob
from pathlib import Path
from ot2rec_report import main as o2r_report

import yaml

from . import logger as logMod
from . import metadata as mdMod
from . import params as prmMod
from . import mgui_import as mgMod

from . import motioncorr as mcMod
from . import ctffind as ctffindMod
from . import align as alignMod
from . import recon as reconMod
from . import aretomo as atMod

from . import mgui_previewer as previewerMGUI
from . import mgui_import as importMGUI
from . import mgui_mc2 as mc2MGUI
from . import mgui_aretomo as atMGUI
from . import mgui_imod_align as imodMGUI


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


def run_previewer():
    """
    Method to run MotionCor2 + Aretomo automatically
    """
    # Get user parameters
    user_params = asObject(
        previewerMGUI.get_params_full_aretomo.show(run=True).asdict()
    )
    assert user_params.project_name != "", "FATAL ERROR: Project name cannot be blank."

    # Collect raw images and produce master metadata
    new_proj_params = asObject(importMGUI.get_args_new_proj(return_only=True))
    new_proj_params.project_name = user_params.project_name
    new_proj_params.source_folder = user_params.source_folder
    new_proj_params.mdocs_folder = user_params.mdocs_folder
    new_proj_params.stack_field = user_params.stack_field
    new_proj_params.index_field = user_params.index_field
    new_proj_params.tiltangle_field = user_params.tiltangle_field
    new_proj_params.ext = user_params.ext

    prmMod.new_master_yaml(new_proj_params)

    # Create empty Metadata object
    # Master yaml file will be read automatically
    meta = mdMod.Metadata(project_name=new_proj_params.project_name, job_type="master")

    # Create master metadata and serialise it as yaml file
    meta.create_master_metadata()
    if not new_proj_params.no_mdoc:
        meta.get_mc2_temp()
        meta.get_acquisition_settings()

    master_md_name = new_proj_params.project_name + "_master_md.yaml"
    acqui_md_name = new_proj_params.project_name + "_acquisition_md.yaml"
    with open(master_md_name, "w") as f:
        yaml.dump(meta.metadata, f, indent=4)
    with open(acqui_md_name, "w") as g:
        yaml.dump(meta.acquisition, g, indent=4)

    logger = logMod.Logger(log_path="o2r_general.log")
    logger(level="info", message="Master metadata file created.")

    # Motion-correction (MotionCor2)
    mc2_params = asObject(mc2MGUI.get_args_mc2(return_only=True))
    mc2_params.project_name = user_params.project_name
    mc2_params.pixel_size = meta.acquisition["pixel_spacing"]
    mc2_params.exec_path = "MotionCor2_1.4.0_Cuda110"

    logger = logMod.Logger(log_path="o2r_motioncor2.log")
    prmMod.new_mc2_yaml(mc2_params)
    logger(level="info", message="MotionCor2 metadata file created.")
    mcMod.update_yaml(mc2_params)

    logger(level="info", message="Motion correction in progress...")
    mcMod.run(exclusive=False, args_in=mc2_params)

    time.sleep(2)

    # Create stacks (IMOD)
    imod_params = asObject(imodMGUI.get_args_align(return_only=True))
    imod_params.project_name = user_params.project_name
    imod_params.pixel_size = meta.acquisition["pixel_spacing"]
    imod_params.image_dims = meta.acquisition["image_size"]
    imod_params.rot_angle = meta.acquisition["rotation_angle"]
    imod_params.output_folder = Path("./stacks/")

    logger = logMod.Logger()
    logger(level="info", message="Creating stacks for reconstruction...")

    prmMod.new_align_yaml(imod_params)
    alignMod.update_yaml(imod_params, logger)
    alignMod.run(newstack=True, do_align=False, exclusive=False, args_in=imod_params)

    # Alignment + reconstruction (AreTomo)
    at_params_dict = atMGUI.get_args_aretomo(return_only=True)
    at_params = asObject(at_params_dict)
    at_params.project_name = user_params.project_name
    at_params.aretomo_mode = 2
    at_params.pixel_size = meta.acquisition["pixel_spacing"]
    at_params.rot_angle = meta.acquisition["rotation_angle"]
    at_params.input_mrc_folder = Path("./stacks/")
    at_params.input_ext = "mrc"
    at_params.sample_thickness = user_params.thickness
    at_params.output_binning = user_params.binning
    at_params.aretomo_path = str(user_params.aretomo_path)

    logger = logMod.Logger(log_path="o2r_aretomo_align-recon.log")
    prmMod.new_aretomo_yaml(at_params)
    logger(level="info", message="AreTomo metadata file created.")
    atMod.update_yaml(at_params_dict)

    logger(level="info", message="AreTomo processing in progress...")

    aretomo_config = prmMod.read_yaml(
        project_name=user_params.project_name,
        filename=f"{user_params.project_name}_aretomo_align-recon.yaml",
    )

    aretomo_obj = atMod.AreTomo(
        project_name=user_params.project_name,
        params_in=aretomo_config,
        logger_in=logger,
    )

    # Run AreTomo commands
    aretomo_obj.run_aretomo_all()

    # Run Ot2Rec report
    ot2rec_report_args = o2r_report.get_args_o2r_report
    ot2rec_report_args.project_name.value = user_params.project_name
    ot2rec_report_args.processes.value = [
        o2r_report.Choices.motioncor2,
        o2r_report.Choices.aretomo_align,
        o2r_report.Choices.aretomo_recon,
    ]
    ot2rec_report_args.to_slides.value = True

    o2r_report.main(args=ot2rec_report_args)
