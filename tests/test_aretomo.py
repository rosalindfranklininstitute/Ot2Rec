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
import unittest
from unittest.mock import patch
import tempfile

from Ot2Rec import magicgui as mgMod
from Ot2Rec import aretomo
from Ot2Rec import params as prmMod


@unittest.skip("WIP")
class AreTomoTest(unittest.TestCase):
    def _create_aretomo_yaml_from_magicgui(self, kv=None):
        """Creates an aretomo yaml from sensible defaults except for
        those defined in kv = [('key', 'value'), ...]"""
        sensible_defaults = mgMod.get_args_aretomo(
            project_name="TS",
            input_mrc_folder="./aretomo",
            output_path="./aretomo",
        )
        if kv is not None:
            for key, value in kv:
                sensible_defaults.__setitem__(key, value)
        return sensible_defaults

    def _create_temp_files(self, ext, aretomo_mode, rootname="", suffix="", kv=[]):
        tmpdir = tempfile.TemporaryDirectory()
        tmpfiles = []
        os.mkdir(f"{tmpdir.name}\\aretomo")
        if rootname == "":
            rootname = "TS"  # replace with project name
        for i in range(3):
            if suffix != "":
                os.mkdir(f"{tmpdir.name}\\aretomo\\{rootname}_{i}_{suffix}")
                for e in ext:
                    tmpf = (
                        f"{tmpdir.name}\\aretomo\\"
                        f"{rootname}_{i}_{suffix}\\"
                        f"{rootname}_{i}_{suffix}{e}"
                    )
                    tmpfiles.append(tmpf)
            elif suffix == "":
                os.mkdir(f"{tmpdir.name}\\aretomo\\{rootname}_{i}")
                for e in ext:
                    tmpf = (
                        f"{tmpdir.name}\\aretomo\\" f"{rootname}_{i}\\{rootname}_{i}{e}"
                    )
                    tmpfiles.append(tmpf)
            for tmpf in tmpfiles:
                with open(tmpf, "w") as f:
                    f.write("abc")

        kv.append(("input_mrc_folder", f"{tmpdir.name}\\aretomo"))
        kv.append(("aretomo_mode", aretomo_mode))
        kv.append(("volz", 10))  # for the recon workflows, just arbitrary
        mgNS = self._create_aretomo_yaml_from_magicgui(kv)
        aretomo.create_yaml(input_mgNS=mgNS)
        aretomo_params = prmMod.read_yaml(
            project_name="TS", filename=aretomo._get_yaml_filename(aretomo_mode, "TS")
        )
        return aretomo_params, tmpfiles, tmpdir

    def test_magicgui_sets_anyvalue_args(self):
        """Tests that arguments are passed to magicgui namespace
        The values are only sanity-checked in the `aretomo.update_yaml` function
        so any values are accepted at this stage.
        """
        test_cases = [
            ("project_name", "abc"),
            ("aretomo_mode", 0),
            ("rot_angle", 90.0),
            ("pixel_size", 1.5),
            ("rootname", "abc"),
            ("suffix", "abc"),
            ("input_mrc_folder", "./test"),
            ("output_path", "./test"),
            ("tilt_angles", ".tlt"),
            ("volz", 10),
            ("sample_thickness", 10),
            ("output_binning", 4),
            ("recon_algo", "WBP"),
        ]

        for arg, input in test_cases:
            with self.subTest(f"{arg}, {input} -> {input}"):
                ns = mgMod.get_args_aretomo()
                ns.__setitem__(arg, input)
                self.assertEqual(input, ns[arg])

    def test_magicgui_namespace_saved_to_yaml(self):
        """Tests that the magicgui namespace values are saved by
        `aretomo.create_yaml` if all args are sensible.
        """
        mgNS = self._create_aretomo_yaml_from_magicgui()
        aretomo.create_yaml(input_mgNS=mgNS)
        self.assertTrue(os.path.exists("./TS_aretomo_align.yaml"))
        os.remove("./TS_aretomo_align.yaml")

    def test_aretomo_rootname_set(self):
        """Tests that rootname is set and read correctly from yaml"""
        mgNS = self._create_aretomo_yaml_from_magicgui([("rootname", "test_rootname")])
        aretomo.create_yaml(input_mgNS=mgNS)
        aretomo_params = prmMod.read_yaml(
            project_name="abc", filename="./TS_aretomo_align.yaml"
        )
        self.assertEqual(
            aretomo_params.params["System"]["output_rootname"], "test_rootname"
        )
        os.remove("./TS_aretomo_align.yaml")

    def test_aretomo_suffix_set(self):
        """Tests that suffix is set and read correctly from yaml"""
        mgNS = self._create_aretomo_yaml_from_magicgui([("suffix", "test_suffix")])
        aretomo.create_yaml(input_mgNS=mgNS)
        aretomo_params = prmMod.read_yaml(
            project_name="abc", filename="./TS_aretomo_align.yaml"
        )
        self.assertEqual(
            aretomo_params.params["System"]["output_suffix"], "test_suffix"
        )
        os.remove("./TS_aretomo_align.yaml")

    def test_aretomo_yaml_names(self):
        """Tests that aretomo_yaml names are correctly generated
        based on aretomo_mode"""
        test_cases = [
            ([("aretomo_mode", 0)], "./TS_aretomo_align.yaml"),
            ([("aretomo_mode", 1), ("volz", 10)], "./TS_aretomo_recon.yaml"),
            ([("aretomo_mode", 2), ("volz", 10)], "./TS_aretomo_align-recon.yaml"),
        ]
        for mgNS_args, expected_filename in test_cases:
            with self.subTest(f"{mgNS_args} -> {expected_filename}"):
                mgNS = self._create_aretomo_yaml_from_magicgui(mgNS_args)
                aretomo.create_yaml(input_mgNS=mgNS)
                self.assertTrue(os.path.exists(expected_filename))
                os.remove(expected_filename)

    def test_aretomo_mode_raises_error(self):
        """Tests that aretomo mode raises error when not 0, 1, 2"""
        test_cases = [-1, "a", 4]
        for aretomo_mode in test_cases:
            with self.subTest(f"{aretomo_mode} -> ValueError"):
                with self.assertRaises(ValueError):
                    mgNS = self._create_aretomo_yaml_from_magicgui(
                        ["aretomo_mode", aretomo_mode]
                    )

    @patch("Ot2Rec.align.create_yaml")
    def test_aretomo_align_creates_stacks(self, imod_st_mock):
        """Tests that the command to create stacks with IMOD is called by
        AreTomo align."""
        for aretomo_mode in [0, 2]:
            with self.subTest(f"AreTomo Mode {aretomo_mode} creates stacks"):
                mgNS = self._create_aretomo_yaml_from_magicgui(
                    [("aretomo_mode", aretomo_mode), ("volz", 10)]
                )

                # volz not needed for aretomo_mode=0 but it's ignored anyway
                yaml_fname = aretomo._get_yaml_filename(aretomo_mode, "TS")
                aretomo.create_yaml(input_mgNS=mgNS)
                aretomo_obj = aretomo.AreTomo(
                    project_name="TS",
                    params_in=prmMod.read_yaml("TS", yaml_fname),
                    logger_in=None,
                )
                self.assertTrue(imod_st_mock.called)

    def test_aretomo_align_st_file_list(self):
        """Tests that the input MRC files list is set and read correctly
        from yaml"""
        test_cases = [
            ({"rootname": "", "suffix": "", "aretomo_mode": 0}, "TS_*/TS_*.st"),
            (
                {"rootname": "test", "suffix": "", "aretomo_mode": 0},
                "test_*/test_*.st",
            ),
            (
                {"rootname": "", "suffix": "test", "aretomo_mode": 0},
                "TS_*_test/TS_*_test.st",
            ),
            (
                {"rootname": "abc", "suffix": "def", "aretomo_mode": 0},
                "abc_*_def/abc_*_def.st",
            ),
            ({"rootname": "", "suffix": "", "aretomo_mode": 2}, "TS_*/TS_*.st"),
            (
                {"rootname": "test", "suffix": "", "aretomo_mode": 2},
                "test_*/test_*.st",
            ),
            (
                {"rootname": "", "suffix": "test", "aretomo_mode": 2},
                "TS_*_test/TS_*_test.st",
            ),
            (
                {"rootname": "abc", "suffix": "def", "aretomo_mode": 2},
                "abc_*_def/abc_*_def.st",
            ),
        ]

        for rn_sf_dict, expected in test_cases:
            with self.subTest(f"{rn_sf_dict} -> {expected}"):
                aretomo_params, tmpsts, tmpdir = self._create_temp_files(
                    ext=[".st"],
                    aretomo_mode=rn_sf_dict["aretomo_mode"],
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )
                self.assertEqual(
                    aretomo_params.params["AreTomo_setup"]["input_mrc"], tmpsts
                )
                os.remove(aretomo._get_yaml_filename(rn_sf_dict["aretomo_mode"], "TS"))
                tmpdir.cleanup()

    def test_aretomo_align_tilt_angles_file_set_default(self):
        """Tests that the aretomo tilt angles file is set correctly
        for align and align+recon workflows"""
        test_cases = [
            ({"rootname": "", "suffix": "", "aretomo_mode": 0}, "TS_*/TS_*.rawtlt"),
            (
                {"rootname": "test", "suffix": "", "aretomo_mode": 0},
                "test_*/test_*.rawtlt",
            ),
            (
                {"rootname": "", "suffix": "test", "aretomo_mode": 0},
                "TS_*_test/TS_*_test.rawtlt",
            ),
            (
                {"rootname": "abc", "suffix": "def", "aretomo_mode": 0},
                "abc_*_def/abc_*_def.rawtlt",
            ),
            ({"rootname": "", "suffix": "", "aretomo_mode": 2}, "TS_*/TS_*.rawtlt"),
            (
                {"rootname": "test", "suffix": "", "aretomo_mode": 2},
                "test_*/test_*.rawtlt",
            ),
            (
                {"rootname": "", "suffix": "test", "aretomo_mode": 2},
                "TS_*_test/TS_*_test.rawtlt",
            ),
            (
                {"rootname": "abc", "suffix": "def", "aretomo_mode": 2},
                "abc_*_def/abc_*_def.rawtlt",
            ),
        ]

        for rn_sf_dict, expected in test_cases:
            with self.subTest(f"{rn_sf_dict} -> {expected}"):
                aretomo_params, tmprawtlt, tmpdir = self._create_temp_files(
                    ext=[".rawtlt"],
                    aretomo_mode=rn_sf_dict["aretomo_mode"],
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )
                self.assertEqual(
                    aretomo_params.params["AreTomo_setup"]["tilt_angles"], tmprawtlt
                )
                os.remove(aretomo._get_yaml_filename(rn_sf_dict["aretomo_mode"], "TS"))
                tmpdir.cleanup()

    def test_aretomo_align_process_list_set(self):
        """Tests that the aretomo align process list is set correctly"""
        test_cases = [
            {"rootname": "", "suffix": ""},
            {"rootname": "test", "suffix": ""},
            {"rootname": "", "suffix": "test"},
            {"rootname": "abc", "suffix": "def"},
        ]

        for rn_sf_dict in test_cases:
            with self.subTest(f"{rn_sf_dict} -> [0,1,2]"):
                aretomo_params, tmpsts, tmpdir = self._create_temp_files(
                    ext=[".st"],
                    aretomo_mode=0,
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )
                self.assertEqual(
                    aretomo_params.params["System"]["process_list"], [0, 1, 2]
                )
                os.remove("TS_aretomo_align.yaml")
                tmpdir.cleanup()

    def test_aretomo_recon_alimrc_filelist(self):
        """Tests that aretomo recon sets the input mrcs to _ali.mrc"""
        test_cases = [
            ({"rootname": "", "suffix": ""}, "TS_*/TS_*_ali.mrc"),
            ({"rootname": "test", "suffix": ""}, "test_*/test_*_ali.mrc"),
            ({"rootname": "", "suffix": "test"}, "TS_*_test/TS_*_test_ali.mrc"),
            ({"rootname": "abc", "suffix": "def"}, "abc_*_def/abc_*_def_ali.mrc"),
        ]

        for rn_sf_dict, expected in test_cases:
            with self.subTest(f"{rn_sf_dict} -> {expected}"):
                aretomo_params, tmpalimrc, tmpdir = self._create_temp_files(
                    ext=["_ali.mrc"],
                    aretomo_mode=1,
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )
                self.assertEqual(
                    aretomo_params.params["AreTomo_setup"]["input_mrc"], tmpalimrc
                )
                os.remove("TS_aretomo_recon.yaml")
                tmpdir.cleanup()

    def test_aretomo_input_mrc_notfound(self):
        """Tests that a warning is made when the input mrc folder does not have
        the correct filename. e.g., if recon, _ali.mrc files not found."""
        for aretomo_mode in [0, 1, 2]:
            with self.subTest(f"AreTomo Mode{aretomo_mode} wrong file -> ValueError"):
                with self.assertWarns(UserWarning):
                    aretomo_params, tmpxyz, tmpdir = self._create_temp_files(
                        ext=[".nonexistent"],
                        aretomo_mode=aretomo_mode,
                        rootname="TS",
                        suffix="",
                    )
                    os.remove(aretomo._get_yaml_filename(aretomo_mode, "TS"))
                    tmpdir.cleanup()

    def test_aretomo_recon_process_list_set(self):
        """Tests that the aretomo recon process list is set correctly"""
        test_cases = [
            {"rootname": "", "suffix": ""},
            {"rootname": "test", "suffix": ""},
            {"rootname": "", "suffix": "test"},
            {"rootname": "abc", "suffix": "def"},
        ]

        for rn_sf_dict in test_cases:
            with self.subTest(f"{rn_sf_dict} -> [0,1,2]"):
                aretomo_params, tmpalimrc, tmpdir = self._create_temp_files(
                    ext=["_ali.mrc"],
                    aretomo_mode=1,
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )
                self.assertEqual(
                    aretomo_params.params["System"]["process_list"], [0, 1, 2]
                )
                os.remove("TS_aretomo_recon.yaml")
                tmpdir.cleanup()

    def test_aretomo_alignrecon_process_list_set(self):
        """Tests that the aretomo align + recon process list is set correctly"""
        test_cases = [
            {"rootname": "", "suffix": ""},
            {"rootname": "test", "suffix": ""},
            {"rootname": "", "suffix": "test"},
            {"rootname": "abc", "suffix": "def"},
        ]

        for rn_sf_dict in test_cases:
            with self.subTest(f"{rn_sf_dict} -> [0,1,2]"):
                aretomo_params, tmpst, tmpdir = self._create_temp_files(
                    ext=[".st"],
                    aretomo_mode=2,
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )
                self.assertEqual(
                    aretomo_params.params["System"]["process_list"], [0, 1, 2]
                )

                os.remove(aretomo._get_yaml_filename(2, "TS"))
                tmpdir.cleanup()

    def test_aretomo_recon_tilt_angles_set_default(self):
        """Tests that the aretomo recon tilt angles list is set correctly
        by default if not otherwise specified by magicgui"""
        test_cases = [
            ({"rootname": "", "suffix": ""}, "TS_*/TS_*.tlt"),
            ({"rootname": "test", "suffix": ""}, "test_*/test_*.tlt"),
            ({"rootname": "", "suffix": "test"}, "TS_*_test/TS_*_test.tlt"),
            ({"rootname": "abc", "suffix": "def"}, "abc_*_def/abc_*_def.tlt"),
        ]

        for rn_sf_dict, expected in test_cases:
            with self.subTest(f"{rn_sf_dict} -> {expected}"):
                aretomo_params, tmptlt, tmpdir = self._create_temp_files(
                    ext=[".tlt"],
                    aretomo_mode=1,
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )
                self.assertEqual(
                    aretomo_params.params["AreTomo_setup"]["tilt_angles"], tmptlt
                )
                os.remove(aretomo._get_yaml_filename(1, "TS"))
                tmpdir.cleanup()

    def test_aretomo_tilt_angles_set_magicgui(self):
        """Tests that the aretomo tilt angles list is set correctly
        when specified by magicgui"""
        for aretomo_mode in [0, 1, 2]:
            with self.subTest(f"AreTomo Mode {aretomo_mode} -> test.tlt set"):
                mgNS = self._create_aretomo_yaml_from_magicgui(
                    [
                        ("aretomo_mode", aretomo_mode),
                        ("tilt_angles", "test.tlt"),
                        ("volz", 10),
                    ]
                )
                aretomo.create_yaml(input_mgNS=mgNS)
                aretomo_params = prmMod.read_yaml(
                    project_name="TS",
                    filename=aretomo._get_yaml_filename(aretomo_mode, "TS"),
                )
                self.assertEqual(
                    aretomo_params.params["AreTomo_setup"]["tilt_angles"], "test.tlt"
                )

    def test_aretomo_output_mrc_set(self):
        """Tests that aretomo output_mrc filenames are set correctly,
        and end in _ali.mrc for align only, and _rec.mrc for others"""
        test_cases = [
            ({"rootname": "", "suffix": "", "aretomo_mode": 0}, "_ali.mrc"),
            ({"rootname": "test", "suffix": "", "aretomo_mode": 0}, "_ali.mrc"),
            ({"rootname": "", "suffix": "test", "aretomo_mode": 0}, "_ali.mrc"),
            ({"rootname": "abc", "suffix": "def", "aretomo_mode": 0}, "_ali.mrc"),
            ({"rootname": "", "suffix": "", "aretomo_mode": 1}, "_ali_rec.mrc"),
            ({"rootname": "test", "suffix": "", "aretomo_mode": 1}, "_ali_rec.mrc"),
            ({"rootname": "", "suffix": "test", "aretomo_mode": 1}, "_ali_rec.mrc"),
            ({"rootname": "abc", "suffix": "def", "aretomo_mode": 1}, "_ali_rec.mrc"),
            ({"rootname": "", "suffix": "", "aretomo_mode": 2}, "_rec.mrc"),
            ({"rootname": "test", "suffix": "", "aretomo_mode": 2}, "_rec.mrc"),
            ({"rootname": "", "suffix": "test", "aretomo_mode": 2}, "_rec.mrc"),
            ({"rootname": "abc", "suffix": "def", "aretomo_mode": 2}, "_rec.mrc"),
        ]

        for rn_sf_dict, search in test_cases:
            with self.subTest(f"{rn_sf_dict} -> {search}"):
                exts = {
                    0: [".st", ".rawtlt"],
                    1: ["_ali.mrc", ".tlt"],
                    2: [".st", ".rawtlt"],
                }
                aretomo_params, tmpsts, tmpdir = self._create_temp_files(
                    ext=exts[rn_sf_dict["aretomo_mode"]],
                    aretomo_mode=rn_sf_dict["aretomo_mode"],
                    rootname=rn_sf_dict["rootname"],
                    suffix=rn_sf_dict["suffix"],
                    kv=[
                        ("rootname", rn_sf_dict["rootname"]),
                        ("suffix", rn_sf_dict["suffix"]),
                    ],
                )

                if rn_sf_dict["rootname"] == "":
                    rootname = "TS"
                else:
                    rootname = rn_sf_dict["rootname"]
                if rn_sf_dict["suffix"] == "":
                    expected = [
                        (
                            f"{tmpdir.name}\\aretomo\\"
                            f"{rootname}_{i}\\"
                            f"{rootname}_{i}{search}"
                        )
                        for i in range(3)
                    ]
                else:
                    expected = [
                        (
                            f"{tmpdir.name}\\aretomo\\"
                            f"{rootname}_{i}_{rn_sf_dict['suffix']}\\"
                            f"{rootname}_{i}_{rn_sf_dict['suffix']}{search}"
                        )
                        for i in range(3)
                    ]
                self.assertEqual(
                    aretomo_params.params["AreTomo_setup"]["output_mrc"], expected
                )
                os.remove(aretomo._get_yaml_filename(rn_sf_dict["aretomo_mode"], "TS"))
                tmpdir.cleanup()

    def test_aretomo_volz_accepts_defaults(self):
        """Tests that aretomo volz >0 works"""
        test_cases = [
            ("volz", 1),
            ("volz", 10),
            ("volz", 1e6),
            ("volz", 12.3),
        ]

        for arg, input in test_cases:
            with self.subTest(f"{arg}, {input} -> {input}"):
                mgNS = self._create_aretomo_yaml_from_magicgui(
                    [("aretomo_mode", 1), (arg, input)]
                )
                aretomo.create_yaml(input_mgNS=mgNS)
                aretomo_params = prmMod.read_yaml(
                    project_name="abc", filename="./TS_aretomo_recon.yaml"
                )
                self.assertEqual(aretomo_params.params["AreTomo_recon"]["volz"], input)

        os.remove("./TS_aretomo_recon.yaml")

    def test_aretomo_volz_raises_error(self):
        """Tests that ValueError is raised when volz is not -1 or >0"""
        test_cases = [("volz", 0), ("volz", "a"), ("volz", -1e6), ("volz", 0.1)]

        for arg, input in test_cases:
            with self.subTest(f"{arg}, {input} -> ValueError"):
                with self.assertRaises(ValueError):
                    mgNS = self._create_aretomo_yaml_from_magicgui(
                        [("aretomo_mode", 1), (arg, input)]
                    )
                    aretomo.create_yaml(input_mgNS=mgNS)
        os.remove("./TS_aretomo_recon.yaml")

    def test_aretomo_raises_error_when_volz_is_neg_one_sample_thickness_pixel_size_unset(
        self,
    ):
        """Tests that ValueError is raised when volz=-1, but samplethickness
        and pixel size are not set"""
        test_cases = [
            [("volz", -1), ("sample_thickness", -1), ("pixel_size", -1)],
            [("volz", -1), ("sample_thickness", 10), ("pixel_size", 0)],
            [("volz", -1), ("sample_thickness", -1), ("pixel_size", 10)],
        ]
        for mgNS_args in test_cases:
            with self.subTest(f"{mgNS_args} -> ValueError"):
                with self.assertRaises(ValueError):
                    mgNS_args.append(("aretomo_mode", 1))
                    mgNS = self._create_aretomo_yaml_from_magicgui(mgNS_args)
                    aretomo.create_yaml(input_mgNS=mgNS)
        os.remove("./TS_aretomo_recon.yaml")

    def test_aretomo_volz_set_if_sample_thickness_and_pixel_size_ok(self):
        """Tests that samplethickness accepted values work (-1, >0)"""
        test_cases = [
            ([("sample_thickness", 1), ("pixel_size", 1)], 201),
            ([("sample_thickness", 10), ("pixel_size", 1)], 210),
            ([("sample_thickness", 1e6), ("pixel_size", 1)], 1000200),
            ([("sample_thickness", 12.3), ("pixel_size", 1)], 212),
        ]

        for mgNS_args, expected_volz in test_cases:
            with self.subTest(f"{mgNS_args} -> {expected_volz}"):
                mgNS_args.append(("aretomo_mode", 1))
                mgNS = self._create_aretomo_yaml_from_magicgui(mgNS_args)
                aretomo.create_yaml(input_mgNS=mgNS)
                aretomo_params = prmMod.read_yaml(
                    project_name="abc", filename="./TS_aretomo_recon.yaml"
                )
                self.assertEqual(
                    aretomo_params.params["AreTomo_recon"]["volz"], expected_volz
                )

        os.remove("./TS_aretomo_recon.yaml")

    def test_aretomo_process_list_folders_created(self):
        """Tests that folders to hold the results for aretomo are created
        accorging to the process list"""
        for aretomo_mode in [0, 1, 2]:
            with self.subTest(f"Mode {aretomo_mode} creates results folder"):
                tmpdir = tempfile.TemporaryDirectory()

                mgNS = self._create_aretomo_yaml_from_magicgui(
                    [
                        ("aretomo_mode", aretomo_mode),
                        ("volz", 10),
                        ("output_path", tmpdir.name),
                    ]
                )

                # volz not needed for aretomo_mode=0 but it's ignored anyway
                yaml_fname = aretomo._get_yaml_filename(aretomo_mode, "TS")
                aretomo.create_yaml(input_mgNS=mgNS)
                p = prmMod.read_yaml("TS", yaml_fname)
                p.params["System"]["process_list"] = [0, 1, 2]
                aretomo_obj = aretomo.AreTomo(
                    project_name="TS",
                    params_in=p,
                    logger_in=None,
                )

                for i in [0, 1, 2]:
                    self.assertTrue(
                        os.path.isdir(
                            (
                                f"{tmpdir.name}/"
                                f"{aretomo_obj.rootname}_0{i}{aretomo_obj.suffix}"
                            )
                        )
                    )

    def test_aretomo_writes_process_list_folders_to_mdout(self):
        """Test that mdout contains process list folders"""
        for aretomo_mode in [0, 1, 2]:
            with self.subTest(f"Mode {aretomo_mode} results folder in mdout"):
                tmpdir = tempfile.TemporaryDirectory()

                mgNS = self._create_aretomo_yaml_from_magicgui(
                    [
                        ("aretomo_mode", aretomo_mode),
                        ("volz", 10),
                        ("output_path", tmpdir.name),
                    ]
                )

                # volz not needed for aretomo_mode=0 but it's ignored anyway
                yaml_fname = aretomo._get_yaml_filename(aretomo_mode, "TS")
                aretomo.create_yaml(input_mgNS=mgNS)
                p = prmMod.read_yaml("TS", yaml_fname)
                p.params["System"]["process_list"] = [0, 1, 2]
                aretomo_obj = aretomo.AreTomo(
                    project_name="TS",
                    params_in=p,
                    logger_in=None,
                )

                for i in [0, 1, 2]:
                    self.assertEqual(
                        (
                            f"{tmpdir.name}/"
                            f"{aretomo_obj.rootname}_0{i}{aretomo_obj.suffix}"
                        ),
                        aretomo_obj.md_out["aretomo_output_dir"][i],
                    )

    def test_aretomo_align_cmd(self):
        """Test that align cmd is reasonable for a default input"""

    def test_aretomo_recon_cmd(self):
        """Tests that recon cmd is reasonable for a default input"""

    def test_aretomo_extra_kwargs(self):
        """Tests that extra aretomo kwargs are passed to the cmd"""
