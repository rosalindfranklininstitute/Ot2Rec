# Copyright 2022 Rosalind Franklin Institute
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
import shutil
import tempfile
import unittest
from unittest.mock import patch

import mrcfile
import numpy as np
from Ot2Rec import aretomo
from Ot2Rec import logger as logMod
from Ot2Rec import magicgui as mgMod
from Ot2Rec import params as prmMod


class AreTomoReconSmokeTest(unittest.TestCase):

    def _create_expected_input_args(self):
        """Create expected input magicGUI args
        NOTE: This is not the proper way to write this function,
        please refer to the savu tests instead. This returns the args as
        a dict, which the aretomo plugin uses as input, rather than
        the FunctionGui. This will be made consistent in the future"""
        args = mgMod.get_args_aretomo(
            project_name="TS",
            aretomo_mode=1,
            pixel_size=1.0,
            input_mrc_folder="./aretomo_aligned",
            output_path="./aretomo_recon",
            volz=1000,
        )

        return args

    def _create_expected_folder_structure(self):
        tmpdir = tempfile.TemporaryDirectory()

        # create aretomo_aligned folder input
        # create ali.mrc files
        os.mkdir(f"{tmpdir.name}/aretomo_aligned")
        os.mkdir(f"{tmpdir.name}/aretomo_aligned/TS_0001")
        st_file = f"{tmpdir.name}/aretomo_aligned/TS_0001/TS_0001_ali.mrc"
        with mrcfile.new(st_file) as mrc:
            mrc.set_data(np.arange(18, dtype=np.int8).reshape(2,3,3))

        # create tlt files
        tlt_file = f"{tmpdir.name}/aretomo_aligned/TS_0001/TS_0001.tlt"
        with open(tlt_file, "w") as f:
            f.write("-30.0\n")
            f.write("0.0\n")
            f.write("30.0\n")

        return tmpdir

    def test_yaml_creation(self):
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        aretomo.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_aretomo_recon.yaml",
        )

        # Ensure process list is not empty
        self.assertNotEqual(len(params.params["System"]["process_list"]), 0)

        tmpdir.cleanup()

    @patch("subprocess.run")
    def test_aretomo_called(self, aretomo_mock):
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        aretomo.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_aretomo_recon.yaml",
        )

        # Run
        logger = logMod.Logger("./o2r_aretomo_recon.log")
        aretomo_obj = aretomo.AreTomo(
            project_name="TS",
            params_in=params,
            logger_in=logger
        )
        aretomo_obj.run_aretomo_all()

        # Check that aretomo is called
        self.assertTrue(aretomo_mock.called)

        tmpdir.cleanup()
    
    @patch("subprocess.run")
    def test_aretomo_STA_output_folders_created(self, aretomo_mock):
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()
        args["out_imod"] = "Warp"   

        # Create yaml
        aretomo.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_aretomo_recon.yaml",
        )

        # Run
        logger = logMod.Logger("./o2r_aretomo_recon.log")
        aretomo_obj = aretomo.AreTomo(
            project_name="TS",
            params_in=params,
            logger_in=logger
        )
        sta_folder = "./aretomo_recon/STA"
        aretomo_obj._run_aretomo(0)
        os.mkdir(f"{tmpdir.name}/aretomo_recon/TS_0001/TS_0001_ali_rec_Imod")

        aretomo_obj.export_metadata()

        self.assertTrue(
            os.path.isdir(f"{sta_folder}/TS_0001_ali_rec_Imod")
        )

        tmpdir.cleanup()
