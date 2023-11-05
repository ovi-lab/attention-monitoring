from abc import abstractmethod
import os
import re
from typing import Any

from ._study import StudyItem

# TODO: add documentation for all classes

class StudySession(StudyItem):
    def __init__(self, *args, **kwargs):
        self._PARENT_DIR_ = os.path.join(self._STUDY_DATA_DIR, "sessions")
        
        super().__init__(*args, **kwargs)
        
    @property
    def _PARENT_DIR(self) -> str:
        return self._PARENT_DIR_
    
    @staticmethod
    def _makeItemName(
            id: int|str,
            date: str,
            participant_id: int|str|None,
            parent_dir: str|None = None
            ) -> str:
        _pID = "unspecified" if participant_id is None else participant_id
        participantDir = f"p_{_pID}"
        
        try:
            it = os.scandir(os.path.join(parent_dir, participantDir))
        except FileNotFoundError as E:
            sessionNum = 1
        else:
            sessionNums = []
            for entry in it:
                match = re.match(r"(?<=s_)\d+", entry.name)
                if entry.is_dir() and match is not None:
                    sessionNums.append(int(match.group()[0]))
            sessionNum = max(sessionNums, default=0) + 1          
        finally:
            it.close()
            name = os.path.join(
                participantDir,
                _nameItem("s", f"{sessionNum}-{id}", date, participant_id)
            )

            return name  
        
class _DependantStudyItem(StudyItem):
    def __init__(
            self,
            dependee: StudyItem,
            *args,
            **kwargs
            ) -> None:
        
        # TODO: do below checks cover all edge cases?
        if not isinstance(dependee, self._getDependeeClass()):
            raise ValueError(
                "`dependee` must be an instance of " +
                f"`{self._getDependeeClass()}`"
            )
        if not self.getStudyType() == dependee.getStudyType():
            raise ValueError(
                f"The study type of `dependee` must be '{self.getStudyType()}'"
            )
            
        self._DEPENDEE = dependee
        
        # Specify or validate the participant_id
        participantID = kwargs.pop("participant_id", default=None)
        dependeeParticipantID = self._DEPENDEE.info.participant_id
        if participantID is None:
            participantID = dependeeParticipantID
        elif participantID != str(dependeeParticipantID):
            raise ValueError(
                "`participant_id` must be the same as the participant_id " +
                "for `dependee`, or be `None`."
            ) 
        kwargs["participant_id"] = participantID
        
        super().__init__(*args, **kwargs)
    
    @classmethod
    @abstractmethod
    def _getDependeeClass(cls) -> StudyItem:
        pass

    @classmethod
    def getStudyType(cls) -> str:
        return cls._getDependeeClass().getStudyType() 
    
class StudyBlock(_DependantStudyItem):
    def __init__(
            self,
            *args,
            **kwargs
            ) -> None:
        
        dependee = args[0]
        self._PARENT_DIR_ = os.path.join(dependee.info["dir"], "blocks") 
        
        super().__init__(**args, **kwargs)
        
    @classmethod
    def _getDependeeClass(cls) -> StudyItem:
        return StudySession
    
    @property
    def session(self) -> StudySession:
        return self._DEPENDEE
    
    @property
    def _PARENT_DIR(self) -> str:
        return self._PARENT_DIR_
    
    @staticmethod
    def _makeItemName(
            id: int|str,
            date: str,
            participant_id: int|str|None,
            parent_dir: str|None = None
            ) -> str:
        return _nameItem("b", id, date, participant_id)  
            
# class StudyBlock(StudyItem):
#     def __init__(
#             self, 
#             parentSession: StudySession, 
#             *args, **kwargs
#             ) -> None:
        
#         # Ensure this block is the same study type as its parent session
#         # TODO: implement
        
#         self._PARENT_SESSION = parentSession
#         self._PARENT_DIR_ = os.path.join(
#             self._PARENT_SESSION.info["dir"], "blocks"
#         )   
        
