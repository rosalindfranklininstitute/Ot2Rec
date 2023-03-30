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

import magicgui
import mrcfile
import numpy as np
from Ot2Rec import recon
from Ot2Rec import logger as logMod
from Ot2Rec import magicgui as mgMod
from Ot2Rec import metadata as mdMod
from Ot2Rec import params as prmMod


class ImodReconSmokeTest(unittest.TestCase):
    def _create_expected_input_args(self):
        """Create expected input magicgui args"""
        args = magicgui.widgets.FunctionGui(mgMod.get_args_recon)
        args.project_name.value = "TS"

        return args

    def _create_expected_folder_structure(self):
        tmpdir = tempfile.TemporaryDirectory()
        template_folder = f"{os.path.dirname(__file__)}/template_yamls"

        # create align.yaml file
        align_yaml = f"{tmpdir.name}/TS_align.yaml"
        shutil.copyfile(f"{template_folder}/TS_align.yaml", align_yaml)

        # create align_mdout.yaml file
        align_md_yaml = f"{tmpdir.name}/TS_align_mdout.yaml"
        shutil.copyfile(f"{template_folder}/TS_align_mdout.yaml", align_md_yaml)

        # create imod_aligned folder input
        # create ali.mrc files
        os.mkdir(f"{tmpdir.name}/stacks")
        os.mkdir(f"{tmpdir.name}/stacks/TS_0001")
        st_file = f"{tmpdir.name}/stacks/TS_0001/TS_0001_ali.mrc"
        with mrcfile.new(st_file) as mrc:
            mrc.set_data(np.arange(18, dtype=np.int8).reshape(2, 3, 3))

        # create tlt files
        tlt_file = f"{tmpdir.name}/stacks/TS_0001/TS_0001.tlt"
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
        recon.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_recon.yaml",
        )

        # Ensure process list is not empty
        self.assertNotEqual(len(params.params["System"]["process_list"]), 0)

        tmpdir.cleanup()

    @patch("subprocess.run")
    def test_imod_called(self, imod_mock):
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        recon.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_recon.yaml",
        )

        # Get align mdout
        align_md = mdMod.read_md_yaml(
            project_name="TS", job_type="reconstruct", filename="./TS_align_mdout.yaml"
        )

        # Run
        logger = logMod.Logger("./o2r_imod_recon.log")
        imod_recon_obj = recon.Recon(
            project_name="TS", md_in=align_md, params_in=params, logger_in=logger
        )
        imod_recon_obj.recon_stack()

        self.assertTrue(imod_mock.called)
