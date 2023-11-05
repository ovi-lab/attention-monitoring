import csv
import errno
import logging
import os
import subprocess
from typing import Any

import polars as pl

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
        
class CSVLogger:
    """A log backed by a csv file.
    
    The log is backed by a '.csv' file specified by `filePath` when creating a
    new `CSVLogger` object. Changes to the log made through this object using
    the provided methods are reflected in the log file. Note that the data
    returned by instances of `CSVLogger` are undefined and may result in
    unexpected behaviour if:
     - The content of the log file is changed externally
     - Multiple instances of `CSVLogger` exist simultaneously and are backed by
       the same file.
     
    Parameters
    ----------
    filePath : str
        The path to the file to use as the log. The file extension must either
        be ommited or '.csv'. If the specified file already exists and is not
        empty, it will be used as the log. Otherwise, a new log file will be
        created.
    fieldNames : list of str
        A list of the names of all fields in the log. Cannot contain
        duplicates. If using an existing file, these must match the existing
        column names in the file.
    forceReadFile : bool, default=False
        If true, raises a FileNotFound exception instead of creating a new file
        if the log cannot be loaded from the file specified by `filePath`.

    Attributes
    ----------
    logFields : list of str
        The names of the fields in the log.
    path : str
        The path to the log file.
    numLines : int
        The number of lines in the log. More specifically, the number of
        sessions that are recorded in the log.

    Raises
    ------
    ValueError
        If `filePath` specifies an invalid extension.
    """

    __rowCountCol = "row_count"
    
    def __init__(
            self, 
            filePath: str, 
            fieldNames: list[str],
            forceReadFile: bool = False
            ) -> None:
        
        # Get the path to the log file
        name, ext = os.path.splitext(filePath)
        if not ext in ("", ".csv"):
            raise ValueError(
                f"Unsupported file type '{ext}'. Filetype must either be "
                + "unspecified or '.csv'"
                )
        self.__path = name + ".csv"
        
        # Helper function to check that a given list of field names is valid.
        # Returns nothing if all field names are valid, otherwise raises a
        # relevant exception.
        def assertValidFieldnames(
            fieldnames : list[str], 
            source : str
            ) -> None:
            if self.__rowCountCol in fieldNames:
                raise ValueError(
                    f"{source} contains an illegal field name: "
                    + f"{self.__rowCountCol}"
                    )
            
            if len(fieldNames) == len(set(fieldNames)):
                raise ValueError(
                    f"{source} cannot contain duplicate field names."
                    )
                
        # Check that the specified fieldnames are valid
        assertValidFieldnames(fieldNames, "`fieldNames`")
          
        # Create a new log file with the specified field names if it does not
        # exist yet or exists and is empty, or raise an exception if
        # `forceReadFile` is True and the log file does not exist. Otherwise,
        # assume it follows the correct structure expected by this class (like
        # if it was created by a previous instance of this class)
        try:
            makeNewLog = os.path.getsize(self.path) == 0
        except FileNotFoundError as E:
            makeNewLog = True
        finally:
            if makeNewLog:
                if forceReadFile:
                    raise RuntimeError(
                        "Failed to read from existing file as it either "
                        + f"can't be found or it is empty: {self.path}"
                        )
                
                # Initialize the new log file with the specified fields
                with open(self.path, "w") as f:
                    dWriter = csv.DictWriter(f, fieldnames=fieldNames)
                    dWriter.writeheader()
                    self._fieldNames = dWriter.fieldnames
            else:
                # Check that the fieldnames in the existing file are valid and
                # match the provided fieldnames
                with open(self.path, "r") as f:
                    dReader = csv.DictReader(f)
                    assertValidFieldnames(
                        dReader.fieldnames,
                        f"The specified file (`filePath`={self.path})"
                        )
                    if not dReader.fieldnames == fieldNames:
                        raise ValueError(
                            "The field names specified in `fieldNames` do not "
                            + "match the field names in the specified file "
                            + f"(`filePath`={self.path})"
                            )
                    self._fieldNames = dReader.fieldnames
    
    @property
    def fieldNames(self) -> list[str]:
        return self._fieldNames

    @property
    def path(self) -> str:
        return self.__path
    
    @property
    def numLines(self) -> int:
        data = self.__lazyLoadLog()
        _numLines = data.select(self.__rowCountCol).max().collect()[0,0]
        if _numLines is None:
            _numLines = 0
        
        return _numLines
    
    def __lazyLoadLog(self) -> pl.LazyFrame:
        
        # Note that below function will raise an indescriptive `OSError` if the
        # file is not found
        log = pl.scan_csv(
            self.path,
            infer_schema_length=0,
            row_count_name=self.__rowCountCol,
            row_count_offset=1
            )
        
        # Make sure the row count column was added properly
        numRowCountCols = log.columns.count(self.__rowCountCol)
        if numRowCountCols > 1:
            # The existing log file cannot contain a column with the same
            # name as the row count column
            raise ValueError(
                f"The specified file {self.path} contains an illegal "
                + f"field name: {self.__rowCountCol}"
                )
        elif numRowCountCols < 1:
            # Row count column doesn't get added if the log is empty, so we
            # have to add it manually
            log = log.with_row_count(name=self.__rowCountCol, offset=1)
            
        return log
            
    
    def read(self, *lines: int) -> dict[str, list[Any]]:
        """Read the specified line(s) from the log
        
        Parameters
        ----------
        *lines : tuple of int
            The lines in the log to read from (note that indices start at 1).
            Negative indexing is supported. If unspecified, all lines are read.

        Raises
        ------
        IndexError:
            If any of the specified line(s) are invalid.

        Returns
        -------
        dict of str to list of Any
            A dictionary mapping the name of each field in the log to a list
            containing the corresponding values from the specified lines. An
            additional field also specifies the corresponding row number.
        """
        
        # Assume the log file exists and is properly formatted
        
        readSelectLines = len(lines) > 0
        data = self.__lazyLoadLog()
        
        if readSelectLines:
            lastLineNum = self.numLines
            
            # Handle negative indexing and check that all lines are in bounds
            _lines = [x if x >= 0 else lastLineNum + 1 + x for x in lines]
            if any(x < 1 or x > lastLineNum for x in _lines):
                invalids = [
                    lines[k] for k in range(len(_lines)) 
                    if (_lines[k] < 1 or _lines[k] > lastLineNum)
                    ]
                raise ValueError(
                    "Specified lines are out of bounds for log with "
                    + f"{self.numLines} line(s): {invalids}"
                )
            
            # Assume that the log contains a line for every line number in the
            # range [1,lastLineNum]
            data = data.filter(pl.col(self.__rowCountCol).is_in(_lines))
          
        # Read the data into memory  
        data = data.collect()
        
        if readSelectLines and data.height != len(lines):
            raise Exception(
                f"Expected to read {len(lines)} lines, but read {data.height}."
                )
            
        return data.to_dict(as_series=False)
        
    def addLine(self, **lineItems) -> None:
        """Add a line to the end of the log.

        Data to include in the line are specified as keyword arguments, where
        the argument is the value to add and the key is the name of the
        corresponding log field. Any fields in the log file that are not
        assigned a value in the keyword arguments are left empty (in other
        words, the value written is `""`). Specifying a keyword argument where
        the key is not the name of a field in the log file raises a
        `ValueError`.

        Parameters
        ----------
        **lineItems
            The data to include in the line, specified as keyword arguments.
            
        Raises
        ------
        ValueError
            If any of the specified items do not correspond to an existing
            field in the log.
        """
        
        # Assume the log file exists and is properly formatted
        
        # Convert data to strings for writing to the log
        _lineItems = {}
        for k, v in lineItems.items():
            _lineItems[k] = str(v) if v is not None else ""
        
        # Add the line to the log
        with open(self.path, "a") as f:
            dWriter = csv.DictWriter(f, fieldnames=self.fieldNames, restval="")
            dWriter.writerow(_lineItems)    