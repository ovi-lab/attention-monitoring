# TODO: still needs a lot of fixing up

import subprocess
from pylsl import StreamInfo, StreamInlet, resolve_streams, resolve_bypred
import textwrap

import EEGDevice
from attention_monitoring.src.config import CONFIG

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
                "secondary_timestamp_format",
                *[
                    signal.lower() + "_enabled" 
                    for signal in self.__validSignals
                    ]
                ]
            values = [
                "LSL_LOCAL_CLOCK_NATIVE",
                "LSL_LOCAL_CLOCK_BLUEMUSE",
                *[
                    str(signal in self.signals).lower()
                    for signal in self.__validSignals
                    ]
                ]
            commands = [
                f'start bluemuse://setting?key={keys[i]}!value={values[i]}'
                for i in range(len(keys))
                ]

            if CONFIG.verbose >= 3:
                print("Starting Bluemuse.")
            for command in commands:
                subprocess.run(command, shell=True) 

            # Connect to the Muse device
            if CONFIG.verbose >= 3:
                print("Connecting to Muse device")
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
        if CONFIG.verbose >= 3:
            msg = textwrap.wrap(
                "Waiting 30 seconds for all desired Muse signals to stream to"
                + "LSL.",
                width=80
            )
            print("\n".join(msg))
        pred = " or ".join(f"type='{x}'" for x in self.signals)
        streams = resolve_bypred(pred, minimum=len(self.signals), timeout=30)
        streamTypes = [stream.type() for stream in streams]
        if not all(signal in streamTypes for signal in self.signals):
            if CONFIG.verbose >= 1:
                label = "WARNING: "
                msg = [
                    "Not all of the desired Muse signals are streaming to "
                    + "LSL (Waited 30 seconds).",
                    f"Desired Signals: {self.signals}",
                    f"Streaming Signals: {streamTypes}"
                ]
                for text in msg:
                    lines = textwrap.wrap(text, width=80 - len(label))
                    print("\n".join([label + line for line in lines]))
        elif CONFIG.verbose >= 3:
            print("All Muse signals are streaming on LSL.")