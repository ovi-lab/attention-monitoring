from abc import abstractmethod
import csv
import logging
import os
import subprocess
from time import sleep

import matlab.engine
import polars as pl

from src.config import CONFIG
from src.eeg_device import EEGDevice
from src.study import StudySession, StudyBlock
from src.study.helpers import getVerboseLogFormatter
from ._gradcpt_block import GradCPTBlock

_log = logging.getLogger(__name__)

class GradCPTSession(StudySession):
    
    # TODO: add documentation
    # TODO: add functionality for starting an existing session
    # TODO: integrate logger with MATLAB and labrecorder
    
    def __init__(
            self, 
            dataSubDir: [None | str] = None,
            sessionName: [str | None] = None,
            participantID: [int | None] = None
            ) -> None:
        
        super().__init__(
            dataSubDir=dataSubDir,
            sessionName=sessionName, 
            participantID=participantID
            )        
        
        # Create the blocks for this session
        _log.debug("Creating session blocks")
        self._blocks = {}
        if CONFIG.do_practice_block:
            name = f"{self._info['session_name']}_practice_block"
            _log.debug(f"Creating block: {name}")
            block = GradCPTBlock.makePracticeBlock(name, self._DIR)
            self._blocks[block.name] = block
        for k in range(CONFIG.num_full_blocks):
            name = f"{self._info['session_name']}_full_block_{k + 1}"
            _log.debug(f"Creating block: {name}")
            block = GradCPTBlock.makeFullBlock(name, self._DIR, n=(k + 1))
            self._blocks[block.name] = block
        
        # Create a new session if `sessionName` is unspecified.
        if sessionName is None:
            # Create a "blocks file" that summarizes the blocks for this
            # session
            blocksFile = os.path.join(self._DIR, "blocks.csv")
            _log.debug(f"Creating blocks file: {blocksFile}")
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
            self._info["blocks_file"] = blocksFile
            
            # Update the info file with relevant config values
            configVals = [
                "num_full_blocks", "do_practice_block", 
                "stim_transition_time_ms", "stim_static_time_ms", 
                "stim_diameter", "full_block_sequence_length", "muse_signals"
                ]
            _log.debug(f"Updating info file with fields: {configVals}")
            self._info.update(**{v : getattr(CONFIG, v) for v in configVals})
        
    @property
    @abstractmethod
    def eeg(self) -> EEGDevice:
        pass
    
    @property
    def blocks(self) -> dict[str, StudyBlock]:
        return {k : v for (k, v) in self._blocks.items()}
    
    def run(self) -> None:
        # TODO: finish this
        
        # Write log to file
        runLogPath = os.path.join(self._DIR, "run_log.log")
        runHandler = logging.FileHandler(runLogPath)
        runHandler.setLevel(logging.DEBUG)
        runHandler.setFormatter(getVerboseLogFormatter(self.getStudyType()))
        _log.addHandler(runHandler)
        
        try:
            _log.info("RUNNING GRADCPT SESSION")
            _log.debug("Session info: %s", self.info)
            
            # Start MATLAB engine asynchronously (do this first as it may take
            # some time)
            _log.debug("Starting the MATLAB engine asynchronously")
            future = matlab.engine.start_matlab(background=True)
            
            # Connect to the EEG device and start streaming
            _log.debug("Connecting to the EEG")
            self.eeg.connect()
            self.eeg.startStreaming()
            
            # Start LabRecorder
            if CONFIG.path_to_LabRecorder != "":
                _log.debug("Starting LabRecorder")
                proc1 = subprocess.Popen(
                    os.path.realpath(CONFIG.path_to_LabRecorder),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                    )   
                
            # Wait for MATLAB to finish starting
            _log.info("Running experiment in MATLAB ...")
            _log.debug("Waiting for MATLAB to start ...")
            while not future.done():
                sleep(0.5)
            _log.debug("Waiting for MATLAB to start: DONE")

            # Run the experiment on MATLAB
            _log.debug("Displaying stimuli using Psychtoolbox")
            eng = future.result()
            p = eng.genpath(CONFIG.projectRoot)
            eng.addpath(p, nargout=0)
            data = eng.gradCPT(
                self._info["info_file"],
                'verbose', CONFIG.verbose,
                'streamMarkersToLSL', CONFIG.stream_markers_to_lsl,
                'recordLSL', CONFIG.record_lsl,
                'tcpAddress', CONFIG.tcp_address,
                'tcpPort', CONFIG.tcp_port
                )
            _log.info("Running experiment in MATLAB: DONE")

            # Close the EEG device
            _log.debug("Closing the EEG")
            self.eeg.stopStreaming()
            self.eeg.disconnect()

            # Close LabRecorder
            if CONFIG.path_to_LabRecorder != "":
                _log.debug("Closing LabRecorder")
                proc1.kill()
                out, err = proc1.communicate()
                if CONFIG.verbose >= 2:
                    print("\nLabRecorder Output\n")
                    print(out)
        finally:
            runHandler.close()
            _log.removeHandler(runHandler)
    
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