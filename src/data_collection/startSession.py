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
import matlab.engine

def main(participant_id = None):

    # Preferences
    MUSE_SIGNALS = ["EEG", "PPG", "Accelerometer", "Gyroscope"]
    VERBOSE = 3
    STREAM_MARKERS_TO_LSL = False
    RECORD_LSL = False
    TCP_ADDRESS = 'localhost'
    TCP_PORT = 22345

    # Constants
    NUM_FULL_BLOCKS = 2
    DO_PRACTICE_BLOCK = False
    STIM_TRANSITION_TIME_MS = 800 # milliseconds
    STIM_STATIC_TIME_MS = 400 # milliseconds
    STIM_DIAMETER = 1000
    FULL_BLOCK_SEQUENCE_LENGTH = 50
    PRACTICE_BLOCK_SEQUENCE_LENGTH = 10
    PRE_FULL_BLOCK_BREAK_TIME = 30 # seconds
    PRE_PRACTICE_BLOCK_BREAK_TIME = 5 # seconds
    ROOT = os.path.abspath("C:/Users/HP User/source/repos/attention-monitoring")
    DATA_DIR = os.path.abspath("../data/gradCPT_sessions")
    STIMULI_DIR = os.path.abspath("../data/stimuli")

    # TODO: change path to data dir to automatically get the path of the current file
    
    log = os.path.join(DATA_DIR, "log.csv")

    # # Start MATLAB engine asynchronously
    # future = matlab.engine.start_matlab(background=True)

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
            "session_dir" : outputDir,
            "num_full_blocks" : NUM_FULL_BLOCKS,
            "do_practice_block" : DO_PRACTICE_BLOCK,
            "stim_transition_time_ms" : STIM_TRANSITION_TIME_MS,
            "stim_static_time_ms" : STIM_STATIC_TIME_MS,
            "stim_diameter" : STIM_DIAMETER,
            "full_block_sequence_length" : FULL_BLOCK_SEQUENCE_LENGTH,
            "practice_block_sequence_length" : PRACTICE_BLOCK_SEQUENCE_LENGTH,
            "muse_signals" : MUSE_SIGNALS
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

    # Generate the stimuli sequences to be used for gradCPT blocks, and specify
    # order of blocks in csv file
    blocksFile = _newSessionFile("blocks.csv")
    blocksFileFields = [
        "block_name",
        "pre_block_msg",
        "pre_block_wait_time",
        "stim_sequence_file",
        "data_file"
        ]
    with open(blocksFile, "w", newline="") as f:
        dictWriter = csv.DictWriter(f, fieldnames=blocksFileFields)
        dictWriter.writeheader()

        if (DO_PRACTICE_BLOCK):
            blockName = "practice_block"
            SSFName = _newSessionFile(blockName + "_stim_sequence")
            generateSequence(
                SSFName,
                STIMULI_DIR,
                PRACTICE_BLOCK_SEQUENCE_LENGTH
            )
            msg = (
                f"Starting practice block in {PRE_PRACTICE_BLOCK_BREAK_TIME} "
                + "seconds."
            )
            dictWriter.writerow({
                "block_name" : blockName,
                "pre_block_msg" : msg,
                "pre_block_wait_time" : PRE_PRACTICE_BLOCK_BREAK_TIME,
                "stim_sequence_file" : SSFName + ".csv",
                "data_file" : ""
            })

        for i in range(1, NUM_FULL_BLOCKS + 1):
            blockName = f"full_block_{i}"
            SSFName = _newSessionFile(blockName + "_stim_sequence")
            generateSequence(
                SSFName,
                STIMULI_DIR,
                FULL_BLOCK_SEQUENCE_LENGTH
            )
            msg = (
                f"Starting block {i} in {PRE_FULL_BLOCK_BREAK_TIME} "
                + "seconds."
            )
            dictWriter.writerow({
                "block_name" : blockName,
                "pre_block_msg" : msg,
                "pre_block_wait_time" : PRE_FULL_BLOCK_BREAK_TIME,
                "stim_sequence_file" : SSFName + ".csv",
                "data_file" : ""
            })
    _updateInfoFile({"blocks_file" : blocksFile})

    print(infoFile)

    # # Setup the Muse device
    # setupMuse(*MUSE_SIGNALS)

    # Start LabRecorder
    # TODO: don't hardcode path to LabRecorder
    subprocess.run(os.path.abspath('C:/Users/HP User/Downloads/LabRecorder-1.16.4-Win_amd64/LabRecorder/LabRecorder.exe'), shell=True)

    # # Run the experiment
    # if VERBOSE >= 1:
    #     print("Running experiment in MATLAB. This may take a few moments ...")
    # eng = future.result()
    # data = eng.gradCPT(
    #     infoFile,
    #     'verbose', VERBOSE,
    #     'streamMarkersToLSL', STREAM_MARKERS_TO_LSL,
    #     'recordLSL', RECORD_LSL,
    #     'tcpAddress', TCP_ADDRESS,
    #     'tcpPort', TCP_PORT
    # )    
    


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
            _session_name = _session_name + f"_P{_participant_id}"
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
    main(participant_id = 1)