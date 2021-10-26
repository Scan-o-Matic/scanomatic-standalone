from typing import Optional, Sequence
from scanomatic.generics import model


class GrayScaleModel(model.Model):
    def __init__(self, name, targets):
        self.name = name
        self.targets = targets
        super(GrayScaleModel, self).__init__()


class GrayScaleAreaModel(model.Model):
    def __init__(
        self,
        name: str = "",
        values: Sequence = tuple(),
        width: float = -1.0,
        section_length: float = -1.0,
        x1: int = 0,
        x2: int = 0,
        y1: int = 0,
        y2: int = 0,
    ):
        self.name: str = name
        self.values: str = values
        self.width: float = width
        self.section_length: float = section_length
        self.x1: int = x1
        self.x2: int = x2
        self.y1: int = y1
        self.y2: int = y2
        super(GrayScaleAreaModel, self).__init__()


class FixtureModel(model.Model):

    def __init__(
        self,
        path: str = "",
        grayscale: Optional[GrayScaleAreaModel] = None,
        orientation_mark_path: str = "",
        orientation_marks_x: Sequence = [],
        orientation_marks_y: Sequence = [],
        shape: Sequence = [],
        coordinates_scale: float = 1,
        plates: Sequence = [],
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
        self.orentation_mark_path: str = orientation_mark_path
        self.scale: float = scale
        super(FixtureModel, self).__init__()


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
        super(FixturePlateModel, self).__init__()
