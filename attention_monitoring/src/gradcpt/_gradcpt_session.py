from abc import abstractmethod
import aiofiles
import asyncio
from contextlib import ExitStack, contextmanager
import csv
from io import StringIO
import logging
import os
import shlex
import shutil
import subprocess
from time import sleep
from typing import Any, Callable

import matlab.engine
import polars as pl

from src.config import CONFIG
from src.eeg_device import EEGDevice
from src.gradcpt.helpers import _GradCPTLogToFileCM
from src.gradcpt.matlab.pyhelpers import _getMatlabCallback
from src.study import StudySession, StudyBlock
from src.study.helpers import _LaunchLabRecorder
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
        _log.debug("Running session: '%s'", self.info["session_name"])
        with ExitStack() as mainStack:
            # On `mainStack` place a new `ExitStack` object followed by a
            # callback function. This allows the new stack to be used as a
            # normal `ExitStack`, with the exception that the callback function
            # is always executed first when exiting the stack
            
            # Add all context managers for running the study to `stack`
            stack = mainStack.enter_context(ExitStack())
            
            # Add callback to top of mainStack that logs any errors that may
            # have occurred while running the study session. This makes it more
            # clear in the logs when exactly the Exception occurred, as it gets
            # logged before any logging messages made by exiting the stack
            @mainStack.push
            def exitLogger(exc_type, exc_value, exc_tb) -> None:
                studyType = self.getStudyType()
                name = self.info["session_name"]
                if exc_type is not None:
                    exc_info = (exc_type, exc_value, exc_tb)
                    _log.error(
                        "%s occurred while running a %s session (%s), "
                        + "performing clean-up operations",
                        exc_type, studyType, name,
                        exc_info=exc_info
                        )
                else:
                    _log.info(
                        "The %s session (%s) concluded without raising "
                        + "Exceptions, performing clean-up operations",
                        studyType, name
                        )
                                
            # Setup writing log to file if necessary
            if writeLogToFile:
                logFilePath = os.path.join(self._DIR, "run.log")
                stack.enter_context(
                    _GradCPTLogToFileCM(logFilePath, useBaseLogger=True)
                    )
                
            _log.info(
                "Starting a %s session: '%s'", 
                self.getStudyType(), self.info["session_name"]
                )
            
            # Start MATLAB engine asynchronously (do this first as it may take
            # some time) and add callback to cancel MATLAB startup
            _log.debug("Starting the MATLAB engine")
            future = matlab.engine.start_matlab(background=True)
            stack.push(_getMatlabCallback(future, "MATLAB startup"))
            
            # Connect to the EEG device
            stack.enter_context(self.eeg)
            
            # Setup LabRecorder
            lrPath = CONFIG.path_to_LabRecorder
            if CONFIG.record_lsl and lrPath is not None:
                lrLogFilePath = os.path.join(self._DIR, "lab_recorder.log")
                stack.enter_context(_LaunchLabRecorder(lrLogFilePath, lrPath))
                
            # Wait for MATLAB to finish starting and get the MATLAB engine
            _log.info("Running experiment in MATLAB")
            _log.debug("Waiting for MATLAB to start ...")
            while not future.done():
                sleep(0.5)
            _log.debug("MATLAB started")
            eng = stack.enter_context(future.result())
            
            # Run experiment in MATLAB
            _log.debug("Displaying stimuli in MATLAB")
            
            # Add project root directory to MATLAB path
            p = eng.genpath(CONFIG.projectRoot)
            eng.addpath(p, nargout=0)
            
            # Write MATLAB output from stimuli presentation to file on exit
            matlabOut = stack.enter_context(StringIO())
            @stack.push
            def foo(exc_type, exc_value, exc_tb):
                # TODO: should we do this while running the experiment?
                matlabLogFile = os.path.join(self._DIR, "matlab.log")
                _log.debug("Writing MATLAB output to file: %s", matlabLogFile)
                with open(matlabLogFile, "a") as f:
                    matlabOut.seek(0)
                    shutil.copyfileobj(matlabOut, f)
                    
            # Display the stimuli, running in background, and add callback to
            # cancel stimuli presentation
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
            stack.push(_getMatlabCallback(future, "stimuli presentation"))
            
            # Wait for experiment in MATLAB to end
            _log.debug("Waiting for MATLAB to finish presenting stimuli...")
            future.result()
            _log.debug("Done presenting stimuli in MATLAB")
            
            # Close the MATLAB engine
            _log.debug("Terminating the MATLAB engine")
            eng.quit()   
            
            # Remaining resources (eg. the EEG device, LabRecorder) are closed
            # automatically when exiting the context manager
    
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