"""Facilitates project-level configuration.

To use, import using `from config import CONFIG` and access the properties of
`CONFIG` to obtain configuration values. Configuration values are automatically
fetched from the relevant configuration file (see below) at runtime, meaning
that changes to the configuration file are automatically reflected in the
`CONFIG` object.

(Note that paths specified below are relative to the project root directory.)

Custom configurations can be specified in a `.yaml` file and must follow the
same structure as the default configuration file (`src/default_config.yaml`).
The files to read config values from are specified as a list of file paths
relative to the project root directory stored in the PATH attribute of CONFIG;
if a value is specified in both PATH[i] and PATH[j] for integers
0<=i<j<len(PATH), the value in PATH[j] is used. In other words, values
specified in files later in the list overwrite corresponding values specified
in files earlier in the list. PATH may be specified in two ways:
  - Specifying the list of file paths as a list name 'PATH' in the default
    config file before initializing CONFIG (that is, before importing CONFIG
    for the first time)
  - Directly modifying CONFIG.PATH after initialization. Note that this changes
    PATH project wide, ie. everywhere that CONFIG has been imported
See the documentation for the _Config class for more information.
"""
# TODO: update doc to include new import location
# TODO: refactor and put in appropriate directory. Maybe make a different one for each study?

import glob
import logging
import os
from typing import Any

import yaml

_log = logging.Logger(__name__)

class _Config:
    """Project-level configuration values.

    Provides access to various constants, preferences, and settings as
    specified in a configuration file (`.yaml`). Configuration values are
    obtained as properties of instances of this class.

    Attributes
    ----------
    PATH : list[str]
        The list of files read from to create the config (excludes the default
        config file, which is always read from first), specified as paths
        relative to the project root directory. If a value is specified in both
        PATH[i] and PATH[j] for integers 0<=i<j<len(PATH), the value in PATH[j]
        is used. In other words, values specified in files later in the list
        overwrite corresponding values specified in files earlier in the list.
        File paths may be added or removed from PATH after initialization by
        accessing a _Config instance's PATH attribute; changes to the PATH list
        in the default config file are not reflected by existing _Config
        instances.
    Any
        Any values specified in an included config file.
    """
    
    def __init__(self) -> None:
        # Get the path to the project root directory by searching for the
        # "closest" parent directory that contains a .gitignore file
        root = os.path.dirname(os.path.abspath(__file__))
        target = ".gitignore"
        while len(glob.glob(target, root_dir=root)) == 0:
            # Check if the system root has been reached
            if len(os.path.basename(root)) == 0:
                raise Exception(
                    "Could not find project root directory on path "
                    + os.path.abspath(__file__)
                )
            else:
                root = os.path.dirname(root)
        self.__root = root
        
        # Specfiy the path to the default config, stored in the same directory
        # as this file
        dirPath = os.path.relpath(os.path.dirname(__file__), start=self.__root)
        self.__defaultConfig = os.path.join(dirPath, "default_config.yaml")
        
        # Read the list of config paths to check from the default config.
        # Values specified in config files later in the list will overwrite
        # corresponding values in config files earlier in the list. Changes to
        # this list in the default config file made after initializing this
        # object are not reflected.
        with open(os.path.join(self.__root, self.__defaultConfig), "r") as f:
            contents = yaml.load(f, Loader=yaml.FullLoader)
            self.PATH = contents["PATH"] if contents is not None else []
            if isinstance(self.PATH, str):
                self.PATH = [self.PATH]
    
    def __getConfig(self) -> dict[str: Any]:
        config = {}
        for k, configPath in enumerate((self.__defaultConfig, *self.PATH)):
            try:
                f = open(os.path.join(self.__root, configPath), 'rt')
            except FileNotFoundError as E:
                if k == 0:
                    errmsg = (
                        "Could not read from default config file: " + 
                        f"{configPath}"
                    )
                    raise RuntimeError(errmsg) from E
                else:
                    _log.warn(
                        "Config file at following location could not be " +
                        "read, continuing execution: %s", configPath
                    )
            else:
                _log.debug("Loading config file: %s", configPath)
                contents = yaml.load(f, Loader=yaml.FullLoader)
                if contents is not None:
                    config.update(contents)
            finally:
                f.close()
                
        config["root"] = self.__root
        return config

    def __getattr__(self, name):
        # PATH is both a attribute of this class and a value in the config.
        # Users must only interact with the attribute, so this method must not
        # be called with name="PATH". Calling `self.PATH` is the itended way of
        # accessing PATH and internally will not call this method. 
        if name == "PATH":
            raise ValueError(
                "`name` must not be 'PATH'. Use `self.PATH` instead."
            )
        
        try:
            val = self.__getConfig()[name]
        except KeyError as E:
            raise AttributeError(name) from E
        else:
            return val
    
    def attrNames(self) -> list[str]:
        c = self.__getConfig()
        c["PATH"] = self.PATH
        return list(c.keys())
    
    def __str__(self):
        c = self.__getConfig()
        c["PATH"] = self.PATH
        return str(c)

CONFIG = _Config()