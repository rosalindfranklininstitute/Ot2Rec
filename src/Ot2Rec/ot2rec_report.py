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

import shutil
from . import logger as logMod

class Ot2Rec_Report:
    """Ot2Rec Report object

    Attributes:
        proj_name (str): name of the Ot2Rec project to report on
        flags_to_append (list): flags to append to the end of `o2r.report.run`
            Can be either "--to_html" or "--to_slides".
    """

    def __init__(
        self,
        *flags: str,
        project_name: str,
        logger_in: logMod.Logger,
        docker_image_name: str = None,
    ):
        """Initialise a Ot2Rec Report plugin object.

        Args:
            project_name (str): name of the Ot2Rec project
            docker_image_name (str): name of the Docker image to use. Defaults
                to None. If None and Docker is not installed on the system,
                `o2r.report.run` will be run with `subprocess.run`. If None and
                Docker is found on the system, then the default 
                `ot2rec_report:dev` image will be used. Otherwise, if a value 
                is specified and Docker is found, the Docker image with 
                `docker_image_name` will be used.
            *flags (str): flags to add to the end of the command. These can be 
                "--to_html" or "--to_slides", others will be ignored
        """
        self.proj_name = project_name
        self.logObj = logger_in
        
        # Check for docker // set docker_image_name
        if shutil.which("docker") is None:
            self.docker_image_name = None
        else:
            if docker_image_name is None:
                self.docker_image_name = "ot2rec_report:dev"
            else:
                self.docker_image_name = docker_image_name        
        
        # Add flags to attrs
        self.flags_to_add = []
        for flag in flags:
            if (flag == "--to_html") or (flag == "--to_slides"):
                self.flags_to_add.append(flag)

    def _get_ot2rec_report_docker_command(self) -> list:
        """Method to get commands to run ot2rec_report from docker container

        Assumes that Docker image is already on the system
        
        Returns:
            list: List of commands to pass to `subprocess.run` to run the
                Ot2Rec Report Docker command
        """
        cmd = [
            "docker",
            "run",
            "-v",
            "`pwd`:`pwd`",
            "-w",
            "`pwd`",
            self.docker_image_name,
            self.proj_name,
        ]
        
        return cmd

    def _get_ot2rec_report_subprocess_command(self) -> list:
        """Method to get commands to run ot2rec_report using `subprocess.run`

        Assumes that Docker is not available on the system

        Returns:
            list: List of commands to pass to `subprocess.run` as if running
                `o2r.report.run` in the terminal
        """
        cmd = [
            "o2r.report.run",
            self.proj_name,
        ]
        
        return cmd

    def _get_ot2rec_report_command(self) -> list:
        """Gets command to run `o2r.report.run` through docker or directly

        Raises:
            ValueError: when neither Docker or o2r.report.run will work

        Returns:
            list: commands to run `o2r.report.run` through Docker or directly
        """
        if shutil.which("docker") is None:
            self.logObj("ot2rec.ot2rec_report: Docker not found on path")
            cmd = self._get_ot2rec_report_subprocess_command()
        else:
            cmd = self._get_ot2rec_report_docker_command()
        
        if len(self.flags_to_add) > 0:
            for flag in self.flags_to_add:
                cmd.append(flag)
        
        if shutil.which("o2r.report.run") is None:
            self.logObj(
                message=(
                    "ot2rec.ot2rec_report: Docker and o2r.report.run not found"
                    "Ensure o2r.report.run works in the terminal."
                ),
                level="error"
            )
            raise ValueError(
                "ot2rec.ot2rec_report: Docker and o2r.report.run not found "
                "Ensure o2r.report.run works in the terminal."
            )
        return cmd
