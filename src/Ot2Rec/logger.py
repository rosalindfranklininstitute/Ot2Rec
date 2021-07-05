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


import threading
import datetime as dt


class Logger():
    """
    Class encapsulating a Logger object
    """

    def __init__(self,
                 log_path: str=None,
    ):
        """
        Initialise Logger object

        ARGS:
        log_path :: Path to the log file
        """

        self.lock = threading.Lock()
        self.log_path = log_path


    def __call__(self,
                 log: str,
                 stdout: bool=True,
                 newline: bool=False):
        """
        Send a string to stdout and log file one process at a time.

        ARGS:
        log     :: message to be output to file
        stdout  :: whether to output to shell
        newline :: whether to add new line before message
        """

        now = dt.datetime.now().strftime("%d%b%Y-%H:%M:%S")
        with self.lock:
            if newline:
                message = '\n{} - {}'.format(now, log)
            else:
                message = '{} - {}'.format(now, log)

            if stdout:
                print(message)
            if self.log_path is not None:
                with open(self.log_path, 'a') as f:
                    f.write(message + '\n')
