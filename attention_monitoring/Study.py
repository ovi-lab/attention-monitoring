from abc import ABC, abstractmethod
import os
import csv
import errno
from datetime import datetime
import json
import polars as pl
import logging

from typing import Optional, Any

from attention_monitoring.src.config import CONFIG

# TODO: change JsonBackedDict to properly behave like a dict

class Study(ABC):
    
    def __init__(self):
        # Define some useful directories, creating them if they don't already 
        # exist 
        
        # Directory to store all data for studies of this type
        self._DATA_DIR = os.path.join(
            CONFIG.projectRoot, "src", "data", self.getStudyType()
            )
        if not os.path.isdir(self._DATA_DIR):
            os.makedirs(self._DATA_DIR)
        
        # Directory to store stimuli used in this study
        self._STIMULI_DIR = os.path.join(self._DATA_DIR, "stimuli")
        if not os.path.isdir(self._STIMULI_DIR):
            os.makedirs(self._STIMULI_DIR)
        
        # Parent directory to contain the individual directories of every
        # session of this study.
        self._SESSIONS_DIR = os.path.join(self._DATA_DIR, "sessions")
        if not os.path.isdir(self._SESSIONS_DIR):
            os.makedirs(self._SESSIONS_DIR)
            
    # @property
    # def data_dir(self) -> str:
    #     return self._DATA_DIR
    
    # @property
    # def stimuli_dir(self) -> str:
    #     return self._STIMULI_DIR
    
    # @property
    # def sessions_dir(self) -> str:
    #     return self._SESSIONS_DIR
    
    @classmethod
    @abstractmethod
    def getStudyType(cls) -> str:
        pass

class StudyBlock(Study):
    """A block of a scientific study.
    
    An abstract class representing a block of trials in a scientific study.
    Concrete subclasses must implement the abstract properties and methods, 
    listed below.
    
    Paramaters
    ----------
    name : str
        The name of this block.
    
    Attributes
    ----------
    name : str
        The name of this block (read only).
    
    Abstract Attributes
    -------------------
    data : Any or None
        The data collected during this block. If no data has been collected,
        its value is `None`.
    
    Abstract Methods
    ----------------
    display() -> None
        Visualize the data collected in this block.
    """
    def __init__(self, name: str) -> None:
        super().__init__()
        
        self._name = name
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    @abstractmethod
    def data(self) -> [Any | None]:
        pass
    
    @abstractmethod
    def display(self) -> None:
        """Visualize the data collected in this block.
        
        Display the data collected for this block. If no data has been 
        collected, display a message indicating so.
        """
        pass

