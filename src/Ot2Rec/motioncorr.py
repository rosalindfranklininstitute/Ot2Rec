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
import itertools
import pandas as pd
import yaml
from tqdm import tqdm

from . import metadata as mdMod
from . import user_args as uaMod
from . import mgui_mc2 as mgMod
from . import logger as logMod
from . import params as prmMod


class Motioncorr:
    """
    Class encapsulating a Motioncorr object
    """

    def __init__(self, project_name, mc2_params, md_in, logger):
        """
        Initialise Motioncorr object

        Args:
            project_name (str): Name of current project.
            mc2_params (Params): Parameters read in from yaml file.
            md_in (Metadata): Metadata containing information of images.
            logger (Logger): Logger for recording events.
        """

        self.proj_name = project_name

        self.logObj = logger
        self.log = []

        self.prmObj = mc2_params
        self.params = self.prmObj.params

        self._process_list = self.params['System']['process_list']
        self.meta = pd.DataFrame(md_in.metadata)
        self.meta = self.meta[self.meta['ts'].isin(self._process_list)]
        self._set_output_path()

        self._dose_data_present = 'frame_dose' in self.meta.columns

        # Get index of available GPU
        self.use_gpu = self._get_gpu_nvidia_smi()

        # Set GPU index as new column in metadata
        self.meta = self.meta.assign(gpu=self.use_gpu[0])
        self.no_processes = False
        self._check_processed_images()

        # Check if output folder exists, create if not
        if not os.path.isdir(self.params['System']['output_path']):
            # subprocess.run(['mkdir', self.params['System']['output_path']],
            #                stdout=subprocess.PIPE,
            #                stderr=subprocess.PIPE,
            #                encoding='ascii',
            #                check=True,
            #                )
            os.mkdir(self.params['System']['output_path'])

    def _check_processed_images(self):
        """
        Method to check images which have already been processed before
        """
        # Create new empty internal output metadata if no record exists
        if not os.path.isfile(self.proj_name + '_mc2_mdout.yaml'):
            self.meta_out = pd.DataFrame(columns=self.meta.columns)

        # Read in serialised metadata and turn into DataFrame if record exists
        else:
            _meta_record = mdMod.read_md_yaml(project_name=self.proj_name,
                                              job_type='motioncorr',
                                              filename=self.proj_name + '_mc2_mdout.yaml')
            self.meta_out = pd.DataFrame(_meta_record.metadata)

        # Compare output metadata and output folder
        # If a file (in specified TS) is in record but missing, remove from record
        if len(self.meta_out) > 0:
            self._missing = self.meta_out.loc[~self.meta_out['output'].apply(lambda x: os.path.isfile(x))]
            self._missing_specified = pd.DataFrame(columns=self.meta.columns)

            for curr_ts in self.params['System']['process_list']:
                _to_append = self._missing[self._missing['ts'] == curr_ts]
                self._missing_specified = pd.concat([self._missing_specified, _to_append],
                                                    ignore_index=True,
                                                    )
            self._merged = self.meta_out.merge(self._missing_specified, how='left', indicator=True)
            self.meta_out = self.meta_out[self._merged['_merge'] == 'left_only']

            if len(self._missing_specified) > 0:
                self.logObj(f"{len(self._missing_specified)} images in record missing in folder. "
                            "Will be added back for processing.")

        # Drop the items in input metadata if they are in the output record
        _ignored = self.meta[self.meta.output.isin(self.meta_out.output)]
        if len(_ignored) > 0 and len(_ignored) < len(self.meta):
            self.logObj(f"{len(_ignored)} images had been processed and will be omitted.")
        elif len(_ignored) == len(self.meta):
            self.logObj("All specified images had been processed. Nothing will be done.")
            self.no_processes = True

        self.meta = self.meta[~self.meta.output.isin(self.meta_out.output)]


    def _get_gpu_nvidia_smi(self):
        """
        Subroutine to get visible GPU ID(s) from nvidia-smi
        """

        nv_uuid = subprocess.run(['nvidia-smi', '--list-gpus'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 encoding='ascii',
                                 check=True,
                                 )
        nv_processes = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid', '--format=csv'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      encoding='ascii',
                                      check=True,
                                      )

        # catch the visible GPUs
        if nv_uuid.returncode != 0 or nv_processes.returncode != 0:
            self.logObj(msg=f"nvidia-smi returned an error: {nv_uuid.stderr}",
                        level='critical',
            )
            raise AssertionError(f"Error in Ot2Rec.Motioncorr._get_gpu_from_nvidia_smi: "
                                 f"nvidia-smi returned an error: {nv_uuid.stderr}")

        nv_uuid = nv_uuid.stdout.strip('\n').split('\n')
        nv_processes = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid', '--format=csv'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      encoding='ascii',
                                      check=True,
                                      )
        visible_gpu = []
        for gpu in nv_uuid:
            id_idx = gpu.find('GPU ')
            uuid_idx = gpu.find('UUID')

            gpu_id = gpu[id_idx + 4:id_idx + 6].strip(' ').strip(':')
            gpu_uuid = gpu[uuid_idx + 5:-1].strip(' ')

            # discard the GPU hosting a process
            if gpu_uuid not in nv_processes.stdout.split('\n'):
                visible_gpu.append(gpu_id)

        if not visible_gpu:
            self.logObj(f"{len(nv_uuid)} GPU detected, but none of them is free.",
                        level='critical',
            )
            raise ValueError(f"Error in metadata._get_gpu_from_nvidia_smi: {len(nv_uuid)} GPU detected, "
                             "but none of them is free.")
        return visible_gpu

    def _set_output_path(self):
        """
        Subroutine to set output path for motioncorr'd images
        """
        self.meta['output'] = self.meta.apply(
            lambda row: f"{self.params['System']['output_path']}/"
            f"{self.params['System']['output_prefix']}_{row['ts']}_{row['angles']}.mrc", axis=1)

    def _get_command(self, image, extra_info=None):
        """
        Subroutine to get commands for running MotionCor2

        Args:
            image (tuple)      : metadata for current image (in_path, out_path, #GPU)
            extra_info (tuple) : extra information (#EER frames, binning factor, frame dose rate)

        Returns:
            list
        """

        in_path, out_path, gpu_number = image
        if extra_info is not None:
            frame, ds, dose = extra_info
            with open('mc2.tmp', 'w') as f:
                f.write(f"{frame} {ds} {dose}")

        image_type = 'In' + self.params['System']['filetype'].capitalize()
        if self.params['System']['filetype'] == 'tif':
            image_type += 'f'

        # Set FtBin parameter for MC2
        ftbin = self.params['MC2']['desired_pixel_size'] / self.params['MC2']['pixel_size']

        cmd = [self.params['MC2']['MC2_path'],
               f'-{image_type}', in_path,
               '-OutMrc', out_path,
               '-Gpu', gpu_number,
               '-GpuMemUsage', str(self.params['System']['gpu_memory_usage']),
               '-Gain', self.params['MC2']['gain_reference'],
               '-Tol', str(self.params['MC2']['tolerance']),
               '-Patch', ','.join(str(i) for i in self.params['MC2']['patch_size']),
               '-Iter', str(self.params['MC2']['max_iterations']),
               '-Group', '1' if self.params['MC2']['use_subgroups'] else '0',
               '-FtBin', str(ftbin),
               '-PixSize', str(self.params['MC2']['pixel_size']),
               '-Throw', str(self.params['MC2']['discard_frames_top']),
               '-Trunc', str(self.params['MC2']['discard_frames_bottom']),
               '-LogFile', out_path + '.log',
               ]

        if extra_info is not None:
            cmd += ['-FmIntFile', 'mc2.tmp']

        return cmd


    @staticmethod
    def _yield_chunks(iterable, size):
        """
        Subroutine to get chunks for GPU processing
        """
        iterator = iter(iterable)
        for first in iterator:
            yield itertools.chain([first], itertools.islice(iterator, size - 1))


    def run_mc2(self):
        """
        Subroutine to run MotionCor2
        """

        # Add log entry when job starts
        self.logObj("Ot2Rec-MotionCor2 started.")

        # Process tilt-series one at a time
        ts_list = self.params['System']['process_list']
        tqdm_iter = tqdm(self.meta.iterrows(), total=self.meta.shape[0], ncols=100)
        for idx, curr_image in tqdm_iter:
            curr_ts = self.meta.ts[idx]
            tqdm_iter.set_description(f"Processing TS {curr_ts}...")
            self._curr_meta = curr_image

            file_in = self._curr_meta.file_paths
            file_out = self._curr_meta.output
            gpu = self._curr_meta.gpu

            # Get commands to run MC2
            if self._dose_data_present:
                frame = self._curr_meta.num_frames
                ds = self._curr_meta.ds_factor
                dose = self._curr_meta.frame_dose

                cmd = self._get_command((file_in, file_out, gpu), (frame, ds, dose))

            else:
                cmd = self._get_command((file_in, file_out, gpu))

            job = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                assert(job.returncode is None)
            except:
                self.logObj("Ot2Rec-MotionCor2 job failed.",
                            level="warning")

            self.log.append(job.communicate()[0].decode('UTF-8'))
            self.update_mc2_metadata()
            self.export_metadata()


        self.logObj("Ot2Rec-MotionCor2 jobs finished.")


    def update_mc2_metadata(self):
        """
        Subroutine to update metadata after one set of runs
        """

        # Search for files with output paths specified in the metadata
        # If the files don't exist, keep the line in the input metadata
        # If they do, move them to the output metadata

        _to_append = self.meta.loc[self.meta['output'].apply(lambda x: os.path.isfile(x))]
        self.meta_out = pd.concat([self.meta_out, _to_append],
                                  ignore_index=True)
        self.meta = self.meta.loc[~self.meta['output'].apply(lambda x: os.path.isfile(x))]


    def export_metadata(self):
        """
        Method to serialise output metadata, export as yaml
        """

        yaml_file = self.proj_name + '_mc2_mdout.yaml'

        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False)


"""
PLUGIN METHODS
"""


def create_yaml(args=None):
    """
    Subroutine to create new yaml file for motioncorr
    """
    mgMod.get_args_mc2.show(run=True)


def update_yaml(args):
    """
    Subroutine to update yaml file for motioncorr

    Args:
        args (Namespace) : Arguments obtained from user
    """
    logger = logMod.Logger(log_path="o2r_motioncor2.log")

    # Check if MC2 yaml exists
    mc2_yaml_name = args.project_name + '_mc2.yaml'
    if not os.path.isfile(mc2_yaml_name):
        logger(level="error",
               message="MotionCor2 metadata file not found.")
        raise IOError("Error in Ot2Rec.main.update_mc2_yaml: File not found.")

    # Read in master yaml
    master_yaml = args.project_name + '_proj.yaml'
    with open(master_yaml, 'r') as f:
        master_config = yaml.load(f, Loader=yaml.FullLoader)
    logger(message="Master config read successfully.")


    # Read in master metadata (as Pandas dataframe)
    master_md_name = args.project_name + '_master_md.yaml'
    with open(master_md_name, 'r') as f:
        master_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]

    logger(message="Master metadata read successfully.")

    # Read in previous MC2 output metadata (as Pandas dataframe) for old projects
    mc2_md_name = args.project_name + '_mc2_md.yaml'
    if os.path.isfile(mc2_md_name):
        is_old_project = True
        with open(mc2_md_name, 'r') as f:
            mc2_md = pd.DataFrame(yaml.load(f, Loader=yaml.FullLoader))[['ts', 'angles']]
        logger(log_type="info",
               message="Previous MotionCor2 metadata found and read.")
    else:
        is_old_project = False
        logger(message="Previous MotionCor2 metadata not found.")

    # Diff the two dataframes to get numbers of tilt-series with unprocessed data
    if is_old_project:
        merged_md = master_md.merge(mc2_md,
                                    how='outer',
                                    indicator=True)
        unprocessed_images = merged_md.loc[lambda x: x['_merge'] == 'left_only']
    else:
        unprocessed_images = master_md

    unique_ts_numbers = unprocessed_images['ts'].sort_values(ascending=True).unique().tolist()

    # Read in MC2 yaml file, modify, and update
    mc2_params = prmMod.read_yaml(project_name=args.project_name,
                                  filename=mc2_yaml_name)
    mc2_params.params['System']['process_list'] = unique_ts_numbers
    mc2_params.params['System']['filetype'] = master_config['filetype']

    with open(mc2_yaml_name, 'w') as f:
        yaml.dump(mc2_params.params, f, indent=4, sort_keys=False)

    logger(message="MotionCor2 metadata updated.")


