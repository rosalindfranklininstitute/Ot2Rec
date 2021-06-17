"""
Ot2Rec.motioncorr.py

Copyright (C) Rosalind Franklin Institute 2021

Author: Neville B.-y. Yee
Date: 14-Jun-2021

Version: 0.0.2
"""

import os
import subprocess
import itertools
import pandas as pd
import yaml
from tqdm import tqdm

from icecream import ic         # for debugging

import Ot2Rec.metadata as mdMod


class Motioncorr:
    """
    Class encapsulating a Motioncorr object
    """

    def __init__(self, project_name, mc2_params, md_in, logger):
        """
        Initialise Motioncorr object

        ARGS:
        project_name (str)  :: Name of current project
        mc2_params (Params) :: Parameters read in from yaml file
        md_in (Metadata)    :: Metadata containing information of images
        logger (Logger)     :: Logger for recording events
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
        
        # Get index of available GPU
        self.use_gpu = self._get_gpu_nvidia_smi()

        # Set GPU index as new column in metadata
        self.meta = self.meta.assign(gpu=self.use_gpu[0])
        self.no_processes = False
        self._check_processed_images()

        # Check if output folder exists, create if not
        if not os.path.isdir(self.params['System']['output_path']):
            subprocess.run(['mkdir', self.params['System']['output_path']],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           encoding='ascii')


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
            
        # Drop the items in input metadata if they are in the output record
        _ignored = self.meta[self.meta.output.isin(self.meta_out.output)]
        if len(_ignored) > 0 and len(_ignored) < len(self.meta):
            self.logObj(f"Info: {len(_ignored)} images had been processed and will be omitted.")
        elif len(_ignored) == len(self.meta):
            self.logObj(f"Info: All specified images had been processed. Nothing will be done.")
            self.no_processes = True
            
        self.meta = self.meta[~self.meta.output.isin(self.meta_out.output)]
            
            
    @staticmethod
    def _get_gpu_nvidia_smi():
        """
        Subroutine to get visible GPU ID(s) from nvidia-smi
        """

        nv_uuid = subprocess.run(['nvidia-smi', '--list-gpus'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 encoding='ascii')
        nv_processes = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid', '--format=csv'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      encoding='ascii')

        # catch the visible GPUs
        if nv_uuid.returncode != 0 or nv_processes.returncode != 0:
            raise AssertionError(f"Error in Ot2Rec.Motioncorr._get_gpu_from_nvidia_smi: "
                                 f"nvidia-smi returned an error: {nv_uuid.stderr}")
        else:
            nv_uuid = nv_uuid.stdout.strip('\n').split('\n')
            nv_processes = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid', '--format=csv'],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          encoding='ascii')
            visible_gpu = []
            for gpu in nv_uuid:
                id_idx = gpu.find('GPU ')
                uuid_idx = gpu.find('UUID')

                gpu_id = gpu[id_idx + 4:id_idx + 6].strip(' ').strip(':')
                gpu_uuid = gpu[uuid_idx + 5:-1].strip(' ')

                # discard the GPU hosting a process
                if gpu_uuid not in nv_processes.stdout.split('\n'):
                    visible_gpu.append(gpu_id)

        if visible_gpu:
            return visible_gpu
        else:
            raise ValueError(f'Error in metadata._get_gpu_from_nvidia_smi: {len(nv_uuid)} GPU detected, but none of them is free.')


    def _set_output_path(self):
        """
        Subroutine to set output path for motioncorr'd images
        """
        self.meta['output'] = self.meta.apply(
            lambda row: f"{self.params['System']['output_path']}"
            f"{self.params['System']['output_prefix']}_{row['ts']:03}_{row['angles']}.mrc", axis=1)
        

    def _get_command(self, image):
        """
        Subroutine to get commands for running MotionCor2

        ARGS:
        image (tuple): metadata for current image (in_path, out_path, #GPU)

        RETURNS:
        list
        """

        in_path, out_path, gpu_number = image

        if self.params['System']['source_TIFF']:
            image_type = 'InTiff'
        else:
            image_type = 'InMrc'

        # Set output pixel size
        if self.params['MC2']['desired_pixel_size'] == 'ps_x2':
            self.params['MC2']['desired_pixel_size'] = self.params['MC2']['pixel_size'] * 2
        else:
            self.params['MC2']['desired_pixel_size'] = self.params['MC2']['pixel_size']

        # Set FtBin parameter for MC2
        ftbin = self.params['MC2']['desired_pixel_size'] / self.params['MC2']['pixel_size']

        return [self.params['MC2']['MC2_path'],
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
        ]
    
        
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

        # Process tilt-series one at a time
        ts_list = self.params['System']['process_list']
        tqdm_iter = tqdm(ts_list, ncols=100)
        for curr_ts in tqdm_iter:
            tqdm_iter.set_description(f"Processing TS {curr_ts}...")
            self._curr_meta = self.meta.loc[self.meta.ts==curr_ts]
        
            while len(self._curr_meta) > 0:
                # Get commands to run MC2
                mc_commands = [self._get_command((_in, _out, _gpu))
                               for _in, _out, _gpu in zip(self._curr_meta.file_paths, self._curr_meta.output, self._curr_meta.gpu)]

                jobs = (subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) for cmd in mc_commands)
            
                # run subprocess by chunks of GPU
                chunks = self._yield_chunks(jobs, len(self.use_gpu) * self.params['System']['jobs_per_gpu'])
                for job in chunks:
                    # from the moment the next line is read, every process in job are spawned
                    for process in [i for i in job]:
                        self.log.append(process.communicate()[0].decode('UTF-8'))

                        self.update_mc2_metadata()
        

    def update_mc2_metadata(self):
        """
        Subroutine to update metadata after one set of runs
        """

        # Search for files with output paths specified in the metadata
        # If the files don't exist, keep the line in the input metadata
        # If they do, move them to the output metadata

        self.meta_out = self.meta_out.append(self.meta.loc[self.meta['output'].apply(lambda x: os.path.isfile(x))],
                                             ignore_index=True)
        self.meta = self.meta.loc[~self.meta['output'].apply(lambda x: os.path.isfile(x))]
        self._curr_meta = self._curr_meta.loc[~self._curr_meta['output'].apply(lambda x: os.path.isfile(x))]


    def export_metadata(self):
        """
        Method to serialise output metadata, export as yaml
        """

        yaml_file = self.proj_name + '_mc2_mdout.yaml'

        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False) 

