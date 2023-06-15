"""Start a data collection session.

""" 
from pylsl import StreamInfo, StreamInlet, resolve_stream
import os
import csv
from datetime import datetime
from stimuliSetup import generateSequence
from museSetup import setupMuse
import json

def main(participant_id = None):

    # Constants
    FULL_RUN_SEQUENCE_LENGTH = 1
    PRACTICE_RUN_SEQUENCE_LENGTH = 1
    NUM_FULL_RUNS = 3
    DO_PRACTICE_RUN = True
    DATA_DIR = os.path.abspath("data/gradCPT_sessions")

    museSignals = ["EEG", "PPG", "Accelerometer", "Gyroscope"]
    log = os.path.join(DATA_DIR, "log.csv")

    # Determine the current session ID by checking the log
    logHeaders = ["session_name", "session_id", "date", "participant_id"]
    if (os.path.isfile(log)):
        with open(log, 'r') as f:
            reader = csv.reader(f)
            for entry in reader: pass
            lastEntry = entry
        lastsession_id = int(lastEntry[logHeaders.index("session_id")])
        session_id = lastsession_id + 1
    else:
        with open(log, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(logHeaders)
        session_id = 0

    # Update the log with current session's info
    info = SessionInfo(
        session_id=session_id,
        date=datetime.now().strftime("%d%m%y"),
        participant_id=participant_id
        )
    with open(log, "a") as f:
        writer = csv.writer(f)
        logValues = info.asStringDict()
        writer.writerow([logValues[label] for label in logHeaders])

    # Make a folder and info file for the current session
    outputDir = os.path.join(DATA_DIR, info.session_name)
    infoFile = os.path.join(outputDir, "info.json")
    os.mkdir(outputDir)
    with open(infoFile, "w") as f:
        json.dump(info.asStringDict(), f)

    def newSessionFile(name):
        return os.path.join(outputDir, info.session_name + "_" + name)

    # Generate the stimuli sequences to be used for gradCPT runs, and specify
    # order of runs in csv file
    runsFile = newSessionFile("runs.csv")
    with open(runsFile, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["stimSeqFile"])

        if (DO_PRACTICE_RUN):
            name = newSessionFile("stimuli_sequence_practice")
            generateSequence(name, outputDir, PRACTICE_RUN_SEQUENCE_LENGTH) 
            writer.writerow([name])

        for i in range(1, NUM_FULL_RUNS + 1):
            name = newSessionFile(f"stimuli_sequence_run{i}")
            generateSequence(name, outputDir, FULL_RUN_SEQUENCE_LENGTH)
            writer.writerow([name])
    with open(infoFile, "a") as f:
        json.dump({"runs_file" : runsFile})

    # Setup the Muse device
    setupMuse(*museSignals)


class SessionInfo:
    """Stores info about a data collection section.

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

    Attributes
    ----------
    session_name : str or None
        The name assigned to the session. Follows the convention:
        "S[session_id]_[ddmmyy]" where [session_id] is `session_id` and [ddmmyy]
        is the date. This can optionally be followed by "_P[participant_id]",
        where [participant_id] is `participant_id`.
    session_id : str or None
        The numerical ID assigned to this session.
    date : str or None
        The date of this session, in the format `ddmmyy`.
    participant_id : str or None
        The numerical ID assigned to the participant in this session.
    """

    def __init__(self, session_name=None, session_id=None, date=None,
                 participant_id=None):

        self.session_name = (
            session_name
            if session_name is not None
            else None)
        self.session_id = (
            str(session_id)
            if session_id is not None
            else None)
        self.date = (
            date
            if date is not None
            else None)
        self.participant_id = (
            str(participant_id)
            if participant_id is not None
            else None)

        if (
            session_name is None
            and all(x is not none for x in [session_id, date])
            ):
            # Create session_name from other info
            self.session_name = f"S{self.session_id}_{self.date}"
            if (participant_id is not None):
                self.session_name = self.session_name + f"_{self.participant_id}"
        elif (
            session_name is not None
            and all(x is none for x in [session_id, date, participant_id])
            ):
            # Use session_name to specify other info
            expandedName = self.session_name.split("_")
            self.session_id = expandedName[0].lstrip("S")
            self.date = expandedName[1]
            if (len(expandedName) > 2):
                self.participant_id = expandedName[2].lstrip("P")
            
    def asStringDict(self):
        """Return a `dict` containing the session info.
        
        All values are formatted as `str`. If any values are `None`, the
        corresponding value in the return `dict` is `""`.
        """
        out =  {
            "session_name" : self.session_name,
            "session_id" : self.session_id,
            "date" : self.date,
            "participant_id" : self.participant_id
        }

        for key, value in out.items():
            if value is None:
                out[key] = ""

        return out
        
    