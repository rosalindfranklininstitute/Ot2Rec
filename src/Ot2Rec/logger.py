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


import sys
import logging
import threading
import datetime as dt


class Logger:
    """
    Class encapsulating a Logger object
    """

    LEVELS = {"info": 20, "warning": 30, "error": 40, "critical": 50}

    def __init__(
            self,
            name: str = None,
            log_path: str = "",
            level: str = "info",
    ):
        """
        Initialise Logger object

        Args:
            log_path: Path to the log file
        """
        self.name = name
        self.log_path = log_path
        self.level = level
        self.logger = self._setup_logger()


    def _setup_logger(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(fmt="[%(asctime)s] %(levelname)s - %(message)s",
                                      datefmt="%d %b %Y-%H:%M:%S")

        screen_handler = logging.StreamHandler(stream=sys.stdout)
        screen_handler.setFormatter(formatter)

        if not logger.hasHandlers():
            logger.addHandler(screen_handler)

        if self.log_path != "":
            file_handler = logging.FileHandler(self.log_path, mode="a")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger
