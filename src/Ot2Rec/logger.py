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


import logging
import threading
import datetime as dt


class Logger():
    """
    Class encapsulating a Logger object
    """

    def __init__(self,
                 log_path: str = None,
                 ):
        """
        Initialise Logger object

        ARGS:
        log_path :: Path to the log file
        """
        self.log_path = log_path

        # Define default logging behaviour
        logging.basicConfig(
            filename=self.log_path,
            level=logging.INFO,
            format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
            datefmt="%d%b%Y-%H:%M:%S"
        )


    def __call__(self,
                 log_path: str,
                 log_type: str,
                 message: str,
                 stdout: bool = True,
    ):
        """
        Send a string to stdout and log file one process at a time.

        ARGS:
        log_path :: Path to the log file
        log_type :: type of log (info / warning / error)
        message  :: message to be output to file
        stdout   :: whether to output to shell
        """

        # Define default logging behaviour
        # logging.basicConfig(
        #     filename=self.log_path,
        #     level=logging.INFO,
        #     format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
        #     datefmt="%d%b%Y-%H:%M:%S"
        # )

        if log_type == "info":
            logging.info(message)
        elif log_type == "warning":
            logging.warning(message)
        elif log_type == "error":
            logging.error(message)

        if stdout:
            print(message)
