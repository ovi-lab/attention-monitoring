from abc import ABC, abstractmethod

class EEGDevice(ABC):

    def __init__(self):
        pass
    
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def startStreaming(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def stopStreaming(self):
        pass