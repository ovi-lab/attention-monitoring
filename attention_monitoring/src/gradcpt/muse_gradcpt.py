import logging

from src.config import CONFIG
from src.eeg_device import Muse
from src.gradcpt import GradCPTSession

_log = logging.getLogger(__name__)

class MuseGradCPTSession(GradCPTSession):
    
    def __init__(self, /, museTimeout: [int | float] = -1, **kwargs) -> None:
        
        super().__init__(**kwargs)
        
        self.__eeg = Muse(
            *CONFIG.muse_signals, 
            connectTimeout=museTimeout, 
            startStreamingTimeout=museTimeout
            )
        
        # Update the info file with the signals that will be streamed from Muse
        _log.debug("Updating info file with fields: %s", ["muse_signals"])
        self._info["muse_signals"] = CONFIG.muse_signals
        
    @property
    def eeg(self) -> Muse:
        return self.__eeg