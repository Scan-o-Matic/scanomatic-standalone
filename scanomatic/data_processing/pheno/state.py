from collections import deque
from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Optional, Union

import numpy as np
import numpy.typing as npt

from scanomatic.data_processing.growth_phenotypes import Phenotypes
from scanomatic.data_processing.norm import (
    NormState,
    Offsets,
    get_reference_positions
)
from scanomatic.data_processing.phases.analysis import CurvePhasePhenotypes
from scanomatic.data_processing.phases.features import CurvePhaseMetaPhenotypes
from scanomatic.data_processing.phenotypes import (
    PhenotypeDataType,
    infer_phenotype_from_name
)
from scanomatic.generics.phenotype_filter import Filter, FilterArray
from scanomatic.io.meta_data import MetaData2

_logger = Logger("Phenotyper State")

PlateByPhenotypeArrays = npt.NDArray[Optional[dict[Phenotypes, npt.NDArray]]]
PlateByCurveMetaPhenotypeArrays = npt.NDArray[
    Optional[dict[CurvePhaseMetaPhenotypes, npt.NDArray]]
]


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

    normalized_phenotypes: Optional[PlateByPhenotypeArrays] = field(
        default=None,
    )
    meta_data: Optional[MetaData2] = field(default=None)
    phenotype_filter: Optional[PlateByPhenotypeArrays] = field(
        default=None,
    )
    phenotype_filter_undo: Optional[tuple[deque, ...]] = field(default=None)
    reference_surface_positions: list[Offsets] = field(default_factory=list)
    smooth_growth_data: Optional[np.ndarray] = field(default=None)
    times_data: Optional[np.ndarray] = field(default=None)
    vector_meta_phenotypes: Optional[CurvePhaseMetaPhenotypes] = field(
        default=None,
    )
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
        plate_arr = self.raw_growth_data[plate]
        if plate_arr is None:
            return None
        return plate_arr.shape[:2]

    def has_reference_surface_positions(self) -> bool:
        return (
            self.phenotypes is not None
            and len(self.reference_surface_positions) == len(self.phenotypes)
        )

    def has_phenotype_filter_undo(self) -> bool:
        return (
            self.phenotype_filter_undo is not None
            and self.phenotypes is not None
            and len(self.phenotypes) == len(self.phenotype_filter_undo)
        )

    def has_phenotypes_for_plate(self, plate: int) -> bool:
        return (
            self.phenotypes is not None
            and self.phenotypes[plate] is not None
        )

    def has_phenotype_on_any_plate(self, phenotype: Phenotypes) -> bool:
        return (
            self.phenotypes is not None
            and any(
                phenotype in plate
                for plate in self.phenotypes
                if plate is not None
            )
        )

    def has_phenotype(
        self,
        phenotype: Union[str, Phenotypes, CurvePhaseMetaPhenotypes],
    ) -> bool:
        if isinstance(phenotype, str):
            try:
                phenotype = infer_phenotype_from_name(phenotype)
            except ValueError:
                return False

        if isinstance(phenotype, Phenotypes):
            return self.has_phenotype_on_any_plate(phenotype)
        elif (
            isinstance(phenotype, CurvePhaseMetaPhenotypes)
            and self.vector_meta_phenotypes is not None
        ):
            return any(
                phenotype in plate for plate in
                self.vector_meta_phenotypes
                if plate is not None
            )
        return False

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
            isinstance(self.normalized_phenotypes, np.ndarray)
            and not all(
                plate is None
                or all(plate[phenotype].size == 0 for phenotype in plate)
                for plate in self.normalized_phenotypes
            )
            and self.normalized_phenotypes.size > 0
        )

    def has_phenotype_filter(self) -> bool:
        return (
            self.phenotype_filter is not None
            and self.phenotypes is not None
            and len(self.phenotypes) == len(self.phenotype_filter)
        )

    def has_any_colony_removed_from_plate(self, plate: int) -> bool:
        return (
            self.phenotype_filter is not None
            and (
                False if self.phenotype_filter[plate] is None
                else any(
                    pheno_filter.any() for pheno_filter in
                    self.phenotype_filter[plate].values()
                )
            )
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
            or len(self.smooth_growth_data) != len(self.raw_growth_data)
        ):
            return False

        return all(
            (None if a is None else a.shape)
            == (None if b is None else b.shape)
            for a, b in zip(
                self.raw_growth_data,
                self.smooth_growth_data,
            )
        )

    def get_phenotype(
        self,
        settings: PhenotyperSettings,
        phenotype: Union[Phenotypes, CurvePhasePhenotypes],
        filtered: bool = True,
        norm_state: NormState = NormState.Absolute,
        reference_values: Optional[tuple[float, ...]] = None,
        **kwargs: Any,
    ) -> list[Optional[Union[FilterArray, np.ndarray]]]:
        """Getting phenotype data

        Args:
            phenotype:
                The phenotype, either a `.growth_phenotypes.Phenotypes`
                or a `.curve_phase_phenotypes.CurvePhasePhenotypes`
            filtered:
                Optional, if the curve-markings should be present or not on
                the returned object. Defaults to including curve markings.
            norm_state:
                Optional, the type of data-state to return.
                If `NormState.NormalizedAbsoluteNonBatched`, then
                `reference_values` must be supplied.
            reference_values:
                Optional, tuple of the means of all comparable plates-medians
                of their reference positions.
                One value per plate in the current project.

        Returns:
            List of plate-wise phenotype data. Depending on the `filtered`
            argument this is either `FilterArray` that behave similar to
            `numpy.ma.masked_array` or pure `numpy.ndarray`s for non-filtered
            data.

        See Also:
            Phenotyper.get_reference_median:
                Produces reference values for plates.
        """
        if not self.has_phenotype(phenotype):
            raise ValueError(
                "'{0}' has not been extracted, please re-run 'extract_phenotypes()' to include it.".format(  # noqa: E501
                    phenotype.name,
                ),
            )

        if 'normalized' in kwargs:
            _logger.warning(
                "Deprecation warning: Use phenotyper.NormState enums instead",
            )
            norm_state = (
                NormState.NormalizedRelative if kwargs['normalized']
                else NormState.Absolute
            )

        if not PhenotypeDataType.Trusted(phenotype):
            _logger.warning(
                "The phenotype '{0}' has not been fully tested and verified!".format(  # noqa: E501
                    phenotype.name,
                ),
            )

        self.init_remove_filter_and_undo_actions(settings)

        if norm_state is NormState.NormalizedRelative:
            return self._get_norm_phenotype(phenotype, filtered)

        elif norm_state is NormState.Absolute:
            return self._get_abs_phenotype(phenotype, filtered)

        else:
            normed_plates = self._get_norm_phenotype(phenotype, filtered)
            if norm_state is NormState.NormalizedAbsoluteBatched:
                reference_values = self.get_reference_median(
                    settings,
                    phenotype,
                )
            if reference_values is None:
                _logger.error(
                    f"Can't produce {norm_state.name} values for {phenotype.name} without supplied reference values",  # noqa: E501
                )
                return [None for _ in normed_plates]
            return tuple(
                (
                    None if ref_val is None or plate is None
                    else ref_val * np.power(2, plate)
                )
                for ref_val, plate in zip(reference_values, normed_plates)
            )

    def _get_phenotype_data(self, phenotype):
        if (
            isinstance(phenotype, CurvePhaseMetaPhenotypes)
            and self.vector_meta_phenotypes is not None
        ):
            return [
                None if p is None else p[phenotype]
                for p in self.vector_meta_phenotypes
            ]
        return [None for _ in self.enumerate_plates]

    def _restructure_growth_phenotype(self, phenotype):
        def _plate_type_converter_vector(plate):
            out = plate.copy()
            if out.dtype == np.floating and out.shape[-1] == 1:
                return out.reshape(out.shape[:2])

            return out

        def _plate_type_converter_scalar(plate):
            dtype = type(plate[0, 0])
            out = np.zeros(plate.shape, dtype=dtype)

            if issubclass(type(out.dtype), np.floating):
                out *= np.nan

            out[...] = plate
            return out

        def _plate_type_converter(plate):
            if plate.ndim == 3:
                return _plate_type_converter_vector(plate)
            else:
                return _plate_type_converter_scalar(plate)

        return [
            None if (
                plate_arr is None
                or phenotype not in plate_arr
                or plate_arr[phenotype].size == 0
            ) else _plate_type_converter(plate_arr[phenotype])
            for plate_arr in self.phenotypes
        ]

    def _get_abs_phenotype(self, phenotype, filtered):

        if isinstance(phenotype, Phenotypes):
            data = self._restructure_growth_phenotype(phenotype)
        else:
            data = self._get_phenotype_data(phenotype)

        if filtered:
            return [
                None
                if (
                    p is None
                    or phenotype not in self.phenotype_filter[id_plate]
                )
                else FilterArray(
                    p,
                    self.phenotype_filter[id_plate][phenotype],
                )
                for id_plate, p in enumerate(data)
                ]
        else:
            return data

    def _get_norm_phenotype(self, phenotype, filtered):
        if (
            self.normalized_phenotypes is None
            or not self.has_normalized_phenotype(phenotype)
        ):

            if self.normalized_phenotypes is None:
                _logger.warning("No phenotypes have been normalized")
            else:
                _logger.warning(
                    "Phenotypes {0} not included in normalized phenotypes".format(  # noqa: E501
                        phenotype,
                    ),
                )
            return [None for _ in self.phenotype_filter]

        if filtered:
            return [
                None if (
                    p is None
                    or phenotype not in self.phenotype_filter[id_plate]
                ) else FilterArray(
                    p[phenotype],
                    self.phenotype_filter[id_plate][phenotype],
                )
                for id_plate, p in enumerate(self.normalized_phenotypes)
            ]

        else:
            return [
                None if p is None else p[phenotype]
                for _, p in enumerate(self.normalized_phenotypes)
            ]

    def get_reference_median(
        self,
        settings: PhenotyperSettings,
        phenotype: Union[Phenotypes, CurvePhasePhenotypes],
    ) -> tuple[float, ...]:
        """ Getting reference position medians per plate."""
        plates = self.get_phenotype(
            settings,
            phenotype,
            filtered=False,
        )
        return tuple(
            np.ma.median(np.ma.masked_invalid(
                get_reference_positions([plate], [offset]),
            )) if plate is not None else None
            for plate, offset in
            zip(plates, self.reference_surface_positions)
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
        self.vector_phenotypes = None

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

    def init_remove_filter_and_undo_actions(self, settings: PhenotyperSettings):
        if self.phenotypes is None:
            self.phenotype_filter = None
            self.phenotype_filter_undo = None
            return

        if not self.has_phenotype_filter():
            _logger.warning(
                "Filter doesn't match number of plates. Rewriting...",
            )
            self.phenotype_filter = np.array(
                [{} for _ in self.phenotypes],
                dtype=np.object,
            )
            self.phenotype_filter_undo = tuple(
                deque() for _ in self.phenotypes
            )

        elif not self.has_phenotype_filter_undo():
            _logger.warning(
                "Undo doesn't match number of plates. Rewriting...",
            )
            self.phenotype_filter_undo = tuple(
                deque() for _ in self.phenotypes
            )

        if (
            self.has_phenotype(Phenotypes.Monotonicity)
            and self.has_phenotype(Phenotypes.ExperimentPopulationDoublings)
        ):
            growth_filter = [
                (
                    (
                        plate[Phenotypes.Monotonicity]
                        < settings.no_growth_monotonicity_threshold
                    )
                    | (
                        np.isfinite(plate[Phenotypes.Monotonicity])
                        == np.False_
                    )
                )
                & (
                    (
                        plate[Phenotypes.ExperimentPopulationDoublings]
                        < settings.no_growth_pop_doublings_threshold
                    )
                    | (
                        np.isfinite(
                            plate[Phenotypes.ExperimentPopulationDoublings],
                        )
                        == np.False_
                    )
                )
                for plate in self.phenotypes
            ]
        elif self.has_phenotype(Phenotypes.Monotonicity):
            growth_filter = [
                (
                    (
                        plate[Phenotypes.Monotonicity]
                        < settings.no_growth_monotonicity_threshold
                    )
                    | (
                        np.isfinite(plate[Phenotypes.Monotonicity])
                        == np.False_
                    )
                )
                for plate in self.phenotypes
            ]
        elif self.has_phenotype(Phenotypes.ExperimentPopulationDoublings):
            growth_filter = [
                (
                    (
                        plate[Phenotypes.ExperimentPopulationDoublings]
                        < settings.no_growth_pop_doublings_threshold
                    )
                    | (
                        np.isfinite(
                            plate[Phenotypes.ExperimentPopulationDoublings],
                        )
                        == np.False_
                    )
                )
                for plate in self.phenotypes
            ]
        else:
            growth_filter = [[] for _ in self.phenotypes]

        for phenotype in settings.phenotypes_inclusion():
            if not self.has_phenotype(phenotype):
                continue

            phenotype_data = self._get_abs_phenotype(phenotype, False)

            for plate_index in range(self.phenotypes.shape[0]):
                if phenotype_data[plate_index] is None:
                    continue

                if phenotype not in self.phenotype_filter[plate_index]:
                    self._init_plate_filter(
                        plate_index,
                        phenotype,
                        phenotype_data[plate_index],
                        growth_filter[plate_index],
                    )

                elif (
                    self.phenotype_filter[plate_index][phenotype].shape
                    != phenotype_data[plate_index].shape
                ):
                    _logger.warning(
                        "The phenotype filter doesn't match plate {0} shape!".format(  # noqa: E501
                            plate_index + 1,
                        )
                    )
                    self._init_plate_filter(
                        plate_index,
                        phenotype,
                        phenotype_data[plate_index],
                        growth_filter[plate_index],
                    )

    def _init_plate_filter(
        self,
        plate_index,
        phenotype,
        phenotype_data,
        growth_filter,
    ):
        self.phenotype_filter[plate_index][phenotype] = np.zeros(
            self.raw_growth_data[plate_index].shape[:2],
            dtype=np.int8,
        )
        if phenotype_data is not None:
            self.phenotype_filter[plate_index][phenotype][
                np.where(np.isfinite(phenotype_data) == False)  # noqa: E712
            ] = Filter.UndecidedProblem.value

            self.phenotype_filter[plate_index][phenotype][
                growth_filter
            ] = Filter.NoGrowth.value

        if self.phenotype_filter_undo[plate_index]:
            _logger.warning(
                "Undo cleared for plate {0} because of rewriting, better solution not yet implemented.".format(  # noqa: E501
                    plate_index + 1,
                ),
            )
