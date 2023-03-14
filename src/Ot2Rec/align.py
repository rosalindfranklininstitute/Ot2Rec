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
import re
import argparse
import subprocess
from glob import glob
import multiprocess as mp
from icecream import ic

import pandas as pd
import numpy as np
from tqdm import tqdm
import yaml
from beautifultable import BeautifulTable as bt

from . import user_args as uaMod
from . import mgui_imod_align as mgMod
from . import metadata as mdMod
from . import params as prmMod
from . import logger as logMod


class Align:
    """
    Class encapsulating an Align object
    """

    def __init__(self,
                 project_name,
                 md_in,
                 params_in,
                 logger_in,
                 ):
        """
        Initialising an Align object

        ARGS:
        project_name (str) :: name of current project
        md_in (Metadata)   :: metadata containing images to be put into stack(s) for alignment
        params_in (Params) :: parameters for stack creation
        logger_in (Logger) :: logger object to keep record of progress and errors
        """

        self.proj_name = project_name

        self.logObj = logger_in

        self.mObj = md_in
        self.meta = pd.DataFrame()
        if self.mObj is not None:
            self.meta = pd.DataFrame(self.mObj.metadata)

        self.pObj = params_in
        self.params = self.pObj.params

        self._get_internal_metadata()
        self.no_processes = False

        self._process_list = self.params['System']['process_list']
        self._check_aligned_images()

    def _get_internal_metadata(self):
        """
        Method to prepare internal metadata for processing and checking
        """
        self.basis_folder = self.params['System']['output_path']
        while self.basis_folder.endswith('/'):
            self.basis_folder = self.basis_folder[:-1]
        self.rootname = self.params['System']['output_rootname']
        while self.rootname.endswith('_'):
            self.rootname = self.rootname[:-1]
        self.suffix = self.params['System']['output_suffix']
        self.output_ext = self.params['System']['output_ext']

        self._align_images = pd.DataFrame(columns=['ts', 'stack_output', 'align_output'])
        for curr_ts in self.params['System']['process_list']:
            subfolder_name = f'{self.rootname}_{curr_ts}{self.suffix}'
            _to_append = pd.DataFrame(
                {'ts': [curr_ts],
                 'stack_output': [f'{self.basis_folder}/{subfolder_name}/{subfolder_name}.{self.output_ext}'],
                 'align_output': [f'{self.basis_folder}/{subfolder_name}/{subfolder_name}_ali.mrc']
                 },
            )
            self._align_images = pd.concat([self._align_images, _to_append],
                                           ignore_index=True,
                                           )

    def _check_aligned_images(self):
        """
        Method to check images which have already been aligned
        """
        # Create new empty internal output metadata if no record exists
        if not os.path.isfile(self.proj_name + '_align_mdout.yaml'):
            self.meta_out = pd.DataFrame(columns=self._align_images.columns)

        # Read in serialised metadata and turn into DataFrame if record exists
        else:
            _meta_record = mdMod.read_md_yaml(project_name=self.proj_name,
                                              job_type='align',
                                              filename=self.proj_name + '_align_mdout.yaml')
            self.meta_out = pd.DataFrame(_meta_record.metadata)
        self.meta_out.drop_duplicates(inplace=True)

        # Compare output metadata and output folder
        # If a file (in specified TS) is in record but missing, remove from record
        if len(self.meta_out) > 0:
            self._missing = self.meta_out.loc[~self.meta_out['align_output'].apply(lambda x: os.path.isfile(x))]
            self._missing_specified = pd.DataFrame(columns=self.meta.columns)

            for curr_ts in self.params['System']['process_list']:
                _to_append = self._missing[self._missing['ts'] == curr_ts]
                self._missing_specified = pd.concat([self._missing_specified, _to_append],
                                                    ignore_index=True,
                                                    )
            self._merged = self.meta_out.merge(self._missing_specified, how='left', indicator=True)
            self.meta_out = self.meta_out[self._merged['_merge'] == 'left_only']

            if len(self._missing_specified) > 0:
                self.logObj(f"Info: {len(self._missing_specified)} images in record missing in folder. "
                            "Will be added back for processing.")

        # Drop the items in input metadata if they are in the output record
        _ignored = self._align_images[self._align_images.align_output.isin(self.meta_out.align_output)]
        if len(_ignored) > 0 and len(_ignored) < len(self._align_images):
            self.logObj(f"Info: {len(_ignored)} images had been processed and will be omitted.")
        elif len(_ignored) == len(self._align_images):
            self.logObj("Info: All specified images had been processed. Nothing will be done.")
            self.no_processes = True

        self._merged = self._align_images.merge(_ignored, how='left', indicator=True)
        self._align_images = self._align_images[self._merged['_merge'] == 'left_only']
        self._process_list = self._align_images['ts'].sort_values(ascending=True).unique().tolist()

    """
    STACK CREATION
    """

    def create_stack_folders(self, single_folder=False):
        """
        Method to create folders for storing stacked images.
        These folders will be used for alignment and reconstruction as well.
        """

        self.basis_folder = self.params['System']['output_path']
        if self.basis_folder.endswith('/'):
            self.basis_folder = self.basis_folder[:-1]

        self.rootname = self.params['System']['output_rootname']
        while self.rootname.endswith('_'):
            self.rootname = self.rootname[:-1]

        self.suffix = self.params['System']['output_suffix']

        # Create the folders and dictionary for future reference
        self._path_dict = {}
        if single_folder:
            subfolder_path = f'{self.basis_folder}'
            os.makedirs(subfolder_path, exist_ok=True)
            for curr_ts in self._process_list:
                self._path_dict[curr_ts] = subfolder_path
        else:
            for curr_ts in self._process_list:
                subfolder_path = f'{self.basis_folder}/{self.rootname}_{curr_ts}{self.suffix}'
                os.makedirs(subfolder_path, exist_ok=True)
                self._path_dict[curr_ts] = subfolder_path


    def _sort_tilt_angles(self,
                          curr_ts: int
                          ):
        """
        Method to sort images within a tilt-series according to their tilt angles

        ARGS:
        curr_ts :: index of the tilt-series currently being processed

        RETURNS:
        pandas df
        """

        # Extract metadata for current TS
        meta_ts = self.meta[self.meta['ts'] == curr_ts]

        # Sorting
        meta_ts_sorted = meta_ts.sort_values(by='angles',
                                             axis=0,
                                             ascending=True,
                                             )

        return meta_ts_sorted

    def create_rawtlt(self):
        """
        Method to create rawtlt file for a given tilt-series
        (Note: Rather than grabbing info from file names as done in OTTERec,
               we use information directly from input metadata
        """
        for curr_ts in self._process_list:
            # Define path where the new rawtlt file should go
            rawtlt_file = (f"{self._path_dict[curr_ts]}/{self.params['System']['output_rootname']}_"
                           f"{curr_ts}{self.params['System']['output_suffix']}.rawtlt")

            # Sort the filtered metadata
            # Metadata is fetched in the _sort_tilt_angles method
            meta_ts = self._sort_tilt_angles(curr_ts)

            # Text to go into the rawtlt file
            rawtlt = '\n'.join(meta_ts['angles'].astype(str)) + '\n'

            with open(rawtlt_file, 'w') as f:
                f.write(rawtlt)

    def create_stack(self):
        """
        Method to create stack file for a given tilt-series.
        """
        # Add log entry when job starts
        self.logObj("Ot2Rec-align (IMOD) started: newstack.")

        error_count = 0
        tqdm_iter = tqdm(self._process_list, ncols=100)
        for curr_ts in tqdm_iter:
            tqdm_iter.set_description(f"Creating stack for TS {curr_ts}...")

            # Define path where the new stack file should go
            stack_file = self._align_images[self._align_images['ts'] == curr_ts]['stack_output'].values[0]

            # Sort the filtered metadata
            # Metadata is fetched in the _sort_tilt_angles method
            meta_ts = self._sort_tilt_angles(curr_ts)

            # Create template for newstack
            self._filename_fileinlist = \
                (f"{self._path_dict[curr_ts]}/{self.params['System']['output_rootname']}"
                 f"_{curr_ts}{self.params['System']['output_suffix']}_sources.txt")
            self._stack_template = f"{len(meta_ts)}\n" + '\n0\n'.join(meta_ts['output']) + '\n0\n'
            with open(self._filename_fileinlist, 'w') as f:
                f.write(self._stack_template)

            # Define command for running newstack
            cmd = ['newstack',
                   '-fileinlist', self._filename_fileinlist,
                   '-output', stack_file,
                   '-bin', str(self.params['BatchRunTomo']['setup']['stack_bin_factor']),
                   ]

            # Run newstack to create stack
            run_newstack = subprocess.run(cmd,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT,
                                          check=True,
                                          )

            try:
                assert(not run_newstack.stderr)
            except:
                error_count += 1
                self.logObj(level='error',
                            message='newstack: An error has occurred ({run_newstack.returncode}) on stack{curr_ts}.')

            self.stdout = run_newstack.stdout
            self.update_align_metadata(ext=False)
            self.export_metadata()

        if error_count == 0:
            self.logObj("All Ot2Rec-align (IMOD): newstack jobs successfully finished.")
        else:
            self.logObj(level='warning',
                        message="All Ot2Rec-align (IMOD): newstack jobs finished. {error_count} of {len(tqdm_iter)} jobs failed.")


    """
    ALIGNMENT - BATCHTOMO
    """

    def _get_adoc(self):
        """
        Method to create directives for batchtomo alignment
        """

        # Template for directive file
        adoc_temp = """
setupset.currentStackExt = <ext>
setupset.copyarg.stackext = <ext>
setupset.copyarg.dual = 0
setupset.copyarg.userawtlt = <use_rawtlt>
setupset.copyarg.pixel = <pixel_size>
setupset.copyarg.rotation = <rot_angle>
setupset.copyarg.gold = <gold_size>
setupset.copyarg.skip = <excl_views>
setupset.systemTemplate = <adoc_template>

runtime.Excludeviews.any.deleteOldFiles = <delete_old_files>
runtime.Preprocessing.any.removeXrays = <remove_xrays>

comparam.prenewst.newstack.BinByFactor = <aligned_bin_factor>

runtime.AlignedStack.any.binByFactor = <aligned_bin_factor>
"""

        fiducial_temp = """
runtime.Positioning.any.wholeTomogram = 1
runtime.Fiducials.any.trackingMethod = 2

runtime.RAPTOR.any.useAlignedStack = 1
runtime.RAPTOR.any.numberOfMarkers = <num_beads>

comparam.track.beadtrack.SobelFilterCentering = 1
comparam.track.beadtrack.ScalableSigmaForSobel = 0.12

comparam.newst.newstack.TaperAtFill = 1,1
comparam.newst.newstack.AntialiasFilter = -1
comparam.golderaser.ccderaser.ExpandCircleIterations = 3
comparam.eraser.ccderaser.PeakCriterion = 8.0
comparam.eraser.ccderaser.DiffCriterion = 6.0

runtime.Fiducials.any.seedingMethod = 3
comparam.track.beadtrack.LightBeads = 0
comparam.track.beadtrack.LocalAreaTracking = 1
comparam.track.beadtrack.LocalAreaTargetSize = <size_of_patches>
comparam.autofidseed.autofidseed.TwoSurfaces = 0
comparam.autofidseed.autofidseed.TargetNumberOfBeads = <num_beads>

comparam.align.tiltalign.SurfacesToAnalyze = 1
comparam.align.tiltalign.MagOption = 0
comparam.align.tiltalign.TiltOption = 0
comparam.align.tiltalign.RotOption = -1
comparam.align.tiltalign.BeamTiltOption = 2
"""

        patchtrack_temp = """
runtime.Fiducials.any.trackingMethod = 1

comparam.xcorr_pt.tiltxcorr.SizeOfPatchesXandY = <size_of_patches>
comparam.xcorr_pt.tiltxcorr.NumberOfPatchesXandY = <num_of_patches>
comparam.xcorr_pt.tiltxcorr.ShiftLimitsXandY = <limits_on_shift>
comparam.xcorr_pt.tiltxcorr.IterateCorrelations = <num_iterations>
runtime.PatchTracking.any.adjustTiltAngles = <adj_tilt_angles>
comparam.xcorr_pt.imodchopconts.LengthOfPieces = -1

comparam.align.tiltalign.SurfacesToAnalyze = <num_surfaces>
comparam.align.tiltalign.MagOption = <mag_option>
comparam.align.tiltalign.TiltOption = <tilt_option>
comparam.align.tiltalign.RotOption = <rot_option>
comparam.align.tiltalign.BeamTiltOption = <beamtilt_option>
comparam.align.tiltalign.RobustFitting = <use_robust>
comparam.align.tiltalign.WeightWholeTracks = <weight_contours>
        """

        fiducial = self.params['BatchRunTomo']['setup']['gold_size'] > 0

        if fiducial:
            adoc_temp = adoc_temp + fiducial_temp
        else:
            adoc_temp = adoc_temp + patchtrack_temp

        convert_dict = {
            'ext': self.params['System']['output_ext'],
            'use_rawtlt': 1 if self.params['BatchRunTomo']['setup']['use_rawtlt'] else 0,
            'pixel_size': self.params['BatchRunTomo']['setup']['pixel_size'] * self.params['BatchRunTomo']['setup']['stack_bin_factor'],
            'rot_angle': self.params['BatchRunTomo']['setup']['rot_angle'],
            'excl_views': "" if self.params["BatchRunTomo"]["setup"]["excluded_views"] == [0] \
            else f'{",".join(map(str, self.params["BatchRunTomo"]["setup"]["excluded_views"]))}',
            'gold_size': self.params['BatchRunTomo']['setup']['gold_size'] if fiducial else 0,
            'adoc_template': self.params['BatchRunTomo']['setup']['adoc_template'],
            'stack_bin_factor': self.params['BatchRunTomo']['setup']['stack_bin_factor'],
            'aligned_bin_factor': self.params['BatchRunTomo']['setup']['aligned_bin_factor'],

            'delete_old_files': 1 if self.params['BatchRunTomo']['preprocessing']['delete_old_files'] else 0,
            'remove_xrays': 1 if self.params['BatchRunTomo']['preprocessing']['remove_xrays'] else 0,

            'num_beads': self.params['BatchRunTomo']['setup']['num_beads'],

            'size_of_patches': f'{",".join(map(str, self.params["BatchRunTomo"]["patch_track"]["size_of_patches"]))}',
            'num_of_patches': f'{",".join(map(str, self.params["BatchRunTomo"]["patch_track"]["num_of_patches"]))}',
            'limits_on_shift': f'{",".join(map(str, self.params["BatchRunTomo"]["patch_track"]["limits_on_shift"]))}',
            'num_iterations': self.params['BatchRunTomo']['patch_track']['num_iterations'],
            'adj_tilt_angles': 1 if self.params['BatchRunTomo']['patch_track']['adjust_tilt_angles'] else 0,

            'num_surfaces': self.params['BatchRunTomo']['fine_align']['num_surfaces'],
            'mag_option': {'all': 1, 'group': 3, 'fixed': 0}[self.params['BatchRunTomo']['fine_align']['mag_option']],
            'tilt_option': {'all': 1, 'group': 5, 'fixed': 0}[self.params['BatchRunTomo']['fine_align']['tilt_option']],
            'rot_option': {'all': 1, 'group': 3, 'one': -1, 'fixed': 0}[
                self.params['BatchRunTomo']['fine_align']['rot_option']],
            'beamtilt_option': {'all': 2, 'group': 5, 'fixed': 0}[
                self.params['BatchRunTomo']['fine_align']['beam_tilt_option']],
            'use_robust': 1 if self.params['BatchRunTomo']['fine_align']['use_robust_fitting'] else 0,
            'weight_contours': 1 if self.params['BatchRunTomo']['fine_align']['weight_all_contours'] else 0,
        }

        for param in list(convert_dict.keys()):
            adoc_temp = adoc_temp.replace(f'<{param}>', f'{convert_dict[param]}')

        with open('./align.adoc', 'w') as f:
            f.write(adoc_temp)

    def _get_brt_align_command(self,
                               curr_ts: int):
        """
        Method to get command to run batchtomo for alignment

        ARGS:
        curr_ts :: index of the tilt-series currently being processed

        RETURNS:
        list
        """

        # Get indices of usable CPUs
        temp_cpu = [str(i) for i in range(1, mp.cpu_count() + 1)]

        cmd = ['batchruntomo',
               '-CPUMachineList', f"{temp_cpu}",
               '-GPUMachineList', '1',
               '-DirectiveFile', './align.adoc',
               '-RootName', self.params['System']['output_rootname'] + f'_{curr_ts}',
               '-CurrentLocation', f'{self.basis_folder}/{self.rootname}_{curr_ts}{self.suffix}',
               '-StartingStep', '0',
               '-EndingStep', '8',
               ]
        return cmd

    def align_stack(self, ext=False):
        """
        Method to align specified stack(s) using IMOD batchtomo
        """
        # Add log entry when job starts
        self.logObj("Ot2Rec-align (IMOD) started: batchruntomo.")

        # Create adoc file
        self._get_adoc()

        error_count = 0
        tqdm_iter = tqdm(self._process_list, ncols=100)
        for curr_ts in tqdm_iter:
            tqdm_iter.set_description(f"Aligning TS {curr_ts}...")

            # Get command for current tilt-series
            batchruntomo = subprocess.run(self._get_brt_align_command(curr_ts),
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT,
                                          encoding='ascii',
                                          check=True,
                                          )

            try:
                assert (not batchruntomo.stderr)
            except:
                error_count += 1
                self.logObj(f'Batchruntomo: An error has occurred ({batchruntomo.returncode}) '
                            f'on stack{curr_ts}.')
            self.stdout = batchruntomo.stdout
            self.update_align_metadata(ext)
            self.export_metadata()

        # Add log entry when job finishes
        if error_count == 0:
            self.logObj("All Ot2Rec-align (IMOD) jobs successfully finished.")
        else:
            self.logObj("WARNING: All Ot2Rec-align (IMOD) jobs finished."
                        f"{error_count} of {len(tqdm_iter)} jobs failed."
            )


    def update_align_metadata(self, ext=False):
        """
        Subroutine to update metadata after one set of runs
        """

        # Search for files with output paths specified in the metadata
        # If the files don't exist, keep the line in the input metadata
        # If they do, move them to the output metadata

        if ext:
            self.meta_out = self._align_images
        _to_append = self._align_images.loc[self._align_images['align_output'].apply(lambda x: os.path.isfile(x))]
        self.meta_out = pd.concat([self.meta_out, _to_append],
                                  ignore_index=True)
        self._align_images = self._align_images.loc[~self._align_images['align_output'].apply(
            lambda x: os.path.isfile(x))]

        # Sometimes data might be duplicated (unlikely) -- need to drop the duplicates
        self.meta_out.drop_duplicates(inplace=True)

    def export_metadata(self):
        """
        Method to serialise output metadata, export as yaml
        """

        yaml_file = self.proj_name + '_align_mdout.yaml'

        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False)


