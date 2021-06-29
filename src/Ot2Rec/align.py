"""
Ot2Rec.align.py

Copyright (C) Rosalind Franklin Institute 2021

Author: Neville B.-y. Yee
Date: 23-Jun-2021

Version: 0.0.2
"""

import os
import subprocess
import multiprocess as mp
from glob import glob
import pandas as pd
from tqdm import tqdm

from icecream import ic


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

        self.loggerObj = logger_in
        
        self.mObj = md_in
        self.meta = pd.DataFrame(self.mObj.metadata)
        
        self.pObj = params_in
        self.params = self.pObj.params

        self._process_list = self.params['System']['process_list']


    """
    STACK CREATION
    """
    def create_stack_folders(self):
        """
        Method to create folders for storing stacked images.
        These folders will be used for alignment and reconstruction as well.
        """

        basis_folder = self.params['System']['output_path']
        if basis_folder.endswith('/'):
            basis_folder = basis_folder[:-1]

        # Create the folders and dictionary for future reference
        self._path_dict = dict()
        for curr_ts in self._process_list:
            subfolder_name = f'stack{curr_ts:03}'
            subfolder_path = basis_folder + '/' + subfolder_name + '/'
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
        meta_ts = self.meta[self.meta['ts']==curr_ts]


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
            rawtlt_file = self._path_dict[curr_ts] + self.params['System']['output_prefix'] + f'_{curr_ts:03}.rawtlt'
        
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

        tqdm_iter = tqdm(self._process_list, ncols=100)
        for curr_ts in tqdm_iter:
            tqdm_iter.set_description(f"Creating stack for TS {curr_ts}...")

            # Define path where the new stack file should go
            stack_file = self._path_dict[curr_ts] + self.params['System']['output_prefix'] + f'_{curr_ts:03}.st'

            # Sort the filtered metadata
            # Metadata is fetched in the _sort_tilt_angles method
            meta_ts = self._sort_tilt_angles(curr_ts)

            # Create template for newstack
            self._filename_fileinlist = self._path_dict[curr_ts] + self.params['System']['output_prefix'] + f'{curr_ts:03}_sources.txt'
            self._stack_template = f"{len(meta_ts)}\n" + '\n0\n'.join(meta_ts['output']) + '\n0\n'
            with open(self._filename_fileinlist, 'w') as f:
                f.write(self._stack_template)

            # Define command for running newstack
            cmd = ['newstack',
                   '-fileinlist', self._filename_fileinlist,
                   '-output', stack_file,
            ]

            # Run newstack to create stack
            subprocess.run(cmd,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)

            
    """
    ALIGNMENT - BATCHTOMO
    """
    def _get_adoc(self):
        """
        Method to create directives for batchtomo alignment
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

runtime.Excludeviews.any.deleteOldFiles = <delete_old_files>
runtime.Preprocessing.any.removeXrays = <remove_xrays>

comparam.prenewst.newstack.BinByFactor = <ca_bin_factor>

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

        convert_dict = {
            'use_rawtlt': 1 if self.params['BatchRunTomo']['setup']['use_rawtlt'] else 0,
            'pixel_size': self.params['BatchRunTomo']['setup']['pixel_size'],
            'rot_angle': self.params['BatchRunTomo']['setup']['rot_angle'],
            'gold_size': self.params['BatchRunTomo']['setup']['gold_size'],
            'adoc_template': self.params['BatchRunTomo']['setup']['adoc_template'],

            'delete_old_files': 1 if self.params['BatchRunTomo']['preprocessing']['delete_old_files'] else 0,
            'remove_xrays': 1 if self.params['BatchRunTomo']['preprocessing']['remove_xrays'] else 0,

            'ca_bin_factor': self.params['BatchRunTomo']['coarse_align']['bin_factor'],

            'size_of_patches': f'{",".join(map(str, self.params["BatchRunTomo"]["patch_track"]["size_of_patches"]))}',
            'num_of_patches': f'{",".join(map(str, self.params["BatchRunTomo"]["patch_track"]["num_of_patches"]))}',
            'limits_on_shift': f'{",".join(map(str, self.params["BatchRunTomo"]["patch_track"]["limits_on_shift"]))}',
            'num_iterations': self.params['BatchRunTomo']['patch_track']['num_iterations'],
            'adj_tilt_angles': 1 if self.params['BatchRunTomo']['patch_track']['adjust_tilt_angles'] else 0,

            'num_surfaces': self.params['BatchRunTomo']['fine_align']['num_surfaces'],
            'mag_option': {'all': 1, 'group': 3, 'fixed': 0}[self.params['BatchRunTomo']['fine_align']['mag_option']],
            'tilt_option': {'all': 1, 'group': 5, 'fixed': 0}[self.params['BatchRunTomo']['fine_align']['tilt_option']],
            'rot_option': {'all': 1, 'group': 3, 'one': -1, 'fixed': 0}[self.params['BatchRunTomo']['fine_align']['rot_option']],
            'beamtilt_option': {'all': 2, 'group': 5, 'fixed': 0}[self.params['BatchRunTomo']['fine_align']['beam_tilt_option']],
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
        temp_cpu = [str(i) for i in range(1, mp.cpu_count()+1)]
        
        cmd = ['batchruntomo',
               '-CPUMachineList', f"{temp_cpu}",
               '-GPUMachineList', '1',
               '-DirectiveFile', './align.adoc',
               '-RootName', self.params['System']['output_prefix'] + f'_{curr_ts:03}',
               '-CurrentLocation', self._path_dict[curr_ts],
               '-StartingStep', '0',
               '-EndingStep', '8',
        ]

        return cmd


    def align_stack(self):
        """
        Method to align specified stack(s) using IMOD batchtomo
        """

        # Create adoc file
        self._get_adoc()
        
        tqdm_iter = tqdm(self._process_list, ncols=100)
        for curr_ts in tqdm_iter:
            tqdm_iter.set_description(f"Aligning TS {curr_ts}...")

            # Get command for current tilt-series
            cmd_ts = self._get_brt_align_command(curr_ts)

            batchruntomo = subprocess.run(self._get_brt_align_command(curr_ts),
                                          stdout=subprocess.PIPE,
                                          encoding='ascii')

            self.stdout = batchruntomo.stdout
        
