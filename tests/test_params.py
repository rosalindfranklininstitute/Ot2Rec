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
import pathlib as pl
import subprocess
from glob import glob


# Test imports
import Ot2Rec
from Ot2Rec import user_args as uaMod
from Ot2Rec import params as pMod


class ParamsTest(unittest.TestCase):
    """
    Tests the Params functions work in O2R
    """

    def setUp(self):
        test = pMod.Params(project_name="test")


    def tearDown(self):
        yaml_list = glob("./*.yaml")
        if len(yaml_list) > 0:
            for curr_file in yaml_list:
                subprocess.run(["rm", f"{curr_file}"])
        

    def test_master_yaml(self):
        """
        Method to test O2R.params:new_master_yaml function
        """
        parser = uaMod.get_args_new_proj()
        args = parser.parse_args(["test"])

        pMod.new_master_yaml(args)

        out_file = pl.Path(f"{args.project_name}_proj.yaml")
        self.assertTrue(out_file.is_file())


    def test_mc2_yaml(self):
        """
        Method to test O2R.params:new_mc2_yaml function
        """
        parser = uaMod.get_args_mc2()
        args = parser.parse_args(["test", "1.0"])

        pMod.new_mc2_yaml(args)
    
        out_file = pl.Path(f"{args.project_name}_mc2.yaml")
        self.assertTrue(out_file.is_file())


    def test_ctffind_yaml(self):
        """
        Method to test O2R.params:new_ctffind_yaml function
        """
        parser = uaMod.get_args_ctffind()
        args = parser.parse_args(["test"])

        pMod.new_ctffind_yaml(args)
    
        out_file = pl.Path(f"{args.project_name}_ctffind.yaml")
        self.assertTrue(out_file.is_file())
