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
import tempfile
import pathlib

# Import plugin
from Ot2Rec import aretomo
from Ot2Rec import user_args as uaMod
from Ot2Rec import params as prmMod

@unittest.skip("Deprecated but keeping for reference")
class AreTomoTest(unittest.TestCase):
    """
    Tests the AreTomo plugin
    """

    def setUp(self):
        """
        Creates prerequisite files
        """
        self._temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = pathlib.Path(self._temp_dir.name)
        os.mkdir(self.temp_path / 'aretomo')
        os.mkdir(self.temp_path / 'aretomo/TS_01')
        self._create_file(self.temp_path / 'aretomo/TS_01/TS_01.st', '')
        self._create_file(self.temp_path / 'aretomo/TS_01/TS_01.rawtlt', '')

    def tearDown(self):
        self._temp_dir.cleanup()

    def _create_file(self, path, data):
        with open(path, 'w') as f:
            f.write(data)

    def _generate_yaml(self, working_dir, args, kwargs):
        """
        Generates the AreTomo yaml in working_dir based on args, return params
        """
        # Create the yaml file
        os.chdir(working_dir)
        prmMod.new_aretomo_yaml(args)
        aretomo.update_yaml(args, kwargs)

        # Read in params from yaml file
        aretomo_params = prmMod.read_yaml(
            args.project_name,
            self._get_aretomo_yaml_name(args)
        )

        return aretomo_params

    def _get_aretomo_yaml_name(self, args):
        aretomo_yaml_names = {
            0: args.project_name + "_aretomo_align.yaml",
            1: args.project_name + "_aretomo_recon.yaml",
            2: args.project_name + "_aretomo_align-recon.yaml"
        }

        aretomo_yaml_name = aretomo_yaml_names[int(args.aretomo_mode)]

        return aretomo_yaml_name

    def test_prereq_files(self):
        """
        Tests that prerequisite files are created correctly
        """
        self.assertEqual(len(os.listdir(self.temp_path / 'aretomo/TS_01')), 2)

    def test_aretomo_align_defaults(self):
        """
        Tests that the aretomo_align.yaml is created correctly with default values
        """
        parser = uaMod.get_args_aretomo()
        args, kwargs = parser.parse_known_args([
            'TS',
            '0',
            '90'
        ])

        aretomo_params = self._generate_yaml(
            self.temp_path,
            args,
            kwargs
        )

        self.assertEqual(
            aretomo_params.params["System"]["process_list"], [1]
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["aretomo_mode"], 0
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["rot_angle"], 90
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["input_mrc"][0],
            './aretomo/TS_01/TS_01.st'
        )
        self.assertTrue(
            aretomo_params.params["AreTomo_setup"]["output_mrc"][0].endswith("_ali.mrc")
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["tilt_angles"][0],
            './aretomo/TS_01/TS_01.rawtlt'
        )

    def test_aretomo_extra_kwargs(self):
        """
        Tests passing extra kwargs to aretomo parser
        """
        parser = uaMod.get_args_aretomo()
        args, kwargs = parser.parse_known_args([
            'TS',
            '0',
            '90',
            '--extra',
            'kwargs'
        ])

        aretomo_params = self._generate_yaml(
            self.temp_path,
            args,
            kwargs
        )

        self.assertEqual(aretomo_params.params['AreTomo_kwargs'], ['--extra', 'kwargs'])

    def test_aretomo_recon_defaults(self):
        """
        Tests that aretomo_recon.yaml is created correctly
        """
        # Add .ali and .tlt files
        self._create_file(self.temp_path / 'aretomo/TS_01/TS_01_ali.mrc', '')
        self._create_file(self.temp_path / 'aretomo/TS_01/TS_01_ali.tlt', '')

        parser = uaMod.get_args_aretomo()
        args, kwargs = parser.parse_known_args([
            'TS',
            '1',
            '90',
            '--volz',
            '200'
        ])

        aretomo_params = self._generate_yaml(
            self.temp_path,
            args,
            kwargs
        )

        self.assertEqual(
            aretomo_params.params["System"]["process_list"], [1]
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["aretomo_mode"], 1
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["input_mrc"][0],
            "./aretomo/TS_01/TS_01_ali.mrc"
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["tilt_angles"][0],
            "./aretomo/TS_01/TS_01_ali.tlt"
        )
        self.assertTrue(
            aretomo_params.params["AreTomo_setup"]["output_mrc"][0].endswith("_rec.mrc")
        )
        self.assertTrue(
            aretomo_params.params["AreTomo_recon"]["volz"] > 0
        )

    def test_aretomo_alignrecon_defaults(self):
        """
        Tests that aretomo_align-recon.yaml is created correctly
        """

        parser = uaMod.get_args_aretomo()
        args, kwargs = parser.parse_known_args([
            'TS',
            '2',
            '90',
            '--volz',
            '200'
        ])

        aretomo_params = self._generate_yaml(
            self.temp_path,
            args,
            kwargs
        )

        self.assertEqual(
            aretomo_params.params["System"]["process_list"], [1]
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["aretomo_mode"], 2
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["input_mrc"][0],
            "./aretomo/TS_01/TS_01.st"
        )
        self.assertEqual(
            aretomo_params.params["AreTomo_setup"]["tilt_angles"][0],
            "./aretomo/TS_01/TS_01.rawtlt"
        )
        self.assertTrue(
            aretomo_params.params["AreTomo_setup"]["output_mrc"][0].endswith("_rec.mrc")
        )
        self.assertTrue(
            aretomo_params.params["AreTomo_recon"]["volz"] > 0
        )


if __name__ == "__main__":
    unittest.main()
