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
from unittest import mock

from glob import glob
import argparse

from icecream import ic

# Test imports
from Ot2Rec import params as prmMod


class ParamsTest(unittest.TestCase):
    """
    Tests functions within the Ot2Rec.Params class
    """
    def setUp(self):
        self.proj_name = "test"
        self.pObj = prmMod.Params(project_name=self.proj_name,
                                  params_in=None)

        
    def test_new_master_yaml(self):
        # Argparse stuff --- must be the same as main
        parser = argparse.ArgumentParser()
        parser.add_argument("project_name", default=self.proj_name)
        parser.add_argument("-s", "--source_folder",
                            type=str,
                            default='../raw/',
                            help="Path to folder with raw images (Default: ../raw/)")
        parser.add_argument("-fp", "--folder_prefix",
                            type=str,
                            default='',
                            help="Common prefix of raw tilt series folder(s). Don't use this flag if all images are in the parent folder.")
        parser.add_argument("-p", "--file_prefix",
                            type=str,
                            help="Common prefix of raw image files (Default: project name).")
        parser.add_argument("-t", "--tiffs",
                            action="store_true",
                            help="Use this flag if the raw images are TIFFs.")
        parser.add_argument("--stack_field",
                            type=int,
                            default=0,
                            help="Field number of tilt series indices (Default: 0).")
        parser.add_argument("--tiltangle_field",
                            type=int,
                            default=2,
                            help="Field number of tilt angles (Default: 2).")

        args = parser.parse_args([f'{self.proj_name}'])

        prmMod.new_master_yaml(args=args)

        file_to_find = f'{self.proj_name}_proj.yaml'
        self.assertTrue(file_to_find in glob(file_to_find))
    

    def test_new_mc2_yaml(self):
        # Parse user inputs
        parser = argparse.ArgumentParser()
        parser.add_argument("project_name",
                            type=str,
                            help="Name of current project")
        parser.add_argument("-o", "--output_folder",
                            type=str,
                            default='./motioncor/',
                            help="Path to folder for storing motion-corrected images (Default: ./motioncor/)")
        parser.add_argument("-p", "--file_prefix",
                            type=str,
                            help="Common prefix of image files (Default: project name).")
        parser.add_argument("--no_gpu",
                            action="store_true",
                            help="Use CPU only for motion-correction.")
        parser.add_argument("-jpg", "--jobs_per_gpu",
                            type=int,
                            default=2,
                            help="Number of job instance(s) per GPU. Only valid when --no_gpu is off.")
        parser.add_argument("-m", "--gpu_mem_usage",
                            type=float,
                            default=1,
                            help="MotionCor2 memory usage.")
        parser.add_argument("--exec_path",
                            type=str,
                            default='/opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110',
                            help="Path to MotionCor2 executable. (Default: /opt/lmod/modules/motioncor2/1.4.0/MotionCor2_1.4.0/MotionCor2_1.4.0_Cuda110)")
        parser.add_argument("--gain",
                            type=str,
                            help="Path to gain reference file. (Default: None)")
        parser.add_argument("pixel_size",
                            type=float,
                            help="Image pixel size in Angstroms.")
        parser.add_argument("--super_res",
                            action="store_true",
                            help="Use flag if images are super-resolution.")
        parser.add_argument("-dt", "--discard_top",
                            type=int,
                            default=0,
                            help="Number of frames discarded from top per image. (Default: 0)")
        parser.add_argument("-db", "--discard_bottom",
                            type=int,
                            default=0,
                            help="Number of frames discarded from bottom per image. (Default: 0)")
        parser.add_argument("-tol", "--tolerance",
                            type=float,
                            default=0.5,
                            help="Threshold of alignment errors in pixels. (Default: 0.5)")
        parser.add_argument("--max_iter",
                            type=int,
                            default=10,
                            help="Maximum number of iterations performed by MotionCor2.")
        parser.add_argument("-ps", "--patch_size",
                            nargs=3,
                            type=int,
                            default=[5, 5, 20],
                            help="Size of patches used in alignment.")
        parser.add_argument("--no_subgroups",
                            action="store_false",
                            help="Do not use subgroups in alignment.")
    
        args = parser.parse_args([f'{self.proj_name}',
                                  '1.0',
        ])

        prmMod.new_mc2_yaml(args=args)

        file_to_find = f'{self.proj_name}_mc2.yaml'
        self.assertTrue(file_to_find in glob(file_to_find))
        