#         # Specify or validate the participant_id
#         participant_id = kwargs.pop("participant_id", default=None)
#         session_participant_id = self.session.info.participant_id
#         kwargs["participant_id"] = _validateParticipantID(
#             participant_id, 
#             session_participant_id, 
#             errmsg = (
#                 "`participant_id` must be the same as the participant_id " +
#                 "for `parentSession`, or be `None`."
#             )
#         )
        
#         super().__init__(*args, **kwargs)
        
#     @property
#     def session(self) -> StudySession:
#         return self._PARENT_SESSION

#     @property
#     def _PARENT_DIR(self) -> str:
#         return self._PARENT_DIR_
    
#     @staticmethod
#     def _makeItemName(
#             id: int|str,
#             date: str,
#             participant_id: int|str|None,
#             parent_dir: str|None = None
#             ) -> str:
#         return _nameItem("b", id, date, participant_id) 

class StudyTrial(_DependantStudyItem):
    def __init__(
            self,
            *args,
            **kwargs
            ) -> None:
        
        dependee = args[0]
        self._PARENT_DIR_ = os.path.join(dependee.info["dir"], "trials") 
        
        super().__init__(**args, **kwargs)  
        
    @classmethod
    def _getDependeeClass(cls) -> StudyItem:
        return StudyBlock
    
    @property
    def block(self) -> StudyBlock:
        return self._DEPENDEE

    @property
    def _PARENT_DIR(self) -> str:
        return self._PARENT_DIR_
    
    @staticmethod
    def _makeItemName(
            id: int|str,
            date: str,
            participant_id: int|str|None,
            parent_dir: str|None = None
            ) -> str:
        return _nameItem("t", id, date, participant_id)    
        
# class StudyTrial(StudyItem):
#     def __init__(
#             self, 
#             parentBlock: StudyBlock, 
#             *args, **kwargs
#             ) -> None:
        
#         self._PARENT_BLOCK = parentBlock
#         self._PARENT_DIR_ = os.path.join(
#             self._PARENT_BLOCK.info["dir"], "trials"
#         )   
        
#         # Specify or validate the participant_id
#         participant_id = kwargs.pop("participant_id", default=None)
#         block_participant_id = self.block.info.participant_id
#         kwargs["participant_id"] = _validateParticipantID(
#             participant_id, 
#             block_participant_id, 
#             errmsg = (
#                 "`participant_id` must be the same as the participant_id " +
#                 "for `parentBlock`, or be `None`."
#             )
#         )

#         super().__init__(*args, **kwargs)
        
#     @property
#     def block(self) -> StudyBlock:
#         return self._PARENT_BLOCK

#     @property
#     def _PARENT_DIR(self) -> str:
#         return self._PARENT_DIR_
    
#     @staticmethod
#     def _makeItemName(
#             id: int|str,
#             date: str,
#             participant_id: int|str|None,
#             parent_dir: str|None = None
#             ) -> str:
#         return _nameItem("t", id, date, participant_id)
   
##################
# HELPER METHODS #
##################
    
def _nameItem(
        prefix: str,
        id: int|str,
        date: str,
        participant_id: int|str|None
        ) -> str:
    name = f"{prefix}_{id}_{date}"
    if participant_id is not None:
        name = f"{name}_{participant_id}"
    return name
    
def _validateParticipantID(
        participant_id: int|str|None,
        targetPID: int|str|None,
        errmsg: str|None = None
        ) -> int|str|None:
    
    if participant_id is None:
        _participant_id = targetPID
    elif str(participant_id) == str(targetPID):
        _participant_id = participant_id
    else:
        defaultErrmsg = (
            "`participant_id` must have a value that, if converted to " +
            f"`str`, equals '{targetPID}', or be `None`"
        )
        raise ValueError(errmsg if errmsg is not None else defaultErrmsg)
        
    return _participant_id