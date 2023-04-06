# Copyright 2023 Rosalind Franklin Institute
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
from unittest.mock import patch

import yaml

from Ot2Rec import params as prmMod
from Ot2Rec import previewer
from Ot2Rec.metadata import Metadata


class PreviewerTest(unittest.TestCase):

    reassigned_names = {
        "Position_10_001_-20.00_20230324_121311_EER.eer": "Position_001_001_-20.00.eer",
        "Position_10_002_-17.00_20230324_121400_EER.eer": "Position_001_002_-17.00.eer",
        "Position_10_003_-23.00_20230324_121457_EER.eer": "Position_001_003_-23.00.eer",
        "Position_1_2_001_-20.00_20230324_121311_EER.eer": "Position_002_001_-20.00.eer",
        "Position_1_2_002_-17.00_20230324_121400_EER.eer": "Position_002_002_-17.00.eer",
        "Position_1_2_003_-23.00_20230324_121457_EER.eer": "Position_002_003_-23.00.eer",
    }

    def _create_expected_folder_structure(self):
        tmpdir = tempfile.TemporaryDirectory()
        template_folder = f"{os.path.dirname(__file__)}/template_yamls"

        # copy test mdoc
        shutil.copyfile(
            f"{template_folder}/Position_1_2.mdoc", f"{tmpdir.name}/Position_1_2.mdoc"
        )
        shutil.copyfile(
            f"{template_folder}/Position_10.mdoc", f"{tmpdir.name}/Position_10.mdoc"
        )
        os.makedirs(f"{tmpdir.name}/raw", exist_ok=True)

        for f in list(self.__class__.reassigned_names.keys()):
            Path(f"{tmpdir.name}/raw/{f}").touch()

        return tmpdir

    @patch("ot2rec_report.main.main")
    @patch("Ot2Rec.aretomo.AreTomo.run_aretomo_all")
    @patch("Ot2Rec.aretomo._create_stacks_with_imod")
    @patch("Ot2Rec.motioncorr.run")
    @patch("Ot2Rec.metadata.Metadata.get_num_frames_parallel")
    @patch("Ot2Rec.mgui_import.get_args_new_proj")
    def test_run_previewer(
        self,
        import_args_mock,
        get_num_frames_mock,
        mc2_mock,
        aretomo_create_stacks_mock,
        aretomo_run_mock,
        o2r_report_mock,
    ):
        import_args_mock.return_value = {
            "project_name": "",
            "source_folder": Path("../raw"),
            "mdocs_folder": Path("../raw"),
            "folder_prefix": "",
            "file_prefix": "",
            "ext": "mrc",
            "stack_field": 0,
            "index_field": 1,
            "tiltangle_field": 2,
            "no_mdoc": False,
            "return_only": True,
        }

        # Mock get number of frames as our test data is empty and not EER
        num_frames_list = []
        for i in range(6):
            num_frames_list.append([15, 1])
        get_num_frames_mock.return_value = num_frames_list

        # Make fake .st files to mock creating stacks with imod
        def create_sts(args):
            os.makedirs(f"{tmpdir.name}/aretomo/Position_001")
            os.makedirs(f"{tmpdir.name}/aretomo/Position_002")
            Path(f"{tmpdir.name}/aretomo/Position_001/Position_001.st").touch()
            Path(f"{tmpdir.name}/aretomo/Position_001/Position_002.st").touch()

        aretomo_create_stacks_mock.side_effect = create_sts

        tmpdir = self._create_expected_folder_structure()

        os.chdir(tmpdir.name)

        previewer.run_previewer(
            mdocs_directory=f"{tmpdir.name}", micrograph_directory=f"{tmpdir.name}/raw"
        )

        # Check that Position_proj.yaml contains updated variables
        import_params = prmMod.read_yaml(
            project_name="Position", filename=f"{tmpdir.name}/Position_proj.yaml"
        )
        self.assertEqual(import_params.params["source_folder"], f"{tmpdir.name}/raw")
        self.assertEqual(import_params.params["mdocs_folder"], "./ot2rec_mdocs")

        # Check that master_md is correct
        with open(f"{tmpdir.name}/Position_master_md.yaml", "r") as f:
            master_md = yaml.load(f, Loader=yaml.FullLoader)
        self.assertListEqual(
            master_md["angles"],
            ["-20.00", "-17.00", "-23.00", "-20.00", "-17.00", "-23.00"],
        )
        self.assertListEqual(
            master_md["file_paths"],
            [
                f"{tmpdir.name}/raw/{img}"
                for img in list(self.__class__.reassigned_names.values())
            ],
        )
        self.assertListEqual(master_md["image_idx"], [1, 2, 3, 1, 2, 3])
        self.assertListEqual(master_md["ts"], [1, 1, 1, 2, 2, 2])

        # Check that acquisition yaml is correct
        with open(f"{tmpdir.name}/Position_acquisition_md.yaml", "r") as f:
            acquisition_md = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual(acquisition_md["magnification"], 64000)

        # Check that motioncor2 params are created correctly
        mc2_params = prmMod.read_yaml(
            project_name="Position", filename=f"{tmpdir.name}/Position_mc2.yaml"
        )
        self.assertListEqual(mc2_params.params["System"]["process_list"], [1, 2])
        self.assertEqual(mc2_params.params["MC2"]["pixel_size"], 1.98)

        # Check that AreTomo parameters are created correctly
        aretomo_params = prmMod.read_yaml(
            project_name="Position",
            filename=f"{tmpdir.name}/Position_aretomo_align-recon.yaml",
        )
        self.assertListEqual(aretomo_params.params["System"]["process_list"], [1, 2])
        self.assertTrue(
            "aretomo/Position_001/Position_001.st"
            in aretomo_params.params["AreTomo_setup"]["input_mrc"]
        )
