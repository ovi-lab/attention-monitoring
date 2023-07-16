"""Facilitates project-level configuration.

To use, import using `from config import CONFIG` and access the properties of
`CONFIG` to obtain configuration values. Configuration values are automatically
fetched from the relevant configuration file (see below) at runtime, meaning
that changes to the configuration file are automatically reflected in the
`CONFIG` object.

(Note that paths specified below are relative to the project root directory.)

Custom configurations can be specified in a `.yaml` file and must follow the
same structure as the default configuration file (`default_config.yaml` in the
project root directory). This can be done in two ways:

local config 
    A configuration file named `config.yaml` can be placed in the project root
    directory.
environment config
    Multiple configuration files can be placed in `configs` to use as preset
    configurations. To select which one to use, specify an environment variable
    named `CONFIG_MODE` storing the name of the desired file (not including the
    `.yaml` extension).

To determine the configuration to use, the project root directory is first
checked for `config.yaml`, which is used if it exists. The environment variable
`CONFIG_MODE` is then checked; if it exists and is not set to `DEFAULT`, the
configuration file `configs/(CONFIG_MODE).yaml` is used. Otherwise, the default
configuration is used.
"""

import os
import errno
import yaml

def _getRoot():
    """Get the absolute path to the root directory of this project.
    
    Returns
    -------
    string
        The absolute path to the root directory of this project, named
        "attention-monitoring".
    """

    rootName = "attention-monitoring"
    root = os.path.abspath(__file__)
    while os.path.basename(root) != rootName:
        root = os.path.dirname(root)
        if not os.path.basename(root):
            raise Exception(
                f"Could not find target root directory `{rootName}` on path "
                + os.path.abspath(__file__)
            )
    return root

__configsDir = os.path.join(_getRoot(), "configs")
__customConfigPath = os.path.join(_getRoot(), "config.yaml")
__defaultConfigPath = os.path.join(_getRoot(), "default_config.yaml")
    
def _getConfigPath():
    """Get the path to the configuration file to use.
    
    Returns
    -------
    string
        The path to the configuration file to use.
    """

    envVar = 'CONFIG_MODE'
    if os.path.isfile(__customConfigPath):
        # Check for a custom config file
        return __customConfigPath
    elif envVar in os.environ and os.environ.get(envVar).lower() != 'default':
        # Check if a config file is specified by the environment variable
        # `envVar`, and attempt to use that config file
        envConfigFilename = os.environ.get(envVar) + ".yaml"
        envConfigPath = os.path.join(__configsDir, envConfigFilename)
        if os.path.isfile(envConfigPath):
            return envConfigPath
        else:
            msg = (
                f'Illegal value for environment variable `{envVar}` - '
                + os.strerror(errno.ENOENT)
                )
            raise FileNotFoundError(
                errno.ENOENT, msg, envConfigPath
            )
    else:
        # In all other cases, use the default config file
        if os.path.isfile(__defaultConfigPath):
            return __defaultConfigPath
        else:
            msg = (
                "Default config file not found - " + os.strerror(errno.ENOENT)
                )
            raise FileNotFoundError(
                errno.ENOENT, msg, __defaultConfigPath
            )

def _getConfig():
    """Get the contents of the configuration file.
    
    Returns
    -------
    dict
        The contents of the configuration file as key value pairs in a `dict`.
    """

    with open(_getConfigPath(), 'rt') as f:
        return yaml.load(f, Loader=yaml.FullLoader)

