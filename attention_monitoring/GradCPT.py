import os
import pyxdf
import csv
import random
import polars as pl
from abc import abstractmethod
import subprocess
import matlab.engine

from attention_monitoring.src.config import CONFIG
from Study import StudySession, StudyBlock
from EEGDevice import EEGDevice

class GradCPTSession(StudySession):
    
    # TODO: add documentation
    # TODO: add functionality for starting an existing session
    
    def __init__(
            self, 
            sessionName: [str | None] = None,
            participantID: [int | None] = None
            ) -> None:
        
        super().__init__(sessionName=sessionName, participantID=participantID)
        
        # Create the blocks for this session
        self.__blocks = {}
        if CONFIG.do_practice_block:
            name = f"{self.info['session_name']}_practice_block"
            block = GradCPTBlock.makePracticeBlock(name, self.__DIR)
            self.__blocks[block.name] = block
        for k in range(CONFIG.num_full_blocks):
            name = f"{self.info['session_name']}_full_block_{k}"
            block = GradCPTBlock.makeFullBlock(name, self.__DIR, n=k)
            self.__blocks[block.name] = block
        
        # Create a new session if `sessionName` is unspecified.
        if sessionName is None:
            # Create a "blocks file" that summarizes the blocks for this
            # session
            blocksFile = os.path.join(self.__DIR, "blocks.csv")
            blocksFileFieldNames = [
                "block_name", "pre_block_msg", "pre_block_wait_time",
                "stim_sequence_file", "data_file"
                ]
            with open(blocksFile, "w") as f:
                dictWriter = csv.DictWriter(f, fieldnames=blocksFileFieldNames)
                dictWriter.writeheader()
                for block in self.blocks.values():
                    dictWriter.writerow(
                        {
                            "block_name" : block.name,
                            "pre_block_msg" : block.preBlockMsg,
                            "pre_block_wait_time" : block.preBlockWaitTime,
                            "stim_sequence_file" : block.stimSequenceFile,
                            "data_file" : block.dataFile
                        }
                        )
            self.info["blocks_file"] = blocksFile
        
    @property
    @abstractmethod
    def eeg(self) -> EEGDevice:
        pass
    
    @property
    def blocks(self) -> dict[str, StudyBlock]:
        return self.__blocks
    
    def run(self) -> None:
        # TODO: finish this
        
        if CONFIG.verbose == 2:
            print(f"Info file for this session: {infoFile}")
        elif CONFIG.verbose >= 3:
            msg = [
                "\nStarting experiment:",
                *[f"|   {key} : {value}" for key, value in self.info.items()]
            ]
            print("\n".join(msg))
        
        # Start MATLAB engine asynchronously (do this first as it may take some
        # time)
        if CONFIG.verbose >= 2:
            print("Starting the MATLAB engine asynchronously")
        future = matlab.engine.start_matlab(background=True)
        
        # Connect to the EEG device and start streaming
        if CONFIG.verbose >= 2:
            print("Connecting to the EEG")
        self.eegDevice.connect()
        self.eegDevice.startStreaming()
        
        # Start LabRecorder
        if CONFIG.path_to_LabRecorder != "":
            if CONFIG.verbose >= 2:
                print("Starting LabRecorder")
            proc1 = subprocess.Popen(
                os.path.realpath(CONFIG.path_to_LabRecorder),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
                )   
            
        # Run the experiment on MATLAB
        if CONFIG.verbose >= 1:
            print(
                "Running experiment in MATLAB. This may take a few moments ..."
                )
        eng = future.result()
        p = eng.genpath(CONFIG.projectRoot)
        eng.addpath(p, nargout=0)
        data = eng.gradCPT(
            self.info["info_file"],
            'verbose', CONFIG.verbose,
            'streamMarkersToLSL', CONFIG.stream_markers_to_lsl,
            'recordLSL', CONFIG.record_lsl,
            'tcpAddress', CONFIG.tcp_address,
            'tcpPort', CONFIG.tcp_port,
            )

        # Close the EEG device
        if CONFIG.verbose >= 2:
            print("Closing the EEG")
        self.eegDevice.stopStreaming()
        self.eegDevice.disconnect()

        # Close LabRecorder
        if CONFIG.path_to_LabRecorder != "":
            if CONFIG.verbose >= 2:
                print("Closing LabRecorder")
            proc1.kill()
            out, err = proc1.communicate()
            if CONFIG.verbose >= 2:
                print("\nLabRecorder Output\n")
                print(out)
    
    def display(self) -> None:
        # TODO: finish this
        if all(block.data is None for block in self.blocks.values()):
            print("No data to display.")
        else:
            for name, block in self.blocks.items():
                if block.data is None:
                    print(f"No data to display for block {name}.")
                else:
                    block.display()
            
    @classmethod
    def getStudyType(cls) -> str:
        return "GradCPT"
    
    
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
        
        self.__OUTPUT_DIR = outputDir
        self.preBlockMsg = preBlockMsg if preBlockMsg is not None else ""
        self.preBlockWaitTime = preBlockWaitingTime
        
        # Define the directories where the stimuli are stored, creating them if
        # they don't exist yet.
        self.__COMMON_TARGET_DIR = os.path.join(
            self.__STIMULI_DIR, "common_target"
            )
        if not os.path.isdir(self.__COMMON_TARGET_DIR):
            os.makedirs(__COMMON_TARGET_DIR)
        self.__RARE_TARGET_DIR = os.path.join(
            self.__STIMULI_DIR, "rare_target"
            )
        if not os.path.isdir(self.__RARE_TARGET_DIR):
            os.makedirs(__RARE_TARGET_DIR)
        
        # Specify the paths to the stim sequence and data files
        self.__stimSequenceFile = os.path.join(
            self.__OUTPUT_DIR, self.name + "_stim_sequence.csv"
            )
        self.__dataFile = os.path.join(
            self.__OUTPUT_DIR, self.name + "_data.xdf"
            )
        
        # Create the stim sequence file if it doesn't exist yet
        if not os.path.isfile(self.__stimSequenceFile):
            self.__generateStimSequence(stimSequenceLength)
            
        # Initialize both the data and stim sequence as None
        self.__stimSequence = None
        self.__data = None
    
    @classmethod
    def makePracticeBlock(cls, 
            name: str, 
            outputDir: str,
            ) -> GradCPTBlock:
        
        preBlockWaitingTime = CONFIG.CONFIG.pre_practice_block_break_time
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
            ) -> GradCPTBlock:
        
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
    def name(self) -> str:
        return self.__name
    
    @property
    def stimSequenceFile(self) -> str:
        return self.__stimSequenceFile
    
    @property
    def stimSequence(self) -> dict[str, list[str]]:
        return pl.read_csv(self.stimSequenceFile).to_dict(as_series=False)
    
    @property
    def dataFile(self) -> str:
        return self.__dataFile
    
    @property
    def data(self) -> [Any | None]:
        if self.__data is None and self.dataFile is not None:
            if os.path.isfile(self.dataFile):
                self.__data = self.loadData(self.dataFile)
        return self.__data
    
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
            If `commonTargetsDir` or `rareTargetsDir` don't contain two or more
            stimuli.
        """

        # (For each item in the sequence) probability of stimulus being
        # selected from common targets or rare targets, respectively
        weights = [90, 10]

        name = os.path.splitext(self.stimSequenceFile)[0]

        # Get path to each stimulus and whether it is a common or rare target
        targets = {
            "common" : {
                "folder" : self.__COMMON_TARGET_DIR,
                "files" : [
                    os.path.join(commonTargetsDir, f) 
                    for f in os.listdir(commonTargetsDir)
                    ]
                },
            "rare" : {
                "folder" : self.__RARE_TARGET_DIR,
                "files" : [
                    os.path.join(rareTargetsDir, f)
                    for f in os.listdir(rareTargetsDir)
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
            if k == 0:
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
                stimPath = targets[targetType][stimPathIndex[0]]
                
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