"""
PLUGIN METHODS
"""


def create_yaml(args_in=None):
    """
    Subroutine to create new yaml file for IMOD newstack / alignment
    """
    mgMod.get_args_align.show(run=True)


def update_yaml(args, logger):
    """
    Subroutine to update yaml file for IMOD newstack / alignment

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """
    # Check if align and motioncorr yaml files exist
    align_yaml_name = args.project_name + '_align.yaml'
    mc2_yaml_name = args.project_name + '_mc2.yaml'
    if not os.path.isfile(align_yaml_name):
        logger(level="error",
               message="IMOD alignment config file not found.")
        raise IOError("Error in Ot2Rec.align.update_yaml: alignment config file not found.")
    if not os.path.isfile(mc2_yaml_name):
        logger(level="error",
               message="MotionCor2 config file not found.")
        raise IOError("Error in Ot2Rec.align.update__yaml: motioncorr config file not found.")

    # Read in MC2 metadata (as Pandas dataframe)
    # We only need the TS number and the tilt angle for comparisons at this stage
    mc2_md_name = args.project_name + '_mc2_mdout.yaml'
    with open(mc2_md_name, 'r') as f:
        mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]
    # logger(message="MotionCor2 metadata read successfully.")

    # Read in previous alignment output metadata (as Pandas dataframe) for old projects
    align_md_name = args.project_name + '_align_mdout.yaml'
    if os.path.isfile(align_md_name):
        is_old_project = True
        with open(align_md_name, 'r') as f:
            align_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]
        # logger(message="Previous IMOD alignment metadata found and read.")
    else:
        is_old_project = False
        # logger(message="Previous IMOD alignment metadata not found.")

    # Diff the two dataframes to get numbers of tilt-series with unprocessed data
    if is_old_project:
        merged_md = mc2_md.merge(align_md,
                                 how='outer',
                                 indicator=True)
        unprocessed_images = merged_md.loc[lambda x: x['_merge'] == 'left_only']
    else:
        unprocessed_images = mc2_md

    unique_ts_numbers = unprocessed_images['ts'].sort_values(ascending=True).unique().tolist()

    # Read in ctffind yaml file, modify, and update
    # read in MC2 yaml as well (some parameters depend on MC2 settings)
    align_params = prmMod.read_yaml(project_name=args.project_name,
                                    filename=align_yaml_name)
    mc2_params = prmMod.read_yaml(project_name=args.project_name,
                                  filename=mc2_yaml_name)

    align_params.params['System']['process_list'] = unique_ts_numbers
    align_params.params['BatchRunTomo']['setup']['pixel_size'] = mc2_params.params['MC2']['desired_pixel_size'] * 0.1

    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_params.params, f, indent=4, sort_keys=False)

    # logger(message="IMOD alignment metadata updated.")


