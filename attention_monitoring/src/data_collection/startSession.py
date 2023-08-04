"""Start a data collection session.

""" 
from pylsl import StreamInfo, StreamInlet, resolve_stream
import os
import sys
import io
import csv
from datetime import datetime
from attention_monitoring.src.data_collection.stimuliSetup import generateSequence
from attention_monitoring.src.data_collection.museSetup import setupMuse, endMuse
import json
import subprocess
import matlab.engine
from attention_monitoring.src.config import CONFIG
from time import sleep

def main(participantID = None):
    # TODO: refactor to use subprocess module effectively (multithreading? Need
    #       to run main control process concurrently with other processes)
    # TODO: Fix timing errors
    # TODO: implement logging using official module/methods
    # TODO: write documentation
    # TODO: fix importing of config
    # TODO: cleanup how output from matlab and LR are handled and printed
    # TODO: change filepaths to relative

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
        lastSessionID = int(lastEntry["session_id"])
        sessionID = lastSessionID + 1
    else:
        with open(log, 'w', newline="") as f:
            dictWriter = csv.DictWriter(f, fieldnames=logFields)
            dictWriter.writeheader()
        sessionID = 1
    
    # Update the log with the current session
    with open(log, "a", newline="") as f:
        dictWriter = csv.DictWriter(f, fieldnames=logFields)
        logInfo = _formatLogInfo(
            sessionID=sessionID,
            date=datetime.now().strftime("%d%m%y"),
            participantID=participantID
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
        sessionName = info["session_name"]
        return os.path.join(outputDir, sessionName + "_" + name)

    def _updateInfoFile(data):
        with open(infoFile, "r+") as f:
            fileData = json.load(f)
            fileData.update(data)
            f.seek(0)
            json.dump(fileData, f)
            f.truncate()

    def _timer(msg, period):
        def makeFrame(displayVal, _end):
            def frame():
                print(f'\r{msg}{displayVal}', end=_end)
                sleep(period)
            return frame

        def animation():
            sequence = ['-','\\','|','/']
            k = 0
            while True:
                frame = makeFrame(sequence[k], '')
                k = k + 1 if k + 1 < len(sequence) else 0
                yield frame

        lastFrame = makeFrame('DONE', '\n')
        return animation(), lastFrame

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

    # Setup the Muse device
    if CONFIG.verbose >= 2:
        print("Setting up the Muse device.")
    setupMuse(*CONFIG.muse_signals)

    # Start LabRecorder
    if CONFIG.path_to_LabRecorder != "":
        if CONFIG.verbose >= 2:
            print("Starting LabRecorder")
        proc1 = subprocess.Popen(
            os.path.realpath(CONFIG.path_to_LabRecorder),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
            )    

    # Run the experiment
    if CONFIG.verbose >= 1:
        print("Running experiment in MATLAB. This may take a few moments ...")
        animation, lastFrame = _timer("Waiting for MATLAB to start: ", 0.1)
        while not future.done():
            next(animation)()
        lastFrame()
    eng = future.result()
    p = eng.genpath(CONFIG.projectRoot)
    eng.addpath(p, nargout=0)
    data = eng.gradCPT(
        infoFile,
        'verbose', CONFIG.verbose,
        'streamMarkersToLSL', CONFIG.stream_markers_to_lsl,
        'recordLSL', CONFIG.record_lsl,
        'tcpAddress', CONFIG.tcp_address,
        'tcpPort', CONFIG.tcp_port,
        )

    # Close the Muse device
    if CONFIG.verbose >= 2:
        print("Closing the Muse device.")
    endMuse()

    # Close LabRecorder
    if CONFIG.path_to_LabRecorder != "":
        if CONFIG.verbose >= 2:
            print("Closing LabRecorder.")
        proc1.kill()
        out, err = proc1.communicate()
    
    print("\n======LABREC======\n")
    print("===OUT===\n")
    print(out)
    print("\n===ERR===\n")
    print(err)
    print("\n==================\n")
    print(data)

    return infoFile
                    
                                               
                                                                           
                                                                                                       
                                                                                                       
                                                                                                       
        


def _formatLogInfo(sessionName=None, sessionID=None, date=None,
                   participantID=None):
    """Format info about a data collection session to be entered in the log.

    All values are formatted as `str` and returned in a `dict`. If any values
    are `None`, the corresponding value in the returned `dict` is `""`.

    Parameters
    ----------
    sessionName : str, optional
        The name assigned to the session. Must follow the convention:
        "S[sessionID]_[ddmmyy]" where [sessionID] is `sessionID` and [ddmmyy]
        is the date. This can optionally be followed by "_P[participantID]",
        where [participantID] is `participantID`.
    sessionID : int or str, optional
        The numerical ID assigned to this session.
    date : str, optional
        The date of this session, in the format `ddmmyy`.
    participantID : int or str, optional
        The numerical ID assigned to the participant in this session.

    Returns
    -------
    dict
        Info about data collection session formatted for entry in the log.
    
    """

    _sessionName = sessionName
    _sessionID = None if sessionID is None else str(sessionID)
    _date = date
    _participantID = None if participantID is None else str(participantID)

    # Try to specify unknown values by extrapolating from known values
    if (
        sessionName is None
        and all(x is not None for x in [sessionID, date])
        ):
        # Create sessionName from other info
        _sessionName = f"S{_sessionID}_{_date}"
        if (participantID is not None):
            _sessionName = _sessionName + f"_P{_participantID}"
    elif (
        sessionName is not None
        and all(x is none for x in [sessionID, date, participantID])
        ):
        # Use sessionName to specify other info
        expandedName = _sessionName.split("_")
        _sessionID = expandedName[0].lstrip("S")
        _date = expandedName[1]
        if (len(expandedName) > 2):
            _participantID = expandedName[2].lstrip("P")

    # Return values in a dict
    out = {
        "session_name" : _sessionName,
        "session_id" : _sessionID,
        "date" : _date,
        "participant_id" : _participantID
        }
    for key, value in out.items():
        if value is None:
            out[key] = ""

    return out
