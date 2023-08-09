import os
import pyxdf
import csv
import random
import polars as pl
from typing import Any
from typing_extensions import Self
import sys

from attention_monitoring.src.config import CONFIG
from .. import StudyBlock

class GradCPTBlock(StudyBlock):
    def __init__(
            self, 
            name: str,
            outputDir: str,
            preBlockMsg: [str | None] = None,
            preBlockWaitingTime: int = 30,
            stimSequenceLength: int = 10
            ) -> None:
        
        super().__init__(name)
        
        self._OUTPUT_DIR = outputDir
        self.preBlockMsg = preBlockMsg if preBlockMsg is not None else ""
        self.preBlockWaitTime = preBlockWaitingTime
        
        # Define the directories where the stimuli are stored, creating them if
        # they don't exist yet.
        self._COMMON_TARGET_DIR = os.path.join(
            self._STIMULI_DIR, "common_target"
            )
        if not os.path.isdir(self._COMMON_TARGET_DIR):
            self._log.debug(f"Creating directory: {self._COMMON_TARGET_DIR}")
            os.makedirs(self._COMMON_TARGET_DIR)
        self._RARE_TARGET_DIR = os.path.join(
            self._STIMULI_DIR, "rare_target"
            )
        if not os.path.isdir(self._RARE_TARGET_DIR):
            self._log.debug(f"Creating directory: {self._RARE_TARGET_DIR}")
            os.makedirs(self._RARE_TARGET_DIR)
        
        # Specify the paths to the stim sequence and data files
        self._stimSequenceFile = os.path.join(
            self._OUTPUT_DIR, self.name + "_stim_sequence.csv"
            )
        self._dataFile = os.path.join(
            self._OUTPUT_DIR, self.name + "_data.xdf"
            )
        
        # Create the stim sequence file if it doesn't exist yet
        if not os.path.isfile(self._stimSequenceFile):
            self._log.debug(
                f"Creating stimulus sequence file: {self._stimSequenceFile}"
                )
            self.__generateStimSequence(stimSequenceLength)
            
        # Initialize the data as None
        self._data = None
    
    @classmethod
    def makePracticeBlock(cls, 
            name: str, 
            outputDir: str,
            ) -> Self:
        
        preBlockWaitingTime = CONFIG.pre_practice_block_break_time
        preBlockMsg = (
            f"Starting practice block in {preBlockWaitingTime} seconds."
            )
        stimSequenceLength = CONFIG.practice_block_sequence_length
        
        return cls(
            name, 
            outputDir, 
            preBlockMsg=preBlockMsg, 
            preBlockWaitingTime=preBlockWaitingTime, 
            stimSequenceLength=stimSequenceLength
            )
    
    @classmethod
    def makeFullBlock(
            cls, 
            name: str, 
            outputDir: str, 
            n: [int | None] = None
            ) -> Self:
        
        preBlockWaitingTime = CONFIG.pre_full_block_break_time
        _n = f" {n}" if n is not None else ""
        preBlockMsg = (
            f"Starting block{_n} in {preBlockWaitingTime} seconds."
            )
        stimSequenceLength = CONFIG.full_block_sequence_length
        
        return cls(
            name, 
            outputDir, 
            preBlockMsg=preBlockMsg, 
            preBlockWaitingTime=preBlockWaitingTime, 
            stimSequenceLength=stimSequenceLength
            )
    
    @property
    def stimSequenceFile(self) -> str:
        return self._stimSequenceFile
    
    @property
    def stimSequence(self) -> dict[str, list[str]]:
        self._log.debug(
            f"Reading stimulus sequence file: {self.stimSequenceFile}"
            )
        return pl.read_csv(self.stimSequenceFile).to_dict(as_series=False)
    
    @property
    def dataFile(self) -> str:
        return self._dataFile
    
    @property
    # Note that the returned dict should not be modified, only read.
    def data(self) -> [Any | None]:
        if self._data is None:
            if os.path.isfile(self.dataFile):
                self._log.debug(f"Loading data file: {self.dataFile}")
                self._data = self.loadData(self.dataFile)
            else:
                self._log.info("No data found")
        return self._data
    
    def display(self) -> None:
        # TODO: implement
        pass
    
    @classmethod
    def getStudyType(cls) -> str:
        return "GradCPT"
    
    @classmethod
    def loadData(cls, dataFile: str) -> dict:
        """Load data from an xdf file created by a gradCPT session.

        Relevant data streams are returned in a dictionary.

        Parameters
        ----------
        dataFile : str
            The file path to the data file to load.
            
        Raises
        ------
        FileNotFoundError
            If `datFile` cannot be found.

        Returns
        -------
        dict
            Stores relevant gradCPT streams as values, mapped to by a relevant
            name.
        
        """
        if not os.path.isfile(dataFile):
            raise FileNotFoundError(
                errno.ENOENT, "Specified data file cannot be found.", dataFile
                )

        data, header = pyxdf.load_xdf(dataFile)

        dataStreams = {}
        markerStreamNames = ["response_marker_stream", "stimuli_marker_stream"]
        for stream in data:
            streamType = stream['info']['type'][0]
            streamName = stream['info']['name'][0]
            if streamType in CONFIG.muse_signals:
                name = streamType[0:3].lower()
                dataStreams[name] = stream
            elif streamName in markerStreamNames:
                dataStreams[streamName] = stream

        return dataStreams
    
    # TODO: check this algorithm
    def __generateStimSequence(
            self,
            sequenceLength: str
            ) -> None:
        """Generate a sequence of images for a gradCPT run.

        Rare and common targets are selected from all files in the
        corresponding directories. The sequence is output to lines of a csv
        file with two columns: 'stimulus_path', which gives the absolute path
        to the stimulus file, and 'target_type', which specifies whether the
        stimulus is a 'rare' or a 'common' target. The sequence consists of
        randomly selected stimuli such that a) each selected stimulus has 90%
        probability of being a common target and a 10% chance of being a rare
        target, and b) no consecutive stimuli are identical.

        Parameters
        ----------
        sequenceLength : int
            The length of the generated sequence of stimuli.
            
        Raises
        ------
        ValueError
            If `self._COMMON_TARGET_DIR` or `self._RARE_TARGET_DIR` don't contain two or more
            stimuli.
        """
        # TODO: fix valueerror in docstring

        # (For each item in the sequence) probability of stimulus being
        # selected from common targets or rare targets, respectively
        weights = [90, 10]

        name = os.path.splitext(self.stimSequenceFile)[0]

        # Get path to each stimulus and whether it is a common or rare target
        targets = {
            "common" : {
                "folder" : self._COMMON_TARGET_DIR,
                "files" : [
                    os.path.join(self._COMMON_TARGET_DIR, f) 
                    for f in os.listdir(self._COMMON_TARGET_DIR)
                    ]
                },
            "rare" : {
                "folder" : self._RARE_TARGET_DIR,
                "files" : [
                    os.path.join(self._RARE_TARGET_DIR, f)
                    for f in os.listdir(self._RARE_TARGET_DIR)
                    ]
                }
            }
        
        # Check that there are enough stimuli
        for targetType in targets.keys():
            numStimuli = len(targets[targetType]["files"])
            if numStimuli < 2:
                raise ValueError(
                    f"Require two or more {targetType} target stimuli, but "
                    + f"only {numStimuli} were found in "
                    + f"{targets[targetType]['folder']}"
                    )
                
        # Write stimuli paths and target types to csv file
        #TODO: ensure probability distribution is correctly implemented
        with open(name + ".csv", 'w', newline="") as f:
            # Write the header to the sequence file
            dictWriter = csv.DictWriter(
                f, 
                fieldnames=["stimulus_path", "target_type"]
                )
            dictWriter.writeheader()
            
            # For each target type, create a "mask" of the files to use for
            # preventing consecutive stimuli from being identical, as well as a
            # list of indices to use for accessing the list of files
            for targetType in targets.keys():
                numStimuli = len(targets[targetType]["files"])
                targets[targetType]['mask'] = [1 for x in range(numStimuli)]
                targets[targetType]['indices'] = [x for x in range(numStimuli)]
                
            # Specify a random stimulus of random target type that cannot be
            # selected as the first in the sequence by changing the mask. This
            # is done so that the probability of selecting a certain stimulus
            # is consistent throughout the sequence.
            lastTargetType = random.choices(
                ["common", "rare"],
                weights=weights
                )
            lastTargetType = lastTargetType[0]
            lastStimPathIndex = random.choices(
                targets[lastTargetType]["indices"]
                )
            lastStimPathIndex = lastStimPathIndex[0]
            targets[lastTargetType]["mask"][lastStimPathIndex] = 0
                
            # Create the sequence one item at a time
            for k in range(sequenceLength):
                # Choose target type according to preset weights
                targetType = random.choices(
                    ["common", "rare"],
                    weights=weights
                    )
                targetType = targetType[0]
                
                # Choose a random file of the selected target type
                stimPathIndex = random.choices(
                    targets[targetType]["indices"],
                    weights=targets[targetType]["mask"]
                )
                stimPathIndex = stimPathIndex[0]
                stimPath = targets[targetType]["files"][stimPathIndex]
                
                # Write to the sequence file
                dictWriter.writerow(
                    {
                        "stimulus_path" : stimPath,
                        "target_type" : targetType
                        }
                    )
                
                # Update the mask so that the previous stimulus can be selected
                # and this stimulus cannot be selected in the next loop
                # iteration
                targets[lastTargetType]["mask"][lastStimPathIndex] = 1
                targets[targetType]["mask"][stimPathIndex] = 0
                lastTargetType = targetType
                lastStimPathIndex = stimPathIndex