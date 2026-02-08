
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import ClassVar, Final, Optional, Tuple, Dict, Any

UUID = str

@dataclass 
class Entry:
    uuid : UUID
    problem_id : int
    confidence: int
    ts : int

    @classmethod
    def from_row(cls, row: tuple) -> Entry:
        return Entry(
            uuid=row[0],
            problem_id=row[1],
            confidence=row[2],
            ts=row[3]
        )
    
    def to_row(self) -> Tuple[str, int, int, int]:
        return (self.uuid, self.problem_id, self.confidence, self.ts)

@dataclass
class BaseEvent(ABC):  # Inherit from ABC
    uuid: UUID
    ts: int

    # This forces subclasses to define EVENT_TYPE
    @property
    @abstractmethod
    def EVENT_TYPE(self) -> str:
        pass

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["EVENT_TYPE"] = self.EVENT_TYPE
        return data

@dataclass
class AddEntryEvent(BaseEvent):
    EVENT_TYPE: ClassVar[Final[str]] = "ADD_ENTRY"
    
    entry_uuid: UUID
    problem_id: int
    confidence: int

@dataclass
class RmEntryEvent(BaseEvent):
    EVENT_TYPE: ClassVar[Final[str]] = "RM_ENTRY"
    target_entry_uuid: UUID

@dataclass
class Problem:
    id: int
    slug : str
    title : str
    difficulty : int
    difficulty_txt : str
    last_review_at : Optional[int]
    next_review_at : int
    ef : float
    i : int
    n : int
    active : bool

    @classmethod
    def from_row(cls, row: tuple) -> Problem:
        return cls(
            id=row[0],
            slug=row[1],
            title=row[2],
            difficulty=row[3],
            difficulty_txt=INT_TO_DIFF[row[3]],
            last_review_at=row[4],
            next_review_at=row[5],
            ef=row[6],
            i=row[7],
            n=row[8],
            active=bool(row[9])
        )

DIFF_TO_INT = {
    "Hard" : 2, 
    "Medium" : 1,
    "Easy" : 0
}

INT_TO_DIFF = {
    2 : "Hard",
    1 : "Medium",
    0 : "Easy"
}

