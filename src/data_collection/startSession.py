"""Start a data collection session.

""" 
from pylsl import StreamInfo, StreamInlet, resolve_stream
import os
import csv
from datetime import datetime
from stimuliSetup import generateSequence
from museSetup import setupMuse

def main(participantId = None):

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
        lastsessionId = int(lastEntry[logHeaders.index("session_id")])
        sessionId = lastsessionId + 1
    else:
        with open(log, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(logHeaders)
        sessionId = 0

    # Update the log with current session's info
    currentSession = SessionInfo(
        sessionId=sessionId,
        date=datetime.now().strftime("%d%m%y"),
        participantId=participantId
        )
    with open(log, "a") as f:
        writer = csv.writer(f)
        writer.writerow(currentSession.asStrings())

    # Make a folder and info file for the current session
    outputDir = os.path.join(DATA_DIR, currentSession.sessionName)
    os.mkdir(outputDir)

    with open(os.path.join(outputDir, "info.csv"), "w") as f:
        writer = csv.writer(f)
        for i in range(len(logHeaders)):
            writer.writerow([logHeaders[i], currentSession.asStrings()[i]])

    def newSessionFile(name):
        return os.path.join(outputDir, currentSession.sessionName + "_" + name)

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

    # Setup the Muse device
    setupMuse(*museSignals)


class SessionInfo:
    """Stores info about a data collection section.

    Parameters
    ----------
    sessionName : str, optional
        The name assigned to the session. Must follow the convention:
        "S[sessionId]_[ddmmyy]" where [sessionId] is `sessionId` and [ddmmyy]
        is the date. This can optionally be followed by "_P[participantId]",
        where [participantId] is `participantId`.
    sessionId : int or str, optional
        The numerical ID assigned to this session.
    date : str, optional
        The date of this session, in the format `ddmmyy`.
    participantId : int or str, optional
        The numerical ID assigned to the participant in this session.

    Attributes
    ----------
    sessionName : str or None
        The name assigned to the session. Follows the convention:
        "S[sessionId]_[ddmmyy]" where [sessionId] is `sessionId` and [ddmmyy]
        is the date. This can optionally be followed by "_P[participantId]",
        where [participantId] is `participantId`.
    sessionId : int or None
        The numerical ID assigned to this session.
    date : datetime object or None
        The date of this session.
    participantId : int or None
        The numerical ID assigned to the participant in this session.
    """

    def __init__(self, sessionName=None, sessionId=None, date=None,
                 participantId=None):

        self.sessionName = (
            str(sessionName)
            if sessionName is not None
            else None)
        self.sessionId = (
            int (sessionId)
            if sessionId is not None
            else None)
        self.date = (
            datetime.strptime(date, "%d%m%y")
            if date is not None
            else None)
        self.participantId = (
            int(participantId)
            if participantId is not None
            else None)

        if (
            sessionName is None
            and all(x is not none for x in [sessionId, date])
            ):
            # Create sessionName from other info
            self.sessionName = f"S{self.sessionId}_{self.date}"
            if (participantId is not None):
                self.sessionName = self.sessionName + f"_{self.participantId}"
        elif (
            sessionName is not None
            and all(x is none for x in [sessionId, date, participantId])
            ):
            # Use sessionName to specify other info
            expandedName = self.sessionName.split("_")
            self.sessionId = int(expandedName[0].lstrip("S"))
            self.date = datetime.strptime(expandedName[1], "%d%m%y")
            if (len(expandedName[2].lstrip("P")) != 0):
                self.participantId = int(expandedName[2].lstrip("P"))
            

    def asStrings(self):
        """Return metadata formated as a list of `str`."""
        return [str(x) if x is not None else ""
                for x in [self.sessionName, self.sessionId, self.date,
                          self.participantId]]
        
    