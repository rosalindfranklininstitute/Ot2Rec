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

from icecream import ic         # for debugging


class Motioncorr:
    """
    Class encapsulating a Motioncorr object
    """

    def __init__(self, project_name, mc2_params, md_in):
        """
        Initialise Motioncorr object

        ARGS:
        project_name (str)  :: Name of current project
        mc2_params (Params) :: Parameters read in from yaml file
        md_in (Metadata)    :: Metadata containing information of images
        """

        self.proj_name = project_name
        
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
        self.meta_out = None

        # Check if output folder exists, create if not
        if not os.path.isdir(self.params['System']['output_path']):
            subprocess.run(['mkdir', self.params['System']['output_path']],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           encoding='ascii')
                           
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

        # Get commands to run MC2
        mc_commands = [self._get_command((_in, _out, _gpu))
                       for _in, _out, _gpu in zip(self.meta.file_paths, self.meta.output, self.meta.gpu)]

        jobs = (subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) for cmd in mc_commands)

        # run subprocess by chunks of GPU
        run = 0
        for job in self._yield_chunks(jobs, len(self.use_gpu) * self.params['System']['jobs_per_gpu']):
            # from the moment the next line is read, every process in job are spawned
            for process in [i for i in job]:
                ic(process.communicate()[0])
                run += 1
        

    def update_mc2_metadata(self):
        """
        Subroutine to update metadata after one set of runs
        """

        # Search for files with output paths specified in the metadata
        # If the files don't exist, keep the line in the input metadata
        # If they do, move them to the output metadata
        self.meta_out = self.meta.loc[self.meta['output'].apply(lambda x: os.path.isfile(x))]
        self.meta = self.meta.loc[~self.meta['output'].apply(lambda x: os.path.isfile(x))]
        

    def export_metadata(self):
        """
        Method to serialise output metadata, export as yaml
        """

        yaml_file = self.proj_name + '_mc2_mdout.yaml'

        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False) 

