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
import subprocess
import multiprocess as mp
from glob import glob
import pandas as pd
from tqdm import tqdm
import yaml
from icecream import ic

from . import metadata as mdMod


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
        basis_folder = self.params['System']['output_path']
        if basis_folder.endswith('/'):
            basis_folder = basis_folder[:-1]

        self._align_images = pd.DataFrame(columns=['ts', 'stack_output', 'align_output'])
        for curr_ts in self.params['System']['process_list']:
            self._align_images = self._align_images.append(
                pd.Series({
                    'ts': curr_ts,
                    'stack_output': basis_folder + '/' + f'stack{curr_ts:03}' + '/' + self.params['System']['output_prefix'] + f'_{curr_ts:03}.st',
                    'align_output': basis_folder + '/' + f'stack{curr_ts:03}' + '/' + self.params['System']['output_prefix'] + f'_{curr_ts:03}_ali.mrc'
                }), ignore_index=True
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
                self._missing_specified = self._missing_specified.append(self._missing[self._missing['ts']==curr_ts],
                                                                         ignore_index=True,
                )
            self._merged = self.meta_out.merge(self._missing_specified, how='left', indicator=True)
            self.meta_out = self.meta_out[self._merged['_merge']=='left_only']

            if len(self._missing_specified) > 0:
                self.logObj(f"Info: {len(self._missing_specified)} images in record missing in folder. Will be added back for processing.")
            
        # Drop the items in input metadata if they are in the output record 
        _ignored = self._align_images[self._align_images.align_output.isin(self.meta_out.align_output)]
        if len(_ignored) > 0 and len(_ignored) < len(self._align_images):
            self.logObj(f"Info: {len(_ignored)} images had been processed and will be omitted.")
        elif len(_ignored) == len(self._align_images):
            self.logObj(f"Info: All specified images had been processed. Nothing will be done.")
            self.no_processes = True

        self._merged = self._align_images.merge(_ignored, how='left', indicator=True)
        self._align_images = self._align_images[self._merged['_merge']=='left_only']
        self._process_list = self._align_images['ts'].sort_values(ascending=True).unique().tolist()
   

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
            stack_file = self._align_images[self._align_images['ts']==curr_ts]['stack_output'].values[0]

            # Sort the filtered metadata
            # Metadata is fetched in the _sort_tilt_angles method
            meta_ts = self._sort_tilt_angles(curr_ts)

            # Create template for newstack
            self._filename_fileinlist = self._path_dict[curr_ts] + self.params['System']['output_prefix'] + f'_{curr_ts:03}_sources.txt'
            self._stack_template = f"{len(meta_ts)}\n" + '\n0\n'.join(meta_ts['output']) + '\n0\n'
            with open(self._filename_fileinlist, 'w') as f:
                f.write(self._stack_template)

            # Define command for running newstack
            cmd = ['newstack',
                   '-fileinlist', self._filename_fileinlist,
                   '-output', stack_file,
            ]

            # Run newstack to create stack
            run_newstack = subprocess.run(cmd,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT)

            if run_newstack.stderr:
                raise ValueError(f'newstack: An error has occurred ({run_newstack.returncode}) '
                                 f'on stack{curr_ts}.')
            else:
                self.stdout = run_newstack.stdout

            
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

runtime.AlignedStack.any.binByFactor = <stack_bin_factor>
        """

        convert_dict = {
            'use_rawtlt': 1 if self.params['BatchRunTomo']['setup']['use_rawtlt'] else 0,
            'pixel_size': self.params['BatchRunTomo']['setup']['pixel_size'],
            'rot_angle': self.params['BatchRunTomo']['setup']['rot_angle'],
            'gold_size': self.params['BatchRunTomo']['setup']['gold_size'],
            'adoc_template': self.params['BatchRunTomo']['setup']['adoc_template'],
            'stack_bin_factor': self.params['BatchRunTomo']['setup']['stack_bin_factor'],

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
                                          stderr=subprocess.STDOUT,
                                          encoding='ascii')

            if batchruntomo.stderr:
                raise ValueError(f'Batchtomo: An error has occurred ({batchruntomo.returncode}) '
                                 f'on stack{curr_ts}.')
            else:
                self.stdout = batchruntomo.stdout
                self.update_align_metadata()
                self.export_metadata()

                
    def update_align_metadata(self):
        """
        Subroutine to update metadata after one set of runs
        """

        # Search for files with output paths specified in the metadata
        # If the files don't exist, keep the line in the input metadata
        # If they do, move them to the output metadata

        self.meta_out = self.meta_out.append(self._align_images.loc[self._align_images['align_output'].apply(lambda x: os.path.isfile(x))],
                                             ignore_index=True)
        self._align_images = self._align_images.loc[~self._align_images['align_output'].apply(lambda x: os.path.isfile(x))]

        # Sometimes data might be duplicated (unlikely) -- need to drop the duplicates
        self.meta_out.drop_duplicates(inplace=True)

        
    def export_metadata(self):
        """
        Method to serialise output metadata, export as yaml
        """

        yaml_file = self.proj_name + '_align_mdout.yaml'

        with open(yaml_file, 'w') as f:
            yaml.dump(self.meta_out.to_dict(), f, indent=4, sort_keys=False) 
