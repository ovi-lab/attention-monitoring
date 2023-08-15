import logging
from typing import Callable

import matab.engine

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
        
def _makeMatlabCanceller(
        future: matlab.engine.FutureResult, 
        errmsg: str
        ) -> Callable[[], None]:
    """Get a function that, when called, cancels the specified asynchronous
    call to MATLAB.
    
    When calling the returned function, if (at that time) the specified call to
    MATLAB is already done or has already been cancelled, the returned function
    will return without attempting to cancel the call to MATLAB.
    
    Parameters
    ----------
    future : matlab.engine.FutureResult
        The call to MATLAB that is to be cancelled. Specifically, this is the
        value that was returned by making a call to MATLAB with
        `background=True`.
    errmsg : str
        The error message to include in the raised exception if the call to
        MATLAB is not successfully cancelled.
        
    Raises
    ------
    matlab.engine.CancelledError
        If the call to MATLAB is not successfully cancelled.
        
    Returns
    -------
    Callable[[], None]
        The function to call to cancel the specified MATLAB call.
    """
    def f() -> None:
        # Only cancel if not already cancelled
        if (not future.cancelled()) or (not future.done()):
            future.cancel()
            if not future.cancelled():
                raise matlab.engine.CancelledError(errmsg)
        
    return f  
