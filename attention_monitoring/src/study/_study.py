from abc import ABC, abstractmethod
import logging
import os

from src.config import CONFIG

# TODO: change JsonBackedDict to properly behave like a dict
# TODO: add documentation for Study

# TODO: change logging formatting, see note on performance in: https://stackoverflow.com/questions/32291361/how-can-i-log-a-dictionary-into-a-log-file

class Study(ABC):
    
    def __init__(self, dataSubDir: [None | str] = None) -> None:
        
        # consoleHandler = logging.StreamHandler()
        # consoleFormatter = logging.Formatter(
        #     "%(levelname)-8s : %(cls)-16s : %(message)-s"
        #     )   
        # consoleHandler.setFormatter(consoleFormatter)
        
                 
        
        
        # # Create a logger from the name of the class
        # self._log = logging.Logger(__name__ + "->" + self.__class__.__name__)
        
        # ##############
        # if not self._log.hasHandlers():
        #     handlerConsole = logging.StreamHandler()
        #     handlerConsole.setLevel(logging.CRITICAL)
        #     formatterDefault = logging.Formatter("%(name)s")
        #     formatterVerbose = logging.Formatter("%(asctime)s %(levelname)8s : %(name)16s :\n   %(message)s")
        #     formatterConsole = logging.Formatter(
        #         "%(asctime)s | %(levelname)8s : %(name)16s : "
        #         + "File ""%(pathname)s"", line %(lineno)d: "
        #         + "\n    %(message)-s"
        #     ) 
        #     handlerConsole.setFormatter(formatterConsole)
        #     self._log.addHandler(handlerConsole)
            
        #     # handler = logging.StreamHandler()
        #     # handler.setLevel(logging.DEBUG)
        #     # handler.setFormatter(formatter)
        #     # self._log.addHandler(handler)
        # ##############
        
        # Define some useful directories, creating them if they don't already 
        # exist 
        
        # Directory to store all data for studies of this type
        self._DATA_DIR = os.path.join(
            CONFIG.projectRoot, "src", "data", self.getStudyType()
            )
        if dataSubDir is not None:
            self._DATA_DIR = os.path.join(self._DATA_DIR, dataSubDir)
        if not os.path.isdir(self._DATA_DIR):
            self._log.debug(f"Creating directory: {self._DATA_DIR}")
            os.makedirs(self._DATA_DIR)
        
        # Directory to store stimuli used in this study
        self._STIMULI_DIR = os.path.join(self._DATA_DIR, "stimuli")
        if not os.path.isdir(self._STIMULI_DIR):
            self._log.debug(f"Creating directory: {self._STIMULI_DIR}")
            os.makedirs(self._STIMULI_DIR)
        
        # Parent directory to contain the individual directories of every
        # session of this study.
        self._SESSIONS_DIR = os.path.join(self._DATA_DIR, "sessions")
        if not os.path.isdir(self._SESSIONS_DIR):
            self._log.debug(f"Creating directory: {self._SESSIONS_DIR}")
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