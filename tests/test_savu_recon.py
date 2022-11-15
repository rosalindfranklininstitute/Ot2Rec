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
import tempfile
import unittest
from unittest.mock import patch

import magicgui
import mrcfile
from Ot2Rec import logger as logMod
from Ot2Rec import magicgui as mgMod
from Ot2Rec import params as prmMod
from Ot2Rec import savurecon


class SavuSmokeTest(unittest.TestCase):

    def _create_expected_input_args(self):
        """Create expected input magicGUI args"""
        args = magicgui.widgets.FunctionGui(mgMod.get_args_savurecon)
        args.project_name.value = "TS"
        args.stacks_folder.value = "./stacks"
        args.output_path.value = "./savurecon"

        return args

    def _create_expected_folder_structure(self):
        """Create expected folder structure """
        tmpdir = tempfile.TemporaryDirectory()
        os.mkdir(f"{tmpdir.name}/stacks")
        os.mkdir(f"{tmpdir.name}/stacks/TS_0001")

        # aligned stack files
        ali_mrc = f"{tmpdir.name}/stacks/TS_0001/TS_0001_ali.mrc"
        with mrcfile.new(ali_mrc) as mrc:
            mrc.header.nx = 100

        # tilt angle files
        tltfile = f"{tmpdir.name}/stacks/TS_0001/TS_0001.tlt"
        with open(tltfile, "w") as f:
            f.write("abc")

        return tmpdir

    def test_yaml_creation(self):
        """Test yaml is created with expected input"""
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        savurecon.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_savurecon.yaml"
        )

        # Ensure process list is not empty
        self.assertNotEqual(len(params.params["System"]["process_list"]), 0)

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_savu_called(self, savu_config_mock, savu_mock):
        """Test Savu is called with correct input"""
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Spoof results
        os.mkdir(f"{tmpdir.name}/savurecon")
        os.mkdir(f"{tmpdir.name}/savurecon/TS_0001")
        os.mkdir(f"{tmpdir.name}/savurecon/TS_0001/r")
        tomofile = f"{tmpdir.name}/savurecon/TS_0001/r/TS_0001_processed.mrc"
        with open(tomofile, "w") as f:
            f.write("abc")

        # Create yaml
        savurecon.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_savurecon.yaml"
        )

        # Run
        logger = logMod.Logger("./o2r_savu_recon.log")
        savurecon_obj = savurecon.SavuRecon(
            project_name="TS",
            params_in=params,
            logger_in=logger
        )
        print(savurecon_obj.md_out)
        savurecon_obj.run_savu_all()

        # Check that savu_config and savu are called
        self.assertTrue(savu_config_mock.called)
        self.assertTrue(savu_mock.called)
