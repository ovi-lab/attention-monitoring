import logging
from typing import Callable

import matlab.engine

_log = logging.getLogger(__name__)      
        
def _getMatlabCallback(
        future: matlab.engine.FutureResult, 
        desc: str
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
    desc : str
        A description of the call to MATLAB - basically a string to help
        identify the specific call in the log file.
        
    Raises
    ------
    matlab.engine.CancelledError
        If the call to MATLAB is not successfully cancelled.
        
    Returns
    -------
    Callable[[], None]
        The function to call to cancel the specified MATLAB call.
    """
    # TODO: use weakref?
    def f(exc_type, exc_value, exc_tb) -> None:
        if exc_type is not None:
            _log.error(
                "%s occurred, cleaning up call to MATLAB: '%s'", 
                exc_type, desc
                )
        else:
            _log.debug("Cleaning up call to MATLAB: '%s'", desc)
        
        try:
            # Only cancel if not already cancelled or done
            callIsActive = not (future.cancelled() or future.done())
        except matlab.engine.RejectedExecutionError as E:
            # No clean up to perform if the MATLAB engine has already
            # terminated
            _log.debug(
                "The MATLAB engine used to make this call has already "
                + "terminated, no clean up necessary: '%s'",
                desc
                )
        else:
            if callIsActive:
                _log.debug("Cancelling call to MATLAB: '%s'", desc)
                future.cancel()
                if future.cancelled():
                    _log.debug(
                        "Successfully cancelled call to MATLAB: '%s'", 
                        desc
                        )
                else:
                    errmsg = f"Failed to cancel call to MATLAB: '{desc}'"
                    _log.error(errmsg)
                    raise matlab.engine.CancelledError(errmsg)
            else:
                _log.debug(
                    "Call to MATLAB was done or already cancelled: '%s'", 
                    desc
                    )
        
    return f  