import json
import csv
import polars as pl
import matplotlib.pyplot as plt
import os
import pyxdf
import numpy as np

from attention_monitoring.src.config import CONFIG

# TODO: plot stim types as target or nontarget
# TODO: calculate response times

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
            # TODO: fix formatting
            blocksFileData = pl.read_csv(self.info["blocks_file"])
            blockNames = blocksFileData["block_name"].to_list()
            dataFiles = blocksFileData["data_file"].to_list()

            # For all blocks that did not previously have data files, check if 
            # data files have since been created. If so, update the blocks
            for k in range(len(blockNames)):
                if not self.__dataFilesExist[blockNames[k]]:
                    if dataFiles[k] is not None and os.path.isfile(dataFiles[k]):
                        self.__blocks[blockNames[k]].dataFile = dataFiles[k]
                        self.__dataFilesExist[blockNames[k]] = True

        return self.__blocks

    def display(
            self, fig=None, blockNames=[], signalType='eeg', channelNames=[], 
            domain=[-np.inf, np.inf], rereferenceTime=True
            ):

        invalidBlocks = [b for b in blockNames if b not in self.blocks.keys()]
        if len(invalidBlocks) > 0:
            raise ValueError(f"Invalid block names: {invalidBlocks}")

        if len(self.blocks) == 0 or not any(self.__dataFilesExist.values()):
            print("No data to display")
            return

        _blocks = []
        _blockNames = blockNames if len(blockNames) > 0 else self.blocks.keys()
        for name in _blockNames:
            if self.__dataFilesExist[name]:
                _blocks.append(self.blocks[name])
            else:
                print(f"No data to display for block '{name}'.")

        _fig = fig if fig is not None else plt.figure(layout="constrained")
        subfigs = np.array(_fig.subfigures(len(_blocks))).flatten()

        for k in range(len(_blocks)):
            _blocks[k].display(
                fig=subfigs[k], 
                signalType=signalType,
                channelNames=channelNames,
                domain=domain,
                rereferenceTime=rereferenceTime
                )

        _fig.suptitle(f"Session '{self.info['session_name']}'")

        return _fig


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
                block = cls(
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
        if self.__stimSequence is None and self.stimSequenceFile is not None:
            if os.path.isfile(self.stimSequenceFile):
                self.__stimSequence = pl.read_csv(self.stimSequenceFile)
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
        if self.__data is None and self.dataFile is not None:
            if os.path.isfile(self.dataFile):
                self.__data = self.__loadData(self.dataFile)
        return self.__data

    @classmethod
    def __loadData(cls, dataFile):
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

    def display(
            self, fig=None, signalType='eeg', channelNames=[], 
            domain=[-np.inf, np.inf], rereferenceTime=True
            ):

        if self.data is None:
            print("No data to display")
            return
        
        # Helper function for validating `channelNames`
        def validateChannelNames(validChannelNames):
            if len(channelNames) > 0:
                invalidChannelNames = [
                    cn for cn in channelNames if cn not in validChannelNames
                    ]
                if len(invalidChannelNames) > 0:
                    raise ValueError(
                        f"Invalid channel names for signal type {signalType}: "
                        + f"{invalidChannelNames}"
                        )

        # Validate the inputs to the function
        # TODO: add suppoer for target channels for other types of signals
        if signalType == 'eeg':
            validChannelNames = ["TP9", "AF7", "AF8", "TP10"]
            validateChannelNames(validChannelNames)
            _channelNames = (
                channelNames if len(channelNames) > 0
                else validChannelNames
                )
        else:
            raise ValueError(f"Invalid signalType: {signalType}")

        # Get the signal channels to plot
        sigInfo = self.data[signalType]['info']
        existingChannels = sigInfo['desc'][0]['channels'][0]['channel']
        channels = []
        for channelName in _channelNames:
            for k in range(len(existingChannels)):
                if existingChannels[k]['label'][0] == channelName:
                    channels.append({"index" : k})
                    channels[-1].update(existingChannels[k])
                    break
            else:
                print(
                    f"'{channelName}' is a valid channel name for signal type "
                    + f"'{signalType}', but no data for this channel was "
                    + "found so the channel will not be plotted."
                    )

        # Define some relevant values for plotting
        numChannels = len(channels)
        startTime = (
            0 if not rereferenceTime
            else min(np.min(x['time_stamps']) for x in self.data.values())
        )
        
        # Plot the data
        plotter = BlockPlotter(self)
        _fig = fig if fig is not None else plt.figure(layout="constrained")
        gs = _fig.add_gridspec(numChannels, hspace=0)
        axs = gs.subplots(sharex=True, sharey=True)

        # Define callback that is applied to every plot
        def baseCB(x, y):
            x_, y_ = x, y
            # Rereference time axis to common start time
            x_ = x_ - startTime
            # Only plot data within the specified domain
            mask = np.logical_and(x_ >= domain[0], x_ <= domain[1])
            x_ = x_[mask]
            y_ = y_[mask]
            return x_, y_

        # Plot data for specified signal type
        def sigCB(x, y):
            x_, y_ = x, y
            # Average reference channel
            y_ = y_ - y_.mean()
            return baseCB(x_, y_)   

        for k in range(numChannels):
            plotter.plotMuseSig(
                axs[k], signalType, k, 
                "b", 
                callback=sigCB, 
                linewidth=1
                )

        # Plot stimuli onset
        def stimOnsetCB(x, y):
            x_, y_ = x, y
            # Stimulus onset is at the start of the transition period
            mask = (y_ == "transition_period_start")
            x_ = x_[mask]
            y_ = y_[mask]
            return baseCB(x_, y_)

        for k in range(numChannels):
            plotter.plotStimMarkers(
                axs[k], 
                callback=stimOnsetCB, 
                color='r'
                )

        # Plot block start and end
        def blockTimeCB(x, y):
            x_, y_ = x, y
            mask = np.logical_or(y == "block_start", y == "block_stop")
            x_ = x_[mask]
            y_ = y_[mask]
            return baseCB(x_, y_)

        for k in range(numChannels):
            plotter.plotStimMarkers(
                axs[k], 
                callback=blockTimeCB, 
                color='y'
                )

        # Plot response markers
        for k in range(numChannels):
            # Only one possible value in response marker stream ('response'),
            # so no need to specify additional callbacks
            plotter.plotResponseMarkers(
                axs[k], 
                callback=baseCB, 
                color='g'
                )

        # Label each channel
        for k in range(numChannels):
            axs[k].set_ylabel(channels[k]['label'][0])

        # Label the plot
        _fig.suptitle(f"Block '{self.name}'")
        _fig.supxlabel("Time (s)")
        _fig.supylabel(
            f"{channels[0]['type'][0]}: Average Referenced ("
            + f"{channels[0]['unit'][0]})"
            )

        return _fig

class BlockPlotter:
    def __init__(self, block):
        self.block = block

    def __validateData(self):
        dataExists = self.block.data is not None
        if not dataExists:
            print("No data found, nothing will be plotted.")
        return dataExists


    def plotMuseSig(self, ax, signalType, channel, *args, callback=None, **kwargs):
        if self.__validateData():
            sigData = self.block.data[signalType]
            x = np.array(sigData['time_stamps']).flatten()
            y = np.array(sigData['time_series'][:,channel]).flatten()
            if callback is not None:
                x, y = callback(x, y)

            ax.plot(x, y, *args, **kwargs)

    def plotStimMarkers(self, ax, callback=None, **kwargs):
        if self.__validateData():
            stimData = self.block.data['stimuli_marker_stream']
            x = np.array(stimData['time_stamps']).flatten()
            y = np.array(stimData['time_series']).flatten()
            if callback is not None:
                x, y = callback(x, y)

            # TODO: fix height of markers
            ylim = ax.get_ylim()
            ax.vlines(x, ylim[0], ylim[1], **kwargs)

    def plotResponseMarkers(self, ax, callback=None, **kwargs):
        if self.__validateData():
            stimData = self.block.data['response_marker_stream']
            x = np.array(stimData['time_stamps']).flatten()
            y = np.array(stimData['time_series']).flatten()
            if callback is not None:
                x, y = callback(x, y)

            ylim = ax.get_ylim()
            ax.vlines(x, ylim[0], ylim[1], **kwargs)









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
        