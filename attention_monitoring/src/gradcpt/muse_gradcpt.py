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
    
    def run(self) -> None:
        with ExitStack() as stack:
            # TODO: start with -logfile option
            
            # Setup writing log to file if specified
            if writeLogToFile:
                logFilePath = os.path.join(self._DIR, "run.log")
                formatter = getVerboseLogFormatter(self.getStudyType())
                stack.enter_context(_GradCPTLogToFileCM(logFilePath))
                
            # Start MATLAB engine asynchronously (do this first as it may take
            # some time)
            future = self._startMatlab()
            # Add callback to cancel MATLAB startup
            errmsg = "Failed to cancel MATLAB startup"
            stack.callback(_makeMatlabCanceller(future, errmsg))
            
            # Setup LabRecorder
            lrPath = CONFIG.path_to_LabRecorder
            if lrPath is not None:
                lrLogFilePath = os.path.join(self.__dir, "lab_recorder.log")
                stack.enter_context(_LaunchLabRecorder(lrLogFilePath, lrPath))
                
            # Run experiment. Pass `writeLogToFile=False` as it has already
            # been dealt with. If needed, log messages made by the below method
            # will automatically by saved to the correct file. (passing True
            # could result in possibly two logs trying to write to the same
            # file)
            super().run(writeLogToFile=False)
            
            # The remaining resources (eg Bluemuse, LabRecorder) are closed
            # automatically when exiting the context manager