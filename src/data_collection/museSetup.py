import subprocess
from pylsl import StreamInfo, StreamInlet, resolve_stream, resolve_bypred

def main(*signals):
    """
    Setup the Muse device to begin streaming data to LSL.

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

    streams = resolve_stream()

    # Check whether any desired signals are not yet streaming
    if not all(stream.type() in targetSignals for stream in streams):
        # Start bluemuse and enable desired signals to stream
        for signal in validSignals:
            key = signal.lower() + "_enabled"
            value = str(signal in targetSignals).lower()
            subprocess.run(f'start bluemuse://setting?key={key}!value={value}',
                shell=True)
        
        # Wait until all desired signals are streaming
        pred = " or ".join(f"type='{x}'" for x in targetSignals)
        streams = resolve_bypred(pred, minimum=len(targetSignals))

