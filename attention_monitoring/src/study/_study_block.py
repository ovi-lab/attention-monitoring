from abc import abstractmethod
import logging
import os
from typing import Any

from ._study import Study

from ._study import StudyItem, _baseItemsLogEntryFormatter
from ._study_session import StudySession

_log = logging.getLogger(__name__)

class StudyBlock(StudyItem):
    def __init__(self, parentSession: StudySession, *args, **kwargs) -> None:
        self._PARENT_DIR_ = os.path.join(parentSession.info["dir"], "blocks")        
        
        super().__init__(*args, **kwargs)
        
        self._PARENT_SESSION = parentSession

    @property
    def _PARENT_DIR(self) -> str:
        return self._PARENT_DIR_
    
    @staticmethod
    def _formatItemsLogEntry(*args, **kwargs) -> dict[str, str]:
        return _baseItemsLogEntryFormatter("B", *args, **kwargs)











# class StudyBlock(Study):
#     """A block of a scientific study.
    
#     An abstract class representing a block of trials in a scientific study.
#     Concrete subclasses must implement the abstract properties and methods, 
#     listed below.
    
#     Paramaters
#     ----------
#     name : str
#         The name of this block.
    
#     Attributes
#     ----------
#     name : str
#         The name of this block (read only).
    
#     Abstract Attributes
#     -------------------
#     data : Any or None
#         The data collected during this block. If no data has been collected,
#         its value is `None`.
    
#     Abstract Methods
#     ----------------
#     display() -> None
#         Visualize the data collected in this block.
#     """
#     def __init__(self, name: str, **kwargs) -> None:
#         super().__init__(**kwargs)
#         _log.debug("Initializing block")
        
#         self._name = name
    
#     @property
#     def name(self) -> str:
#         return self._name
    
#     @property
#     @abstractmethod
#     def data(self) -> [Any | None]:
#         pass
    
#     @abstractmethod
#     def display(self) -> None:
#         """Visualize the data collected in this block.
        
#         Display the data collected for this block. If no data has been 
#         collected, display a message indicating so.
#         """
#         pass