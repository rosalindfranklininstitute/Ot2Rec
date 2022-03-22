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
from Ot2Rec import user_args as uaMod


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
        parser = uaMod.get_args_new_proj()
        args = parser.parse_args([f'{self.proj_name}'])

        prmMod.new_master_yaml(args=args)

        file_to_find = f'{self.proj_name}_proj.yaml'
        self.assertTrue(file_to_find in glob(file_to_find))
    

    def test_new_mc2_yaml(self):
        # Parse user inputs
        parser = uaMod.get_args_mc2()
            args = parser.parse_args([f'{self.proj_name}',
                                  '1.0',
        ])

        prmMod.new_mc2_yaml(args=args)

        file_to_find = f'{self.proj_name}_mc2.yaml'
        self.assertTrue(file_to_find in glob(file_to_find))
        
