from enum import Enum, auto
from typing import Optional
from collections.abc import Sequence

from scanomatic.generics import model


class GrayScaleAreaModelFields(Enum):
    _name = auto()
    values = auto()
    width = auto()
    section_length = auto()
    x1 = auto()
    x2 = auto()
    y1 = auto()
    y2 = auto()


class GrayScaleAreaModel(model.Model):
    def __init__(
        self,
        name: str = "",
        section_values: Sequence[float] = tuple(),
        width: float = -1.0,
        section_length: float = -1.0,
        x1: int = 0,
        x2: int = 0,
        y1: int = 0,
        y2: int = 0,
    ):
        self.name: str = name
        self.section_values: Sequence[float] = section_values
        self.width: float = width
        self.section_length: float = section_length
        self.x1: int = x1
        self.x2: int = x2
        self.y1: int = y1
        self.y2: int = y2
        super().__init__()


class FixtureModelFields(Enum):
    _name = auto()
    path = auto()
    grayscale = auto()
    orientation_marks_x = auto()
    orientation_marks_y = auto()
    shape = auto()
    coordinates_scale = auto()
    plates = auto()
    orientation_mark_path = auto()
    scale = auto()


class FixtureModel(model.Model):
    def __init__(
        self,
        path: str = "",
        grayscale: Optional[GrayScaleAreaModel] = None,
        orientation_mark_path: str = "",
        orientation_marks_x: Sequence[float] = [],
        orientation_marks_y: Sequence[float] = [],
        shape: Sequence[int] = [],
        coordinates_scale: float = 1.0,
        plates: Sequence["FixturePlateModel"] = [],
        name: str = "",
        scale: float = 1.0,
    ):
        self.name: str = name
        self.path: str = path
        self.grayscale: Optional[GrayScaleAreaModel] = grayscale
        self.orientation_marks_x: Sequence = orientation_marks_x
        self.orientation_marks_y: Sequence = orientation_marks_y
        self.shape: Sequence = shape
        self.coordinates_scale: float = coordinates_scale
        self.plates: Sequence = plates
        self.orientation_mark_path: str = orientation_mark_path
        self.scale: float = scale
        super().__init__()


class FixturePlateModelFields(Enum):
    index = auto()
    x1 = auto()
    x2 = auto()
    y1 = auto()
    y2 = auto()


class FixturePlateModel(model.Model):
    def __init__(
        self,
        index: int = 0,
        x1: int = 0,
        x2: int = 0,
        y1: int = 0,
        y2: int = 0,
    ):
        self.index: int = index
        self.x1: int = x1
        self.x2: int = x2
        self.y1: int = y1
        self.y2: int = y2
        super().__init__()