def create_yaml_stacked():
    """
    Subroutine to create new yaml file for IMOD newstack / alignment
    prestack (bool) :: if stacks already exist
    """
    # Parse user inputs
    args = mgMod.get_args_align_ext.show(run=True)

    # Create the yaml file, then automatically update it
    prmMod.new_align_yaml(args)
    update_yaml_stacked(args)


def update_yaml_stacked(args):
    """
    Method to update yaml file for IMOD newstack / alignment --- if stacks already exist

    ARGS:
    args (Namespace) :: User input parameters
    """
    project_name = args.project_name.value
    parent_path = str(args.input_folder.value)
    assert (os.path.isdir(parent_path)), \
        "Error in main.update_align_yaml_stacked: IMOD parent folder not found."
    while parent_path.endswith('/'):
        parent_path = parent_path[:-1]

    rootname = args.file_prefix.value if args.file_prefix.value != "" else args.project_name.value

    pixel_size = args.pixel_size.value * 0.1
    suffix = args.file_suffix.value

    # Find stack files
    st_file_list = glob(f'{parent_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.st')
    print(f'{parent_path}/{rootname}_*{suffix}/{rootname}_*{suffix}.st')
    print(st_file_list)

    # Extract tilt series number
    ts_list = [int(i.split('/')[-1].replace(f'{rootname}_', '').replace(f'{suffix}.st', '')) for i in st_file_list]

    # Read in and update YAML parameters
    align_yaml_name = project_name + '_align.yaml'
    align_params = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml_name)

    align_params.params['System']['output_path'] = str(args.output_folder.value)
    align_params.params['System']['output_rootname'] = rootname
    align_params.params['System']['output_suffix'] = suffix
    align_params.params['System']['process_list'] = ts_list
    align_params.params['BatchRunTomo']['setup']['pixel_size'] = float(pixel_size) * 0.1

    # Write out YAML file
    with open(align_yaml_name, 'w') as f:
        yaml.dump(align_params.params, f, indent=4, sort_keys=False)


