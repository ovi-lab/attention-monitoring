from abc import ABC, abstractmethod
from datetime import datetime
import errno
import logging
import os
from typing import Any

import yaml

from src.helpers import JsonBackedDict
from .helpers import CSVLogger
from src.config import CONFIG

_log = logging.Logger(__name__)

# Update the config path
_studyConfig = os.path.join(
    os.path.relpath(os.path.dirname(__file__), start=CONFIG.root),
    "study_config.yaml"
)
if not _studyConfig in CONFIG.PATH:
    CONFIG.PATH.append(_studyConfig)
    
    
class StudyItem(ABC):
    
    def __init__(
            self, 
            name: str|None = None,
            participant_id: int|str|None = None
            ) -> None:
        # Define some useful directories, creating them if they don't already 
        # exist 
        
        # Directory to store all data for studies of this type
        studyDir = self.getStudyType()
        self._STUDY_DATA_DIR = os.path.join(
            CONFIG.root, CONFIG.data_dir, self.getStudyType()
            )
        if not os.path.isdir(self._STUDY_DATA_DIR):
            _log.debug("Creating directory: %s", self._STUDY_DATA_DIR)
            os.makedirs(self._STUDY_DATA_DIR)
        
        # Directory to store stimuli used in this study
        self._STIMULI_DIR = os.path.join(self._STUDY_DATA_DIR, "stimuli")
        if not os.path.isdir(self._STIMULI_DIR):
            _log.debug("Creating directory: %s", self._STIMULI_DIR)
            os.makedirs(self._STIMULI_DIR)
            
        # Create a new item or load an existing one from the parent directory.
        # Parent directories contain a csv file logging all items that existed
        # in that directory:
        itemsLogPath = os.path.join(self._PARENT_DIR, "log.csv")
        itemsLogFieldnames = [
            "name",
            "id",
            "date",
            "participant_id"
            ]
        
        # Define this item's directory and info file path in terms of its name
        def getItemDir(name):
            return os.path.join(self._PARENT_DIR, name)
        def getItemInfoPath(name):
            return os.path.join(getItemDir(name), "info.yaml")
        
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
            date = datetime.now().strftime("%d%m%y")
            itemsLogEntry = {
                "id" : str(id),
                "name" : self._makeItemName(
                    id, date, participant_id, parent_dir=self._PARENT_DIR
                ),
                "date" : date,
                "participant_id" : participant_id
            }
            itemsLog.addLine(**itemsLogEntry)
            
            # Create a directory to store data for this item
            self._DIR = getItemDir(itemsLogEntry["name"])
            _log.debug("Creating directory: %s", self._DIR)
            os.makedirs(self._DIR, exist_ok=True)
                
            # Create an info file for this item, and initialize it with this
            # item's log info and some basic details
            infoPath = getItemInfoPath(itemsLogEntry["name"])
            _log.debug("Creating info file: %s", infoPath)
            self._info = Info(infoPath)
            self._info.update(
                **itemsLogEntry,
                dir=self._DIR,
                parent_dir=self.PARENT_DIR,
                info_file=infoPath,
                study_type=self.getStudyType()
                )
        else:
            # If an item name was provided, ignore participant_id and try to
            # load it
            _log.info("Loading existing %s: %s", self.__class__, name)
            
            # Define paths to item directory and info file
            self._DIR = getItemDir(name)
            infoPath = getItemInfoPath(name)
                
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
                self._info = Info(infoPath, forceReadFile=True)
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
                
        # Create a viewer for the info. The user can only read info by
        # interacting with this viewer, while self._info can be modified as
        # needed by the implementer and changes are reflected by the viewer
        self._infoViewer = InfoViewer(self._info)
        
    @classmethod
    @abstractmethod
    def getStudyType(cls) -> str:
        pass
    
    @property
    @abstractmethod
    def _PARENT_DIR(self) -> str:
        # Define the path to the parent directory that contains (or will
        # contain) the directory for this item
        pass
    
    @property
    def info(self) -> InfoViewer:
        return self._infoViewer
    
    @staticmethod
    def _makeItemName(
            id: int|str,
            date: str,
            participant_id: int|str|None,
            parent_dir: str|None = None
            ) -> str:
        name = f"{id}_{date}"
        if participant_id is not None:
            name = f"{name}_{participant_id}"
        return name
    
    @property
    @abstractmethod
    def data(self) -> Any:
        pass
    
    @abstractmethod
    def run(self) -> None:
        pass
    
#     @abstractmethod
#     def display(self) -> None:
#         pass  

class DependantStudyItem(StudyItem):
    def __init__(
            self,
            parent: StudyItem,
            *args,
            **kwargs
            ) -> None:
        
        if not isinstance(parent, self._getDependeeClass()):
            raise ValueError(
                f"`parent` is an instance of `{parent.__class__}', but must " +
                f"be an instance of `{self._getDependeeClass()}`."
            )
            
        self._PARENT = parent
        
        # Specify or validate the participant_id
        participant_id = kwargs.pop("participant_id", default=None)
        session_participant_id = self.session.info.participant_id
        if participant_id is None:
            participant_id = session_participant_id
        elif participant_id != str(session_participant_id):
            raise ValueError(
                "`participant_id` must be the same as the participant_id " +
                "for `parent`, or be `None`."
            ) 
        kwargs["participant_id"] = participant_id
        
        super().__init__(*args, **kwargs)
    
    @classmethod
    def _getDependeeClass(cls) -> StudyItem:
        return StudyItem

    @classmethod
    def getStudyType(cls) -> str:
        return cls._getDependeeClass().getStudyType() 

# TODO: add documentation
class Info:    
    def __init__(self, path: str, forceReadFile: bool = False) -> None:
        self._path = os.path.splittext(os.path.abspath(path))[0] + ".yaml"
        
        if forceReadFile and not os.path.isfile(self._path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), filePath
            )
        
        try:
            with open(self._path, "x") as f:
                pass
        except FileExistsError as E:
            # Assume the existing file is an info file
            _log.debug("Found existing info file: %s", self._path)
        else:
            _log.debug("Created new info file: %s", self._path)
        
    def __getInfo(self) -> dict[str, Any]:
        with open(self._path, "r") as f:
            contents = yaml.safe_load(f)
        return contents if contents is not None else {}
    
    def __getattr__(self, name: str) -> Any:
        try:
            val = self.__getConfig()[name]
        except KeyError as E:
            raise AttributeError(name) from E
        else:
            return val
        
    def __setattr__(self, name: str, val: Any) -> None:
        self.update(**{name : val})
        
    def __str__(self) -> str:
        return str(self.__getInfo())
    
    def attrNames(self) -> list[str]:
        return list(self.__getInfo().keys())
    
    def update(self, **kwargs) -> None:
        info = self.__getInfo()
        info.update(kwargs)
        with open(self._path, "w") as f:
            yaml.safe_dump(info, f)
        
# TODO: add documentation    
class InfoViewer:
    def __init__(self, info: Info) -> None:
        self.__info = info
        
    def __getattr__(self, name: str) -> Any:
        return self.__info.__getattr__(name)
    
    def __str__(self) -> str:
        return self.__info.__str__()
    
    def attrNames(self) -> list[str]:
        return self.__info.attrNames()