from abc import ABC, abstractmethod
from datetime import datetime
import logging
import os
from typing import Any

from src.helpers import JsonBackedDict
from .helpers import CSVLogger
from src.config import CONFIG

_log = logging.Logger(__name__)

# TODO: change JsonBackedDict to properly behave like a dict
# TODO: add documentation for Study

class Study(ABC):
    
    #TODO: remove dataSubDir. possibly move to studySession implementation
    
    def __init__(self, /, dataSubDir: [None | str] = None) -> None:
        
        # Define some useful directories, creating them if they don't already 
        # exist 
        
        # Directory to store all data for studies of this type
        studyDir = self.getStudyType()
        if dataSubDir is not None:
            studyDir = os.path.join(dataSubDir, studyDir)
        self._DATA_DIR = os.path.join(
            CONFIG.projectRoot, "src", "data", studyDir
            )
        if not os.path.isdir(self._DATA_DIR):
            _log.debug("Creating directory: %s", self._DATA_DIR)
            os.makedirs(self._DATA_DIR)
        
        # Directory to store stimuli used in this study
        self._STIMULI_DIR = os.path.join(self._DATA_DIR, "stimuli")
        if not os.path.isdir(self._STIMULI_DIR):
            _log.debug("Creating directory: %s", self._STIMULI_DIR)
            os.makedirs(self._STIMULI_DIR)
        
        # # Parent directory to contain the individual directories of every
        # # session of this study.
        # self._SESSIONS_DIR = os.path.join(self._DATA_DIR, "sessions")
        # if not os.path.isdir(self._SESSIONS_DIR):
        #     _log.debug("Creating directory: %s", self._SESSIONS_DIR)
        #     os.makedirs(self._SESSIONS_DIR)
    
    @classmethod
    @abstractmethod
    def getStudyType(cls) -> str:
        pass
    
    
