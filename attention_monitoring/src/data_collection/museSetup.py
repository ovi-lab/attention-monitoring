import subprocess
from pylsl import StreamInfo, StreamInlet, resolve_streams, resolve_bypred
from attention_monitoring.src.config import CONFIG
import textwrap

def setupMuse(*signals):
    """Setup the Muse device to begin streaming data to LSL.

    If data is not already streaming, the Bluemuse app is launched and the user
    must manually connect the Muse and click on "Start Streaming".

    Parameters
    ----------
    signals : list of str
        The signals to obtain from the muse. Any combination of "EEG", "PPG",
        "Accelerometer", "Gyroscope". If unspecified, obtains all of these.
    """

    validSignals = ("EEG", "PPG", "Accelerometer", "Gyroscope")
    if len(signals) > 0:
        if not all(signal in validSignals for signal in signals):
            raise Exception("Invalid signal.")
        targetSignals = signals
    else:
        targetSignals = validSignals

    streams = resolve_streams()

    # Check whether any desired signals are not yet streaming
    streamTypes = [stream.type() for stream in streams]
    if not all(signal in streamTypes for signal in targetSignals):
        # Start bluemuse and enable desired signals to stream
        keys = [
            "primary_timestamp_format",
            *[signal.lower() + "_enabled" for signal in validSignals]
            ]
        values = [
            "LSL_LOCAL_CLOCK_NATIVE",
            *[str(signal in targetSignals).lower() for signal in validSignals]
            ]
        commands = [
            f'start bluemuse://setting?key={keys[i]}!value={values[i]}'
            for i in range(len(keys))
            ]
        print(commands)
        if CONFIG.verbose >= 3:
            print("Starting Bluemuse.")
        for command in commands:
            subprocess.run(command, shell=True)
        
        # Wait until all desired signals are streaming
        if CONFIG.verbose >= 3:
            msg = textwrap.wrap(
                "Waiting 30 seconds for all desired Muse signals to stream to"
                + "LSL.",
                width=80
            )
            print("\n".join(msg))
        pred = " or ".join(f"type='{x}'" for x in targetSignals)
        streams = resolve_bypred(pred, minimum=len(targetSignals), timeout=30)
        streamTypes = [stream.type() for stream in streams]
        if not all(signal in streamTypes for signal in targetSignals):
            if CONFIG.verbose >= 1:
                label = "WARNING: "
                msg = [
                    "Not all of the desired Muse signals are streaming to "
                    + "LSL (Waited 30 seconds).",
                    f"Desired Signals: {targetSignals}",
                    f"Streaming Signals: {streamTypes}"
                ]
                for text in msg:
                    lines = textwrap.wrap(text, width=80 - len(label))
                    print("\n".join([label + line for line in lines]))
        elif CONFIG.verbose >= 3:
            print("All Muse signals are streaming on LSL.")


def endMuse():
    """Stop streaming Muse data to LSL and close the bluemuse program."""

    commands = ["start bluemuse://stop?stopall", "start bluemuse://shutdown"]
    for command in commands:
        subprocess.run(command, shell=True)