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
from unittest.mock import patch, Mock
from Ot2Rec import ot2rec_report
from Ot2Rec import logger
import sys

class Ot2RecReportTest(unittest.TestCase):

    @patch("Ot2Rec.ot2rec_report.Ot2Rec_Report._run_ot2rec_report_docker")
    def test_o2r_report_docker(self, docker_runner_mock):
        sys.modules["docker"] = Mock()
        o2r_report = ot2rec_report.Ot2Rec_Report(
            project_name="TS",
            logger_in=logger.Logger("o2r_report.log")
        )
        o2r_report.run_ot2rec_report()
        self.assertTrue(docker_runner_mock.called)
    
    @patch("builtins.__import__")
    @patch("subprocess.run")
    def test_o2r_report_direct(
        self, 
        direct_runner_mock, 
        import_mock, 
    ):
        # Ensure docker is not available
        import_mock.side_effect = ModuleNotFoundError

        o2r_report = ot2rec_report.Ot2Rec_Report(
            project_name="TS",
            logger_in=logger.Logger("o2r_report.log")
        )
        o2r_report.run_ot2rec_report()
        self.assertTrue(direct_runner_mock.called)
