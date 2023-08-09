from abc import abstractmethod
import logging
from typing import Any

from ._study import Study

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
        self._log.debug("Initializing block")
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