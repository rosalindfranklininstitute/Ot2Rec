"""
Ot2Rec.logger.py

Copyright (C) Rosalind Franklin Institute 2021

Author: Neville B.-y. Yee
Date: 17-Jun-2021

Version: 0.0.2
"""

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
