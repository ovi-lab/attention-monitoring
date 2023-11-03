import logging

from .EEGDevice import EEGDevice

_log = logging.getLogger(__name__)

class EegoRT(EEGDevice):
    
    def __init__(self):
        self.amplifier = None #TODO: implement this
        pass
    
    def __enter__(self):
        pass
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        pass
    
    def connect(self):
        pass
    
    def isConnected(self) -> bool:
        pass
    
    def disconnect(self):
        pass
    
    def startStreaming(self):
        pass
    
    def isStreaming(self) -> bool:
        pass
    
    def stopStreaming(self):
        pass