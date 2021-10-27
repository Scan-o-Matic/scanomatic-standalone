from typing import Any, List, Optional
import numpy as np
from dataclasses import dataclass
from scanomatic.data_processing.phenotypes import PhenotypeDataType

from scanomatic.io.meta_data import MetaData2


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

    def serialized(self) -> List[str, int, float]:
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
    phenotypes: np.ndarray
    vector_phenotypes: np.ndarray
    vector_meta_phenotypes: np.ndarray
    normalized_phenotypes: np.ndarray
    raw_growth_data: np.ndarray
    smooth_growth_data: np.ndarray
    phenotype_filter: np.ndarray
    reference_surface_positions: np.ndarray
    phenotypes_filter_undo: Any
    phenotype_times: np.ndarray
    times_data: np.ndarray
    meta_data: MetaData2
