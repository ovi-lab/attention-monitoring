from abc import abstractmethod
import os
import csv
import errno
from datetime import datetime
import polars as pl
import logging
from typing import Any

from attention_monitoring.src.config import CONFIG
from .helpers import JsonBackedDict
from .Study import Study
from .StudyBlock import StudyBlock

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
    def __init__(
            self, 
            sessionName: [str | None] = None,
            participantID: [int | None] = None
            ) -> None:
        
        self._log.debug("Initializing session.")
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
        self._log.debug(f"Getting the sessions log: {sessionsLogPath}")
        sessionsLog = SessionLogger(sessionsLogPath)
        
        if sessionName is None:
            # Create a new session if `sessionName` is unspecified.
            self._log.info("Creating a new session")
            
            # Update the session log with the info for this study. This
            # includes the fields "session_name", "session_id", "date", and
            # "participant_id", all of which are automatically formatted by the
            # `SessionLogger` object.
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
            self._log.debug(
                f"Added session to log with fields: {SessionLogEntry}"
                )
            
            # Create a directory to store data for this session
            self._DIR = os.path.join(
                self._SESSIONS_DIR, 
                SessionLogEntry["session_name"]
                )
            self._log.debug(f"Creating directory: {self._DIR}")
            os.makedirs(self._DIR, exist_ok=True)
            
            # Create an info file for this session
            infoPath = os.path.join(self._DIR, "info.json")
            self._log.debug(f"Creating info file: {infoPath}")
            self._info = JsonBackedDict(infoPath)
            self._info.update(
                **SessionLogEntry,
                session_dir=self._DIR,
                info_file=infoPath
                )
        else:
            # If a session name was provided, get its directory and info file
            self._log.info(f"Loading existing session: {sessionName}")
            
            self._DIR = os.path.join(self._SESSIONS_DIR, sessionName)
            infoPath = os.path.join(self._DIR, "info.json")
            self._log.debug(f"Loading info file: {infoPath}")
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