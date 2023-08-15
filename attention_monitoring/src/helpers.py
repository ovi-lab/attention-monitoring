import errno
import json
import logging
import os
from typing import Any

class _LogToFileCM:
    """Context manager for temporarily writing log output to a file.
    
    While in this context, the output of the specified logger (and all its
    child loggers) will be written to the specified file (In the specified
    format) in addition to being handled by existing handlers.
    """
    def __init__(
            self, 
            log: logging.Logger,
            filePath: str, 
            formatter: logging.Formatter,
            ) -> None:
        self._log = log
        self.filePath = filePath
        self._handler = logging.FileHandler(self.filePath)
        self._formatter = formatter
        self._handler.setLevel(logging.DEBUG)
        self._handler.setFormatter(self._formatter)
        
    def __enter__(self):
        self._log.debug(
            "Writing logger '%s' to file: %s", self._log.name, self.filePath
            )
        self._log.addHandler(self._handler)
        
    def __exit__(self, exc_type, exc_value, exc_tb):
        # Include any exceptions in the log file
        exc_info = (exc_type, exc_val, exc_tb)
        if any(x is not None for x in exc_info):
            self._log.error("Exception occurred", exc_info=exc_info)
            
        self._handler.close()
        self._log.removeHandler(self.handler)
        self._log.debug("Stopped writing logger '%s' to file", self._log.name)

class JsonBackedDict:
    """A dictionary-like object backed by a '.json' file.
    
    Maintains a dictionary-like structure (referred to as the 'jdict') that is 
    backed by a '.json' file specified by `filePath` when creating a new 
    `JsonBackedDict` object. Changes to the jdict made through this object
    using the provided methods are reflected in the json file. Once 
    initialised, key value pairs in the jdict can be specified and accessed 
    like a normal dict object (ie. `myJsonBackedDict[x] = y`). Note that the 
    data returned by instances of `JsonBackedDict` are undefined and may result 
    in unexpected behaviour if:
     - The content of the json file is changed externally.
     - Multiple instances of `JsonBackedDict` exist concurrently and are backed
       by the same file.
    
    Parameters
    ----------
    filePath : str
        The path to the backing json file. The file extension must either
        be ommited or '.json'. If the specified file already exists, it will be
        used to initialise and back the jdict. Otherwise, a new file will be 
        created.
    forceReadFile : bool, default=False
        If true, raises a FileNotFound exception instead of creating a new file
        if the file specified by `filePath` cannot be read.

    Raises
    ------
    ValueError
        If `filePath` specifies an invalid extension.
    FileNotFound
        If `forceReadFile` is True and the file specified by `filePath` cannot
        be read.
    """
    def __init__(self, filePath: str, forceReadFile: bool = False) -> None:
        name, ext = os.path.splitext(filePath)
        if not ext in ("", ".json"):
            raise ValueError(
                f"Unsupported file type '{ext}'. Filetype must either be "
                + "unspecified or '.json'"
                )
        self.__path = name + ".json"
        
        # Load the info file if it exists, otherwise create it or raise an 
        # exception if `forceReadFile` is True
        if os.path.isfile(self.__path):
            with open(self.__path, "r") as f:
                self.__data = json.load(f)
        elif not forceReadFile:
            with open(self.__path, "w") as f:
                self.__data = {}
                json.dump(self.__data, f)
        else:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), filePath
                )
                
    def __updateFile(self):
        # Update the saved file to store the contents of self.__data
        with open(self.__path, "w") as f:
            json.dump(self.__data, f, sort_keys=True, indent=0)
                
        
    def __setitem__(self, key, value):
        self.__data[key] = value
        self.__updateFile()
            
            
    def __getitem__(self, key):
        return self.__data[key]
    
    def update(self, **items : Any) -> None:
        """Add multiple items to the info dict at the same time.
        
        Parameters
        ----------
        **items : dict of Any to Any
            The items to add to the info dict, specified as key value pairs
            where the key and value are the name and value in the info dict,
            respectively.
        """
        if len(items) == 0:
            return
        self.__data.update(items)
        self.__updateFile()
        
    # TODO: ensure this is implemented correctly, maybe make a proper subclass
    # of dict instead?
    def items(self):
        return self.__data.items()
        
    def safeView(self) -> dict:
        """Get a copy of the jdict.
        
        Returns
        -------
        dict
            A copy of the jdict. The returned dict is not backed by the
            json file. It will not reflect any changes made to the jdict
            and the jdict will not reflect any changes made to the returned
            dict.
        """
        return {k : v for (k, v) in self.__data.items()}