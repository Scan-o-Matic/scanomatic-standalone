from collections import deque
from typing import Optional
import numpy as np
from dataclasses import dataclass, field
from scanomatic.data_processing.growth_phenotypes import Phenotypes
from scanomatic.data_processing.norm import Offsets
from scanomatic.data_processing.phenotypes import PhenotypeDataType
from scanomatic.io.logger import Logger

from scanomatic.io.meta_data import MetaData2

_logger = Logger("Phenotyper State")


@dataclass
class PhenotyperSettings:
    median_kernel_size: int
    gaussian_filter_sigma: float
    linear_regression_size: int
    phenotypes_inclusion: Optional[PhenotypeDataType]
    no_growth_monotonicity_threshold: float
    no_growth_pop_doublings_threshold: float

    def __post_init__(self):
        assert (
            self.median_kernel_size % 2 == 1
        ), "Median kernel size must be odd"

    def serialized(self) -> list[str, int, float]:
        return [
            self.median_kernel_size,
            self.gaussian_filter_sigma,
            self.linear_regression_size,
            None if self.phenotypes_inclusion is None
            else self.phenotypes_inclusion.name,
            self.no_growth_monotonicity_threshold,
            self.no_growth_pop_doublings_threshold
        ]


@dataclass
class PhenotyperState:
    phenotypes: Optional[np.ndarray]
    raw_growth_data: np.ndarray

    normalized_phenotypes: Optional[np.ndarray] = field(default=None)
    meta_data: Optional[MetaData2] = field(default=None)
    phenotype_filter: Optional[np.ndarray] = field(default=None)
    phenotype_filter_undo: Optional[tuple[deque, ...]] = field(default=None)
    reference_surface_positions: list[Offsets] = field(default=[])
    smooth_growth_data: Optional[np.ndarray] = field(default=None)
    times_data: Optional[np.ndarray] = field(default=None)
    vector_meta_phenotypes: Optional[np.ndarray] = field(default=None)
    vector_phenotypes: Optional[np.ndarray] = field(default=None)

    def __post_init__(self):
        if len(self.reference_surface_positions) != len(self.raw_growth_data):
            self.reference_surface_positions = [
                Offsets.LowerRight() for _ in self.enumerate_plates
            ]

    @property
    def enumerate_plates(self):
        for i in range(len(self.raw_growth_data)):
            yield i

    @property
    def plate_shapes(self):
        for plate in self.raw_growth_data:
            if plate is None:
                yield None
            else:
                yield plate.shape[:2]

    def get_plate_shape(self, plate: int) -> Optional[tuple[int, int]]:
        plate = self.raw_growth_data[plate]
        if plate is None:
            return None
        return plate.shape[:2]

    def has_reference_surface_positions(self) -> bool:
        return (
            self.phenotypes is not None
            and len(self.reference_surface_positions) == len(self.phenotypes)
        )

    def has_phenotype_filter_undo(self) -> bool:
        return (
            self.phenotype_filter_undo is not None
            and len(self.phenotypes) == len(self.phenotype_filter_undo)
        )

    def has_phenotypes_for_plate(self, plate: int) -> bool:
        return (
            self.phenotypes is not None
            and self.phenotypes[plate] is not None
        )

    def has_phenotype_on_any_plate(self, phenotype: Phenotypes) -> bool:
        return (
            self._phenotypes is not None
            and any(
                phenotype in plate
                for plate in self.phenotypes
                if plate is not None
            )
        )

    def has_normalized_phenotype(self, phenotype) -> bool:
        return (
            self.normalized_phenotypes is not None
            and all(
                True if p is None else phenotype in p
                for p in self.normalized_phenotypes
            )
        )

    def has_normalized_data(self) -> bool:
        return (
            self.normalizable_phenotypes is not None
            and isinstance(self.normalized_phenotypes, np.ndarray)
            and not all(
                plate is None or plate.size == 0
                for plate in self.normalized_phenotypes
            )
            and self.normalized_phenotypes.size > 0
        )

    def has_phenotype_filter(self) -> bool:
        return (
            self.phenotype_filter is not None
            and len(self.phenotypes) == len(self.phenotype_filter)
        )

    def has_any_colony_removed_from_plate(self, plate: int) -> bool:
        return (
            self.phenotype_filter is not None
            and self.phenotype_filter[plate].any()
        )

    def has_any_colony_removed(self) -> bool:
        return (
            self.phenotype_filter is not None
            and any(
                self.has_any_colony_removed_from_plate(i)
                for i in range(self.phenotype_filter.shape[0])
            )
        )

    def has_smooth_growth_data(self) -> bool:
        if (
            self.smooth_growth_data is None
            or len(self.smooth_growth_data) != len(self.state.raw_growth_data)
        ):
            return False

        return all(
            ((a is None) is (b is None)) or a.shape == b.shape
            for a, b in zip(
                self.raw_growth_data,
                self.smooth_growth_data,
            )
        )

    def wipe_extracted_phenotypes(self, keep_filter: bool = False) -> None:
        """ This clears all extracted phenotypes but keeps the log2_curve data

        Args:
            keep_filter: Optional, if the markings of curves should be kept,
                default is to not keep them
        """
        if self.phenotypes is not None:
            _logger.info("Removing previous phenotypes")
        self.phenotypes = None

        if self.vector_phenotypes is not None:
            _logger.info("Removing previous vector phenotypes")
        self._vector_phenotypes = None

        if self.vector_meta_phenotypes is not None:
            _logger.info("Removing previous vector meta phenotypes")
        self.vector_meta_phenotypes = None

        if keep_filter:
            _logger.warning(
                "Keeping the filter may cause inconsistencies with what curves are marked as bad."  # noqa: E501
                " Use with care, and consider running the `infer_filter` method."  # noqa: E501
            )
        if not keep_filter:
            if self.phenotype_filter is not None:
                _logger.info("Removing previous remove filter")
            self.phenotype_filter = None

            if self.phenotype_filter_undo is not None:
                _logger.info("Removing filter undo history")
            self.phenotype_filter_undo = None