def run(newstack=False, do_align=True, ext=False, args_pass=None, exclusive=True, args_in=None):
    """
    Method to run IMOD newstack / alignment

    ARGS:
    newstack (bool) :: whether to create new stack(s)
    do_align (bool) :: whether to perform IMOD alignment
    ext (bool)      :: whether external stack(s) are available and to be used
    """
    # logger = logMod.Logger(log_path="o2r_imod_align.log")

    logger = logMod.Logger()
    if do_align:
        logger.log_path="o2r_imod_align.log"

    if exclusive:
        parser = argparse.ArgumentParser()
        parser.add_argument("project_name",
                            type=str,
                            help="Name of current project")
        if args_pass is not None:
            args = parser.parse_args(args_pass)
        else:
            args = parser.parse_args()
        project_name = args.project_name
    else:
        project_name = args_in.project_name.value

    # Check if prerequisite files exist
    align_yaml = project_name + '_align.yaml'
    if not ext:
        mc2_md_file = project_name + '_mc2_mdout.yaml'

    # Read in config and metadata
    align_config = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml)
    if not ext:
        mc2_md = mdMod.read_md_yaml(project_name=project_name,
                                    job_type='align',
                                    filename=mc2_md_file)

    # Create Align object
    align_obj = Align(project_name=project_name,
                      md_in=mc2_md if not ext else None,
                      params_in=align_config,
                      logger_in=logger,
                      )

    # Run IMOD
    # Create the stacks and rawtlt files first
    if not align_obj.no_processes:
        align_obj.create_stack_folders()
        if newstack:
            align_obj.create_rawtlt()
            align_obj.create_stack()
        if do_align:
            align_obj.align_stack(ext=ext)


