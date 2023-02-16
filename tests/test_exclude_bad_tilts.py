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
import tempfile
import unittest

import magicgui
import mrcfile
import numpy as np
import yaml

from Ot2Rec import exclude_bad_tilts
from Ot2Rec import logger as logMod
from Ot2Rec import magicgui as mgMod
from Ot2Rec import params as prmMod


class ExcludeBadTiltsSmokeTest(unittest.TestCase):

    def _create_expected_input_args(self):
        args = magicgui.widgets.FunctionGui(mgMod.get_args_exclude_bad_tilts)
        args.project_name.value = "TS"
        args.min_percentile.value = 20
        args.max_percentile.value = 80
        
        return args
    
    def _create_expected_folder_structure(self):
        tmpdir = tempfile.TemporaryDirectory()
        os.mkdir(f"{tmpdir.name}/stacks")
        os.mkdir(f"{tmpdir.name}/stacks/TS_0001")

        # .st files
        st_mrc = f"{tmpdir.name}/stacks/TS_0001/TS_0001.st"
        bad = np.full(
            shape=(2,2),
            fill_value=1,
        )
        good = np.full(
            shape=(2,2),
            fill_value=200,
        )
        st = np.stack(
            [bad, good, good, good, good, good, good, good, good, bad],
            axis=0,
        ).astype("uint8")
        with mrcfile.new(st_mrc) as mrc:
            mrc.set_data(st)
        
        # create .rawtlt files
        rawtlt_file = f"{tmpdir.name}/stacks/TS_0001/TS_0001.rawtlt"
        tas = np.linspace(-60, 60, 10)
        with open(rawtlt_file, "w") as f:
            f.writelines(f"{str(ta)}\n" for ta in tas)
        
        return tmpdir, st
    
    def test_yaml_creation(self):
        """ Test yaml is created with expected input """
        args = self._create_expected_input_args()
        tmpdir, st = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)

        exclude_bad_tilts.create_yaml(args)

        self.assertTrue(
            os.path.isfile("./TS_exclude_bad_tilts.yaml")
        )

        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_exclude_bad_tilts.yaml"
        )

        # Ensure process list is not empty
        self.assertNotEqual(
            len(params.params["System"]["process_list"]),
            0
        )

        tmpdir.cleanup()
    
    def test_tilts_exclusion(self):
        """ Test that the correct tilts are excluded """
        args = self._create_expected_input_args()
        tmpdir, st = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)

        exclude_bad_tilts.create_yaml(args)

        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_exclude_bad_tilts.yaml",
        )

        ebt_obj = exclude_bad_tilts.ExcludeBadTilts(
            project_name="TS",
            params_in=params,
            logger_in=logMod.Logger("o2r_exclude_bad_tilts.log")
        )

        ebt_obj._exclude_tilt_one_ts(0)

        with mrcfile.mmap("./stacks/TS_0001/TS_0001.excl") as mrc:
            excluded_mrc = mrc.data
        
        with mrcfile.mmap("./stacks/TS_0001/TS_0001.st") as mrc:
            cropped_ts = mrc.data
        
        self.assertEqual(excluded_mrc.shape[0], 2)
        self.assertEqual(cropped_ts.shape[0], 8)
    
    def test_tilt_angles_exclusion(self):
        """ Test that the correct tilt angles are removed from the rawtlt """

        args = self._create_expected_input_args()
        tmpdir, st = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)

        exclude_bad_tilts.create_yaml(args)

        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_exclude_bad_tilts.yaml",
        )

        ebt_obj = exclude_bad_tilts.ExcludeBadTilts(
            project_name="TS",
            params_in=params,
            logger_in=logMod.Logger("o2r_exclude_bad_tilts.log")
        )

        ebt_obj._exclude_tilt_one_ts(0)

        with open("./stacks/TS_0001/TS_0001.rawtlt", "r") as f:
            tas_excluded = f.readlines()
        
        self.assertEqual(len(tas_excluded), 8)
    
    def test_EBT_metadata(self):
        """ Test that excluded tilt indices, tilt angles, filenames saved """

        args = self._create_expected_input_args()
        tmpdir, st = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)

        exclude_bad_tilts.create_yaml(args)

        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_exclude_bad_tilts.yaml",
        )

        ebt_obj = exclude_bad_tilts.ExcludeBadTilts(
            project_name="TS",
            params_in=params,
            logger_in=logMod.Logger("o2r_exclude_bad_tilts.log")
        )

        ebt_obj.run_exclude_bad_tilts()

        with open(
            f"{tmpdir.name}/TS_exclude_bad_tilts_mdout.yaml", "r"
        ) as f:
            md = yaml.load(f, Loader=yaml.FullLoader)
        
        self.assertEqual(
            len(md["Excluded_Tilt_Index"][1]), 2
        )

        self.assertEqual(
            md["Excluded_St_Files"][1],
            "stacks/TS_0001/TS_0001.excl"
        )

        self.assertEqual(
            list(md["Excluded_Tilt_Angles"][1]),
            [-60.0, 60.0]
        )
    
    def test_EBT_recombine(self):
        """ Test that excluded tilts are recombined correctly """
        args = self._create_expected_input_args()
        tmpdir, st = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)

        exclude_bad_tilts.create_yaml(args)

        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_exclude_bad_tilts.yaml",
        )

        ebt_obj = exclude_bad_tilts.ExcludeBadTilts(
            project_name="TS",
            params_in=params,
            logger_in=logMod.Logger("o2r_exclude_bad_tilts.log")
        )

        ebt_obj.run_exclude_bad_tilts()

        with open("TS_exclude_bad_tilts_mdout.yaml", "r") as f:
            md = yaml.load(f, Loader=yaml.FullLoader)
        
        exclude_bad_tilts._recombine_tilt_one_ts(
            0,
            params.params,
            md
        )

        # Check that images are recombined correctly
        with mrcfile.mmap("./stacks/TS_0001/TS_0001.st") as mrc:
            recombined_st = mrc.data
        np.testing.assert_allclose(recombined_st, st)

        # Check that rawtlt files are recombined correctly
        ta = np.loadtxt(
            fname="stacks/TS_0001/TS_0001.rawtlt",
        )
        np.testing.assert_allclose(
            ta,
            np.linspace(-60, 60, 10)
        )
    
    def test_EBT_dryrun(self):
        """Tests that dry run outputs tilts to exclude to yaml
        """
        args = self._create_expected_input_args()
        tmpdir, st = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)

        exclude_bad_tilts.create_yaml(args)

        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_exclude_bad_tilts.yaml",
        )

        ebt_obj = exclude_bad_tilts.ExcludeBadTilts(
            project_name="TS",
            params_in=params,
            logger_in=logMod.Logger("o2r_exclude_bad_tilts.log")
        )

        ebt_obj.dry_run()

        self.assertTrue(os.path.isfile("TS_EBTdryrun.yaml"))
        
        with open("TS_EBTdryrun.yaml", "r") as f:
            dryrun = yaml.load(f, Loader=yaml.FullLoader)
        
        self.assertNotEqual(len(dryrun), 0)
    
    def test_EBT_with_existing_dryrun_file(self):
        """Tests that tilts can be excluded from an existing dry run file
        """
        args = self._create_expected_input_args()
        tmpdir, st = self._create_expected_folder_structure()
        os.chdir(tmpdir.name)

        exclude_bad_tilts.create_yaml(args)

        params = prmMod.read_yaml(
            project_name="TS",
            filename="./TS_exclude_bad_tilts.yaml",
        )

        ebt_obj = exclude_bad_tilts.ExcludeBadTilts(
            project_name="TS",
            params_in=params,
            logger_in=logMod.Logger("o2r_exclude_bad_tilts.log")
        )

        self.assertRaises(
            IOError,
            ebt_obj.run_exclude_bad_tilts,
            True
        )

        tilts_to_exclude = {
            1: [1,2,3,9]
        }

        with open("TS_EBTdryrun.yaml", "w") as f:
            yaml.dump(tilts_to_exclude, f, indent=4, sort_keys=False)

        ebt_obj.run_exclude_bad_tilts(existing_file=True)

        with mrcfile.mmap("./stacks/TS_0001/TS_0001.st") as mrc:
            cropped_ts = mrc.data
        self.assertEqual(cropped_ts.shape[0], 6)
