import logging
import os
import subprocess

_log = logging.getLogger(__name__)

def getVerboseLogFormatter(studyType: str) -> logging.Formatter:
    """Get a formatter for verbose logging of studies"""
    _studyType = "%16s" % studyType
    f = logging.Formatter(
        ">>%(asctime)s : " + studyType + " : %(levelname)8s : %(name)32s : "
        + "line %(lineno)4d : File ""%(pathname)s"" : %(message)s"
    )
    return f

class _LaunchLabRecorder:
    """Context manager for running LabRecorder and logging its output to the 
    specified file."""
    def __init__(self, logFilePath: str, pathToLabRecorder: str) -> None:
        # Below attributes are read only (unenforced)
        self.pathToLabRecorder = os.path.realpath(pathToLabRecorder)
        self.logFilePath = logFilePath
        
    def __enter__(self):
        _log.debug("Starting LabRecorder")
        # Open the log file to use as stdout for LR process
        self._f = open(self.logFilePath, "a")
        _log.debug("Writing LabRecorder output to file: %s", self.logFilePath)
        # Open LR in a subprocess
        self._proc_LR = subprocess.Popen(
            self.pathToLabRecorder,
            stdout=self._f,
            stderr=subprocess.STDOUT,
            text=True
            ) 
                
    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is not None:
            _log.error("%s occurred, closing LabRecorder", exc_type)
        else:
            _log.debug("Closing LabRecorder")
        # End the LR subprocess and close the log file
        self._proc_LR.kill()
        self._f.close()