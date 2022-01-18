from enum import Enum, auto
from typing import Optional

import numpy as np

import scanomatic.generics.model as model
from scanomatic.generics.enums import CycleEnum


class JOB_TYPE(CycleEnum):
    Scan = ("Scanner Job", 0)
    Compile = ("Compile Project", 1)
    Analysis = ("Analysis Job", 10)
    Features = ("Feature Extraction Job", 20)
    Unknown = ("Unknown Job", -1)

    @property
    def int_value(self) -> int:
        return self.value[1]

    @property
    def text(self) -> str:
        return self.value[0]

    @property
    def next(self) -> "JOB_TYPE":
        next_int_val = (1 + np.round(self.int_value/10.)) * 10
        return self.get_by_int_representation(next_int_val)

    @classmethod
    def get_by_int_representation(cls, value) -> "JOB_TYPE":
        for member in cls.__members__.values():
            if value == member.int_value:
                return member
        return cls.get_default()

    @classmethod
    def get_default(cls) -> "JOB_TYPE":
        return cls.Unknown


class JOB_STATUS(Enum):
    Requested = auto()
    Queued = auto()
    Running = auto()
    Restoring = auto()
    Done = auto()
    Aborted = auto()
    Crashed = auto()
    Unknown = auto()


class RPCjobModelFields(Enum):
    id = auto()
    type = auto()
    status = auto()
    pid = auto()
    priority = auto()
    content_model = auto()


class RPCjobModel(model.Model):
    def __init__(
        self,
        id: Optional[str] = None,
        type: JOB_TYPE = JOB_TYPE.Unknown,
        status: JOB_STATUS = JOB_STATUS.Unknown,
        content_model=None,
        priority: int = -1,
        pid=None
    ):
        self.id = id
        self.type: JOB_TYPE = type
        self.status: JOB_STATUS = status
        self.pid = pid
        self.priority: int = priority
        self.content_model = content_model
        super().__init__()

    def __hash__(self) -> int:
        if self.id is None:
            raise ValueError(
                'Hashing a RPCjobModel without and id not allowed',
            )
        return hash(self.id)
