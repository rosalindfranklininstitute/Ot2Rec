# Copyright 2021 Rosalind Franklin Institute
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


# Utility imports
import unittest

# Test imports
import Ot2Rec
from Ot2Rec import user_args as uaMod


class UserArgsTest(unittest.TestCase):
    """
    Tests the Argparse functions work in O2R
    """
    
    def test_args_new_proj(self):
        """
        Method to test O2R.user_args:get_args_new_proj function
        """
        parser = uaMod.get_args_new_proj()
        args = parser.parse_args(["test"])

        self.assertEqual(args.project_name, "test")

        self.assertEqual(args.source_folder, "../raw/")
        self.assertEqual(args.folder_prefix, "")
        self.assertEqual(args.file_prefix, None)
        self.assertFalse(args.tiffs)
        self.assertEqual(args.stack_field, 0)
        self.assertEqual(args.tiltangle_field, 2)


    def test_args_mc2(self):
        """
        Method to test O2R.user_args:get_args_mc2 function
        """
        parser = uaMod.get_args_mc2()
        args = parser.parse_args(["test", "1.0"])
        
        self.assertEqual(args.project_name, "test")
        self.assertEqual(args.pixel_size, 1.0)

        self.assertEqual(args.output_folder, "./motioncor/")
        self.assertEqual(args.file_prefix, None)
        self.assertFalse(args.no_gpu)
        self.assertEqual(args.jobs_per_gpu, 2)
        self.assertEqual(args.gpu_mem_usage, 1)
        self.assertEqual(args.exec_path, '/opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110')
        self.assertEqual(args.gain, None)
        self.assertFalse(args.super_res)
        self.assertEqual(args.discard_top, 0)
        self.assertEqual(args.discard_bottom, 0)
        self.assertEqual(args.tolerance, 0.5)
        self.assertEqual(args.max_iter, 10)
        self.assertEqual(args.patch_size, [5, 5, 20])
        self.assertTrue(args.no_subgroups)
        
        
    def test_args_ctffind(self):
        """
        Method to test O2R.user_args:get_args_ctffind function
        """
        parser = uaMod.get_args_ctffind()
        args = parser.parse_args(["test"])

        self.assertEqual(args.project_name, "test")

        self.assertEqual(args.output_folder, "./ctffind/")
        self.assertEqual(args.file_prefix, None)
        self.assertEqual(args.exec_path, "/opt/lmod/modules/ctffind/4.1.14/bin/ctffind")
        self.assertEqual(args.voltage, 300)
        self.assertEqual(args.spherical_aberration, 2.7)
        self.assertEqual(args.amp_contrast, 0.8)
        self.assertEqual(args.spec_size, 512)
        self.assertEqual(args.res_range, [30, 5])
        self.assertEqual(args.defocus_range, [5000, 50000, 500])
        self.assertEqual(args.astigm_type, None)
        self.assertFalse(args.exhaustive_search)
        self.assertEqual(args.astigm_restraint, None)
        self.assertFalse(args.phase_shift)
