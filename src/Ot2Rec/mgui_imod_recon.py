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
from . import recon


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=True,

    project_name={"label": "Project name *"},
    do_positioning={"label": "Positioning: Do positioning?"},
    unbinned_thickness={"label": "Positioning: Unbinned thickness (in pixels) for samples or whole tomogram *",
                        "min": 0,
                        "max": 50000,
                        "step": 100},
    correct_ctf={"label": "Aligned stack: Correct CTF for aligned stacks?"},
    erase_gold={"label": "Aligned stack: Erase gold fiducials?"},
    filtering={"label": "Aligned stack: Perform 2D filtering?"},
    bin_factor={"label": "Aligned stack: Binning factor for aligned stack",
                "min": 1},
    thickness={"label": "Reconstruction: Thickness (in pixels) for reconstruction *",
               "min": 0,
               "max": 50000,
               "step": 100},
    use_sirt={"label": "Use SIRT?"},
    sirt_iter={"label": "# of SIRT iterations (if applicable)"},
    trimvol={"label": "Postprocessing: Run Trimvol on reconstruction"},
    trimvol_reorient={"widget_type": "RadioButtons",
                      "label": "Postprocessing: Reorientation in Trimvol (if applicable)",
                      "choices": ["none", "flip", "rotate"]}
)
def get_args_recon(
        project_name="",
        do_positioning=False,
        unbinned_thickness=1500,
        correct_ctf=False,
        erase_gold=False,
        filtering=False,
        bin_factor=1,
        thickness=1500,
        use_sirt=False,
        sirt_iter=10,
        trimvol=True,
        trimvol_reorient="rotate"
):
    """
    Function to add arguments to parser for IMOD reconstruction

    ARGS:
    project_name (str)       :: Name of current project
    do_positioning (bool)    :: Whether to perform positioning
    unbinned_thickness (int) :: Unbinned thickness (in pixels) for samples or whole tomogram for positioning
    correct_ctf (bool)       :: Whether to correct CTF for aligned stacks
    erase_gold (bool)        :: Whether to erase gold fiducials
    filtering (bool)         :: Whether to perform 2D filtering
    bin_factor (int)         :: Binning factor for aligned stack
    thickness (int)          :: Thickness (in pixels) for reconstruction
    trimvol (bool)           :: Run Trimvol on reconstruction
    trimvol_reorient (str)   :: Reorientation in Trimvol

    OUTPUTs:
    Namespace
    """
    logger = logMod.Logger(log_path="o2r_imod_recon.log")
    args = asObject(locals())

    # Parse user inputs
    if args is None:
        args = mgMod.get_args_recon.show(run=True)

    prmMod.new_recon_yaml(args)
    recon.update_yaml(args)

    logger(message="IMOD alignment metadata file created.")


    return "Done. You can close this window now."
