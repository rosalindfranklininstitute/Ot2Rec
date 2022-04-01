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
from Ot2Rec import user_args as uaMod


class AreTomoTest(unittest.TestCase):
    """
    Tests the AreTomo functions work in O2R
    """
    

    def test_basecase(self):
        """
        Method to test base case
        setting project name, aretomo_mode, and rot_angle
        """
        parser, kwargs = uaMod.get_args_aretomo()
        args = parser.parse_args(["test", "0", "90"])

        self.assertEqual(args.project_name, "test")
        self.assertEqual(args.aretomo_mode, 0)
        self.assertEqual(args.rot_angle, 90)
    