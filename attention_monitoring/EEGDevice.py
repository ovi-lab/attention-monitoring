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