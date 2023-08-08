from attention_monitoring.src.config import CONFIG
from GradCPT import GradCPTSession
from Muse import Muse

class MuseGradCPTSession(GradCPTSession):
    
    def __init__(
            self, 
            sessionName: [str | None] = None,
            participantID: [int | None] = None
            ) -> None:
        
        super().__init__(sessionName=sessionName, participantID=participantID)
        
        self.__eeg = Muse(*CONFIG.muse_signals)
        
    @property
    def eeg(self) -> Muse:
        return self.__eeg