class StudySession(Study):
    """A session of a scientific study.
    
    An abstract class representing one session of a scientific study. The 
    provided constructor performs some initial setup, creating directories and
    an "info" file for the session in a consistent way. Concrete subclasses
    must implement the abstract properties and methods, listed below.
    
    Parameters
    ----------
    sessionName : str, optional
        If specified, loads the session named `sessionName` instead of creating
        a new one.
    participantID : int, optional
        The numeric ID of the participant for this session. Ignored if 
        `sessionName` is also specified.
        
    Raises
    ------
    ValueError
        If the specified `sessionName` cannot be found.
        
    Attributes
    ----------
    info : dict
        Stores information about this session (view only). Only valid at the 
        time it is accessed, the returned dictionary does not reflect future
        changes made to the session's info.
        
    Abstract Attributes
    -------------------
    studyType : str
        A string specifying the type of this study. Used for naming some 
        directories and as a convenient way to get the of a StudySession 
        object. eg. "gradCPT", "oddball", etc.
    blocks : list of StudyBlock
        The blocks corresponding to this study, represented as a dict 
        containing one item for each block in this study. Each item maps the 
        name of the block to a `StudyBlock` object for that block. The dict
        may be empty iff there are no blocks in this study.
        
    Abstract Methods
    ----------------
    run() -> None
        Run the study session.
    display() -> None
        Visualize the data collected in this session.
        
    Notes
    -----
    Concrete subclasses should modify `self._info` to properly modify the info
    for the session. Users should only access the info through the `info` 
    attribute, which safely returns a copy of `self._info` as `self._info` must
    not be directly modified by users.
    """
    
    print(f"name in StudySession class: {__name__}")
    
    def __init__(
            self, 
            sessionName: [str | None] = None,
            participantID: [int | None] = None
            ) -> None:
        
        super().__init__()

        # # Define some useful directories, creating them if they don't already 
        # # exist 
        # # Directory to store all data for studies of this type
        # self._DATA_DIR = os.path.join(
        #     CONFIG.projectRoot, "src", "data", self.studyType
        #     )
        # os.makedirs(self._DATA_DIR, exist_ok=True)
        # # Directory to store stimuli used in this study
        # self._STIMULI_DIR = os.path.join(self._DATA_DIR, "stimuli")
        # os.makedirs(self._STIMULI_DIR, exist_ok=True)
        # # Parent directory to contain the individual directories of every
        # # session of this study.
        # self._SESSIONS_DIR = os.path.join(self._DATA_DIR, "sessions")
        # os.makedirs(self.__SESSION_DIR, exist_ok=True)
        
        # Get the log for sessions of this study type
        sessionsLogPath = os.path.join(self._SESSIONS_DIR, "log.csv")
        sessionsLog = SessionLogger(sessionsLogPath)
        
        # Create a new session if `sessionName` is unspecified. Otherwise, load
        # the specified session.
        if sessionName is None:
            # Update the session log with the info for this study
            if sessionsLog.numLines > 0:
                session_id = int(sessionsLog.read(-1)["session_id"][0]) + 1
            else:
                session_id = 1
            sessionsLog.addLine(
                session_id=session_id,
                date=datetime.now().strftime("%d%m%y"),
                participant_id=participantID
                )
            SessionLogEntry = sessionsLog.read(-1)
            SessionLogEntry = {
                k : v[0] for (k, v) in SessionLogEntry.items() 
                if k in SessionLogger.logFields
                }
            
            # Create a directory to store data for this session
            self._DIR = os.path.join(
                self._SESSIONS_DIR, 
                SessionLogEntry["session_name"]
                )
            os.makedirs(self._DIR, exist_ok=True)
            
            # Create an info file for this session
            infoPath = os.path.join(self._DIR, "info.json")
            self._info = JsonBackedDict(infoPath)
            self._info.update(
                **SessionLogEntry,
                session_dir=self._DIR,
                info_file=infoPath
                )
        else:
            # If a session name was provided, get its directory and info file
            self._DIR = os.path.join(self._SESSIONS_DIR, sessionName)
            infoPath = os.path.join(self._DIR, "info.json")
            try:
                self._info = JsonBackedDict(infoPath, forceReadFile=True)
            except FileNotFoundError as E:
                errmsg = f"The session {sessionName} cannot be found."
                raise ValueError(errmsg) from E

    # @property
    # @abstractmethod
    # def studyType(self) -> str:
    #     pass
    
    @property
    def info(self) -> dict:
        return self._info.safeView()
    
    @property
    @abstractmethod
    def blocks(self) -> dict[str, StudyBlock]:
        pass

    @abstractmethod
    def run(self) -> None:
        """Run the study session.
        
        Perform all necessary actions for running the study, including (but not
        limited to) setup, having the participant perform tasks, applying 
        stimuli, recording data, communicating with external tools, etc.
        """
        pass
    
    @abstractmethod
    def display(self) -> None:
        """Visualize the data collected in this session.
        
        Display the data collected for each block of this session. If no data
        has been collected for a block, display a message indicating so.
        """
        pass
        

