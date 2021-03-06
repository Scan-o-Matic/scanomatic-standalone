from enum import Enum
from math import floor
from typing import Generator


class DefaultEnum(Enum):
    @classmethod
    def get_default(cls):
        return list(cls.__members__.values())[0]


class IterationEnum(DefaultEnum):
    @property
    def _non_default_values(self) -> Generator["IterationEnum", None, None]:
        return (
            m for m in list(type(self).__members__.values())
            if m is not self.get_default()
        )


class CycleEnum(IterationEnum):
    @property
    def cycle(self) -> IterationEnum:
        known = tuple(self._non_default_values)
        return known[(known.index(self) + 1) % len(known)]


class MinorMajorStepEnum(IterationEnum):
    @property
    def next_major(self) -> "MinorMajorStepEnum":

        known_majors = sorted(
            e.value for e in self._non_default_values if e.value % 10 == 0
        )
        larger_values = tuple(v for v in known_majors if v > self.value)
        if larger_values:
            return type(self)(larger_values[0])
        else:
            return type(self)(min(known_majors))

    @property
    def next_minor(self) -> "MinorMajorStepEnum":
        known_minors = sorted(
            e.value for e in self._non_default_values
            if self.value < e.value < (floor(self.value/10) + 1) * 10
        )
        if known_minors:
            return type(self)(known_minors[0])
        else:
            return self
