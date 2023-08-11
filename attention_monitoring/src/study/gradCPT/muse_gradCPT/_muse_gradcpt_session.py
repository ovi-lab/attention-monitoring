from src.config import CONFIG
from src.study.gradcpt import GradCPTSession
from src.eeg_device import Muse

class MuseGradCPTSession(GradCPTSession):
    
    def __init__(
            self, 
            /,
            **kwargs
            ) -> None:
        
        super().__init__(
            **kwargs
            )
        
        self.__eeg = Muse(*CONFIG.muse_signals)
        
    @property
    def eeg(self) -> Muse:
        return self.__eeg