class SessionLogger:
    """A log to keep track of study sessions.
    
    The log is backed by a '.csv' file specified by `filePath` when creating a 
    new `SessionLogger` object. Changes to the log made through this object
    using the provided methods are reflected in the log file. Note that the 
    data returned by instances of `SessionLogger` are undefined and may result 
    in unexpected behaviour if:
     - The content of the log file is changed externally
     - Multiple instances of `SessionLogger` exist concurrently and are backed 
       by the same file.
     
    Parameters
    ----------
    filePath : str
        The path to the file to use as the log. The file extension must either
        be ommited or '.csv'. If the specified file already exists, it will be
        used as the log. Otherwise, a new log file will be created.

    Attributes
    ----------
    logFields : list of str
        The names of the fields in the log.
    path : str
        The path to the log file.
    numLines : int
        The number of lines in the log. More specifically, the number of 
        sessions that are recorded in the log.

    Raises
    ------
    ValueError
        If `filePath` specifies an invalid extension.
    """

    __rowCountCol = "row_count"
    
    def __init__(self, filePath: str) -> None:
        
        name, ext = os.path.splitext(filePath)
        if not ext in ("", ".csv"):
            raise ValueError(
                f"Unsupported file type '{ext}'. Filetype must either be "
                + "unspecified or '.csv'"
                )
        self.__path = name + ".csv"
        
        self.__path = filePath

        dtypes = {field : pl.Utf8 for field in self.logFields}
        dtypes[self.__rowCountCol] = pl.Int32

        if self.__exists():
            self.__log = pl.read_csv(
                self.path, 
                dtypes=dtypes, 
                row_count_name=self.__rowCountCol
                )
            # Row count column doesn't get added if the log is empty
            if not self.__rowCountCol in self.__log.columns:
                self.__log = self.__log.with_row_count(name=self.__rowCountCol)
        else:
            self.__log = pl.DataFrame(schema=dtypes)
            with open(self.__path, 'w', newline="") as f:
                dictWriter = csv.DictWriter(f, fieldnames=self.logFields)
                dictWriter.writeheader()
                
    @classmethod
    @property
    def logFields(cls) -> list[str]:
        return ["session_name", "session_id", "date", "participant_id"]

    @property
    def path(self) -> str:
        return self.__path
    
    @property
    def numLines(self) -> int:
        return self.__log.height

    def __exists(self):
        return os.path.isfile(self.path)
    
    def read(self, *lines: int) -> dict[str, list[Any]]:
        """Read the specified line(s) from the log
        
        Parameters
        ----------
        *lines : tuple of int
            The lines in the log to read from (note that indices start at 1).
            Negative indexing is supported. If unspecified, all lines are read.

        Raises
        ------
        FileNotFoundError
            If log file cannot be found.
        IndexError:
            If any of the specified line(s) are invalid.

        Returns
        -------
        dict of str to list of Any
            A dictionary mapping the name of each field in the log to a list
            containing the corresponding values from the specified lines. An
            additional field also specifies the corresponding row number.
        """
        if not self.__exists():
            raise FileNotFoundError(
                errno.ENOENT, "The log file does not exist.", self.path
                )
            
        if len(lines) == 0:
            data = self.__log
        else:
            lastLineNum = self.__log.max()[self.__rowCountCol][0]
            _lines = [n if n >= 0 else lastLineNum + 1 + n for n in lines]

            # Assume row numbers are unique
            data = self.__log.filter(pl.col(self.__rowCountCol).is_in(_lines))
            
            selectedLines = data[self.__rowCountCol].to_list()
            unSelectedLines = [x for x in _lines if x not in selectedLines]
            if len(unSelectedLines) > 0:
                # TODO: improve error message
                raise IndexError(
                    "The following specified lines were not found:"
                    + f"{unSelectedLines}"
                    )

        data = data.to_dict(as_series=False)
        return data

    def addLine(self, **items) -> None:
        """Add a line to the end of the log.

        Data to include in the line are specified as keyword arguments, where
        the argument is the value to add and the key is the name of the 
        corresponding log field. For any unspecified fields, an attempt is made
        to extrapolate values from the specified fields. If this cannot be 
        done, the value of the field is left empty in the log.

        Parameters
        ----------
        session_name : str, optional
            The name assigned to the session. Must follow the convention:
            "S[session_id]_[ddmmyy]" where [session_id] is `session_id` and [ddmmyy]
            is the date. This can optionally be followed by "_P[participantID]",
            where [participantID] is `participantID`.
        session_id : int or str, optional
            The numerical ID assigned to this session.
        date : str, optional
            The date of this session, in the format `ddmmyy`.
        participant_id : int or str, optional
            The numerical ID assigned to the participant in this session.
            
        Raises
        ------
        FileNotFoundError
            If log file cannot be found.
        ValueError
            If any of the specified items do not correspond to an existing 
            field in the log.
        """
        if not self.__exists():
            raise FileNotFoundError(
                errno.ENOENT, "The log file does not exist.", self.path
                )
            
        invalidKeys = [k for k in items.keys() if not k in self.logFields]
        if len(invalidKeys) > 0:
            raise ValueError(
                f"The specified key(s) '{invalidKeys}' are not valid fields. "
                + f"Valid fields are: {self.logFields}"
                )
            
        line = self.__formatLogInfo(**items)
        
        # The file (self.path) and the copy of the log stored in self.__log 
        # must always contain the same data.
        
        # Update the file
        with open(self.path, "a", newline="") as f:
            dictWriter = csv.DictWriter(f, fieldnames=self.logFields)
            dictWriter.writerow(line)
            
        # Update the stored copy of the log
        if self.numLines > 0:
            lastLineNum = self.__log.max()[self.__rowCountCol][0]
        else:
            lastLineNum = 0
        thisLine = pl.DataFrame(line).with_row_count(
            name=self.__rowCountCol,
            offset=lastLineNum+1
            )
        self.__log = self.__log.vstack(thisLine)

    @classmethod
    def __formatLogInfo(cls, session_name=None, session_id=None, date=None,
                   participant_id=None):
        """Format info about a data collection session to be entered in the log.

        All values are formatted as `str` and returned in a `dict`. If any values
        are `None`, the corresponding value in the returned `dict` is `""`.

        Parameters
        ----------
        session_name : str, optional
            The name assigned to the session. Must follow the convention:
            "S[session_id]_[ddmmyy]" where [session_id] is `session_id` and [ddmmyy]
            is the date. This can optionally be followed by "_P[participant_id]",
            where [participant_id] is `participant_id`.
        session_id : int or str, optional
            The numerical ID assigned to this session.
        date : str, optional
            The date of this session, in the format `ddmmyy`.
        participant_id : int or str, optional
            The numerical ID assigned to the participant in this session.

        Returns
        -------
        dict
            Info about data collection session formatted for entry in the log.
        
        """

        _session_name = session_name
        _session_id = None if session_id is None else str(session_id)
        _date = date
        _participant_id = None if participant_id is None else str(participant_id)

        # Try to specify unknown values by extrapolating from known values
        if (
            session_name is None
            and all(x is not None for x in [session_id, date])
            ):
            # Create session_name from other info
            _session_name = f"S{_session_id}_{_date}"
            if (participant_id is not None):
                _session_name = _session_name + f"_P{_participant_id}"
        elif (
            session_name is not None
            and all(x is None for x in [session_id, date, participant_id])
            ):
            # Use session_name to specify other info
            expandedName = _session_name.split("_")
            _session_id = expandedName[0].lstrip("S")
            _date = expandedName[1]
            if (len(expandedName) > 2):
                _participant_id = expandedName[2].lstrip("P")

        # Return values in a dict
        out = {
            "session_name" : _session_name,
            "session_id" : _session_id,
            "date" : _date,
            "participant_id" : _participant_id
            }
        for key, value in out.items():
            if value is None:
                out[key] = ""

        return out

