import logging

import src.gradcpt as gradcpt
from src.helpers import _LogToFileCM
from src.study.helpers import getVerboseLogFormatter
    
class _GradCPTLogToFileCM(_LogToFileCM):
    """Context manager for temporarily writing gradCPT logs to a file.
    
    While in this context, the output of the gradcpt logger (and all its child
    loggers) will be written to the specified file in addition to being handled
    by existing handlers.
    """
    def __init__(self, filePath: str):
        # Use the gradcpt logger as the log
        super().__init__(
            logging.getLogger(gradcpt.__name__),
            filePath,
            getVerboseLogFormatter(gradcpt.GradCPTSession.getStudyType())
        )
