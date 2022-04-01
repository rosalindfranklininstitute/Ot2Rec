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
        self.assertEqual(args.ext, "mrc")
        self.assertEqual(args.stack_field, 0)
        self.assertEqual(args.index_field, 1)
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


    def test_args_align(self):
        """
        Method to test O2R.user_args:get_args_align function
        """
        parser = uaMod.get_args_align()
        args = parser.parse_args(["test", "-90.0"])

        self.assertEqual(args.project_name, "test")
        self.assertEqual(args.rot_angle, -90)

        self.assertEqual(args.output_folder, "./stacks/")
        self.assertEqual(args.file_prefix, None)
        self.assertEqual(args.file_suffix, '')
        self.assertTrue(args.no_rawtlt)
        self.assertEqual(args.fiducial_size, 0)
        self.assertEqual(args.adoc_template, '/opt/lmod/modules/imod/4.11.1/IMOD/SystemTemplate/cryoSample.adoc')
        self.assertEqual(args.stack_bin_factor, 4)
        self.assertFalse(args.delete_old_files)
        self.assertFalse(args.remove_xrays)
        self.assertEqual(args.coarse_align_bin_factor, 4)
        self.assertEqual(args.patch_sizes, [200, 200])
        self.assertEqual(args.num_patches, [24, 24])
        self.assertEqual(args.num_iter, 4)
        self.assertEqual(args.limits_on_shift, [2, 2])
        self.assertFalse(args.adjust_tilt_angles)
        self.assertEqual(args.num_surfaces, 1)
        self.assertEqual(args.mag_option, 'fixed')
        self.assertEqual(args.tilt_option, 'fixed')
        self.assertEqual(args.rot_option, 'group')
        self.assertEqual(args.beam_tilt_option, 'fixed')
        self.assertTrue(args.no_robust_fitting)
        self.assertTrue(args.no_weight_contours)
        

    def test_args_align_ext(self):
        """
        Method to test O2R.user_args:get_args_align_ext function
        """
        parser = uaMod.get_args_align_ext()
        args = parser.parse_args(["test", "", "1.0"])

        self.assertEqual(args.project_name, "test")
        self.assertEqual(args.parent_path, "")
        self.assertEqual(args.pixel_res, 1.0)

        self.assertEqual(args.rootname, None)
        self.assertEqual(args.suffix, None)


    def test_args_recon(self):
        """
        Method to test O2R.user_args:get_args_recon function
        """
        parser = uaMod.get_args_recon()
        args = parser.parse_args(["test", "1500", "1500"])

        self.assertEqual(args.project_name, "test")
        self.assertEqual(args.unbinned_thickness, 1500)
        self.assertEqual(args.thickness, 1500)

        self.assertFalse(args.do_positioning)
        self.assertFalse(args.correct_ctf)
        self.assertFalse(args.erase_gold)
        self.assertFalse(args.filtering)
        self.assertEqual(args.bin_factor, 1)
        self.assertTrue(args.no_trimvol)
        self.assertEqual(args.trimvol_reorient, 'rotate')
        
        
    def test_args_ctfsim(self):
        """
        Method to test O2R.user_args:get_args_ctfsim function
        """
        parser = uaMod.get_args_ctfsim()
        args = parser.parse_args(["test", "1.0", "10"])

        self.assertEqual(args.project_name, "test")
        self.assertEqual(args.pixel_res, 1.0)
        self.assertEqual(args.ds_factor, 10)

        self.assertEqual(args.rootname, None)
        self.assertEqual(args.dims, [100, 100])
    

    def test_args_savurecon(self):
        """
        Method to test O2R.user_args:get_args_savurecon function
        """
        parser = uaMod.get_args_savurecon()
        args = parser.parse_args(["test", ""])

        self.assertEqual(args.project_name, "test")
        self.assertEqual(args.stacks_folder, "")

        self.assertEqual(args.rootname, None)
        self.assertEqual(args.suffix, "")
        self.assertEqual(args.extension, "mrc")
        self.assertEqual(args.imod_suffix, "")
        self.assertEqual(args.output_path, "./savurecon/")

        
    def test_args_rldeconv(self):
        """
        Method to test O2R.user_args:get_args_rldeconv function
        """
        parser = uaMod.get_args_rldeconv()
        args = parser.parse_args(["", "", ""])

        self.assertEqual(args.image_path, "")
        self.assertEqual(args.psf_path, "")
        self.assertEqual(args.output_path, "")

        self.assertEqual(args.image_type, "mrc")
        self.assertEqual(args.psf_type, "mrc")
        self.assertEqual(args.device, "gpu")
        self.assertEqual(args.niter, 10)
        self.assertFalse(args.block)
        self.assertFalse(args.uint)
