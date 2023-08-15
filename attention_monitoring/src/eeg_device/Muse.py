# TODO: still needs a lot of fixing up

import asyncio
import subprocess
import logging
from pylsl import StreamInfo, StreamInlet, resolve_streams, resolve_bypred
import shlex
import textwrap

from .EEGDevice import EEGDevice
from src.config import CONFIG

_log = logging.getLogger(__name__)

class Muse(EEGDevice):
    """Setup the Muse device to begin streaming data to LSL.

    If data is not already streaming, the Bluemuse app is launched and the user
    must manually connect the Muse and click on "Start Streaming".

    

    Parameters
    ----------
    signals : list of str
        The signals to obtain from the muse. Any combination of "EEG", "PPG",
        "Accelerometer", "Gyroscope". If unspecified, obtains all of these.
    """

    __validSignals = ("EEG", "PPG", "Accelerometer", "Gyroscope")

    def __init__(self, *signals):
        if len(signals) > 0:
            if not all(signal in self.__validSignals for signal in signals):
                raise Exception("Invalid signal.")
            self.__signals = signals
        else:
            self.__signals = self.__validSignals

    @property
    def signals(self):
        return self.__signals

    def connect(self):
        streams = resolve_streams()

        # Check whether any desired signals are not yet streaming
        streamTypes = [stream.type() for stream in streams]
        if not all(signal in streamTypes for signal in self.signals):
            # Start bluemuse and enable desired signals to stream
            keys = [
                "primary_timestamp_format",
                *[
                    signal.lower() + "_enabled" 
                    for signal in self.__validSignals
                    ]
                ]
            values = [
                "LSL_LOCAL_CLOCK_NATIVE",
                *[
                    str(signal in self.signals).lower()
                    for signal in self.__validSignals
                    ]
                ]
            commands = [
                f'start bluemuse://setting?key={keys[i]}!value={values[i]}'
                for i in range(len(keys))
                ]

            _log.debug("Starting BLuemuse")
            for command in commands:
                subprocess.run(command, shell=True) 

            # Connect to the Muse device
            _log.debug("Connecting to Muse device")
            if CONFIG.eeg_device_id is not None:
                command = (
                    "start bluemuse://start?addresses="
                    + str(CONFIG.eeg_device_id)
                    )
            else:
                command = "start bluemuse://start?startall"
            subprocess.run(command, shell=True) 
            
    async def asyncConnect(self) -> tuple[asyncio.subprocess.Process]:
        streams = resolve_streams()
        
        # Helper method for writing common commands to bluemuse   
        async def execBluemuse(key, value):
            command = f'start bluemuse://setting?key={key}!value={value}'
            # command = shlex.split(command)
            _log.debug("Running command: %s", command)
            proc = await asyncio.create_subprocess_shell(command)
            await proc.wait()
            return proc
        
        # Check whether any desired signals are not yet streaming, starting
        # Bluemuse if not
        streamTypes = [stream.type() for stream in streams]
        if not all(signal in streamTypes for signal in self.signals):
            # Define commands to start Bluemuse with given preferences
            _log.debug("Starting Bluemuse")
            commands = {
                (f"{s.lower()}_enabled") : (str(s in self.signals).lower())
                for s in self.__validSignals
                }
            commands["primary_timestamp_format"] = "LSL_LOCAL_CLOCK_NATIVE"
        
            # Execute the commands
            await asyncio.gather(
                *(execBluemuse(k, v) for k, v in commands.items())
                )
            
            # Wait until all signals are streaming
            # TODO: implement
            
            
        
            
            
        else:
            _log.info("All desired signals are already streaming on LSL")
            return ()
         
        # Run the commands
        # IMPLEMENT

    def startStreaming(self):
        # Connecting to the Muse device in `self.connect` automatically starts 
        # streaming, so here we just make sure that all desired signals are
        # streaming.
        _log.info(
            "Waiting 30 seconds for all desired Muse signals to stream to"
            + "LSL."
            )
        pred = " or ".join(f"type='{x}'" for x in self.signals)
        streams = resolve_bypred(pred, minimum=len(self.signals), timeout=30)
        streamTypes = [stream.type() for stream in streams]
        if not all(signal in streamTypes for signal in self.signals):
            _log.warning(
                "Not all of the desired Muse signals are streaming to "
                + "LSL (Waited 30 seconds)."
                + f" Desired Signals: {self.signals}"
                + f" Streaming Signals: {streamTypes}"
            )
        else:
            _log.debug("All Muse signals are streaming on LSL.")
            
    def disconnect(self):
        _log.debug("Closing Bluemuse")
        command = "start bluemuse://shutdown"
        subprocess.run(command, shell=True)
    
    def stopStreaming(self):
        _log.debug("Stopping Bluemuse from streaming to LSL")
        command = "start bluemuse://stop?stopall"
        subprocess.run(command, shell=True)
