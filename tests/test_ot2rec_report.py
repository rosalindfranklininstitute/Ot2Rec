# Copyright 2023 Rosalind Franklin Institute
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

import unittest
from unittest.mock import patch
from Ot2Rec import ot2rec_report
from Ot2Rec import logger

class Ot2RecReportSmokeTest(unittest.TestCase):

    @patch("shutil.which", return_value="/bin/docker")
    def test_docker_command_created(self, docker_mock):
        o2r_report = ot2rec_report.Ot2Rec_Report(
            project_name="TS",
            logger_in = logger.Logger(),
            docker_image_name=None,
        )
        
        cmd = o2r_report._get_ot2rec_report_command()

        self.assertTrue(cmd[0], "docker")
        self.assertTrue(cmd[-2], "ot2rec-report:dev")
        self.assertTrue(cmd[-1], "TS")

    @patch("shutil.which", return_value="/bin/ot2rec_report")
    @patch("shutil.which", return_value=None)
    def test_direct_command_created(self, docker_mock, o2r_run_mock):
        o2r_report = ot2rec_report.Ot2Rec_Report(
            project_name="TS",
            logger_in = logger.Logger(),
            docker_image_name=None,
        )
        
        cmd = o2r_report._get_ot2rec_report_command()

        self.assertTrue(cmd[0], "o2r.report.run")
        self.assertTrue(cmd[-1], "TS")

    @patch("shutil.which", return_value=None)
    @patch("shutil.which", return_value=None)
    def test_no_command_created(self, docker_mock, o2r_run_mock):
        o2r_report = ot2rec_report.Ot2Rec_Report(
            project_name="TS",
            logger_in = logger.Logger(),
            docker_image_name=None,
        )

        with self.assertRaises(ValueError):
            o2r_report._get_ot2rec_report_command()

    def test_flags_added(self):
        o2r_report = ot2rec_report.Ot2Rec_Report(
            "--to_html",
            "ignore",
            "this",
            project_name="TS",
            logger_in = logger.Logger(),
            docker_image_name=None,
        )
        self.assertListEqual(
            o2r_report.flags_to_add,
            ["--to_html"]
        )
