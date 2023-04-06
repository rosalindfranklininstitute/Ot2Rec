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

from . import mgui_import as importMGUI


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


@mg(
    call_button="Create config file",
    layout="vertical",
    project_name={"label": "Project name *"},
    source_folder={"widget_type": "FileEdit", "label": "Source folder *", "mode": "d"},
    mdocs_folder={"widget_type": "FileEdit", "label": "Mdocs folder *", "mode": "d"},
    ext={
        "widget_type": "ComboBox",
        "label": "Image file extension",
        "choices": ["mrc", "tif", "eer"],
    },
    stack_field={"min": 0, "label": "Stack index field #"},
    index_field={"min": 0, "label": "Image index field #"},
    tiltangle_field={"min": 0, "label": "Tilt angle field #"},
    thickness={"min": 0, "step": 0.1, "label": "Lamella thickness (in nm)"},
    binning={"min": 1, "label": "Output tomogram binning factor"},
    aretomo_path={
        "widget_type": "FileEdit",
        "label": "AreTomo executable",
        "mode": "r",
    },
)
def get_params_full_aretomo(
    project_name="",
    source_folder=Path("../raw"),
    mdocs_folder=Path("../raw"),
    ext="mrc",
    stack_field=0,
    index_field=1,
    tiltangle_field=2,
    thickness=200,
    binning=4,
    aretomo_path="AreTomo",
):
    logger = logMod.Logger("o2r_general.log")
    logger.logger.info("Parameters recorded. You can close the GUI window now.")

    return locals()