class _Config:
    """Project-level configuration values.

    Provides access to various constants, preferences, and settings as
    specified in a configuration file (`.yaml`). Configuration values are
    obtained as properties of instances of this class.

    Attributes
    ----------
    projectRoot : str
        The absolute file path to the root directory of this project, named
        "attention-monitoring".
    verbose : int
        The level of verbosity to use for printing messages. At 0, nothing is
        printed. At 1, warnings and important info messages are printed. At 2,
        information about program execution as well as more detailed error
        messages are printed. At 3, more verbose information is printed. Note
        that Psychtoolbox's verbosity level is also set to this value.
    num_full_blocks : int
        (gradCPT) The number of non-practice blocks to perform.
    do_practice_block : bool
        (gradCPT) Whether to perform a practice block.
    stim_transition_time_ms : int
        (gradCPT) The time in milliseconds for one stimulus to transition to
        the next (equivalently, the length of the transition period).
    stim_static_time_ms : int
        (gradCPT) The time in milliseconds that one stimulus remains fully
        coherent after transitioning from the previous stimulus (equivalently, 
        the length of the static period).
    full_block_sequence_length : int
        (gradCPT) The number of stimuli in a non-practice block.
    practice_block_sequence_length : int
        (gradCPT) The number of stimuli in a practice block.
    pre_full_block_break_time : int
        (gradCPT) The time in seconds to wait before starting a non-practice
        block.
    pre_practice_block_break_time : int
        (gradCPT) The time in seconds to wait before starting a practice block.
    stim_diameter : int
        (gradCPT) The diameter in pixels of the circle that stimuli are cropped
        to.
    muse_signals : list of str
        The signals to obtain from the muse. Any combination of "EEG", "PPG",
        "Accelerometer", "Gyroscope".
    stream_markers_to_lsl : bool
        Whether to stream marker signals indicating the start of transition and
        static periods, the start and end of blocks, and the participant
        responses to the lab streaming layer during gradCPT.
    record_lsl : bool
        Whether to automatically record lab streaming layer streams using
        LabRecorder during gradCPT.
    tcp_address : str
        The remote host name or IP address to use for communicating with
        LabRecorder using TCP.
    tcp_port : int
        The port number to use for communicating with LabRecorder using TCP.
        Must be between 1 and 65535.
    """

    def __fetch(*namev):
        """Get the specified configuration value as a property.
        
        Parameters
        ----------
        *namev : str
            The name of the configuration value to get, as specified in the
            configuration file. If nested within other elements in the file,
            also specify the parent elements as additional argument from
            highest to lowest level.

        Returns
        -------
        property object
            The configuration value as a property object. Set a variable in the
            `_Config` class equal to this value to set it as a property.
        """

        @property
        def f(self):
            configVal = _getConfig()
            for name in namev:
                configVal = configVal[name]
            return configVal
        return f

    # Config Values
    # |---Constants
    __pathConstants = ['constants']
    @property
    def projectRoot(self):
        return _getRoot()
    # |---Preferences
    __pathPreferences = ['preferences']
    # |---|---General
    __pathGeneral = *__pathPreferences, 'general'
    verbose = __fetch(
        *__pathGeneral, 'verbose'
    )
    # |---|---Study
    __pathStudy = *__pathPreferences, 'study'
    num_full_blocks = __fetch(
        *__pathStudy, 'num_full_blocks'
    )
    do_practice_block = __fetch(
        *__pathStudy, 'do_practice_block'
    )
    stim_transition_time_ms = __fetch(
        *__pathStudy, 'stim_transition_time_ms'
    )
    stim_static_time_ms = __fetch(
        *__pathStudy, 'stim_static_time_ms'
    )
    full_block_sequence_length = __fetch(
        *__pathStudy, 'full_block_sequence_length'
    )
    practice_block_sequence_length = __fetch(
        *__pathStudy, 'practice_block_sequence_length'
    )
    pre_full_block_break_time = __fetch(
        *__pathStudy, 'pre_full_block_break_time'
    )
    pre_practice_block_break_time = __fetch(
        *__pathStudy, 'pre_practice_block_break_time'
    )
    stim_diameter = __fetch(
        *__pathStudy, 'stim_diameter'
    )
    muse_signals = __fetch(
        *__pathStudy, 'muse_signals'
    )
    # |---|---LSL
    __pathLSL = *__pathPreferences, 'lsl'
    stream_markers_to_lsl = __fetch(
        *__pathLSL, 'stream_markers_to_lsl'
    )
    record_lsl = __fetch(
        *__pathLSL, 'record_lsl'
    )
    tcp_address = __fetch(
        *__pathLSL, 'tcp_address'
    )
    tcp_port = __fetch(
        *__pathLSL, 'tcp_port'
    )

CONFIG = _Config()
CONFIG.__doc__ = _Config.__doc__