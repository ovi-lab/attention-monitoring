from contextlib import ExitStack
import logging
import os
import subprocess
from typing import Callable

import matlab.engine

from src.config import CONFIG
from src.eeg_device import Muse
from src.gradcpt import GradCPTSession
from src.gradcpt.helpers import _GradCPTLogToFileCM
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

            # Setup writing log to file
            logFilePath = os.path.join(self._DIR, "run.log")
            formatter = getVerboseLogFormatter(self.getStudyType())
            stack.enter_context(_GradCPTLogToFileCM(logFilePath))
            
            # Start MATLAB engine asynchronously (do this first as it may take
            # some time)
            _log.debug("Starting the MATLAB engine asynchronously")
            future = matlab.engine.start_matlab(background=True)
            # Add callback to cancel MATLAB startup
            errmsg = "Failed to cancel MATLAB startup"
            stack.callback(_makeMatlabCanceller(future, errmsg))
            
            # Setup Muse
            stack.enter_context(_MuseCM())
            
            # Setup LabRecorder
            lrPath = CONFIG.path_to_LabRecorder
            if lrPath is not None:
                lrLogFilePath = os.path.join(self.__dir, "lab_recorder.log")
                stack.enter_context(_LaunchLabRecorder(lrLogFilePath, lrPath))
                
            # Wait for MATLAB to finish starting
            _log.info("Running experiment in MATLAB")
            _log.debug("Waiting for MATLAB to start ...")
            while not future.done():
                sleep(0.5)
            _log.debug("Matlab started")
            
            # Run experiment in MATLAB
            _log.debug("Displaying stimuli in MATLAB")
            # Add project root directory to MATLAB path
            p = eng.genpath(CONFIG.projectRoot)
            eng.addpath(p, nargout=0)
            # Display the stimuli, running in background
            future = eng.gradCPT(
                self._info["info_file"],
                'verbose', CONFIG.verbose,
                'streamMarkersToLSL', CONFIG.stream_markers_to_lsl,
                'recordLSL', CONFIG.record_lsl,
                'tcpAddress', CONFIG.tcp_address,
                'tcpPort', CONFIG.tcp_port,
                stdout=matlabOut,
                stderr=matlabOut,
                background=True
                )
            # Add callback to cancel stimuli presentation in MATLAB
            errmsg = "Failed to cancel `gradCPT.m` in MATLAB"
            stack.callback(_makeMatlabCanceller(future, errmsg))
            
            # Wait for experiment in MATLAB to end, then close the engine
            future.result()
            # TODO: add logging
            eng.quit()
            
            # The remaining resources (eg Bluemuse, LabRecorder) are closed
            # automatically when exiting the context manager
                  
def _makeMatlabCanceller(
        future: matlab.engine.FutureResult, 
        errmsg: str
        ) -> Callable[[], None]:
    """Get a function that, when called, cancels the specified asynchronous
    call to MATLAB.
    
    When calling the returned function, if (at that time) the specified call to
    MATLAB is already done or has already been cancelled, the returned function
    will return without attempting to cancel the call to MATLAB.
    
    Parameters
    ----------
    future : matlab.engine.FutureResult
        The call to MATLAB that is to be cancelled. Specifically, this is the
        value that was returned by making a call to MATLAB with
        `background=True`.
    errmsg : str
        The error message to include in the raised exception if the call to
        MATLAB is not successfully cancelled.
        
    Raises
    ------
    matlab.engine.CancelledError
        If the call to MATLAB is not successfully cancelled.
        
    Returns
    -------
    Callable[[], None]
        The function to call to cancel the specified MATLAB call.
    """
    def f() -> None:
        # Only cancel if not already cancelled
        if (not future.cancelled()) or (not future.done()):
            future.cancel()
            if not future.cancelled():
                raise matlab.engine.CancelledError(errmsg)
        
    return f  
                                  
class _MuseCM:
    """Context manager for connecting and streaming a Muse device."""
    def __init__(self, *args, **kwargs):
        self._muse = Muse(*args, **kwargs)
    
    def __enter__(self):
        _log.debug(
            "Attempting to connect to the Muse and stream its data to LSL"
            )
        self._muse.connect()
        self._muse.startStreaming()
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        _log.debug(
            "Attempting to stop Muse from streaming to LSL and disconnect"
            )
        self._muse.stopStreaming()
        self._muse.disconnect()