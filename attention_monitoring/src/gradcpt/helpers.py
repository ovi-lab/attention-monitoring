import logging
from typing import Callable
from typing_extensions import Self

import matlab.engine

import src.gradcpt as gradcpt
from src.helpers import _LogToFileCM
from src.study.helpers import getVerboseLogFormatter

_log = logging.getLogger(__name__)
    
class _GradCPTLogToFileCM(_LogToFileCM):
    """Context manager for temporarily writing gradCPT logs to a file.
    
    While in this context, the output of the gradcpt logger (and all its child
    loggers) will be written to the specified file in addition to being handled
    by existing handlers. Specifying `useBaseLogger=True` will use the gradcpt 
    logger's highest parent logger instead (eg. if the gradcpt logger's name is
    'x.y.z.gradcpt', the logger used will have the name 'x').
    """
    def __init__(self, filePath: str, useBaseLogger: bool = False):
        
        logName = gradcpt.__name__
        if useBaseLogger:
            logName = logName.split(".", 1)[0]
        # Use the gradcpt logger as the log
        super().__init__(
            logging.getLogger(logName),
            filePath,
            getVerboseLogFormatter(gradcpt.GradCPTSession.getStudyType())
        )