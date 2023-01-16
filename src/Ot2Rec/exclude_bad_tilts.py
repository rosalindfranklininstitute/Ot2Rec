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


import argparse
import os

import mrcfile
import numpy as np
import yaml
from tqdm import tqdm
from glob import glob

from . import logger as logMod
from . import magicgui as mgMod
from . import params as prmMod


class ExcludeBadTilts:
    """
    Class encapsulating a ExcludeBadTilts object

    This class excludes very bright/dark "bad" tilts / projections
    which are normally seen at large tilt angles.
    Excluded projections are taken out of the .st files after motion correction
    and before alignment. These projections are kept in a separate .mrc stack.
    The .tlt files are also edited accordingly.

    The <proj_name>_excludebadtilt_mdout.yaml file contains details of the removed
    tilts. These will be parsed into the report later.
    """

    def __init__(
        self,
        project_name: str,
        params_in: prmMod.Params,
        logger_in: logMod.Logger,
    ):
        """Initialises a ExcludeBadTilts object

        Args:
            project_name (str): name of current project
            params_in (prmMod.Params): parameters for removing bad tilts
            logger_in (logMod.Logger): keep record of progress and errors
        """

        self.proj_name = project_name
        self.pObj = params_in
        self.params = self.pObj.params
        self.logObj = logger_in
        self.md_out = {}
        self._get_internal_metadata()
              
        # Set metadata dicts
        self.md_out["Excluded_Tilt_Index"] = {}
        self.md_out["Excluded_St_Files"] = {}
        self.md_out["Excluded_Tilt_Angles"] = {}

    def _get_internal_metadata(self):
        """Prepare internal metadata from params object
        """

        # Process list
        self.md_out["process_list"] = dict(
            zip(
                range(
                    1,
                    len(self.params["System"]["process_list"]) + 1,
                ),
                self.params["System"]["process_list"]
            )
        )

    def _determine_tilts_to_exclude(
        self,
        img: np.ndarray,
    ) -> list:
        """Determines which tilts to exclude based on user parameters

        Args:
            img (np.ndarray): (proj, x, y) of tilt series

        Returns:
            list: list of index of tilts to exclude (starts at 0)
        """
        stack_mean = np.mean(img)
        stack_stdev = np.std(img)
        exclude_factor = float(self.params["EBT_setup"]["exclude_factor"])
        min_accept = stack_mean - (exclude_factor * stack_stdev)
        max_accept = stack_mean + (exclude_factor * stack_stdev)

        tilts_to_exclude = []
        for proj in range(img.shape[0]):
            tilt_mean = np.mean(img[proj,:,:])
            if (tilt_mean < min_accept) or (tilt_mean > max_accept):
                tilts_to_exclude.append(proj)
        
        return tilts_to_exclude            

    def _exclude_tilt_one_ts(
        self,
        i: int
    ):
        """Excludes tilts from one tilt series, saves excluded tilts as a
        separate .mrc file and edits .tlt accordingly. Old .tlt file is
        renamed to *_original.tlt. Index (starts at 0) of excluded tilts saved
        to <proj_name>_exclude_bad_tilts_mdout.yaml

        Args:
            i (int): Index of tilt series on the process list
        """
        # Read image and determine tilts to exclude
        st_file = self.params["EBT_setup"]["input_mrc"][i]
        with mrcfile.mmap(st_file) as mrc:
            img = mrc.data
        
        tilts_to_exclude = self._determine_tilts_to_exclude(img)
        self.md_out["Excluded_Tilt_Index"][i] = tilts_to_exclude

        
        # Take excluded tilt angles out of rawtlt file
        rawtlt_file = self.params["EBT_setup"]["tilt_angles"][i]
        tilt_angles_to_exclude = {}
        with open(rawtlt_file, "r") as f:
            all_tilt_angles = f.readlines()
        if len(all_tilt_angles) == img.shape[0]:
            for tilt in tilts_to_exclude:
                tilt_angles_to_exclude[tilt] = all_tilt_angles[tilt]
            for tilt in sorted(tilts_to_exclude, reverse=True):
                del all_tilt_angles[tilt]
            with open(rawtlt_file, "w+") as f:
                f.writelines(all_tilt_angles)
            self.md_out["Excluded_Tilt_Angles"][i] = tilt_angles_to_exclude

        else:
            raise ValueError(
                f".rawtlt file has {len(all_tilt_angles)} lines, should have "
                f"{img.shape[0]} lines instead.")

        # Write dict of index:excluded tilt angles to separate file
        excluded_ta_file = rawtlt_file.replace(".rawtlt", "_excl.rawtlt")
        with open(excluded_ta_file, "w") as f:
            yaml.dump(tilt_angles_to_exclude, f, indent=4, sort_keys=False)
        
        # Create stack of excluded tilts
        exclude_filename = st_file.replace(".st", "_excl.st")
        with mrcfile.new_mmap(
            exclude_filename,
            shape=(len(tilts_to_exclude), img.shape[1], img.shape[2]),
        ) as mrc:
            excluded_stack = img[tilts_to_exclude, :, :]
            mrc.set_data(excluded_stack)
        self.md_out["Excluded_St_Files"][i] = exclude_filename

    def run_exclude_bad_tilts(self):
        """Method to exclude bad tilts for all tilt series
        """
        ts_list = self.params["System"]["process_list"]
        tqdm_iter = tqdm(ts_list, ncols=100)
        for i, curr_ts in enumerate(tqdm_iter):
            tqdm_iter.set_description(f"Removing bad tilts from TS {curr_ts}")
            self._exclude_tilt_one_ts(i)
        self.export_metadata()

    def export_metadata(self):
        """Method to export metadata as
        <proj_name>_exclude_bad_tilts_mdout.yaml
        """

        yaml_file = f"{self.proj_name}_exclude_bad_tilts_mdout.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(
                self.md_out,
                f,
                indent=4,
                sort_keys=False,
            )


