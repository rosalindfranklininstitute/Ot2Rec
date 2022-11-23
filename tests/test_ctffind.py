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
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import magicgui
import mrcfile
import numpy as np
from Ot2Rec import ctffind
from Ot2Rec import logger as logMod
from Ot2Rec import magicgui as mgMod
from Ot2Rec import metadata as mdMod
from Ot2Rec import params as prmMod


class CTFFindSmokeTest(unittest.TestCase):

    def _create_expected_input_args(self):
        """Create expected input magicgui args"""
        args = magicgui.widgets.FunctionGui(mgMod.get_args_ctffind)
        args.project_name.value = "TS"

        return args

    def _create_expected_folder_structure(self):
        tmpdir = tempfile.TemporaryDirectory()
        template_folder = f"{os.path.dirname(__file__)}/template_yamls"

        # Create proj.yaml
        proj_yaml = f"{tmpdir.name}/TS_proj.yaml"
        shutil.copyfile(f"{template_folder}/TS_proj.yaml", proj_yaml)

        # Create mc2.yaml
        mc2_yaml = f"{tmpdir.name}/TS_mc2.yaml"
        shutil.copyfile(f"{template_folder}/TS_mc2.yaml", mc2_yaml)

        # Create mc2_mdout.yaml
        mc2_md_yaml = f"{tmpdir.name}/TS_mc2_mdout.yaml"
        shutil.copyfile(f"{template_folder}/TS_mc2_mdout.yaml", mc2_md_yaml)

        # Create raw files
        os.mkdir(f"{tmpdir.name}/motioncor")
        tas = [-30.0, 0.0, 30.0]
        raw_mrcs = [
            f"{tmpdir.name}/motioncor/"
            f"TS_0001_{ang}.mrc" for i, ang in enumerate(tas)
        ]
        for raw_mrc in raw_mrcs:
            with mrcfile.new(raw_mrc) as mrc:
                mrc.set_data(np.arange(9, dtype=np.int8).reshape(3,3))

        return tmpdir

    def test_yaml_creation(self):
        """Test yaml is created with expected input"""
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        ctffind.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_ctffind.yaml"
        )

        # Ensure process list is not empty
        self.assertNotEqual(len(params.params["System"]["process_list"]), 0)

        tmpdir.cleanup()


    def test_ctffind_called(self):
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()
        args.output_folder.value = Path(tmpdir.name + "/ctffind")

        # Create yaml
        ctffind.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_ctffind.yaml"
        )

        # Get mc2_md
        mc2_md = mdMod.read_md_yaml(
            project_name="TS",
            job_type="ctffind",
            filename="./TS_mc2_mdout.yaml")

        # Run
        logger = logMod.Logger("./o2r_ctffind.log")
        ctffind_obj = ctffind.ctffind(
            project_name="TS",
            md_in=mc2_md,
            params_in=params,
            logger_in=logger
        )

        try:
            ctffind_obj.run_ctffind()
            self.assertEqual(ctffind_obj.error_count, 0)
        finally:
            tmpdir.cleanup()
