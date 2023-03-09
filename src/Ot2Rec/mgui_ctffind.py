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
from . import ctffind


class asObject(object):
    def __init__(self, dict_obj):
        self.__dict__ = dict_obj


@mg(
    call_button="Create config file",
    layout="vertical",
    result_widget=True,

    project_name={"label": "Project name *"},
    output_folder={"label": "CTFFind4 output folder",
                   "mode": "d"},
    file_prefix={"label": "File prefix (if different from project name)"},
    exec_path={"widget_type": "FileEdit",
               "mode": "w",
               "label": "Path to CTFFind4 executable (Default: ctffind)"},
    voltage={"label": "Electron beam voltage (in keV)"},
    spherical_aberration={"label": "Objective lens spherical aberration (in mrad)",
                          "step": 0.1},
    amp_contrast={"widget_type": "FloatSlider",
                  "min": 0.0,
                  "max": 1.0,
                  "label": "Relative amplitude constrast w1"},
    spec_size={"label": "Size of amplitude spectrum (in pixels)"},
    res_range={"label": "Target function resolution range (in Angstroms)"},
    defocus_range={"widget_type": "LiteralEvalLineEdit",
                   "label": "Initial defocus search range (in Angstroms) [min, max, step]"},
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
        exec_path="",
        voltage=300.0,
        spherical_aberration=2.7,
        amp_contrast=0.8,
        spec_size=512,
        res_range=[30, 5],
        defocus_range=[5000, 50000, 500],
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
    logger = logMod.Logger(log_path="o2r_ctffind.log")
    args = asObject(locals())

    if locals()['exec_path'] == Path("."):
        args.exec_path = "ctffind"

    # Create the yaml file, then automatically update it
    prmMod.new_ctffind_yaml(args)
    ctffind.update_yaml(args)

    logger(message="CTFFind metadata file created.")

    return "Done. You can close this window now."