class StudyItem(Study):
    
    def __init__(
            self, 
            /, 
            name: [str | None] = None, 
            participantID: [int | None] = None,
            **kwargs
            ) -> None:
        
        super().__init__(**kwargs)
            
        # Define the fieldnames and path to the log for items in the parent
        # directory
        itemsLogPath = os.path.join(self._PARENT_DIR, "log.csv")
        itemsLogFieldnames = [
            "name",
            "id",
            "date",
            "participant_id"
            ]
        
        # TODO: use item id instead of item name?
        if name is None:
            # Create a new item if name is unspecified
            _log.debug("Creating new %s", self.__class__)
            
            # Create the parent directory if it does not exist yet
            if not os.path.isdir(self._PARENT_DIR):
                _log.debug("Creating directory: %s", self._PARENT_DIR)
                os.makedirs(self._PARENT_DIR, exist_ok=True)
                
            # Get (or create if necessary) the log file for items in this
            # parent directory
            _log.debug("Getting the %s log: %s", self.__class__, itemsLogPath)
            itemsLog = CSVLogger(itemsLogPath, itemsLogFieldnames)
            
            # Check the log to determine the item id
            if itemsLog.numLines > 0:
                id = int(itemsLog.read(-1)["id"][0]) + 1
            else:
                id = 1
            # Format the info about this item and add it to the log
            itemsLogEntry = self._formatItemsLogEntry(
                id=id,
                date=datetime.now().strftime("%d%m%y"),
                participant_id=participantID
                )
            itemsLog.addLine(**itemsLogEntry)
            
            # Create a directory to store data for this item
            self._DIR = os.path.join(
                self._PARENT_DIR, 
                itemsLogEntry["name"]
                )
            _log.debug("Creating directory: %s", self._DIR)
            os.makedirs(self._DIR, exist_ok=True)
            
            # Create an info file for this item, and initialize it with this
            # item's log info and some basic details
            infoPath = os.path.join(self._DIR, "info.json")
            _log.debug("Creating info file: %s", infoPath)
            self._info = JsonBackedDict(infoPath)
            self._info.update(
                **itemsLogEntry,
                dir=self._DIR,
                parent_dir=self.PARENT_DIR,
                info_file=infoPath,
                study_type=self.getStudyType()
                )
        else:
            # If an item name was provided, try to load it
            _log.info("Loading existing %s: %s", self.__class__, name)
            
            # Define paths to item directory and info file
            self._DIR = os.path.join(self._PARENT_DIR, name)
            infoPath = os.path.join(self._DIR, "info.json")
            
            # Check if specified item has been logged
            _log.debug("Getting the %s log: %s", self.__class__, itemsLogPath) 
            try:
                itemsLog = CSVLogger(
                    itemsLogPath, 
                    itemsLogFieldnames, 
                    forceReadFile=True
                    )
            except FileNotFoundError as E:
                _log.debug(
                    "The %s log does not exist: %s", 
                    self.__class__, itemsLogPath
                    )
                itemsLog = None
                itemIsLogged = False
            else:
                itemIsLogged = name in itemsLog.read()["name"]
                
            # Try to load the specified item's info file
            try:
                # Raises FileNotFoundError if the info file does not exist.
                # This implicitly requires the item directory to also exist.
                self._info = JsonBackedDict(infoPath, forceReadFile=True)
            except FileNotFoundError as E:
                if itemIsLogged:
                    errmsg = (
                        f"The specified {self.__class__} '{name}' could not "
                        + "be found, but is recorded in the log for "
                        + f"{self.__class__} items: {itemsLogPath}"
                        )
                else:
                    errmsg = (
                        f"The specified {self.__class__} '{name}' could not "
                        + "be found"
                        )
                _log.debug("Failed to load %s: %s", self.__class__, name)
                raise ValueError(errmsg) from E
            else:
                if not itemIsLogged:
                    if itemsLog is None:
                        errmsg = (
                            f"The specified {self.__class__} '{name}' was "
                            + f"found, but the log for {self.__class__} "
                            + f"items could not be found: {itemsLogPath}"
                            )
                    else:
                        errmsg = (
                            f"The specified {self.__class__} '{name}' was "
                            + "found, but is not recorded in the log for "
                            + f"{self.__class__} items: {itemsLogPath}"
                            )
                    _log.debug("Failed to load %s: %s", self.__class__, name)
                    raise ValueError(errmsg)
                    
                if self._DIR != self._info["dir"]:
                    raise RuntimeError(
                        f"The info file of the specified {self.__class__} "
                        + f"'{name}' specifies an unexpected value for `dir`: "
                        + f"Expected <{self._DIR}>, "
                        + f"Received <{self._info['dir']}>"
                    )
                    
                # If all above checks pass, we assume the specified item has
                # been found
                _log.debug("Successfully loaded %s: %s", self.__class__, name)
    
    @property
    @abstractmethod
    def _PARENT_DIR(self) -> str:
        # Define the path to the parent directory that contains (or will
        # contain) the directory for this item
        pass
    
    @property
    def info(self) -> dict[str, Any]:
        return self._info.safeView()    
    
    @property
    @abstractmethod
    def data(self) -> Any:
        pass
    
    @abstractmethod
    def run(self) -> None:
        pass
    
    @abstractmethod
    def display(self) -> None:
        pass
    
    @staticmethod    
    @abstractmethod
    def _formatItemsLogEntry(
            name: [str | None] = None,
            id: [int | str | None] = None,
            date: [str | None] = None,
            participant_id: [int | str | None] = None
            ) -> dict[str, str]:
        pass
    
    
def _baseItemsLogEntryFormatter(
        namePrefix: str,
        name: [str | None] = None,
        id: [int | str | None] = None,
        date: [str | None] = None,
        participant_id: [int | str | None] = None
        ) -> dict[str, str]:
    
    _name = name
    _id = None if id is None else str(id)
    _date = date
    _p_id = None if participant_id is None else str(participant_id)
    
    if _name is None and all(x is not None for x in [_id, _date]):
        # Create name from other values
        _name = f"{namePrefix}{_id}_{date}"
        if _p_id is not None:
            _name = _name + f"_P{_p_id}"
    elif _name is not None and all(x is None for x in [_id, _date, _p_id]):
        # Use name to specify other values
        expandedName = _name.split("_", maxsplit=2)
        _id = expandedName[0].lstrip(namePrefix)
        _date = expandedName[1]
        if len(expandedName) > 2:
            _p_id = expandedName[2].lstrp("P")
            
    out = {
        "name" : _name,
        "id" : _id,
        "date" : _date,
        "participant_id" : _p_id
        }
    for k in out.keys():
        if out[k] is None:
            out[k] = ""
            
    return out