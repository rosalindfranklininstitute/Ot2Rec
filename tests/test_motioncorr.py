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
from unittest.mock import patch, Mock, MagicMock

import magicgui
import mrcfile
import numpy as np
from Ot2Rec import motioncorr
from Ot2Rec import logger as logMod
from Ot2Rec import magicgui as mgMod
from Ot2Rec import metadata as mdMod
from Ot2Rec import params as prmMod


class MotioncorrSmokeTest(unittest.TestCase):
    def _create_expected_input_args(self):
        """Create expected input magicgui args"""
        args = magicgui.widgets.FunctionGui(mgMod.get_args_mc2)
        args.project_name.value = "TS"
        args.pixel_size.value = 1.0

        return args

    def _create_expected_folder_structure(self):
        tmpdir = tempfile.TemporaryDirectory()
        template_folder = f"{os.path.dirname(__file__)}/template_yamls"

        # Create proj.yaml
        proj_yaml = f"{tmpdir.name}/TS_proj.yaml"
        shutil.copyfile(f"{template_folder}/TS_proj.yaml", proj_yaml)

        # Create master_md.yaml
        master_md_yaml = f"{tmpdir.name}/TS_master_md.yaml"
        shutil.copyfile(f"{template_folder}/TS_master_md.yaml", master_md_yaml)

        # Create raw files
        os.mkdir(f"{tmpdir.name}/raw")
        tas = [-30.0, 0.0, 30.0]
        raw_mrcs = [
            f"{tmpdir.name}/raw/" f"TS_0001_{i:04}_{ang}.mrc"
            for i, ang in enumerate(tas)
        ]
        for raw_mrc in raw_mrcs:
            with mrcfile.new(raw_mrc) as mrc:
                mrc.set_data(np.arange(9, dtype=np.int8).reshape(3, 3))

        return tmpdir

    def test_yaml_creation(self):
        """Test yaml is created with expected input"""
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        motioncorr.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(project_name="TS", filename="./TS_mc2.yaml")

        # Ensure process list is not empty
        self.assertNotEqual(len(params.params["System"]["process_list"]), 0)

        tmpdir.cleanup()

    @unittest.skip("Cannot figure out how to exit the while loop in run_mc2")
    @patch("subprocess.Popen")
    def test_mc2_called(self, mc2_mock):
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        motioncorr.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(project_name="TS", filename="./TS_mc2.yaml")

        # Get mc2_md
        master_md = mdMod.read_md_yaml(
            project_name="TS", job_type="motioncorr", filename="./TS_master_md.yaml"
        )

        # Run
        logger = logMod.Logger("./o2r_mc2.log")

        # Create MagicMock to spoof _get_gpu_nvidia_smi
        motioncorr.Motioncorr._get_gpu_nvidia_smi = MagicMock(return_value=["0"])

        mc2_obj = motioncorr.Motioncorr(
            project_name="TS", mc2_params=params, md_in=master_md, logger=logger
        )
        mc2_obj.use_gpu = ["0"]
        mc2_mock.return_value.returncode = None
        mc2_obj._curr_meta = []
        mc2_obj.run_mc2()

        self.assertTrue(mc2_mock.called)
