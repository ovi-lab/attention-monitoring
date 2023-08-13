# TODO: still needs a lot of fixing up

import subprocess
import logging
from pylsl import StreamInfo, StreamInlet, resolve_streams, resolve_bypred
import textwrap

from ._eeg_device import EEGDevice
from attention_monitoring.src.config import CONFIG

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
        command = "start bluemuse://shutdown"
        subprocess.run(command, shell=True)
    
    def stopStreaming(self):
        command = "start bluemuse://stop?stopall"
        subprocess.run(command, shell=True)
