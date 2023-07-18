"""Start a data collection session.

""" 
from pylsl import StreamInfo, StreamInlet, resolve_stream
import os
import sys
import csv
from datetime import datetime
from stimuliSetup import generateSequence
from museSetup import setupMuse, endMuse
import json
import subprocess
import matlab.engine
from attention_monitoring.src.config import CONFIG

def main(participant_id = None):
    # TODO: refactor to use subprocess module effectively (multithreading? Need
    #       to run main control process concurrently with other processes)
    # TODO: Fix timing errors
    # TODO: implement logging using official module/methods
    # TODO: write documentation
    # TODO: fix importing of config

    DATA_DIR = os.path.join(CONFIG.projectRoot, "src", "data", "gradCPT_sessions")
    STIMULI_DIR = os.path.join(CONFIG.projectRoot, "src", "data", "stimuli")
    
    log = os.path.join(DATA_DIR, "log.csv")

    # Start MATLAB engine asynchronously
    future = matlab.engine.start_matlab(background=True)

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
        configVals = [
            "num_full_blocks", "do_practice_block", "stim_transition_time_ms",
            "stim_static_time_ms", "stim_diameter",
            "full_block_sequence_length", "muse_signals"
            ]
        info = {}
        info.update(logInfo)
        info.update({"session_dir" : outputDir})
        info.update({val : getattr(CONFIG, val) for val in configVals})
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
        "block_name", "pre_block_msg", "pre_block_wait_time",
        "stim_sequence_file", "data_file"
        ]
    with open(blocksFile, "w", newline="") as f:
        dictWriter = csv.DictWriter(f, fieldnames=blocksFileFields)
        dictWriter.writeheader()

        # Practice block
        if (CONFIG.do_practice_block):
            blockName = "practice_block"
            stimSeqFile = _newSessionFile(blockName + "_stim_sequence.csv")
            generateSequence(
                stimSeqFile,
                STIMULI_DIR,
                CONFIG.practice_block_sequence_length
                )
            preBlockMsg = (
                "Starting practice block in "
                + f"{CONFIG.pre_practice_block_break_time} seconds."
                )
            dictWriter.writerow({
                "block_name" : blockName,
                "pre_block_msg" : preBlockMsg,
                "pre_block_wait_time" : CONFIG.pre_practice_block_break_time,
                "stim_sequence_file" : stimSeqFile,
                "data_file" : ""
                })

        # Non-practice blocks
        for i in range(1, CONFIG.num_full_blocks + 1):
            blockName = f"full_block_{i}"
            stimSeqFile = _newSessionFile(blockName + "_stim_sequence.csv")
            generateSequence(
                stimSeqFile,
                STIMULI_DIR,
                CONFIG.full_block_sequence_length
                )
            preBlockMsg = (
                f"Starting block {i} in {CONFIG.pre_full_block_break_time} "
                + "seconds."
                )
            dictWriter.writerow({
                "block_name" : blockName,
                "pre_block_msg" : preBlockMsg,
                "pre_block_wait_time" : CONFIG.pre_full_block_break_time,
                "stim_sequence_file" : stimSeqFile,
                "data_file" : ""
                })
    _updateInfoFile({"blocks_file" : blocksFile})

    if CONFIG.verbose == 2:
        print(f"Info file for this session: {infoFile}")
    elif CONFIG.verbose >= 3:
        msg = [
            "\nStarting experiment:",
            *[f"|   {key} : {value}" for key, value in info.items()]
        ]
        print("\n".join(msg))

    # # Setup the Muse device
    # if CONFIG.verbose >= 2:
    #     print("Setting up the Muse device.")
    # setupMuse(*CONFIG.muse_signals)

    # Start LabRecorder
    if CONFIG.path_to_LabRecorder != "":
        if CONFIG.verbose >= 2:
            print("Starting LabRecorder")
        subprocess.run(os.path.realpath(CONFIG.path_to_LabRecorder))

    # Run the experiment
    if CONFIG.verbose >= 1:
        print("Running experiment in MATLAB. This may take a few moments ...")
    eng = future.result()
    p = eng.genpath(CONFIG.projectRoot)
    eng.addpath(p, nargout=0)
    data = eng.gradCPT(
        infoFile,
        'verbose', CONFIG.verbose,
        'streamMarkersToLSL', CONFIG.stream_markers_to_lsl,
        'recordLSL', CONFIG.record_lsl,
        'tcpAddress', CONFIG.tcp_address,
        'tcpPort', CONFIG.tcp_port
        )

    # Close the Muse device
    if CONFIG.verbose >= 2:
        print("Closing the Muse device.")
    endMuse()


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
    main(*sys.argv[1:])