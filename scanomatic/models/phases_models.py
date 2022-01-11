from enum import Enum, auto
from typing import Optional

import numpy

import scanomatic.generics.model as model


class SegmentationModelFields(Enum):
    log2_curve = auto()
    times = auto()
    plate = auto()
    pos = auto()
    dydt = auto()
    dydt_ranks = auto()
    dydt_signs = auto()
    d2yd2t = auto()
    d2yd2t_signs = auto()
    offset = auto()
    phases = auto()


class SegmentationModel(model.Model):
    def __init__(
        self,
        dydt: Optional[numpy.ndarray] = None,
        dydt_ranks: Optional[numpy.ndarray] = None,
        dydt_signs: Optional[numpy.ndarray] = None,
        d2yd2t: Optional[numpy.ndarray] = None,
        d2yd2t_signs: Optional[numpy.ndarray] = None,
        phases: Optional[numpy.ndarray] = None,
        offset: int = 0,
        log2_curve=None,
        times: Optional[numpy.ndarray] = None,
        plate: Optional[int] = None,
        pos: Optional[tuple[int, int]] = None,
    ):

        self.log2_curve: Optional[numpy.ndarray] = log2_curve
        self.times: Optional[numpy.ndarray] = times
        self.plate: Optional[int] = plate
        self.pos: Optional[tuple[int, int]] = pos

        self.dydt: Optional[numpy.ndarray] = dydt
        self.dydt_ranks: Optional[numpy.ndarray] = dydt_ranks
        self.dydt_signs: Optional[numpy.ndarray] = dydt_signs

        self.d2yd2t: Optional[numpy.ndarray] = d2yd2t
        self.d2yd2t_signs: Optional[numpy.ndarray] = d2yd2t_signs

        self.offset: int = offset

        self.phases: Optional[numpy.ndarray] = phases

        super().__init__()
