from abc import ABC, abstractmethod
import logging
import os

from src.config import CONFIG

_log = logging.Logger(__name__)

# TODO: change JsonBackedDict to properly behave like a dict
# TODO: add documentation for Study

class Study(ABC):
    
    def __init__(self, dataSubDir: [None | str] = None) -> None:
        
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
        
        # Parent directory to contain the individual directories of every
        # session of this study.
        self._SESSIONS_DIR = os.path.join(self._DATA_DIR, "sessions")
        if not os.path.isdir(self._SESSIONS_DIR):
            _log.debug("Creating directory: %s", self._SESSIONS_DIR)
            os.makedirs(self._SESSIONS_DIR)
    
    @classmethod
    @abstractmethod
    def getStudyType(cls) -> str:
        pass