def update_yaml(args: dict):
    """Updates yaml file <proj_name>_exclude_bad_tilts.yaml

    Args:
        args (dict): User arguments from magicgui
    """
    ebt_yaml_name = f"{args.project_name.value}_exclude_bad_tilts.yaml"

    ebt_params = prmMod.read_yaml(
        project_name=args.project_name.value,
        filename=ebt_yaml_name
    )

    # Get input mrc's
    st_file_list = glob(
        f"{args.input_mrc_folder.value}/*/*.st"
    )
    st_file_list.sort()

    # Get tilt angle files
    rawtlt_file_list = glob(
        f"{args.input_mrc_folder.value}/*/*.rawtlt"
    )
    rawtlt_file_list.sort()

    # Ensure # st = # rawtlt
    if len(st_file_list) != len(rawtlt_file_list):
        raise ValueError(
            f"Inconsistent number of aligned TS ({len(st_file_list)}) and "
            f"tlt ({len(rawtlt_file_list)}) files."
        )
    
    else:
        ebt_params.params["EBT_setup"]["input_mrc"] = st_file_list
        ebt_params.params["EBT_setup"]["tilt_angles"] = rawtlt_file_list

    # Extract tilt series number
    ts_list = [
        int(os.path.basename(i).split("_")[-1].split(".")[0]) 
        for i in st_file_list
    ]

    # Set process list
    ebt_params.params["System"]["process_list"] = ts_list

    # Add remaining magicgui values to ebt_params
    ebt_params.params["EBT_setup"]["create_st_files"] = args.create_st_files.value
    ebt_params.params["EBT_setup"]["exclude_factor"] = args.exclude_factor.value

    # update and write yaml file
    with open(ebt_yaml_name, "w") as f:
        yaml.dump(
            ebt_params.params,
            f,
            indent=4,
            sort_keys=False,
        )


def create_yaml(args=None):
    """Subroutine to create new yaml file for excluding bad tilts
    """

    if args is None:
        args = mgMod.get_args_exclude_bad_tilts.show(run=True)

    prmMod.new_exclude_bad_tilts_yaml(args)
    update_yaml(args)


def run():
    """ Method to exclude bad tilts
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "project_name",
        type=str,
        help="Name of current project",
    )
    run_args = parser.parse_args()

    # check that ebt yaml file exists
    ebt_yaml = f"{run_args.project_name}_exclude_bad_tilts.yaml"
    if not os.path.isfile(ebt_yaml):
        raise IOError(
            "Error in Ot2Rec.exclude_bad_tilts.run: yaml file not found"
        )

    # Read in config and metadata
    ebt_config = prmMod.read_yaml(
        project_name=run_args.project_name,
        filename=ebt_yaml,
    )

    # Create Logger object
    log_path = "o2r_exclude_bad_tilts.log"
    try:
        os.remove(log_path)
    except:
        pass
    logger = logMod.Logger(log_path=log_path)

    # Create Exclude Bad Tilts object
    ebt_obj = ExcludeBadTilts(
        project_name=run_args.project_name,
        params_in=ebt_config,
        logger_in=logger,
    )

    # Run exclude bad tilts commands
    ebt_obj.run_exclude_bad_tilts()


def recombine():
    raise NotImplementedError
