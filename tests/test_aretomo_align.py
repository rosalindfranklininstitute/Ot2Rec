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


class AreTomoAlignSmokeTest(unittest.TestCase):

    def _create_expected_input_args(self):
        """Create expected input magicGUI args
        NOTE: This is not the proper way to write this function,
        please refer to the savu tests instead. This returns the args as
        a dict, which the aretomo plugin uses as input, rather than
        the FunctionGui. This will be made consistent in the future"""
        args = mgMod.get_args_aretomo(
            project_name="TS",
            aretomo_mode=0,
            pixel_size=1.0,
            input_mrc_folder="./motioncor",
            output_path="./aligned",
        )

        return args

    def _create_expected_folder_structure(self):
        tmpdir = tempfile.TemporaryDirectory()
        template_folder = f"{os.path.dirname(__file__)}/template_yamls"

        # create motioncor yaml file
        mc_yaml = f"{tmpdir.name}/TS_mc2.yaml"
        shutil.copyfile(f"{template_folder}/TS_mc2.yaml", mc_yaml)

        # create motioncor mdout yaml file
        mc_md_yaml = f"{tmpdir.name}/TS_mc2_mdout.yaml"
        shutil.copyfile(f"{template_folder}/TS_mc2_mdout.yaml", mc_md_yaml)

        # create motioncor folder input
        os.mkdir(f"{tmpdir.name}/motioncor")
        tas = [-30.0, 0.0, 30.0]
        mc_mrcs = [
            f"{tmpdir.name}/motioncor/TS_0001_{ang}.mrc" for ang in tas
        ]
        for mc_mrc in mc_mrcs:
            with mrcfile.new(mc_mrc) as mrc:
                mrc.set_data(np.arange(9, dtype=np.int8).reshape(3,3))

        return tmpdir

    def _create_expected_st_folder_structure(self, tmpdir):
        """Create folder structure expected from imod stacks"""
        template_folder = f"{os.path.dirname(__file__)}/template_yamls"
        # create align.yaml file
        align_yaml = f"{tmpdir.name}/TS_align.yaml"
        shutil.copyfile(f"{template_folder}/TS_align.yaml", align_yaml)

        # create align_mdout.yaml file
        align_md_yaml = f"{tmpdir.name}/TS_align_mdout.yaml"
        shutil.copyfile(
            f"{template_folder}/TS_align_mdout.yaml",
            align_md_yaml
        )

        # create st files
        os.mkdir(f"{tmpdir.name}/aligned")
        os.mkdir(f"{tmpdir.name}/aligned/TS_0001")
        st_file = f"{tmpdir.name}/aligned/TS_0001/TS_0001.st"
        with mrcfile.new(st_file) as mrc:
            mrc.set_data(np.arange(18, dtype=np.int8).reshape(2,3,3))

        # create rawtlt files
        rawtlt_file = f"{tmpdir.name}/aligned/TS_0001/TS_0001.rawtlt"
        with open(rawtlt_file, "w") as f:
            f.write("-30.0\n")
            f.write("0.0\n")
            f.write("30.0\n")

    @patch("Ot2Rec.align.run")
    def test_imod_stack_creation(self, imod_st_mock):
        """Test imod stack creation is called with motioncor expected input"""
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()

        # Create yaml
        aretomo.create_yaml(args)

        # Test that imod stack creation is called
        self.assertTrue(imod_st_mock.called)

    @patch("Ot2Rec.align.run")
    def test_yaml_creation(self, imod_st_mock):
        # Create expected input until after stacks are created
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()
        self._create_expected_st_folder_structure(tmpdir)

        # Create yaml
        aretomo.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_aretomo_align.yaml",
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
        self._create_expected_st_folder_structure(tmpdir)

        # Create yaml
        aretomo.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_aretomo_align.yaml",
        )

        # Run
        logger = logMod.Logger("./o2r_aretomo_align.log")
        aretomo_obj = aretomo.AreTomo(
            project_name="TS",
            params_in=params,
            logger_in=logger
        )
        aretomo_obj.run_aretomo_all()

        # Check that aretomo is called
        self.assertTrue(aretomo_mock.called)

        tmpdir.cleanup()
    
    def test_aretomo_path_specified(self):
        """ Tests that AreTomo path can be specified correctly in command """
        # Create expected input
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        args = self._create_expected_input_args()
        self._create_expected_st_folder_structure(tmpdir)
        args["aretomo_path"] = "/home/AreTomo_1.2.5_Cuda113_08-01-2022"

        # Create yaml
        aretomo.create_yaml(args)

        # Read params
        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_aretomo_align.yaml",
        )

        # Run
        logger = logMod.Logger("./o2r_aretomo_align.log")
        aretomo_obj = aretomo.AreTomo(
            project_name="TS",
            params_in=params,
            logger_in=logger
        )        

        cmd = aretomo_obj._get_aretomo_align_command(0)

        self.assertEqual(
            cmd[0],
            "/home/AreTomo_1.2.5_Cuda113_08-01-2022"
        )
        
        tmpdir.cleanup()