def run(exclusive=True, args_in=None):
    """
    Method to run motioncorr
    """
    logger = logMod.Logger(log_path="o2r_motioncor2.log")

    if exclusive:
        parser = argparse.ArgumentParser()
        parser.add_argument("project_name",
                            type=str,
                            help="Name of current project")
        args = parser.parse_args()
        project_name = args.project_name
    else:
        project_name = args_in.project_name

    # Check if prerequisite files exist
    mc2_yaml = project_name + '_mc2.yaml'
    master_md_file = project_name + '_master_md.yaml'

    if not os.path.isfile(mc2_yaml):
        logger(level="error",
               msg="MC2 yaml config not found.")
        raise IOError("Error in Ot2Rec.main.run_mc2: MC2 yaml config not found.")

    if not os.path.isfile(master_md_file):
        logger(level="error",
               msg="Master metadata not found.")
        raise IOError("Error in Ot2Rec.main.run_mc2: Master metadata not found.")

    # Read in config and metadata
    mc2_config = prmMod.read_yaml(project_name=project_name,
                                  filename=mc2_yaml)
    master_md = mdMod.read_md_yaml(project_name=project_name,
                                   job_type='motioncorr',
                                   filename=master_md_file)

    # Create Motioncorr object
    mc2_obj = Motioncorr(project_name=project_name,
                         mc2_params=mc2_config,
                         md_in=master_md,
                         logger=logger
                         )

    if not mc2_obj.no_processes:
        # Run MC2 recursively (and update input/output metadata) until nothing is left in the input metadata list
        mc2_obj.run_mc2()

        # Once all specified images are processed, export output metadata
        mc2_obj.export_metadata()
