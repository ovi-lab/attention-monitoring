import json
import csv
import polars as pl

class GradCPTSession:
    def __init__(self, infoFile):
        with open(infoFile, "r") as f:
            self.info = json.load(f)

        # Load the blocks and determine whether data has been collected yet
        self.__blocks = {}
        self.__dataFilesExist = {}
        for block in GradCPTBlock.fromBlocksFile(self.info["blocks_file"]):
            self.__blocks[block.name] = block
            self.__dataFilesExist[block.name] = block.data is not None  

    @property
    def blocks(self):
        if not all(self.__dataFilesExist.values()):
            blocksFileData = pl.read_csv(self.info["blocks_file"])
            blocksNames = blocksFileData["block_name"].to_list()
            dataFiles = blocksFileData["data_file"].to_list()

            # For all blocks that did not previously have data files, check if 
            # data files have since been created. If so, update the blocks
            for k in range(len(blockNames)):
                if not self.__dataFilesExist[blockNames[k]]:
                    if os.path.isfile(dataFiles[k]):
                        self.__blocks[blockNames[k]].dataFile = dataFiles[k]
                        self.__dataFilesExist[blockNames[k]] = True

        return self.__blocks

    def display(self):
        for block in self.blocks:
            block.display()

class GradCPTBlock:
    def __init__(
                self, name, preBlockMsg, preBlockWaitingTime,
                stimSequenceFile, dataFile
                ):
        self.name = name
        self.preBlockMsg = preBlockMsg
        self.preBlockWaitTime = preBlockWaitingTime

        self.__stimSequenceFile = (
            None if stimSequenceFile == "" 
            else stimSequenceFile
            )
        self.__dataFile = (
            None if dataFile == ""
            else dataFile
            )
        self.__stimSequence = None
        self.__data = None

        self.pipeline = DataPipe()

    @classmethod
    def fromBlocksFile(cls, blocksFile):
        """Create a `GradCPTBlock` object for each block specified in a gradCPT
        blocks file.

        Note that the returned `GradCPTBlock` objects always represent the 
        blocks specified by `blocksFile` at the time this function is called. 
        Future changes to the blocks file will not be reflected by the returned 
        `GradCPTBlock` objects.

        Assumes that block names specified in `blocksFile` are unique.

        Parameters
        ----------
        blocksFile : str
            The path to the blocks file.

        Returns
        -------
        list of GradCPTBlock
            A list containing a `GradCPTBlock` object for each of the blocks 
            specified in `blocksFile`, in the same order.
        """
        blocks = []
        with open(blocksFile, "r") as f:
            dictReader = csv.DictReader(f)
            for line in dictReader:
                block = GradCPTBlock(
                    line["block_name"],
                    line["pre_block_msg"],
                    line["pre_block_wait_time"],
                    line["stim_sequence_file"],
                    line["data_file"]
                    )
                blocks.append(block)

        return blocks

    @property
    def stimSequenceFile(self):
        return self.__stimSequenceFile

    @stimSequenceFile.setter
    def stimSequenceFile(self, val):
        self.__stimSequenceFile = val
        self.__stimSequence = None
   
    @property
    def stimSequence(self):
        if self.__stimSequence is None:
            if os.path.isfile(self.__stimSequenceFile):
                self.__stimSequence = pl.read_csv(self.__stimSequenceFile)
        return self.__stimSequence

    @property
    def dataFile(self):
        return self.__dataFile

    @dataFile.setter
    def dataFile(self, val):
        self.__dataFile = val
        self.__data = None
        
    @property
    def data(self):
        if self.__data is None:
            if os.path.isfile(self.__datafile):
                self.__data = __loadData(self.__dataFile)
        return self.__data

    
    def __loadData(dataFile):
        """Load data from an xdf file created by a gradCPT session.

        Relevant data streams are returned in a dictionary after some 
        boilerplate processing is performed.

        Parameters
        ----------
        dataFile : str
            The file path to the data file to load.

        Returns
        -------
        dict
            Stores relevant gradCPT streams as values, mapped to by strings.
        
        """
        # TODO Add support for loading marker streams
        if not os.path.isfile(dataFile):
            raise FileNotFoundError(
                errno.ENOENT, "Specified data file cannot be found.", dataFile
                )

        data, header = pyxdf.load_xdf(dataFile)

        dataStreams = {}
        for stream in data:
            streamType = stream['info']['type'][0]
            streamName = stream['info']['name'][0]
            if streamType in CONFIG.muse_signals:
                name = streamType[0:3].lower()
                dataStreams[name] = stream

        return dataStreams



    def getStimSequence(self):
        """Get the sequence of stimuli used for this block.

        Returns
        -------
        polars.dataframe.frame.DataFrame
            a polars dataframe object with two columns: 1) stimulus_path : str
            : Absolute file path to the stimulus image. 2) target_type :
            {'rare', 'common'} : Whether the stimulus is a rare target or a
            common target.
        """
        return pl.read_csv(self.stimSequenceFile)

    def display(self):
        # TODO implement this
        disp("this function (GradCPTBlock.display) is unimplemented.")







