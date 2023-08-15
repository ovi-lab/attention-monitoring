from contextlib import ExitStack
import logging
import os
import subprocess
from typing import Callable

import matlab.engine

from src.config import CONFIG
from src.eeg_device import Muse
from src.gradcpt import GradCPTSession
from src.gradcpt.helpers import _GradCPTLogToFileCM, _makeMatlabCanceller
from src.study.helpers import _LaunchLabRecorder, getVerboseLogFormatter

_log = logging.getLogger(__name__)

class MuseGradCPTSession(GradCPTSession):
    
    def __init__(self, /, **kwargs) -> None:
        
        super().__init__(**kwargs)
        
        self.__eeg = Muse(*CONFIG.muse_signals)
        
        # Update the info file with the signals that will be streamed from Muse
        _log.debug("Updating info file with fields: %s", ["muse_signals"])
        self._info["muse_signals"] = CONFIG.muse_signals
        
    @property
    def eeg(self) -> Muse:
        return self.__eeg