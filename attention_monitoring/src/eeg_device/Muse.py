# TODO: still needs a lot of fixing up

import asyncio
import subprocess
import logging
from pylsl import StreamInfo, StreamInlet, resolve_streams, resolve_bypred
import shlex
import textwrap
import threading
import time

from .EEGDevice import EEGDevice
from src.config import CONFIG

_log = logging.getLogger(__name__)

class Muse(EEGDevice):
    """Setup the Muse device to begin streaming data to LSL.

    If data is not already streaming, the Bluemuse app is launched and the user
    must manually connect the Muse and click on "Start Streaming". Note that 
    for Muse devices, the device is connected iff the device is streaming.

    Parameters
    ----------
    signals : list of str
        The signals to obtain from the muse. Any combination of "eeg", "ppg",
        "accelerometer", "gyroscope". If unspecified, obtains all of these.
    """

    # All entries must be lowercase
    __validSignals = ("eeg", "ppg", "accelerometer", "gyroscope")

    def __init__(
            self, 
            *signals: str, 
            connectTimeout: [int | float] = -1,
            startStreamingTimeout: [int | float] = -1
            ) -> None:
        if len(signals) > 0:
            if not all(s.lower() in self.__validSignals for s in signals):
                raise Exception("Invalid signal.")
            self.__signals = tuple(s.lower() for s in signals)
        else:
            self.__signals = self.__validSignals

        self._connectTimeout = connectTimeout
        self._startStreamingTimeout = startStreamingTimeout
    
    @property
    def signals(self):
        return self.__signals
    
    def __enter__(self):
        self.connect(timeout=None)
        self.startStreaming(timeout=None)
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        self.stopStreaming()
        self.disconnect()
      
    # if isStreaming()==True then isConnected()==True   
    def isStreaming(self):
        streams = resolve_streams()
        if len(streams) == 0:
            return False
        
        streamTypes = [stream.type().lower() for stream in streams]
        streamNames = [stream.name() for stream in streams]
        connected = (
            all(name == streamNames[0] for name in streamNames)
            and all(signal in streamTypes for signal in self.signals)
            )
        return connected
    
    def isConnected(self):
        return self.isStreaming()
        
    def connect(self, timeout: [int | float] = -1):
        if timeout is not None:
            _timeout = timeout
        else:
            _timeout = self._connectTimeout
        
        # Helper method for writing common commands to Bluemuse
        # TODO: change to not use shell
        async def execBluemuse(key, value):
            command = f'start bluemuse://setting?key={key}!value={value}'
            # command = shlex.split(command)
            _log.debug("Running command: %s", command)
            proc = await asyncio.create_subprocess_shell(command)
            await proc.wait()
        
        # Check whether any desired signals are not yet streaming and start
        # Bluemuse if not
        if not self.isConnected():
            _log.info("Connecting to Muse device")
            
            # Define commands to start Bluemuse with given preferences
            commands = {
                (f"{s}_enabled") : (str(s in self.signals).lower())
                for s in self.__validSignals
                }
            commands["primary_timestamp_format"] = "LSL_LOCAL_CLOCK_NATIVE"
        
            # Execute the commands
            async def execCommands():
                _log.debug("Starting Bluemuse")
                await asyncio.gather(
                    *(execBluemuse(k, v) for k, v in commands.items())
                    )
            asyncio.run(execCommands())
            
            # Wait for user to manually connect
            _log.warn("User must manually connect to Muse device on Bluemuse")
            
            def timedOut(tStart) -> bool:
                # Check whether the maximum amount of time to wait for the
                # Muse device to connect (if specified) has been reached
                if _timeout < 0:
                    r = False
                else:
                    r = time.time() - tStart > _timeout
                return r
            
            # Wait until either the device connects, timing out, or the user
            # indicates to continue (via KeyboardInterrupt)
            print(
                "Press ctrl + c (or equivalent) to continue without waiting "
                + "for the Muse device to connect"
                )
            tI = time.time()
            try:
                while not any((timedOut(tI), self.isConnected())):
                    time.sleep(0.5)
            except KeyboardInterrupt as E:
                _log.warn(
                    "Continuing with waiting for the Muse device to connect"
                    )
            tF = time.time()
                
            # Log whether the Muse device was successfully connected to
            if self.isConnected():
                _log.info("Successfully connected to the Muse device")
            else:
                _log.warn(
                    "Failed to connect to the Muse device (waited %s seconds)",
                    (tF - tI)
                    )
        else:
            _log.debug("Muse device is already connected")
            
    def startStreaming(self, timeout: [int | float] = -1):
        if timeout is not None:
            _timeout = timeout
        else:
            _timeout = self._startStreamingTimeout
            
        _log.info(
            "Waiting%s for Muse device to stream all desired signals to LSL",
            (f" {_timeout} seconds" if _timeout >= 0 else "")
            )
        _log.debug("Desired signals: %s", self.signals)
        
        if not self.isStreaming():
            _log.warn(
                "User must manually start streaming from Muse device on "
                + "Bluemuse"
                )
            
            def timedOut(tStart) -> bool:
                # Check whether the maximum amount of time to wait for the
                # signals to start streaming (if specified) has been reached
                if _timeout < 0:
                    r = False
                else:
                    r = time.time() - tStart > _timeout
                return r
            
            # Wait until either all signals are streaming, timing out, or the
            # user indicates to continue (via KeyboardInterrupt)
            print(
                "Press ctrl + c (or equivalent) to continue without waiting "
                + "for all signals to start streaming"
                )
            tI = time.time()
            try:
                while not any((timedOut(tI), self.isStreaming())):
                    time.sleep(0.5)
            except KeyboardInterrupt as E:
                _log.warn("Continuing with waiting for all signals to stream")
            tF = time.time()
                
            # Log whether all signals successfully started streaming
            if self.isStreaming():
                _log.info("All desired Muse signals are streaming on LSL")
            else:
                streamTypes = [s.type().lower() for s in resolve_streams()]
                _log.warn(
                    "Not all desired Muse signals are streaming on LSL "
                    + "(waited %s seconds). Missing signals: %s",
                    (tF - tI),
                    [s for s in self.signals if s not in streamTypes]
                    )
        else:
            _log.info("All desired Muse signals are already streaming on LSL")
            
    def disconnect(self):
        _log.debug("Closing Bluemuse")
        command = "start bluemuse://shutdown"
        subprocess.run(command, shell=True)
    
    def stopStreaming(self):
        _log.debug("Stopping Bluemuse from streaming to LSL")
        command = "start bluemuse://stop?stopall"
        subprocess.run(command, shell=True)
