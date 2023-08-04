from abc import ABC, abstractmethod
import os
import csv
import errno

from attention_monitoring.src.config import CONFIG

class StudySession(ABC):

    def __init__(self, participantID = None):
        
        self.participantID = participantID

        # Define some useful folder paths, creating the folders if they don't 
        # already exist
        self.__DATA_DIR = os.path.join(
            CONFIG.projectRoot, "src", "data", self.studyType
            )
        self.__SESSION_DATA_DIR = os.path.join(self.__DATA_DIR, "session_data")
        self.__STIMULI_DIR = os.path.join(self.__DATA_DIR, "stimuli")
        os.mkdirs(self.__SESSION_DATA_DIR, exist_ok=True)
        os.mkdirs(self.__STIMULI_DIR, exist_ok=True)





    @property
    @abstractmethod
    def studyType(self):
        pass

    @abstractmethod
    def runStudy(self):
        pass

class SessionLog:

    __logFields = ["session_name", "session_id", "date", "participant_id"]
    __rowCountCol = "row_Count"
    
    def __init__(self, filePath):
        self.__path = filePath

        dtypes = {field:pl.Utf8 for field in self.__logFields}
        dtype[self.__rowCountCol] = pl.Int32

        if self.__exists():
            self.__log = pl.read_csv(
                self.path, 
                dtypes=dtypes, 
                row_count_name=self.__rowCountCol
                )
        else:
            self.__log = pl.DataFrame(schema=dtypes)
            with open(log, 'w', newline="") as f:
                dictWriter = csv.DictWriter(f, fieldnames=logFields)
                dictWriter.writeheader()

    @property
    def path(self):
        return self.__path

    def __exists(self):
        return os.path.isfile(self.path)
    
    def read(self, *lines):
        if len(lines) == 0:
            data = self.__log
        else:
            lastLineNum = self.__log.max()[self.__rowCountCol][0]
            _lines = [n if n >= 0 else lastLineNum + 1 + n for n in lines]

            data = df.filter(pl.col(self.__rowCountCol).is_in(_lines))

            if not all()

        data = data.select(pl.all().exclude(self.__rowCountCol))
        data = data.to_dict(as_series=False)
        return data


    def update(self, ):
        
        pass

    def __formatLogInfo(sessionName=None, sessionID=None, date=None,
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

# class SessionLog:

#     __logFields = ["session_name", "session_id", "date", "participant_id"]
    
#     def __init__(self, filePath):
#         self.__path = filePath

#     @property
#     def path(self):
#         return self.__path

#     def exists(self):
#         return os.path.isfile(self.path)
    
#     def read(self, *lines):
#         if not self.exists():
#             raise FileNotFoundError(
#                 errno.ENOENT, "The log file does not exist.", dataFile
#                 )

#         with open(self.path, "r") as f:
#             dictReader = csv.DictReader(f, fieldnames=self.__logFields)
#             for row in dictReader:
#                 if lines is None or dictReader.line_num in lines:

        

#     def update(self):
#         pass


        
