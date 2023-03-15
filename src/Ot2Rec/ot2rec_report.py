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

import argparse
import os
import shutil
import subprocess

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
                self.docker_image_name = "ot2rec-report:dev"
            else:
                self.docker_image_name = docker_image_name        
        
        # Add flags to attrs
        self.flags_to_add = []
        for flag in flags:
            if (flag == "--to_html") or (flag == "--to_slides"):
                self.flags_to_add.append(flag)

    def _run_ot2rec_report_direct(self) -> list:
        """Run `o2r.report.run` directly

        Raises:
            ValueError: when o2r.report.run is not available
        """
        # if shutil.which("o2r.report.run") is None:
        #     raise ValueError(
        #         "ot2rec.ot2rec_report: o2r.report.run not found "
        #         "Ensure o2r.report.run works in the terminal."
        #     )
        
        cmd = ["o2r.report.run", self.proj_name]
        if len(self.flags_to_add) > 0:
            for flag in self.flags_to_add:
                cmd.append(flag)
        
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='ascii',
            check=True,
        )

        return cmd

    def _run_ot2rec_report_docker(self):
        """Run `o2r.report.run` through Docker container
        """
        client = docker.from_env()
        container = client.containers.run(
            image=self.docker_image_name,
            volumes=[f"{os.getcwd()}:{os.getcwd()}"],
            working_dir=os.getcwd(),
            command=self.proj_name,
            detach=True
        )
        output = container.attach(
            stdout=True,
            stream=True,
            logs=True,
        )
        for line in output:
            self.logObj(line)

    def run_ot2rec_report(self):
        """Runs `o2r.report.run` through Docker if available, otherwise direct.
        """
        try:
            import docker
            self.logObj(
                "ot2rec.ot2rec_report: Running o2r.report.run via Docker"
            )
        except ModuleNotFoundError:
            self.logObj(
                "ot2rec.ot2rec_report: Running o2r.report.run directly"
            )
            self._run_ot2rec_report_direct()
        else:
            self._run_ot2rec_report_docker()

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "project_name",
        type=str,
        help="Name of current project"
    )
    args = parser.parse_args()

    o2r_report = Ot2Rec_Report(
        project_name=args.project_name,
        logger_in=logMod.Logger("o2r_report.log"),
    )

    o2r_report.run_ot2rec_report()
