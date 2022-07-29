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
import argparse
import subprocess
import multiprocess as mp
import pandas as pd
from tqdm import tqdm
import yaml

from . import metadata as mdMod
from . import params as prmMod
from . import user_args as uaMod
from . import logger as logMod
from . import magicgui as mgMod


class Quoll:
    """
    Class encapsulating a Quoll(ity) object
    """

    def __init__(self,
                 project_name,
                 params_in,
                 logger_in,
                 ):
        """
        Initialising a Quoll object

        ARGS:
        project_name (str) :: name of current project
        params_in (Params) :: parameters for stack creation
        logger_in (Logger) :: logger object to keep record of progress and errors
        """

        self.proj_name = project_name

        self.logObj = logger_in

        self.pObj = params_in
        self.params = self.pObj.params

        self._get_internal_metadata()

    def _get_internal_metadata(self):
        """
        Method to prepare internal metadata for processing and checking
        """  

        # Check that tile size makes sense
        if self.params["OneImgFRC"]["tile_size"] < 0:
            raise ValueError("Tile size must be at least 0")
        # maybe also check if the tiles > min dim of the image

        if self.params["OneImgFRC"]["tile_size"] > 0:
            # Create tiles directory
            self.tiles_dir = f"{os.path.splitext(self.params['OneImgFRC']['image_fname'])[0]}_tiles"
            os.mkdir(self.tiles_dir)

    def _get_oneimgFRC_command(self):
        """
        Method to get command to run quoll's one image FRC

        ARGS:

        RETURNS:
        list
        """
        cmd = [
            "oneimgFRC",
            self.params['OneImgFRC']['image_fname'],
            str(self.params['OneImgFRC']['pixel_size']),
            "--unit",
            self.params['OneImgFRC']['unit'],
            "-ts",
            str(self.params['OneImgFRC']['tile_size']),
        ]

        if self.params['OneImgFRC']['tile_size'] > 0:
            cmd.append("-td")
            cmd.append(self.tiles_dir)

        if self.params['OneImgFRC']['show_overlay'] is True:
            cmd.append("--show_plot")
        
        if self.params['OneImgFRC']['results_csv'] is not None:
            cmd.append("--save_csv")
        
        if self.params['OneImgFRC']['overlay_fname'] is not None:
            cmd.append("--save_overlay")
        
        if self.params['OneImgFRC']['heatmap_fname'] is not None:
            cmd.append("--save_heatmap")
        
        return cmd

    def run_quoll(self):
        """
        Method to run Quoll's one-image FRC on the image
        """
        cmd = self._get_oneimgFRC_command()

        quoll_run = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="ascii"
        )

        if quoll_run.stderr:
            raise ValueError(f'Quoll: an error has occurred - {quoll_run.stderr}')
        else:
            self.stdout = quoll_run.stdout
        
        print(cmd)
        print(quoll_run.stdout)


"""
PLUGIN METHODS
"""


def create_yaml():
    """
    Subroutine to create new yaml file for Quoll image quality evaluation
    """
    # Parse user inputs
    args = mgMod.get_args_quoll.show(run=True)

    # Create the yaml file, then automatically update it
    prmMod.new_quoll_yaml(args)
    update_yaml(args)


def update_yaml(args):
    """
    Subroutine to update yaml file for Quoll image quality evaluation

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """

    quoll_yaml_name = args.project_name.value + '_quoll.yaml'
    quoll_params = prmMod.read_yaml(project_name=args.project_name.value,
                                    filename=quoll_yaml_name)

    quoll_params.params["OneImgFRC"]["image_fname"] = args.image_fname.value
    quoll_params.params["OneImgFRC"]["pixel_size"] = args.pixel_size.value
    quoll_params.params["OneImgFRC"]["unit"] = args.unit.value
    quoll_params.params["OneImgFRC"]["tile_size"] = args.tile_size.value
    
    if args.tile_size.value > 0:
        quoll_params.params["OneImgFRC"]["tiles_dir"] = f"{os.path.splitext(args.image_fname.value)[0]}_tiles"
    
    if args.save_csv is True:
        quoll_params.params["OneImgFRC"]["results_csv"] = f"{os.path.splitext(args.image_fname.value)[0]}_oneimgfrc.csv"
    
    if args.save_overlay is True:
        quoll_params.params["OneImgFRC"]["overlay_fname"] = f"{os.path.splitext(args.image_fname.value)[0]}_overlay.svg"
    
    if args.save_heatmap is True:
        quoll_params.params["OneImgFRC"]["heatmap_fname"] = f"{os.path.splitext(args.image_fname.value)[0]}_heatmap.tif"

    with open(quoll_yaml_name, 'w') as f:
        yaml.dump(quoll_params.params, f, indent=4, sort_keys=False)


def run():
    """
    Method to run Quoll
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")

    args = parser.parse_args()

    # Check if prerequisite files exist
    quoll_yaml = args.project_name + '_quoll.yaml'

    # Read in config and metadata
    quoll_config = prmMod.read_yaml(project_name=args.project_name,
                                    filename=quoll_yaml)

    # Create Logger object
    logger = logMod.Logger()

    # Create Recon object
    quoll_obj = Quoll(project_name=args.project_name,
                      params_in=quoll_config,
                      logger_in=logger,
                      )

    # Run IMOD
    quoll_obj.run_quoll()
