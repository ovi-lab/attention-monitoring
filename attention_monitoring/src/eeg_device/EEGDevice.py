from abc import ABC, abstractmethod

class EEGDevice(ABC):

    def __init__(self):
        pass
    
    @abstractmethod
    def __enter__(self):
        pass
    
    @abstractmethod
    def __exit__(self, exc_type, exc_value, exc_tb):
        pass
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def isConnected(self) -> bool:
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def startStreaming(self):
        pass
    
    @abstractmethod
    def isStreaming(self) -> bool:
        pass
    
    @abstractmethod
    def stopStreaming(self):
        pass