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


# Utility imports
import unittest
import os
import pathlib

# Import plugin
from Ot2Rec import quoll
from Ot2Rec import magicgui as mgMod
from Ot2Rec import params as prmMod


class QuollTest(unittest.TestCase):
    """
    Tests the Quoll plugin
    """

    def test_quoll_yaml_basic(self):
        """
        Tests that quoll's yaml is created for the most basic test case
        Uses demo/quoll/042.tif
        """
        # Change to the demo directory
        os.chdir(f"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/demo")
        
        # Set-up args
        args = mgMod.get_args_quoll.show()
        args.project_name.value = "Test01"
        args.image_fname.value = "/quoll/042.tif"
        args.pixel_size.value = 3
        args.tile_size.value = 0

        # Create and update *_quoll.yaml
        prmMod.new_quoll_yaml(args)
        quoll.update_yaml(args)

        self.assertTrue(os.path.exists("Test01_quoll.yaml"))

        read_args = prmMod.read_yaml("Test01", "Test01_quoll.yaml")
        self.assertEqual(read_args.params["OneImgFRC"]["image_fname"], "/quoll/042.tif")
        self.assertEqual(read_args.params["OneImgFRC"]["pixel_size"], 3.0)
        self.assertEqual(read_args.params["OneImgFRC"]["tile_size"], 0)


if __name__ == "__main__":
    unittest.main()
