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

from Ot2Rec import magicgui as mgMod
from Ot2Rec import aretomo

class AreTomoTest(unittest.TestCase):

    def _create_aretomo_yaml_from_magicgui(self, kv=None):
        """ Creates an aretomo yaml from sensible defaults except for
        those defined in kv = [('key', 'value'), ...] """
        sensible_defaults = mgMod.get_args_aretomo(
            project_name="TS",
            input_mrc_folder="./aretomo",
            output_path="./aretomo",
        )
        if kv is not None:
            for (key, value) in kv:
                sensible_defaults.__setitem__(key, value)
        return sensible_defaults

    def test_magicgui_sets_anyvalue_args(self):
        """ Tests that arguments are passed to magicgui namespace
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
            ("recon_algo", "WBP")
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

    @unittest.skip("WIP")
    def test_aretomo_rootname_set(self):
        """Tests that rootname is set and read correctly from yaml
        """
    
    @unittest.skip("WIP")
    def test_aretomo_suffix_set(self):
        """Tests that suffix is set and read correctly from yaml
        """
    
    @unittest.skip("WIP")
    def test_aretomo_yaml_names(self):
        """Tests that aretomo_yaml names are correctly generated
        based on aretomo_mode"""
    
    @unittest.skip("WIP")
    def test_aretomo_mode_accepts_defaults(self):
        """ Tests that aretomo mode can be set to 0, 1, 2 """

    def test_aretomo_mode_raises_error(self):
        """ Tests that aretomo mode raises error when not 0, 1, 2"""
        test_cases = [-1, "a", 4]
        for aretomo_mode in test_cases:
            with self.subTest(f"{aretomo_mode} -> ValueError"):
                with self.assertRaises(ValueError):
                    mgNS = self._create_aretomo_yaml_from_magicgui(
                        ["aretomo_mode", aretomo_mode]
                        )

    @unittest.skip("WIP")
    def test_aretomo_align_creates_stacks(self):
        """ Tests that the command to create stacks with IMOD is run by
        AreTomo align"""
    
    @unittest.skip("WIP")
    def test_aretomo_align_st_file_list(self):
        """ Tests that the input MRC files list is set and read correctly
        from yaml """

    @unittest.skip("WIP")
    def test_aretomo_align_tilt_angles_file_set_default(self):
        """ Tests that the aretomo tilt angles file is set to default value
        when not specified in magicgui"""
    
    @unittest.skip("WIP")
    def test_aretomo_align_tilt_angles_file_set_magicgui(self):
        """ Tests that the aretomo tilt angles file is set and read correctly
        from yaml when specified in magicgui"""
    
    @unittest.skip("WIP")
    def test_aretomo_align_process_list_set(self):
        """ Tests that the aretomo align process list is set correctly """
    
    @unittest.skip("WIP")
    def test_aretomo_recon_inputmrc_set(self):
        """ Tests that aretomo recon sets the input mrc to _ali.mrc by default """
    
    @unittest.skip("WIP")
    def test_aretomo_input_mrc_notfound(self):
        """ Tests that an error is raised when the input mrc folder does not have
        the correct filename. e.g., if recon, _ali.mrc files not found. """
    
    @unittest.skip("WIP")
    def test_aretomo_recon_process_list_set(self):
        """ Tests that the aretomo recon process list is set correctly """
    
    @unittest.skip("WIP")
    def test_aretomo_recon_tilt_angles_set_default(self):
        """ Tests that the aretomo recon tilt angles list is set correctly
        by default if not otherwise specified by magicgui """
    
    @unittest.skip("WIP")
    def test_aretomo_recon_tilt_angles_set_magicgui(self):
        """ Tests that the aretomo recon tilt angles list is set correctly
        when specified by magicgui"""
    
    @unittest.skip("WIP")
    def test_aretomo_output_mrc_set(self):
        """ Tests that aretomo output_mrc filenames are set correctly,
        and end in _ali.mrc for align only, and _rec.mrc for others"""

    @unittest.skip("WIP")
    def test_aretomo_args_passed_to_yaml(self):
        """ Tests that all remaining args are passed to the yaml """
    
    @unittest.skip("WIP")
    def test_aretomo_volz_accepts_defaults(self):
        """ Tests that aretomo volz accepted values work (-1, >0)"""

    @unittest.skip("WIP")
    def test_aretomo_volz_raises_error(self):
        """ Tests that ValueError is raised when volz is not -1 or >0"""
    
    @unittest.skip("WIP")
    def test_aretomo_sample_thickness_accepts_defaults(self):
        """ Tests that samplethickness accepted values work (-1, >0)"""
    
    @unittest.skip("WIP")
    def test_aretomo_sample_thickness_raises_error(self):
        """ Tests that samplethickness does not accept values which are not (-1, >0)"""
    
    @unittest.skip("WIP")
    def test_aretomo_pixel_size_accepts_defaults(self):
        """ Tests that pixel size accepted values work (>0)"""
    
    @unittest.skip("WIP")
    def test_aretomo_volz_autoset_or_not(self):
        """Tests that if either volz or (sample thickness + pixel size) are set, all ok
        """
    
    @unittest.skip("WIP")
    def test_aretomo_volz_samplethickness_pixelsize_allset(self):
        """ Tests that error is raised when volz, and either sample_thickness or 
        pixel_size or both are set"""
    
    @unittest.skip("WIP")
    def test_aretomo_cmd_generated_sensible(self):
        """ Tests that sensible inputs to aretomo will generate the correct cmd"""
    
    @unittest.skip("WIP")
    def test_aretomo_cmd_failing(self):
        """ Tests that cmd cannot be generated from incorrect inputs. previous tests
        should pick up incorrect inputs raising errors in update_yaml so theoretically
        these cannot reach _get_aretomo_align_command or _get_aretomo_recon_comand"""

    @unittest.skip("WIP")
    def test_aretomo_extra_kwargs_passed(self):
        """ Tests that additional kwargs are added to the cmd"""
    
    @unittest.skip("WIP")
    def test_aretomo_cmds_passed_to_mdout(self):
        """ Tests that aretomo commands are saved correctly in mdout """
    
    @unittest.skip("WIP")
    def test_aretomo_mdout_yaml(self):
        """ Tests that the mdout yaml is generated correctly """

