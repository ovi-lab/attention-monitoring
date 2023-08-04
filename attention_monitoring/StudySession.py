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
    # Warning: The data returned by instances of `SessionLog` are undefined and
    # may result in unexpected behaviour if:
    #  - The content of the log file is changed externally
    #  - Multiple instances of `SessionLog` exist concurrently

    __rowCountCol = "row_Count"
    
    def __init__(self, filePath):
        self.__path = filePath

        dtypes = {field:pl.Utf8 for field in self.logFields}
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
                dictWriter = csv.DictWriter(f, fieldnames=self.logFields)
                dictWriter.writeheader()
                
    @property
    @classmethod
    def logFields(cls):
        return ["session_name", "session_id", "date", "participant_id"]

    @property
    def path(self):
        return self.__path

    def __exists(self):
        return os.path.isfile(self.path)
    
    def read(self, *lines):
        if not self.__exists():
            raise FileNotFoundError(
                errno.ENOENT, "The log file does not exist.", self.path
                )
            
        if len(lines) == 0:
            data = self.__log
        else:
            lastLineNum = self.__log.max()[self.__rowCountCol][0]
            _lines = [n if n >= 0 else lastLineNum + 1 + n for n in lines]

            # Assume row numbers are unique
            data = df.filter(pl.col(self.__rowCountCol).is_in(_lines))
            
            selectedLines = data[self.__rowCountCol].to_list()
            unSelectedLines = [x for x in _lines if x not in selectedLine]
            if len(unSelectedLines) > 0:
                raise ValueError(
                    "The following specified lines were not found:"
                    + f"{unSelectedLines}"
                    )

        data = data.select(pl.all().exclude(self.__rowCountCol))
        data = data.to_dict(as_series=False)
        return data


    def addLine(self, **items):
        """Add a line to the end of the log.

        Data to include in the line are specified as keyword arguments, where
        the argument is the value to add and the kay is the name of the 
        corresponding log field. For any unspecified fields, an attempt is made
        to extrapolate values from the specified fields. If this cannot be 
        done, the value of the field is left empty in the log.

        Parameters
        ----------
        session_name : str, optional
            The name assigned to the session. Must follow the convention:
            "S[session_id]_[ddmmyy]" where [session_id] is `session_id` and [ddmmyy]
            is the date. This can optionally be followed by "_P[participantID]",
            where [participantID] is `participantID`.
        session_id : int or str, optional
            The numerical ID assigned to this session.
        date : str, optional
            The date of this session, in the format `ddmmyy`.
        participant_id : int or str, optional
            The numerical ID assigned to the participant in this session.

        """
        if not self.__exists():
            raise FileNotFoundError(
                errno.ENOENT, "The log file does not exist.", self.path
                )
            
        invalidKeys = [k for k in items.keys() if not k in self.logFields]
        if len(invalidKeys) > 0:
            raise ValueError(
                f"The specified key(s) '{invalidKeys}' are not valid fields. "
                + f"Valid fields are: {self.logFields}"
                )
            
        line = self.__formatLogInfo(**items)
        
        # The file (self.path) and the copy of the log stored in self.__log 
        # must always contain the same data.
        
        # Update the file
        with open(self.path, "a", newline="") as f:
            dictWriter = csv.DictWriter(f, fieldnames=self.logFields)
            dictWriter.writerow(line)
            
        # Update the stored copy of the log
        lastLineNum = self.__log.max()[self.__rowCountCol][0]
        thisLine = pl.DataFrame(line).with_row_count(
            name=self.__rowCountCol,
            offset=lastLineNum+1
            )
        self.__log = self.__log.vstack(thisLine)
        
        

    @classmethod
    def __formatLogInfo(cls, session_name=None, session_id=None, date=None,
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
            and all(x is None for x in [session_id, date, participant_id])
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


        