def imod_create_stacks():
    """
    Method to only create stacks using IMOD but omit alignment.
    Separated from the rest of alignment so users can continue processing with other program.
    """
    run(newstack=True,
        do_align=False,
        ext=False,
        )


def imod_standard_align():
    """
    Method to run standard IMOD alignment procedure:
    create stack from micrographs then align them
    """
    run(newstack=True,
        do_align=True,
        ext=False,
        )


def imod_align_ext():
    """
    Method to run IMOD alignment for pre-existing stacks
    """
    run(newstack=False,
        do_align=True,
        ext=True,
        )


def get_align_stats(exclusive=True, args_in=None):
    """
    Method to extract statistics from alignment
    """
    if exclusive:
        parser = argparse.ArgumentParser()
        parser.add_argument("project_name",
                            type=str,
                            help="Name of current project")
        args = parser.parse_args()
        project_name = args.project_name
    else:
        project_name = args_in.project_name.value

    # Check if align metadata file exists
    align_md_name = project_name + '_align_mdout.yaml'
    if not os.path.isfile(align_md_name):
        raise IOError("Error in Ot2Rec.main.get_align_stats: alignment metadata file not found.")

    # Get stacks folder path from config
    align_yaml = project_name + '_align.yaml'
    align_config = prmMod.read_yaml(project_name=project_name,
                                    filename=align_yaml)

    folder_path = align_config.params['System']['output_path']
    while folder_path.endswith('/'):
        folder_path = folder_path[:-1]

    rootname = align_config.params['System']['output_rootname']
    while rootname.endswith('_'):
        rootname = rootname[:-1]

    suffix = align_config.params['System']['output_suffix']

    # Read metadata to extract aligned TS numbers
    with open(align_md_name, 'r') as f:
        aligned_ts = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))['ts'].values.tolist()

    # Create pandas dataframe
    stats_df = pd.DataFrame(
        {'Tilt series': [],
         'Error mean (nm)': [],
         'Error SD (nm)': [],
         }
    )

    # Loop through folders, find data and append to dataframe
    for curr_ts in aligned_ts:
        target_file_path = f"{folder_path}/{rootname}_{curr_ts}{suffix}/taLocals.log"
        if not os.path.isfile(target_file_path):
            raise IOError("Error in Ot2Rec.main.get_align_stats: alignment log file (taLocals) not found.")

        with open(target_file_path, 'r') as f:
            lines = f.readlines()

        mean_sd_criterion = re.compile(r'^\s*Residual error mean')
        filtered = list(filter(mean_sd_criterion.match, lines))
        filter_split = re.split(r'\s+', filtered[0])
        mean, sd = list(float(i) for i in filter_split[6:8])

        stats_df.loc[len(stats_df.index)] = [int(curr_ts), mean, sd]

    # Dump stats as yaml file
    with open(f"{rootname}_imod_align_stats.yaml", "w") as f:
        yaml.dump(stats_df.reset_index().to_dict(orient="records"),
                  f,
                  sort_keys=False, indent=4)

    stats_df.sort_values(by='Error mean (nm)',
                         inplace=True)

    # Create table object and append data from dataframe
    stats = bt()
    stats.columns.headers = ['Tilt series', 'Error mean (nm)', 'Error SD (nm)']
    stats.rows.append(stats.columns.headers)
    for i in stats_df.values.tolist():
        stats.rows.append([int(i[0]), *i[1:]])

    # Print out stats
    print(stats)
