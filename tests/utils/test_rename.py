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

import unittest
from Ot2Rec.utils import rename
import tempfile
import os
from pathlib import Path
import shutil
import mdocfile as mdf
import glob


class RenameTest(unittest.TestCase):
    maxDiff = None

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
        template_folder = f"{os.path.dirname(os.path.dirname(__file__))}/template_yamls"

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

    def test_reassign_names_from_mdoc(self):
        tmpdir = self._create_expected_folder_structure()

        mdocs = sorted(glob.glob(f"{tmpdir.name}/*mdoc"))

        reassigned = rename.reassign_names_from_mdoc(mdocs)

        self.assertDictEqual(self.__class__.reassigned_names, reassigned)

        tmpdir.cleanup()

    def test_rename_files(self):
        tmpdir = self._create_expected_folder_structure()

        rename.rename_files(f"{tmpdir.name}/raw", self.__class__.reassigned_names)

        self.assertListEqual(
            sorted(os.listdir(f"{tmpdir.name}/raw")),
            list(self.__class__.reassigned_names.values()),
        )

        tmpdir.cleanup()

    def test_update_mdocs(self):
        tmpdir = self._create_expected_folder_structure()
        rename.update_mdocs(
            mdocs=[
                f"{tmpdir.name}/Position_1_2.mdoc",
                f"{tmpdir.name}/Position_10.mdoc",
            ],
            new_mdocs_directory=f"{tmpdir.name}/ot2rec_mdocs",
            micrograph_directory=f"{tmpdir.name}/raw",
            reassigned_names=self.__class__.reassigned_names,
        )

        self.assertTrue(os.path.isdir(f"{tmpdir.name}/ot2rec_mdocs"))
        self.assertTrue(os.path.isfile(f"{tmpdir.name}/ot2rec_mdocs/Position_001.mdoc"))
        self.assertTrue(os.path.isfile(f"{tmpdir.name}/ot2rec_mdocs/Position_002.mdoc"))

        mdoc_df = mdf.read(f"{tmpdir.name}/ot2rec_mdocs/Position_001.mdoc")
        self.assertEqual(
            str(mdoc_df.iloc[0].SubFramePath),
            f"{tmpdir.name}/raw/Position_001_001_-20.00.eer",
        )

        tmpdir.cleanup()

    def test_write_md_out(self):
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        rename.write_md_out(self.__class__.reassigned_names)
        self.assertTrue(os.path.isfile(f"{tmpdir.name}/ot2rec_reassigned_names.yaml"))

        tmpdir.cleanup()

    def test_rename_all(self):
        tmpdir = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)
        rename.rename_all(
            mdocs_directory=tmpdir.name, micrograph_directory=f"{tmpdir.name}/raw"
        )

        self.assertTrue(os.path.isfile(f"{tmpdir.name}/ot2rec_reassigned_names.yaml"))
        self.assertListEqual(
            sorted(os.listdir(f"{tmpdir.name}/raw")),
            list(self.__class__.reassigned_names.values()),
        )

        mdoc_df = mdf.read(f"{tmpdir.name}/ot2rec_mdocs/Position_001.mdoc")
        self.assertEqual(
            str(mdoc_df.iloc[0].SubFramePath),
            f"{tmpdir.name}/raw/Position_001_001_-20.00.eer",
        )

        tmpdir.cleanup()
