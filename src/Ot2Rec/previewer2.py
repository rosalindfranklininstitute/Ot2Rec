from magicgui import magicgui
from pathlib import Path
from Ot2Rec.utils import rename
from Ot2Rec import logger as logMod
from Ot2Rec import mgui_import as importMGUI
from Ot2Rec import params as prmMod
from Ot2Rec import metadata as mdMod
import os
import yaml


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
    meta = mdMod.Metadata(project_name=new_proj_params.project_name, job_type="master")
    meta.params["mdocs_folder"] = "./ot2rec_mdocs"

    # # Create master metadata and serialise it as yaml file
    meta.create_master_metadata_from_mdocs(mdocs_folder="./ot2rec_mdocs")
    if not new_proj_params.no_mdoc:
        meta.get_mc2_temp()
    #     meta.get_acquisition_settings()

    master_md_name = f"{new_proj_params.project_name}_master_md.yaml"
    acqui_md_name = f"{new_proj_params.project_name}_acquisition_md.yaml"
    with open(master_md_name, "w") as f:
        yaml.dump(meta.metadata, f, indent=4)
    # with open(acqui_md_name, "w") as g:
    #     yaml.dump(meta.acquisition, g, indent=4)

    logger = logMod.Logger(log_path="o2r_general.log")
    logger(level="info", message="Master metadata file created.")
