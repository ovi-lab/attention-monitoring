from abc import abstractmethod
import aiofiles
import asyncio
from contextlib import ExitStack, contextmanager
import csv
from io import StringIO
import logging
import os
import shlex
import subprocess
from time import sleep
from typing import Any, Callable

import matlab.engine as me
import polars as pl

from src.config import CONFIG
from src.eeg_device import EEGDevice
from src.gradcpt.helpers import _GradCPTLogToFileCM, _makeMatlabCanceller
from src.study import StudySession, StudyBlock
from src.study.helpers import getVerboseLogFormatter, _LaunchLabRecorder
from ._gradcpt_block import GradCPTBlock

_log = logging.getLogger(__name__)

class GradCPTSession(StudySession):
    
    # TODO: add documentation
    # TODO: add functionality for starting an existing session
    # TODO: integrate logger with MATLAB and labrecorder
    
    def __init__(
            self, 
            /,
            dataSubDir: [None | str] = None,
            sessionName: [str | None] = None,
            **kwargs
            ) -> None:
        
        super().__init__(
            dataSubDir=dataSubDir,
            sessionName=sessionName, 
            **kwargs
            )
        
        # Initialize attribute to store result of calls to asynchronously start
        # MATLAB. This attribute may only be accessed or modified by the
        # `_startMatlab()` method of this class. 
        # 
        # Rep invariant: `self.__matlabEng` is either `None` or an instance of
        # `matlab.engine.FutureResult`.
        self.__matlabEng = None
        
        # Create the blocks for this session
        _log.debug("Creating session blocks")
        self._blocks = {}
        if CONFIG.do_practice_block:
            name = f"{self._info['session_name']}_practice_block"
            _log.debug("Creating block: %s", name)
            block = GradCPTBlock.makePracticeBlock(
                name, self._DIR, dataSubDir=dataSubDir
                )
            self._blocks[block.name] = block
        for k in range(CONFIG.num_full_blocks):
            name = f"{self._info['session_name']}_full_block_{k + 1}"
            _log.debug("Creating block: %s", name)
            block = GradCPTBlock.makeFullBlock(
                name, self._DIR, dataSubDir=dataSubDir, n=(k + 1)
                )
            self._blocks[block.name] = block
        
        # Create a new session if `sessionName` is unspecified.
        if sessionName is None:
            # Create a "blocks file" that summarizes the blocks for this
            # session
            blocksFile = os.path.join(self._DIR, "blocks.csv")
            _log.debug("Creating blocks file: %s", blocksFile)
            blocksFileFieldNames = [
                "block_name", "pre_block_msg", "pre_block_wait_time",
                "stim_sequence_file", "data_file"
                ]
            with open(blocksFile, "w") as f:
                dictWriter = csv.DictWriter(f, fieldnames=blocksFileFieldNames)
                dictWriter.writeheader()
                for block in self._blocks.values():
                    dictWriter.writerow(
                        {
                            "block_name" : block.name,
                            "pre_block_msg" : block.preBlockMsg,
                            "pre_block_wait_time" : block.preBlockWaitTime,
                            "stim_sequence_file" : block.stimSequenceFile,
                            "data_file" : block.dataFile
                        }
                        )
            _log.debug("Updating info file with fields: %s", ["blocks_file"])
            self._info["blocks_file"] = blocksFile
            
            # Update the info file with relevant config values
            configVals = [
                "num_full_blocks", "do_practice_block", 
                "stim_transition_time_ms", "stim_static_time_ms", 
                "stim_diameter", "full_block_sequence_length"
                ]
            _log.debug("Updating info file with fields: %s", configVals)
            self._info.update(**{v : getattr(CONFIG, v) for v in configVals})
        
    @property
    @abstractmethod
    def eeg(self) -> EEGDevice:
        pass
    
    @property
    def blocks(self) -> dict[str, StudyBlock]:
        return {k : v for (k, v) in self._blocks.items()}
    
    def run(self, writeLogToFile: bool = True) -> None:
        # Define a context manager for connecting to the EEG device and
        # streaming its data
        @contextmanager
        def eegCM():
            # Start
            _log.debug("Attempting to connect to the EEG device")
            self.eeg.connect()
            self.eeg.startStreaming()
            yield
            # Exit
            _log.debug("Attempting to disconnect the EEG device")
            self.eeg.stopStreaming()
            self.eeg.disconnect()
                
        with ExitStack() as stack:
            # Setup writing log to file if necessary
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
            
            # Connect to the EEG device
            stack.enter_context(eegCM())
            
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
            _log.debug("MATLAB started")
            
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
            _log.debug("Waiting for MATLAB to finish presenting stimuli...")
            future.result()
            _log.debug("Done presenting stimuli in MATLAB")
            _log.debug("Terminating the MATLAB engine")
            eng.quit()   
            
            # Remaining resources (eg. the EEG device, LabRecorder) are closed
            # automatically when exiting the context manager
        
    
    def _startMatlab(self): 
        
        # TODO: start with -logfile option
                    
        startNewEngine = True
        
        # Check if the call to start MATLAB has already been made for this
        # session and that it has not been cancelled
        if self.__matlabEng is not None and not self.__matlabEng.cancelled():
            if self.__matlabEng.done():
                # If MATLAB startup has finished, Ensure the engine hasn't been
                # terminated by trying to call a MATLAB function (in this case,
                # `plus(1, 1)`)
                try:
                    eng = self.__matlabEng.result()
                    eng.plus(1,1, nargout=0)
                except matlab.engine.RejectedExecutionError:
                    # The engine has been terminated, Reset `self.__matlabEng`
                    # to `None` and re-call this method to start a new engine
                    self.__matlabEng = None
                    return self._startMatlab()
                
            startNewEngine = False
        
        # Start a new MATLAB engine if necessary
        if startNewEngine:
            _log.debug("Starting MATLAB engine asynchronously")
            self.__matlabEng = matlab.engine.start_matlab(background=True)

        return self.__matlabEng
    
    def display(self) -> None:
        # TODO: finish this
        if all(block.data is None for block in self._blocks.values()):
            print("No data to display.")
        else:
            for name, block in self._blocks.items():
                if block.data is None:
                    print(f"No data to display for block {name}.")
                else:
                    block.display()
            
    @classmethod
    def getStudyType(cls) -> str:
        return "GradCPT"