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


class Recon:
    """
    Class encapsulating a Recon object
    """

    def __init__(self,
                 project_name,
                 md_in,
                 params_in,
                 logger_in,
                 ):
        """
        Initialising a Recon object

        ARGS:
        project_name (str) :: name of current project
        md_in (Metadata)   :: metadata containing images to be put into stack(s) for alignment
        params_in (Params) :: parameters for stack creation
        logger_in (Logger) :: logger object to keep record of progress and errors
        """

        self.proj_name = project_name

        self.logObj = logger_in

        self.mObj = md_in
        if self.mObj is not None:
            self.meta = pd.DataFrame(self.mObj.metadata)

        self.pObj = params_in
        self.params = self.pObj.params

        self._get_internal_metadata()
        self.no_processes = False

        self._process_list = self.params['System']['process_list']
        self._check_reconned_images()

    def _get_internal_metadata(self):
        """
        Method to prepare internal metadata for processing and checking
        """
        self.basis_folder = self.params['System']['output_path']
        if self.basis_folder.endswith('/'):
            self.basis_folder = self.basis_folder[:-1]

        self.rootname = self.params['System']['output_rootname']
        if self.rootname.endswith('_'):
            self.rootname = self.rootname[:-1]

        self.suffix = self.params['System']['output_suffix']
        if self.suffix.endswith('_'):
            self.suffix = self.suffix[:-1]

        # Create the folders and dictionary for future reference
        self._path_dict = {}
        for curr_ts in self.params['System']['process_list']:
            subfolder = f"{self.basis_folder}/{self.rootname}_{curr_ts:02d}{self.suffix}"
            os.makedirs(subfolder, exist_ok=True)
            self._path_dict[curr_ts] = subfolder

        self._recon_images = pd.DataFrame(columns=['ts', 'align_output', 'recon_output'])
        for curr_ts in self.params['System']['process_list']:
            subfolder = f"{self.basis_folder}/{self.rootname}_{curr_ts:02d}{self.suffix}"
            _to_append = pd.DataFrame({
                'ts': [curr_ts],
                'align_output': [f"{subfolder}/{self.rootname}_{curr_ts:02d}{self.suffix}_ali.mrc"],
                'recon_output': [f"{subfolder}/{self.rootname}_{curr_ts:02d}{self.suffix}_rec.mrc"],
            })
            self._recon_images = pd.concat([self._recon_images, _to_append],
                                           ignore_index=True,
                                           )

    def _check_reconned_images(self):
        """
        Method to check images which have already been reconstructed
        """
        # Create new empty internal output metadata if no record exists
        if not os.path.isfile(self.proj_name + '_recon_mdout.yaml'):
            self.meta_out = pd.DataFrame(columns=self._recon_images.columns)

        # Read in serialised metadata and turn into DataFrame if record exists
        else:
            _meta_record = mdMod.read_md_yaml(project_name=self.proj_name,
                                              job_type='reconstruct',
                                              filename=self.proj_name + '_recon_mdout.yaml')
            self.meta_out = pd.DataFrame(_meta_record.metadata)
        self.meta_out.drop_duplicates(inplace=True)

        # Compare output metadata and output folder
        # If a file (in specified TS) is in record but missing, remove from record
        if len(self.meta_out) > 0:
            self._missing = self.meta_out.loc[~self.meta_out['recon_output'].apply(lambda x: os.path.isfile(x))]
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
        _ignored = self._recon_images[self._recon_images.recon_output.isin(self.meta_out.recon_output)]
        if len(_ignored) > 0 and len(_ignored) < len(self._recon_images):
            self.logObj(f"Info: {len(_ignored)} images had been processed and will be omitted.")
        elif len(_ignored) == len(self._recon_images):
            self.logObj(f"Info: All specified images had been processed. Nothing will be done.")
            self.no_processes = True

        self._merged = self._recon_images.merge(_ignored, how='left', indicator=True)
        self._recon_images = self._recon_images[self._merged['_merge'] == 'left_only']
        self._process_list = self._recon_images['ts'].sort_values(ascending=True).unique().tolist()

    def _get_adoc(self):
        """
        Method to create directives for batchtomo reconstruction
        """

        # Template for directive file
        adoc_temp = f"""
setupset.currentStackExt = st
setupset.copyarg.stackext = st
setupset.copyarg.userawtlt = <use_rawtlt>
setupset.copyarg.pixel = <pixel_size>
setupset.copyarg.rotation = <rot_angle>
setupset.copyarg.gold = <gold_size>
setupset.systemTemplate = <adoc_template>

runtime.Fiducials.any.trackingMethod = 1

runtime.Positioning.any.sampleType = <do_pos>
runtime.Positioning.any.thickness = <pos_thickness>

runtime.AlignedStack.any.correctCTF = <corr_ctf>
runtime.AlignedStack.any.eraseGold = <erase_gold>
runtime.AlignedStack.any.filterStack = <filter_stack>
runtime.AlignedStack.any.binByFactor = <stack_bin_factor>

comparam.tilt.tilt.THICKNESS = <recon_thickness>

runtime.Postprocess.any.doTrimvol = <run_trimvol>
runtime.Trimvol.any.reorient = <trimvol_reorient>
        """

        convert_dict = {
            'use_rawtlt': 1 if self.params['BatchRunTomo']['setup']['use_rawtlt'] else 0,
            'pixel_size': self.params['BatchRunTomo']['setup']['pixel_size'],
            'rot_angle': self.params['BatchRunTomo']['setup']['rot_angle'],
            'gold_size': self.params['BatchRunTomo']['setup']['gold_size'],
            'adoc_template': self.params['BatchRunTomo']['setup']['adoc_template'],

            'do_pos': 1 if self.params['BatchRunTomo']['positioning']['do_positioning'] else 0,
            'pos_thickness': self.params['BatchRunTomo']['positioning']['unbinned_thickness'],

            'corr_ctf': 1 if self.params['BatchRunTomo']['aligned_stack']['correct_ctf'] else 0,
            'erase_gold': 1 if self.params['BatchRunTomo']['aligned_stack']['erase_gold'] else 0,
            'filter_stack': 1 if self.params['BatchRunTomo']['aligned_stack']['2d_filtering'] else 0,
            'stack_bin_factor': self.params['BatchRunTomo']['aligned_stack']['bin_factor'],

            'recon_thickness': self.params['BatchRunTomo']['reconstruction']['thickness'],

            'run_trimvol': 1 if self.params['BatchRunTomo']['postprocessing']['run_trimvol'] else 0,
            'trimvol_reorient': {'none': 0, 'flip': 1, 'rotate': 2}[
                self.params['BatchRunTomo']['postprocessing']['trimvol_reorient']]
        }

        for param in list(convert_dict.keys()):
            adoc_temp = adoc_temp.replace(f'<{param}>', f'{convert_dict[param]}')

        with open('./recon.adoc', 'w') as f:
            f.write(adoc_temp)

    def _get_brt_recon_command(self,
                               curr_ts: int,
                               ext=False,
                               ):
        """
        Method to get command to run batchtomo for reconstruction

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
               '-DirectiveFile', './recon.adoc',
               '-RootName', f'{self.rootname}_{curr_ts:02d}',
               '-CurrentLocation', self._path_dict[curr_ts],
               '-StartingStep', '8' if not ext else '0',
               '-EndingStep', '20' if not ext else '0',
               ]

        return cmd

    def recon_stack(self, ext=False):
        """
        Method to reconstruct specified stack(s) using IMOD batchtomo
        """
        # Add log entry when job starts
        self.logObj("Ot2Rec-reconstruction (IMOD) started.")

        # Create adoc file
        self._get_adoc()

        error_count = 0
        tqdm_iter = tqdm(self._process_list, ncols=100)
        for curr_ts in tqdm_iter:
            tqdm_iter.set_description(f"Reconstructing TS {curr_ts}...")

            # Get command for current tilt-series
            if ext:
                batchruntomo = subprocess.run(self._get_brt_recon_command(curr_ts, ext=True),
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT,
                                              encoding='ascii',
                                              check=True
                )

            batchruntomo = subprocess.run(self._get_brt_recon_command(curr_ts, ext=False),
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT,
                                          encoding='ascii',
                                          check=True
            )

            try:
                assert (not batchruntomo.stderr)
            except:
                error_count += 1
                self.logObj(f'Batchtomo: An error has occurred ({batchruntomo.returncode}) '
                            f'on stack{curr_ts}.')
            else:
                self.stdout = batchruntomo.stdout
                self.update_recon_metadata()
                self.export_metadata()

        # Add log entry when job finishes
        if error_count == 0:
            self.logObj("All Ot2Rec-recon (IMOD) jobs successfully finished.")
        else:
            self.logObj("WARNING: All Ot2Rec-recon (IMOD) jobs finished."
                        f"{error_count} of {len(tqdm_iter)} jobs failed."
            )


    def update_recon_metadata(self):
        """
        Subroutine to update metadata after one set of runs
        """

        # Search for files with output paths specified in the metadata
        # If the files don't exist, keep the line in the input metadata
        # If they do, move them to the output metadata

        _to_append = self._recon_images.loc[self._recon_images['recon_output'].apply(lambda x: os.path.isfile(x))]
        self.meta_out = pd.concat([self.meta_out, _to_append],
                                  ignore_index=True)
        self._recon_images = self._recon_images.loc[~self._recon_images['recon_output'].apply(
            lambda x: os.path.isfile(x))]

        # Sometimes data might be duplicated (unlikely) -- need to drop the duplicates
        self.meta_out.drop_duplicates(inplace=True)

    def export_metadata(self):
        """
        Method to serialise output metadata, export as yaml
        """

        yaml_file = self.proj_name + '_recon_mdout.yaml'

        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False)


"""
PLUGIN METHODS
"""


def create_yaml():
    """
    Subroutine to create new yaml file for IMOD reconstruction
    """
    # Parse user inputs
    args = mgMod.get_args_recon.show(run=True)

    # Create the yaml file, then automatically update it
    prmMod.new_recon_yaml(args)
    update_yaml(args)


def update_yaml(args):
    """
    Subroutine to update yaml file for IMOD reconstruction

    ARGS:
    args (Namespace) :: Namespace generated with user inputs
    """
    # Check if recon and align yaml files exist
    recon_yaml_name = args.project_name.value + '_recon.yaml'
    align_yaml_name = args.project_name.value + '_align.yaml'
    if not os.path.isfile(recon_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_recon_yaml: reconstruction config file not found.")
    if not os.path.isfile(align_yaml_name):
        raise IOError("Error in Ot2Rec.main.update_recon_yaml: alignment config file not found.")

    # Read in alignment metadata (as Pandas dataframe)
    align_md_name = args.project_name.value + '_align_mdout.yaml'
    with open(align_md_name, 'r') as f:
        align_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]

    # Read in previous alignment output metadata (as Pandas dataframe) for old projects
    recon_md_name = args.project_name.value + '_recon_mdout.yaml'
    if os.path.isfile(recon_md_name):
        is_old_project = True
        with open(recon_md_name, 'r') as f:
            recon_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts']]
    else:
        is_old_project = False

    # Diff the two dataframes to get numbers of tilt-series with unprocessed data
    if is_old_project:
        merged_md = align_md.merge(recon_md,
                                   how='outer',
                                   indicator=True)
        unprocessed_images = merged_md.loc[lambda x: x['_merge'] == 'left_only']
    else:
        unprocessed_images = align_md
    unique_ts_numbers = unprocessed_images['ts'].sort_values(ascending=True).unique().tolist()

    # Read in reconstruction yaml file, modify, and update
    # read in alignment yaml as well (some parameters depend on alignment settings)
    recon_params = prmMod.read_yaml(project_name=args.project_name.value,
                                    filename=recon_yaml_name)
    align_params = prmMod.read_yaml(project_name=args.project_name.value,
                                    filename=align_yaml_name)

    recon_params.params['System']['output_rootname'] = align_params.params['System']['output_rootname']
    recon_params.params['System']['output_suffix'] = align_params.params['System']['output_suffix']
    recon_params.params['System']['process_list'] = unique_ts_numbers

    recon_params.params['BatchRunTomo']['setup'] = {key: value for key, value in align_params.params['BatchRunTomo']['setup'].items() \
                                                    if key != 'stack_bin_factor'}

    with open(recon_yaml_name, 'w') as f:
        yaml.dump(recon_params.params, f, indent=4, sort_keys=False)


def run():
    """
    Method to run IMOD reconstruction
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name",
                        type=str,
                        help="Name of current project")

    args = parser.parse_args()

    # Check if prerequisite files exist
    recon_yaml = args.project_name + '_recon.yaml'
    align_md_file = args.project_name + '_align_mdout.yaml'

    # Read in config and metadata
    recon_config = prmMod.read_yaml(project_name=args.project_name,
                                    filename=recon_yaml)
    align_md = mdMod.read_md_yaml(project_name=args.project_name,
                                  job_type='reconstruct',
                                  filename=align_md_file)

    # Create Logger object
    log_path = "./o2r_recon.log"
    try:
        os.remove(log_path)
    except:
        pass
    logger = logMod.Logger(log_path=log_path)

    # Create Recon object
    recon_obj = Recon(project_name=args.project_name,
                      md_in=align_md,
                      params_in=recon_config,
                      logger_in=logger,
                      )

    # Run IMOD
    if not recon_obj.no_processes:
        recon_obj.recon_stack()