class JsonBackedDict:
    """A dictionary-like object backed by a '.json' file.
    
    Maintains a dictionary-like structure (referred to as the 'jdict') that is 
    backed by a '.json' file specified by `filePath` when creating a new 
    `JsonBackedDict` object. Changes to the jdict made through this object
    using the provided methods are reflected in the json file. Once 
    initialised, key value pairs in the jdict can be specified and accessed 
    like a normal dict object (ie. `myJsonBackedDict[x] = y`). Note that the 
    data returned by instances of `JsonBackedDict` are undefined and may result 
    in unexpected behaviour if:
     - The content of the json file is changed externally.
     - Multiple instances of `JsonBackedDict` exist concurrently and are backed
       by the same file.
    
    Parameters
    ----------
    filePath : str
        The path to the backing json file. The file extension must either
        be ommited or '.json'. If the specified file already exists, it will be
        used to initialise and back the jdict. Otherwise, a new file will be 
        created.
    forceReadFile : bool, default=False
        If true, raises a FileNotFound exception instead of creating a new file
        if the file specified by `filePath` cannot be read.

    Raises
    ------
    ValueError
        If `filePath` specifies an invalid extension.
    FileNotFound
        If `forceReadFile` is True and the file specified by `filePath` cannot
        be read.
    """
    def __init__(self, filePath: str, forceReadFile: bool = False) -> None:
        name, ext = os.path.splitext(filePath)
        if not ext in ("", ".json"):
            raise ValueError(
                f"Unsupported file type '{ext}'. Filetype must either be "
                + "unspecified or '.json'"
                )
        self.__path = name + ".json"
        
        # Load the info file if it exists, otherwise create it or raise an 
        # exception if `forceReadFile` is True
        if os.path.isfile(self.__path):
            with open(self.__path, "r") as f:
                self.__data = json.load(f)
        elif not forceReadFile:
            with open(self.__path, "w") as f:
                self.__data = {}
                json.dump(self.__data, f)
        else:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), filePath
                )
                
    def __updateFile(self):
        # Update the saved file to store the contents of self.__data
        with open(self.__path, "w") as f:
            json.dump(self.__data, f, sort_keys=True, indent=0)
                
        
    def __setitem__(self, key, value):
        self.__data[key] = value
        self.__updateFile()
            
            
    def __getitem__(self, key):
        return self.__data[key]
    
    def update(self, **items : Any) -> None:
        """Add multiple items to the info dict at the same time.
        
        Parameters
        ----------
        **items : dict of Any to Any
            The items to add to the info dict, specified as key value pairs
            where the key and value are the name and value in the info dict,
            respectively.
        """
        if len(items) == 0:
            return
        self.__data.update(items)
        self.__updateFile()
        
    # TODO: ensure this is implemented correctly, maybe make a proper subclass
    # of dict instead?
    def items(self):
        return self.__data.items()
        
    def safeView(self) -> dict:
        """Get a copy of the jdict.
        
        Returns
        -------
        dict
            A copy of the jdict. The returned dict is not backed by the
            json file. It will not reflect any changes made to the jdict
            and the jdict will not reflect any changes made to the returned
            dict.
        """
        return {k : v for (k, v) in self.__data.items()}