class DataPipe:
    """Data analysis pipeline
    
    Maintains a list of "actions" that can be applied to data from a gradCPT
    session. An action consists of a unique name and a function that accepts
    gradCPT data as input, processes it in some way, and returns the 
    (potentially) modified gradCPT data. The pipeline follows the same
    structure as a `list`. When executed, each action in the pipe will be
    applied to the specified data in sequential order.

    To use, create a `DataPipe` object, add or remove actions to the pipe 
    (`add`, `remove`, `clear`), and apply to gradCPT data (`execute`). The
    pipe's contents can be obtained using `actions`, and a list of valid
    actions can be obtained using `DataPipe.validActions`.

    Attributes
    ----------
    actions : list of tuple
        Names and descriptions of all actions in the pipe.
    """

    # TODO fix this
    # Stores: {str : action name -> method : function to create action object}
    __validActions = {
        # "mean" : __DataPipe__mean
        }

    def __init__(self):
        self._pipe = []

    def validActions():
        """Get a list of all valid action names and their documentation."""
        return [(name, func.__doc__) for name, func in __validActions.items()]

    @property
    def actions(self):
        """Names and descriptions of all actions in the pipe."""
        return [(action.name, action.desc) for action in self._pipe]

    def add(self, action, position=-1, *args, **kwargs):
        """Add an action to the pipe.

        Parameters
        ----------
        action : str
            The action to add. Must be a valid action.
        position : int, default=-1
            The index in the pipe where the action should be added (follows
            `list` inexing). Behaviour is equivalent to that of the `insert`
            method for python lists.
        *args
            Positional arguments required by action.
        **kwargs
            Keyword arguments required by action.

        Returns
        -------
        self
            The `DataPipe` object that called this method. Allows consecutive
            calls to `add` to be chained together.
        """
        if __isValidAction(action):
            actionMaker = __validActions[action]
            _action = actionMaker(*args, **kwargs)
            self._pipe.insert(position, _action)
        else:
            raise ValueError(f"Invalid Action: {action}")

        return self

    def remove(self, position):
        """Remove an action from the pipe.

        Paramaters
        ----------
        position : int
            The index in the pipe of the action to remove (follows `list` 
            indexing).
        """
        self._pipe.pop(position)

    def clear(self):
        """Remove all members from the pipe."""
        self._pipe = []

    def execute(self, data):
        """Execute the pipe on the specified gradCPT data. 
        
        Each action in the pipe is applied to the data in sequential order
        starting at the front of the pipe (in order of increasing index).
        """
        _data = data
        for action in self._pipe:
            _data = action.execute(_data)
        return _data
    
    def __isValidAction(action):
        """Check whether the specified action is valid."""
        return action in __validActions

    def __mean(dim=1):
        """"Average the data.

        Parameters
        ----------
        dim : int, default=1
            The dimension along which to operate.
        """
        desc = {"dim" : dim}
        def mean(data):
            # use dim as a constant here
            pass
        meanAction = __Action("mean", mean, desc=desc)
        return meanAction

    class __Action:
        def __init__(self, name, func, desc=None):
            self.name = name
            self.func = func
            self.desc = desc if desc is not None else ""

        def execute(self, data):
            return self.func(data)
        