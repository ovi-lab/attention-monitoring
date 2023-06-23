"""Start a data collection session.

""" 
from pylsl import StreamInfo, StreamInlet, resolve_stream
import os
import csv
from datetime import datetime
from stimuliSetup import generateSequence
from museSetup import setupMuse
import json
import subprocess

def main(participant_id = None):

    # Constants
    STIM_TRANSITION_TIME_MS = 800 # milliseconds
    STIM_STATIC_TIME_MS = 400 # milliseconds
    FULL_RUN_SEQUENCE_LENGTH = 10
    PRACTICE_RUN_SEQUENCE_LENGTH = 1
    NUM_FULL_RUNS = 1
    DO_PRACTICE_RUN = False
    DATA_DIR = os.path.abspath("../data/gradCPT_sessions")
    STIMULI_DIR = os.path.abspath("../data/stimuli")

    museSignals = ["EEG", "PPG", "Accelerometer", "Gyroscope"]
    log = os.path.join(DATA_DIR, "log.csv")

    # Determine the current session ID by checking the log if it exists, or
    # creating a new log if it does not
    logFields = ["session_name", "session_id", "date", "participant_id"]
    if (os.path.isfile(log)):
        with open(log, 'r') as f:
            dictReader = csv.DictReader(f, fieldnames=logFields)
            for entry in dictReader: pass
            lastEntry = entry
        last_session_id = int(lastEntry["session_id"])
        session_id = last_session_id + 1
    else:
        with open(log, 'w', newline="") as f:
            dictWriter = csv.DictWriter(f, fieldnames=logFields)
            dictWriter.writeheader()
        session_id = 1
    
    # Update the log with the current session
    with open(log, "a", newline="") as f:
        dictWriter = csv.DictWriter(f, fieldnames=logFields)
        logInfo = _formatLogInfo(
            session_id=session_id,
            date=datetime.now().strftime("%d%m%y"),
            participant_id=participant_id
        )
        dictWriter.writerow(logInfo)

    # Make a folder and info file for the current session
    outputDir = os.path.join(DATA_DIR, logInfo["session_name"])
    infoFile = os.path.join(outputDir, "info.json")
    os.mkdir(outputDir)
    with open(infoFile, "w") as f:
        info = {}
        info.update(logInfo)
        info.update({
            "num_full_runs" : NUM_FULL_RUNS,
            "do_practice_run" : DO_PRACTICE_RUN,
            "stim_transition_time_ms" : STIM_TRANSITION_TIME_MS,
            "stim_static_time_ms" : STIM_STATIC_TIME_MS,
            "full_run_sequence_length" : FULL_RUN_SEQUENCE_LENGTH,
            "practice_run_sequence_length" : PRACTICE_RUN_SEQUENCE_LENGTH,
            "muse_signals" : museSignals
        })
        json.dump(info, f)
    
    def _newSessionFile(name):
        session_name = info["session_name"]
        return os.path.join(outputDir, session_name + "_" + name)

    def _updateInfoFile(data):
        with open(infoFile, "r+") as f:
            fileData = json.load(f)
            fileData.update(data)
            f.seek(0)
            json.dump(fileData, f)
            f.truncate()

    # Generate the stimuli sequences to be used for gradCPT runs, and specify
    # order of runs in csv file
    blocksFile = _newSessionFile("blocks.csv")
    with open(blocksFile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["stimSeqFile"])

        if (DO_PRACTICE_RUN):
            name = _newSessionFile("stimuli_sequence_practice")
            generateSequence(name, STIMULI_DIR, PRACTICE_RUN_SEQUENCE_LENGTH) 
            writer.writerow([name + ".csv"])

        for i in range(1, NUM_FULL_RUNS + 1):
            name = _newSessionFile(f"stimuli_sequence_run{i}")
            generateSequence(name, STIMULI_DIR, FULL_RUN_SEQUENCE_LENGTH)
            writer.writerow([name + ".csv"])
    _updateInfoFile({"blocks_file" : blocksFile})

    # Setup the Muse device
    setupMuse(*museSignals)

    # Run the experiment
    # subprocess.run(["Python", "gradCPT.py", "--infoFile", infoFile])
    print(infoFile)


def _formatLogInfo(session_name=None, session_id=None, date=None,
                   participant_id=None):
    """Format info about a data collection session to be entered in the log.

    All values are formatted as `str` and returned in a `dict`. If any values
    are `None`, the corresponding value in the returned `dict` is `""`.

    Parameters
    ----------
    session_name : str, optional
        The name assigned to the session. Must follow the convention:
        "S[session_id]_[ddmmyy]" where [session_id] is `session_id` and [ddmmyy]
        is the date. This can optionally be followed by "_P[participant_id]",
        where [participant_id] is `participant_id`.
    session_id : int or str, optional
        The numerical ID assigned to this session.
    date : str, optional
        The date of this session, in the format `ddmmyy`.
    participant_id : int or str, optional
        The numerical ID assigned to the participant in this session.

    Returns
    -------
    dict
        Info about data collection session formatted for entry in the log.
    
    """

    _session_name = session_name
    _session_id = None if session_id is None else str(session_id)
    _date = date
    _participant_id = None if participant_id is None else str(participant_id)

    # Try to specify unknown values by extrapolating from known values
    if (
        session_name is None
        and all(x is not None for x in [session_id, date])
        ):
        # Create session_name from other info
        _session_name = f"S{_session_id}_{_date}"
        if (participant_id is not None):
            _session_name = _session_name + f"_{_participant_id}"
    elif (
        session_name is not None
        and all(x is none for x in [session_id, date, participant_id])
        ):
        # Use session_name to specify other info
        expandedName = _session_name.split("_")
        _session_id = expandedName[0].lstrip("S")
        _date = expandedName[1]
        if (len(expandedName) > 2):
            _participant_id = expandedName[2].lstrip("P")

    # Return values in a dict
    out = {
        "session_name" : _session_name,
        "session_id" : _session_id,
        "date" : _date,
        "participant_id" : _participant_id
    }
    for key, value in out.items():
            if value is None:
                out[key] = ""

    return out

if __name__ == "__main__":
    main()