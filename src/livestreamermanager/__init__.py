from .logger import Logger
from .options import Options
from .stream import StreamError
from livestreamer import Livestreamer

import pkgutil
import imp

class Livestreamermanager(object):
    """
A Livestreamermanager session is used to keep track of 
options and log settings.

"""

    def __init__(self):
        self.logger = Logger()
        self.livestreamer = Livestreamer()

    def set_loglevel(self, level):
        """
Set the log level to *level*.
Valid levels are: none, error, warning, info, debug.
"""
        self.logger.set_level(level)

    def set_logoutput(self, output):
        """
Set the log output to *output*. Expects a file like
object with a write method.
"""
        self.logger.set_output(output)

__all__ = ["Livestreamermanager"]
