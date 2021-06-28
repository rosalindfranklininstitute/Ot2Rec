"""
Ot2Rec.align.py

Copyright (C) Rosalind Franklin Institute 2021

Author: Neville B.-y. Yee
Date: 23-Jun-2021

Version: 0.0.2
"""

import os
import subprocess
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


    def create_stack_folders(self):
        """
        Method to create folders for storing stacked images.
        These folders will be used for alignment and reconstruction as well.
        """

        basis_folder = self.params['System']['output_path']
        if basis_folder.endswith('/'):
            basis_folder = basis_folder[:-1]

        # Create the folders and dictionary for future referrals
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
            rawtlt_file = self._path_dict[curr_ts] + self.params['System']['output_prefix'] + f'{curr_ts:03}.rawtlt'
        
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
            tqdm_iter.set_description(f"Processing TS {curr_ts}...")

            # Define path where the new stack file should go
            stack_file = self._path_dict[curr_ts] + self.params['System']['output_prefix'] + f'{curr_ts:03}.st'

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

