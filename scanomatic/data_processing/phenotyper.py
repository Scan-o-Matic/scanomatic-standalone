import csv
import pickle
import os
from collections import deque
from collections.abc import Callable, Generator
from enum import Enum
from io import BytesIO
from itertools import chain, product
from typing import Any, Optional, Union

import numpy as np
from scipy.ndimage import median_filter  # type: ignore
from scipy.signal import convolve  # type: ignore
from scipy.stats import norm  # type: ignore

import scanomatic.io.image_data as image_data
import scanomatic.io.jsonizer as jsonizer
import scanomatic.io.paths as paths
from scanomatic.data_processing.convolution import (
    EdgeCondition,
    filter_edge_condition,
    get_edge_condition_timed_filter,
    merge_convolve
)
from scanomatic.data_processing.growth_phenotypes import (
    Phenotypes,
    get_chapman_richards_4parameter_extended_curve,
    get_derivative,
    get_preprocessed_data_for_phenotypes
)
from scanomatic.data_processing.norm import (
    NormState,
    Offsets,
    get_normalized_data,
    norm_by_diff,
    norm_by_log2_diff,
    norm_by_log2_diff_corr_scaled,
    norm_by_signal_to_noise
)
from scanomatic.data_processing.phases.analysis import (
    CurvePhasePhenotypes,
    get_phase_analysis
)
from scanomatic.data_processing.phases.features import (
    CurvePhaseMetaPhenotypes,
    VectorPhenotypes,
    extract_phenotypes
)
from scanomatic.data_processing.pheno.save import save_state, save_state_to_zip
from scanomatic.data_processing.pheno.state import (
    DEFAULT_NO_GROWTH_THRESHOLD,
    DEFAULT_DOUBLING_THRESHOLD,
    PhenotyperSettings,
    PhenotyperState
)
from scanomatic.data_processing.phenotypes import PhenotypeDataType
from scanomatic.data_processing.strain_selector import StrainSelector
from scanomatic.generics.phenotype_filter import Filter, FilterArray
from scanomatic.io.logger import get_logger
from scanomatic.io.meta_data import MetaData2
from scanomatic.io.pickler import safe_load
from . import mock_numpy_interface

# TODO: Something is wrong with phase features again


class NormalizationMethod(Enum):
    """Methods for calculating normalized values

    The basic feature for all is calculating a normalization surface.

    In `Log2Difference` the norm surface is subtracted from
    the experimental values.

    In `SignalToNoise` the outcome of the difference in absolute
    value between experiment and normalization surface divided by
    the standard deviation of the reference values.

    In `Log2DifferenceCorrelationScaled`, the value of the log2
    difference is scaled with the pearson correlation between the
    observations and the normalization surface in such a way that
    negative correlations gives least trust, no correlation intermediate
    and positive most trust.

    In `Difference`, it is just the abolute difference between
    experiment and normalization surface.
    """
    Log2Difference = 0
    SignalToNoise = 1
    Log2DifferenceCorrelationScaled = 2
    Difference = 3


class Smoothing(Enum):
    Keep = 0
    MedianGauss = 1
    Polynomial = 2
    PolynomialWeightedMulti = 3


# TODO: Phenotypes should possibly not be indexed based on enum value either
# and use dict like the undo/filter


class Phenotyper(mock_numpy_interface.NumpyArrayInterface):
    """The Phenotyper class is a class for producing phenotypes
    based on growth curves as well as storing and easy displaying them.

    There are foure modes of instantiating a phenotyper instance:

    <code>
    #Generic instanciation
    p = Phenotyper(...)

    #Instanciation from numpy data
    p = Phenotyper.LoadFromNumPy(...)

    #Instanciation from a saved phenotyper-state
    #this method will not try to make new phenotypes
    p = Phenotyper.LoadFromState(...)
    </code>

    The names of the currently supported phenotypes are stored in static
    dictionary lookup <code>Phenotyper.NAMES_OF_PHENOTYPES</code>.

    The matching lookup-keys for accessing specific phenotype indices in the
    phenotypes array are stored as static integers on the class following
    the pattern <code>Phenotyper.PHEN_*</code>.
    """

    UNDO_HISTORY_LENGTH = 50

    def __init__(
        self,
        raw_growth_data,
        times_data=None,
        median_kernel_size: int = 5,
        gaussian_filter_sigma: float = 1.5,
        linear_regression_size: int = 5,
        no_growth_monotonicity_threshold: float = DEFAULT_NO_GROWTH_THRESHOLD,
        no_growth_pop_doublings_threshold: float = DEFAULT_DOUBLING_THRESHOLD,
        base_name=None,
        run_extraction=False,
        phenotypes=None,
        phenotypes_inclusion=PhenotypeDataType.Trusted,
    ):
        self._logger = get_logger("Phenotyper")
        self._paths = paths.Paths()
        self._settings = PhenotyperSettings(
            median_kernel_size=median_kernel_size,
            gaussian_filter_sigma=gaussian_filter_sigma,
            linear_regression_size=linear_regression_size,
            phenotypes_inclusion=phenotypes_inclusion,
            no_growth_monotonicity_threshold=no_growth_monotonicity_threshold,
            no_growth_pop_doublings_threshold=(
                no_growth_pop_doublings_threshold
            ),
        )
        self._state = PhenotyperState(
            phenotypes=phenotypes,
            raw_growth_data=raw_growth_data,
        )
        self.times = times_data
        assert self.times is not None, "A data series needs its times"

        self._base_name = base_name

        super(Phenotyper, self).__init__(raw_growth_data)

        self._normalizable_phenotypes = {
            Phenotypes.GenerationTime,
            Phenotypes.GenerationTimePopulationSize,
            Phenotypes.ExperimentGrowthYield,
            Phenotypes.ExperimentPopulationDoublings,
            Phenotypes.GenerationTimePopulationSize,
            Phenotypes.GrowthLag,
            Phenotypes.ColonySize48h,
            Phenotypes.ResidualGrowth,
            Phenotypes.ResidualGrowthAsPopulationDoublings,
            Phenotypes.ExperimentLowPoint,
            Phenotypes.ExperimentBaseLine,

            CurvePhaseMetaPhenotypes.InitialLag,
            CurvePhaseMetaPhenotypes.InitialLagAlternativeModel,
            CurvePhaseMetaPhenotypes.MajorImpulseAveragePopulationDoublingTime,
            CurvePhaseMetaPhenotypes.MajorImpulseYieldContribution,
            CurvePhaseMetaPhenotypes.MajorImpulseFlankAsymmetry,
            CurvePhaseMetaPhenotypes.InitialAccelerationAsymptoteAngle,
            CurvePhaseMetaPhenotypes.InitialAccelerationAsymptoteIntersect,
            CurvePhaseMetaPhenotypes.FinalRetardationAsymptoteAngle,
            CurvePhaseMetaPhenotypes.FinalRetardationAsymptoteIntersect,
            CurvePhaseMetaPhenotypes.TimeBeforeMajorGrowth,
        }

        if run_extraction:
            self.extract_phenotypes()

    def __contains__(
        self,
        phenotype: Union[str, Phenotypes, CurvePhaseMetaPhenotypes],
    ) -> bool:
        return self._state.has_phenotype(phenotype)

    @property
    def state(self) -> PhenotyperState:
        return self._state

    def set_phenotype_inclusion_level(self, level: PhenotypeDataType):
        """Change which phenotypes to be included in feature extraction.

        Default is `PhenotypeDataType.Trusted` which indicates that
        the phenotypes are unlikely to be modified in the future and that the
        algorithms have been thoroughly vetted and are expected to not change.

        If the `Phenotyper` instance has been saved (`Phenotyper.save_state()`)
        after a change to the inclusion level has been made, next time the same
        feature extraction is loaded by `Phenotyper.LoadFromState` that
        inclusion level is loaded instead of `PhenotypeDataType.Trusted`.

        Args:
            level: The PhenotypeDataType-level to toggle to.
                Options are `PhenotypeDataType.Trusted`,
                `PhenotypeDataType.UnderDevelopment`
                and `PhenotypeDataType.Other`.

        Notes:
            Using `PhenotypeDataType.UnderDevelopment` or
            `PhenotypeDataType.Other` is not recommended outside the scope of
            testing stuff. They are both prone to change and haven't been
            vetted for bugs and errors. Especially `Other` can include
            discarded ideas and sketches. If however you decide on using one
            of them, you should discuss this with Martin before-hand and you
            yourself need to ensure that you trust both the data and the
            algorithms that produces the data.

        See Also:
            Phenotyper.extract_phenotypes: Run new feature extraction
            Phenotyper.add_phenotype_to_normalization: Including phenotype to
                what is normalized
            Phenotyper.remove_phenotype_from_normalization: Remove phenotype
                so that it is not normalized
        """
        if isinstance(level, PhenotypeDataType):
            self._settings.phenotypes_inclusion = level
        else:
            self._logger.error("Value not a PhenotypeDataType!")

    def phenotype_names(self, normed: bool = False):
        if normed:
            if self._state.normalized_phenotypes is None:
                return []
            else:
                return set(
                    pheno.name for pheno in
                    chain(*(
                        plate.keys() for plate in
                        self._state.normalized_phenotypes
                        if plate is not None
                    ))
                )
        else:
            return tuple(p.name for p in self.phenotypes if p in self)

    @classmethod
    def LoadFromState(cls, directory_path: str) -> "Phenotyper":
        """Creates an instance based on previously saved phenotyper state
        in specified directory.

        Args:
            directory_path:
                Path to the directory holding the relevant files
        """
        _p = paths.Paths()

        raw_growth_data = np.load(
            safe_load(os.path.join(
                directory_path,
                _p.phenotypes_input_data,
            )),
            allow_pickle=True,
        )

        times = np.load(
            safe_load(os.path.join(
                directory_path,
                _p.phenotype_times,
            )),
            allow_pickle=True,
        )

        phenotyper = cls(
            raw_growth_data,
            times,
            run_extraction=False,
            base_name=directory_path
        )

        try:
            phenotypes = np.load(
                safe_load(os.path.join(
                    directory_path,
                    _p.phenotypes_raw_npy,
                )),
                allow_pickle=True,
            )
        except (IOError, ValueError):
            phenotyper._logger.warning(
                "Could not load Phenotypes, probably too old extraction, please rerun!",  # noqa: E501
            )
            phenotypes = None

        try:
            vector_phenotypes = np.load(
                safe_load(os.path.join(
                    directory_path,
                    _p.vector_phenotypes_raw,
                )),
                allow_pickle=True,
            )
        except (IOError, ValueError):
            phenotyper._logger.warning(
                "Could not load Vector Phenotypes, probably too old extraction, please rerun!",  # noqa: E501
            )
            vector_phenotypes = None

        try:
            vector_meta_phenotypes = np.load(
                safe_load(os.path.join(
                    directory_path,
                    _p.vector_meta_phenotypes_raw,
                )),
                allow_pickle=True,
            )
        except (IOError, ValueError):
            phenotyper._logger.warning(
                "Could not load Vector Meta Phenotypes, probably too old extraction, please rerun!",  # noqa: E501
            )
            vector_meta_phenotypes = None

        smooth_growth_data = np.load(
            safe_load(os.path.join(
                directory_path,
                _p.phenotypes_input_smooth,
            )),
            allow_pickle=True,
        )

        try:
            phenotyper._settings = jsonizer.load(os.path.join(
                directory_path,
                _p.phenotypes_extraction_params,
            ))
        except IOError:
            phenotyper._logger.warning(
                "Could not find stored extraction parameters, assuming defaults were used",  # noqa: E501
            )

        phenotyper.set('smooth_growth_data', smooth_growth_data)
        phenotyper.set('phenotypes', phenotypes)
        phenotyper.set('vector_phenotypes', vector_phenotypes)
        phenotyper.set('vector_meta_phenotypes', vector_meta_phenotypes)

        filter_path = os.path.join(directory_path, _p.phenotypes_filter)
        if os.path.isfile(filter_path):
            phenotyper._logger.info(
                "Loading previous filter {0}".format(filter_path),
            )
            try:
                phenotyper.set(
                    "phenotype_filter",
                    np.load(
                        safe_load(filter_path),
                        allow_pickle=True,
                    ),
                )
            except (ValueError, IOError):
                phenotyper._logger.warning(
                    "Could not load QC Filter, probably too old extraction, please rerun!",  # noqa: E501
                )

        offsets_path = os.path.join(
            directory_path,
            _p.phenotypes_reference_offsets,
        )
        if os.path.isfile(offsets_path):
            phenotyper.set(
                "reference_offsets",
                np.load(
                    safe_load(offsets_path),
                    allow_pickle=True,
                ),
            )

        normalized_phenotypes = os.path.join(
            directory_path,
            _p.normalized_phenotypes,
        )
        if os.path.isfile(normalized_phenotypes):
            try:
                phenotyper.set(
                    "normalized_phenotypes",
                    np.load(
                        safe_load(normalized_phenotypes),
                        allow_pickle=True,
                    ),
                )
            except (ValueError, IOError):
                phenotyper._logger.warning(
                    "Could not load Normalized Phenotypes, probably too old extraction, please rerun!",  # noqa: E501
                )

        filter_undo_path = os.path.join(
            directory_path,
            _p.phenotypes_filter_undo,
        )
        if os.path.isfile(filter_undo_path):
            try:
                phenotyper.set(
                    "phenotype_filter_undo",
                    pickle.load(safe_load(filter_undo_path)),
                )
            except EOFError:
                phenotyper._logger.warning(
                    "Could not load saved undo, file corrupt!",
                )

        meta_data_path = os.path.join(
            directory_path,
            _p.phenotypes_meta_data,
        )
        if os.path.isfile(meta_data_path):
            try:
                phenotyper.set(
                    "meta_data",
                    pickle.load(safe_load(meta_data_path)),
                )
            except EOFError:
                phenotyper._logger.warning(
                    "Could not load saved meta-data, file corrupt!",
                )

        return phenotyper

    @classmethod
    def LoadFromImageData(
        cls,
        path: str = '.',
        phenotype_inclusion: Optional[PhenotypeDataType] = None,
    ) -> "Phenotyper":
        """Loads image data files and performs an extraction

        This is what you use if you have only run an analysis or only
        want your `Phenotyper`-object to be free of previous feature
        extraction.

        Args:
            path: optional, default is current directory
            phenotype_inclusion: optional setting for inclusion level
                during phenotype extraction.
        """
        times, data = image_data.ImageData.read_image_data_and_time(path)
        instance = cls(data, times)
        if phenotype_inclusion is not None:
            instance.set_phenotype_inclusion_level(phenotype_inclusion)
        instance.extract_phenotypes()
        return instance

    @classmethod
    def LoadFromNumPy(
        cls,
        path: str,
        times_data_path=None,
        **kwargs,
    ):
        """Class Method used to create a Phenotype Strider from
        a saved numpy data array and a saved numpy times array.

        Parameters:
            path:
                The path to the data numpy file

            times_data_path:
                The path to the times numpy file
                If not supplied both paths are assumed
                to be named as:

                    some/path.data.npy
                    some/path.times.npy

                And path parameter is expexted to be
                'some/path' in this examply.

        Optional Parameters can be passed as keywords and will be
        used in instantiating the class.
        """
        data_directory = path
        if path.lower().endswith(".npy"):
            path = path[:-4]
            if path.endswith(".data"):
                path = path[:-5]

        if times_data_path is None:
            times_data_path = path + ".times.npy"

        if not os.path.isfile(data_directory):
            if os.path.isfile(times_data_path + ".data.npy"):
                times_data_path += ".data.npy"

            elif os.path.isfile(times_data_path + ".npy"):
                times_data_path += ".npy"

        return cls(
            np.load(
                safe_load(data_directory),
                allow_pickle=True,
            ),
            np.load(
                safe_load(times_data_path),
                allow_pickle=True,
            ),
            base_name=path,
            run_extraction=True,
            **kwargs
        )

    @staticmethod
    def is_segmentation_based_phenotype(phenotype) -> bool:
        return isinstance(phenotype, CurvePhaseMetaPhenotypes)

    @property
    def meta_data(self):
        return self._state.meta_data

    @property
    def raw_growth_data(self):
        return self._state.raw_growth_data

    @property
    def smooth_growth_data(self):
        return self._state.smooth_growth_data

    @property
    def curve_segments(self):
        try:
            return [
                self._state.vector_phenotypes[plate][
                    VectorPhenotypes.PhasesClassifications
                ] for plate in self._state.enumerate_plates
            ]

        except (ValueError, IndexError, TypeError, KeyError):
            return None

    @property
    def enumerate_plates(self):
        for index in self._state.enumerate_plates:
            yield index

    def enumerate_plate_positions(self, plate):
        shape = self._state.raw_growth_data[plate].shape[:-1]
        for pos_tup in zip(
            *np.unravel_index(np.arange(np.prod(shape)), shape)
        ):
            yield pos_tup

    @property
    def plate_shapes(self):
        for shape in self._state.plate_shapes:
            yield shape

    def load_meta_data(self, *meta_data_paths) -> bool:
        """Loads meta-data about the experiment based on paths to compatible
        files.

        See the wiki on how such files should be formatted

        Args:
            meta_data_paths:
                Any number of paths to files OpenOffice or Excel
                compatible that contains the meta data

        """
        m = MetaData2(
            tuple(self._state.plate_shapes),
            *(os.path.expanduser(p) for p in meta_data_paths)
        )
        if m.loaded:
            self._state.meta_data = m
            return True
        else:
            self._logger.warning(
                "New meta-data incompatible, keeping previous meta-data (if any existed).",  # noqa: E501
            )
            return False

    def find_in_meta_data(
        self,
        query,
        column=None,
        plates=None,
    ) -> StrainSelector:
        """Look for results for specific strains.

        Args:
            query: What to look for
            column: Optional, exact name of column to look in. If omitted,
                will search in all columns
            plates: Optional, what plates to include results from, should be a
                list of plate numbers, starting with index 0 for the first
                plate

        Returns: A StrainSelector object with the search results.

        """
        selection = self.meta_data.find(query, column=column)
        return StrainSelector(
            self._state,
            self._settings,
            tuple(
                (list(zip(*s)) if plates is None or i in plates else tuple())
                for i, s in enumerate(selection)
            )
        )

    def iterate_extraction(
        self,
        keep_filter=False,
    ) -> Generator[float, None, None]:
        self._logger.info(
            "Iteration started, will extract {0} phenotypes".format(
                self.get_number_of_phenotypes(),
            ),
        )

        if not self.has_smooth_growth_data:
            self._smoothen()
            self._logger.info("Smoothed")
            yield 0
        else:
            self._logger.info("No smoothing, data already smooth!")

        self.wipe_extracted_phenotypes(keep_filter)

        for x in self._calculate_phenotypes():
            self._logger.debug("Phenotype extraction iteration")
            yield x

        self._state.init_remove_filter_and_undo_actions(self._settings)

    def wipe_extracted_phenotypes(self, keep_filter: bool = False) -> None:
        """ This clears all extracted phenotypes but keeps the log2_curve data

        Args:
            keep_filter: Optional, if the markings of curves should be kept,
                default is to not keep them
        """
        self._state.wipe_extracted_phenotypes(keep_filter=keep_filter)

    def extract_phenotypes(
        self,
        keep_filter: bool = False,
        smoothing: Smoothing = Smoothing.PolynomialWeightedMulti,
        smoothing_coeffs={},
    ) -> None:
        """Extract phenotypes given the current inclusion level

        Args:
            keep_filter:
                Optional, if previous log2_curve marks on phenotypes should
                be kept or not. Default is to clear previous log2_curve
                marks
            smoothing:
                Optional, if smoothing should be redone.
                Default is not to redo it/keep smoothing.
                Alternatives are `Smoothing.MedianGauss` (as published in
                original Scan-o-matic manuscript.
                Or `Smoothing.Polynomial` for polynomial smoothing, or
                `Smoothing.PolynomialWeightedMulti` if fancy weighting of
                all relevant polynomials should be used.
            smoothing_coeffs:
                Optional dict of key-value parameters for the smoothing
                to override default values.

        See Also:
            Phenotyper.set_phenotype_inclusion_level:
                How to change what phenotypes are extracted
            Phenotyper.get_phenotype:
                Accessing extracted phenotypes.
            Phenotyper.normalize_phenotypes:
                Normalize phenotypes.
        """
        self.wipe_extracted_phenotypes(keep_filter)

        self._logger.info("Selecting smoothing.")

        if not self.has_smooth_growth_data and smoothing is Smoothing.Keep:
            self._logger.warning(
                "There was no previous smooth data but setting was to keep previous, will run default.",  # noqa: E501
            )
            self._poly_smoothen_raw_growth_weighted(**smoothing_coeffs)
        elif smoothing is Smoothing.MedianGauss:
            self._smoothen()
        elif smoothing is Smoothing.Polynomial:
            self._poly_smoothen_raw_growth(**smoothing_coeffs)
        elif smoothing is Smoothing.PolynomialWeightedMulti:
            self._poly_smoothen_raw_growth_weighted(**smoothing_coeffs)

        for _ in self._calculate_phenotypes():
            pass

        self._state.init_remove_filter_and_undo_actions(self._settings)
        self._logger.info("Phenotypes extracted")

    @property
    def has_smooth_growth_data(self) -> bool:
        return self._state.has_smooth_growth_data()

    @property
    def has_normalized_data(self) -> bool:
        return (
            self._normalizable_phenotypes is not None
            and self._state.has_normalized_data()
        )

    def _poly_smoothen_raw_growth(
        self,
        power: int = 3,
        time_delta: float = 5.1,
    ) -> None:
        assert power > 1, "Power must be 2 or greater"
        self._logger.info("Starting Polynomial smoothing")

        smooth_data = []
        times = self.times
        time_diffs = np.subtract.outer(times, times)
        filt = (time_diffs < time_delta) & (time_diffs > -time_delta)

        for id_plate, plate in enumerate(self._state.raw_growth_data):
            if plate is None:
                smooth_data.append(None)
                self._logger.info("Plate {0} has no data".format(id_plate + 1))
                continue

            log2_data = np.log2(plate).reshape(
                np.prod(plate.shape[:2]),
                plate.shape[-1],
            )
            smooth_plate = np.array(tuple(
                tuple(self._poly_smoothen_raw_growth_curve(
                    times,
                    log2_curve,
                    power,
                    filt,
                )) for log2_curve in log2_data
            ))

            self._logger.info("Plate {0} data polynomial smoothed".format(
                id_plate + 1,
            ))

            smooth_data.append(smooth_plate.reshape(plate.shape))

        self._state.smooth_growth_data = np.array(smooth_data)
        self._logger.info("Completed Polynomial smoothing")

    def _poly_smoothen_raw_growth_weighted(
        self,
        power: int = 3,
        time_delta: float = 5.1,
        gauss_sigma: float = 1.5,
        apply_median: bool = True,
        edge_condition: EdgeCondition = EdgeCondition.Reflect,
    ) -> None:
        assert power > 1, "Power must be 2 or greater"

        self._logger.info(
            "Starting Weighted Multi-Polynomial smoothing"
            " (Power {0}; Time delta {1}h; Gauss sigma {2}h; {3}; {4}".format(
                power,
                time_delta,
                gauss_sigma,
                "Median filter" if apply_median else "No median filter",
                edge_condition
            ),
        )

        median_kernel = np.ones((1, self._settings.median_kernel_size))
        smooth_data = []
        times = self.times
        left_filt, right_filt = get_edge_condition_timed_filter(
            times,
            time_delta,
            edge_condition,
        )
        left = left_filt.sum()
        right = right_filt.sum()

        times = filter_edge_condition(
            times,
            left_filt,
            right_filt,
            edge_condition,
            extrapolate_values=True,
            logger=self._logger,
        )

        self._logger.info(
            "Data with edge condition has length {0}, ({1} {2})".format(
                times.size,
                left,
                right,
            ),
        )
        time_diffs = np.subtract.outer(times, times)
        filt = (time_diffs < time_delta) & (time_diffs > -time_delta)

        for id_plate, plate in enumerate(self._state.raw_growth_data):
            if plate is None:
                smooth_data.append(None)
                self._logger.info("Plate {0} has no data".format(id_plate + 1))
                continue

            log2_data = np.log2(plate).reshape(
                np.prod(plate.shape[:2]),
                plate.shape[-1],
            )
            epsilon = np.finfo(log2_data.dtype).eps

            if apply_median:
                log2_data[...] = median_filter(
                    log2_data,
                    footprint=median_kernel,
                    mode='reflect',
                )

            smooth_plate = [None] * log2_data.shape[0]
            for id_curve, log2_curve in enumerate(log2_data):

                log2_curve = filter_edge_condition(
                    log2_curve,
                    left_filt,
                    right_filt,
                    edge_condition,
                    logger=self._logger,
                )
                p, r, r0 = zip(*self._poly_estimate_raw_growth_curve(
                    times,
                    log2_curve,
                    power,
                    filt,
                ))

                if any(r0val < epsilon for r0val in r0):

                    self._logger.warning(
                        "Curve {0} has long stretches of (near) identical data and is probably corrupt".format(  # noqa: E501
                            np.unravel_index(id_curve, plate.shape[:2]),
                        ),
                    )

                if any(rval == 0 for rval in r):
                    self._logger.warning(
                        "Curve {0} is probably overfitted somewhere because polynomial residual was 0".format(  # noqa: E501
                            np.unravel_index(id_curve, plate.shape[:2]),
                        ),
                    )

                smooth_plate[id_curve] = tuple(self._multi_poly_smooth(
                    times,
                    p,
                    np.array(r),
                    np.array(r0),
                    filt,
                    gauss_sigma,
                ))[left: -right if right else None]

            self._logger.info(
                "Plate {0} data polynomial smoothed ({1} curves, {2} data-points per curve)".format(  # noqa: E501
                    id_plate + 1,
                    len(smooth_plate),
                    len(smooth_plate[0])
                ),
            )

            smooth_data.append(np.array(smooth_plate).reshape(plate.shape))

        self._state.smooth_growth_data = np.array(smooth_data)

        self._logger.info("Completed Weighted Multi-Polynomial smoothing")

    @staticmethod
    def _multi_poly_smooth(times, polys, r, r0, filt, gauss_sigma: float):
        included = [v is not None for v in r]
        for f in filt:

            f2 = f & included
            t = times[f2].mean()
            w1 = norm.pdf(times[f2], loc=t, scale=gauss_sigma)
            w2 = 1 - r[f2] / r0[f2]
            w = w1 * w2
            yield (
                w * tuple(np.power(2, p(t)) for p, i in zip(polys, f2) if i)
            ).sum() / w.sum()

    def _poly_estimate_raw_growth_curve(self, times, log2_data, power, filt):
        finites = np.isfinite(log2_data)

        for _, f in zip(times, filt):
            f2 = f & finites
            x = times[f2]
            y = log2_data[f2]
            p = None
            yielded = False
            for pwr in range(power, -1, -1):
                try:
                    p, r, _, _, _ = np.polyfit(x, y, power, full=True)
                except TypeError:
                    yielded = True
                    yield None, None, None
                    break
                else:
                    if r.size > 1:
                        break

            if not yielded:
                try:
                    yield np.poly1d(p), r[0] / f2.sum(), np.var(y)
                except IndexError:
                    # This is invoked if only two measurements have finite
                    # data for the entire interval and the values of these are
                    # identical. Heuristically the residuals are set so we
                    # have absolute confidence in this result
                    self._logger.warning(
                        "Encountered large gap in data ({0}/{1} have values)".format(  # noqa: E501
                            f2.sum(),
                            f.sum(),
                        ),
                    )
                    yield np.poly1d(p),  0, 1

    @staticmethod
    def _poly_smoothen_raw_growth_curve(times, log2_data, power: int, filt):

        finites = np.isfinite(log2_data)

        for t, f in zip(times, filt):
            x = times[f]
            y = log2_data[f]
            fin = finites[f]

            try:
                p = np.polyfit(x[fin], y[fin], power)
            except TypeError:
                yield np.nan
            else:
                yield np.power(2, np.poly1d(p)(t))

    def _smoothen(self) -> None:
        self.set("smooth_growth_data", self._state.raw_growth_data.copy())
        self._logger.info("Smoothing Started")
        median_kernel = np.ones((1, self._settings.median_kernel_size))
        times = self.times

        # This conversion is done to reflect that previous filter worked on
        # indices and expected ratio to hours is 1:3.
        gauss_kwargs = {
            'sigma': (
                self._settings.gaussian_filter_sigma / 3.0
                if self._settings.gaussian_filter_sigma == 5
                else self._settings.gaussian_filter_sigma
            ),
        }

        for plate_id, plate in enumerate(self._state.smooth_growth_data):
            if plate is None:
                self._logger.info("Plate {0} has no data, skipping".format(
                    plate_id + 1,
                ))
                continue

            plate_as_flat = np.lib.stride_tricks.as_strided(
                plate,
                shape=(plate.shape[0] * plate.shape[1], plate.shape[2]),
                strides=(plate.strides[1], plate.strides[2]),
            )

            plate_as_flat[...] = median_filter(
                plate_as_flat,
                footprint=median_kernel,
                mode='reflect',
            )

            plate_as_flat[...] = tuple(
                merge_convolve(v, times, func_kwargs=gauss_kwargs)
                for v in plate_as_flat
            )

            self._logger.info("Smoothing of plate {0} done".format(
                plate_id + 1,
            ))

        self._logger.info("Smoothing Done")

    def _calculate_phenotypes(self):
        if (
            self._state.times_data.shape[0]
            - (self._settings.linear_regression_size - 1)
            <= 0
        ):
            self._logger.error(
                "Refusing phenotype extractions since number of scans are less than used in the linear regression",  # noqa: E501
            )
            return

        times_strided = self.times_strided
        flat_times = self._state.times_data
        index_for_48h = np.abs(
            np.subtract.outer(self._state.times_data, [48]),
        ).argmin()

        all_phenotypes = []
        all_vector_phenotypes = []
        all_vector_meta_phenotypes = []

        regression_size = self._settings.linear_regression_size
        position_offset = (regression_size - 1) // 2
        phenotypes_count = self.get_number_of_phenotypes()

        total_curves = float(self.number_of_curves)

        self._logger.info(
            "Phenotypes (N={0}), extraction started for {1} curves".format(
                phenotypes_count,
                int(total_curves),
            ),
        )

        curves_in_completed_plates = 0
        phenotypes_inclusion = self._settings.phenotypes_inclusion

        if phenotypes_inclusion is not PhenotypeDataType.Trusted:
            self._logger.warning(
                "Will extract phenotypes beyond those that are trusted, this is not recommended!"  # noqa: E501
                " It is your responsibility to verify the validity of those phenotypes!"  # noqa: E501
            )

        for id_plate, plate in enumerate(self._state.smooth_growth_data):
            if plate is None:
                all_phenotypes.append(None)
                all_vector_phenotypes.append(None)
                all_vector_meta_phenotypes.append(None)
                continue

            plate_flat_regression_strided = (
                self._get_plate_linear_regression_strided(plate)
            )

            phenotypes = {
                p: np.zeros(plate.shape[:2], dtype=float) * np.nan
                for p in Phenotypes if phenotypes_inclusion(p)}

            plate_size = np.prod(plate.shape[:2])
            self._logger.info("Plate {0} has {1} curves".format(
                id_plate + 1,
                plate_size,
            ))

            vector_phenotypes = {
                p: np.zeros(plate.shape[:2], dtype=object) * np.nan
                for p in VectorPhenotypes if phenotypes_inclusion(p)
            }
            vector_meta_phenotypes = {}

            all_phenotypes.append(phenotypes)
            all_vector_phenotypes.append(vector_phenotypes)
            all_vector_meta_phenotypes.append(vector_meta_phenotypes)

            for pos_index, pos_data in enumerate(
                plate_flat_regression_strided,
            ):
                id1 = pos_index % plate.shape[1]
                id0 = pos_index // plate.shape[1]

                curve_data = get_preprocessed_data_for_phenotypes(
                    curve=plate[id0, id1],
                    curve_strided=pos_data,
                    flat_times=flat_times,
                    times_strided=times_strided,
                    index_for_48h=index_for_48h,
                    position_offset=position_offset,
                )

                curve_has_data = True

                if curve_data['curve_smooth_growth_data'].mask.all():

                    self._logger.warning(
                        "Position ({0}, {1}) on plate {2} seems void of data".format(  # noqa: E501
                            id0,
                            id1,
                            id_plate + 1,
                        ),
                    )
                    curve_has_data = False

                else:
                    for phenotype in Phenotypes:
                        if not phenotypes_inclusion(phenotype):
                            continue

                        if PhenotypeDataType.Scalar(phenotype):
                            phenotypes[phenotype][id0, id1] = phenotype(
                                **curve_data,
                            )

                if (
                    curve_has_data
                    and (
                        phenotypes_inclusion(
                            VectorPhenotypes.PhasesClassifications,
                        )
                        or phenotypes_inclusion(
                            VectorPhenotypes.PhasesPhenotypes,
                        )
                    )
                ):

                    phases, phases_phenotypes = get_phase_analysis(
                        self,
                        id_plate,
                        (id0, id1),
                        experiment_doublings=phenotypes[
                            Phenotypes.ExperimentPopulationDoublings
                        ][id0, id1]
                    )

                    if phenotypes_inclusion(
                        VectorPhenotypes.PhasesClassifications,
                    ):
                        vector_phenotypes[
                            VectorPhenotypes.PhasesClassifications
                        ][id0, id1] = phases
                    if phenotypes_inclusion(
                        VectorPhenotypes.PhasesPhenotypes,
                    ):
                        vector_phenotypes[
                            VectorPhenotypes.PhasesPhenotypes
                        ][id0, id1] = phases_phenotypes

                if id1 == 0:

                    self._logger.debug("Done plate {0} pos {1} {2}".format(
                        id_plate,
                        id0,
                        id1,
                    ))

                    self._logger.info("Plate {1} growth phenotypes {0:.1f}% done".format(  # noqa: E501
                        100.0 * (pos_index + 1.0) / plate_size,
                        id_plate + 1,
                    ))

                    yield (
                        curves_in_completed_plates + pos_index + 1.0
                    ) / total_curves

            for phenotype in CurvePhaseMetaPhenotypes:

                self._logger.info("Extracting {0} for plate {1}".format(
                    phenotype.name,
                    id_plate + 1,
                ))

                if not phenotypes_inclusion(phenotype):
                    continue

                if not phenotypes_inclusion(VectorPhenotypes.PhasesPhenotypes):
                    self._logger.warning(
                        "Can't extract {0} because {1} has not been included.".format(  # noqa: E501
                            phenotype,
                            VectorPhenotypes.PhasesPhenotypes,
                        ),
                    )
                    continue

                phenotype_data = extract_phenotypes(
                    vector_phenotypes[VectorPhenotypes.PhasesPhenotypes],
                    phenotype,
                    phenotypes,
                )

                vector_meta_phenotypes[phenotype] = phenotype_data.astype(
                    float,
                )

            self._logger.info("Plate {0} Done".format(id_plate + 1))
            curves_in_completed_plates += (
                0 if plate is None else plate_flat_regression_strided.shape[0]
            )

        self._state.phenotypes = np.array(all_phenotypes)
        self._state.vector_phenotypes = np.array(all_vector_phenotypes)
        self._state.vector_meta_phenotypes = np.array(
            all_vector_meta_phenotypes,
        )
        self._state.normalized_phenotypes = None
        self._logger.info("Phenotype Extraction Done")

    def _get_plate_linear_regression_strided(self, plate):
        if plate is None:
            return None

        return np.lib.stride_tricks.as_strided(
            plate,
            shape=(
                plate.shape[0] * plate.shape[1],
                plate.shape[2] - (self._settings.linear_regression_size - 1),
                self._settings.linear_regression_size,
            ),
            strides=(
                plate.strides[1],
                plate.strides[2],
                plate.strides[2],
            ),
        )

    def add_phenotype_to_normalization(
        self,
        phenotype: Union[Phenotypes, CurvePhasePhenotypes],
    ):
        """ Add a phenotype to the set of phenotypes that are normalized.

        Only those for which there is previously extracted non-normalized data
        are included in the normalization, so you may need to change inclusion
        level and rerun feature extraction before any change have affect on
        the data produced by normalization.

        Args:
            phenotype: The phenotype to include.
                Typically this is one of
                    * `.growth_phenotypes.Phenotypes`
                      (Based on direct analysis of curves)
                    * `.curve_phase.phenotypes.CurvePhasePhenotypes`
                      (Based on segmenting curves into phases)

        Notes:
            If the current module `phenotyper` was imported, it will have
            imported the `phenotyper.Phenotypes` and
            `phenotyper.CurvePhasePhenotypes`. For more information on
            these refer to their respective help.

        See Also:
            Phenotyper.remove_phenotype_from_normalization:
                Removing phenotype from normalization
            Phenotyper.set_phenotype_inclusion_level:
                Setting which phenotypes are extracted.
            Phenotyper.normalize_phenotypes: Normalize phenotypes
        """
        self._normalizable_phenotypes.add(phenotype)

    def remove_phenotype_from_normalization(
        self,
        phenotype: Union[Phenotypes, CurvePhasePhenotypes],
    ):
        """Removes a phenotype so that it is not normalized.

        Args:
            phenotype: The phenotype to include.
                Typically this is one of
                    * `.growth_phenotypes.Phenotypes`
                      (Based on direct analysis of curves)
                    * `.curve_phase.phenotypes.CurvePhasePhenotypes`
                      (Based on segmenting curves into phases)

        See Also:
            Phenotyper.add_phenotype_to_normalization:
                Adding phenotype to normalization
            Phenotyper.set_phenotype_inclusion_level:
                Setting which phenotypes are extracted.
            Phenotyper.normalize_phenotypes: Normalize phenotypes
        """
        self._normalizable_phenotypes.remove(phenotype)

    def get_normalizable_phenotypes(self):
        return self._normalizable_phenotypes

    def get_curve_phases(self, plate, outer, inner):
        try:
            val = self._state.vector_phenotypes[plate][
                VectorPhenotypes.PhasesClassifications
            ][outer, inner]
            if isinstance(val, np.ma.masked_array):
                return val
            return None
        except (ValueError, IndexError, TypeError, KeyError):
            return None

    def get_curve_phases_at_time(self, plate, time_index):
        try:
            p = self._state.vector_phenotypes[plate][
                VectorPhenotypes.PhasesClassifications
            ]
            # The init value is illegal, no phase has that value. On purpose
            arr = np.ones(p.shape, dtype=int) * -2
            for id1, id2 in product(*(range(d) for d in p.shape)):
                v = self.get_curve_phases(plate, id1, id2)
                if v is not None:
                    arr[id1, id2] = v[time_index]
            return np.ma.masked_array(arr, arr == -2)
        except (ValueError, IndexError, TypeError, KeyError):
            return None

    def get_curve_phase_data(self, plate, outer, inner):
        try:
            return self._state.vector_phenotypes[plate][
                VectorPhenotypes.PhasesPhenotypes
            ][outer, inner]
        except (ValueError, IndexError, TypeError, KeyError):
            return None

    @property
    def phenotypes(self):
        return tuple(p for p in self._settings.phenotypes_inclusion())

    @property
    def phenotypes_that_normalize(self):
        return tuple(
            v for v in
            set(self._normalizable_phenotypes.intersection(
                self._settings.phenotypes_inclusion(),
            ))
        )

    @property
    def phenotypes_that_dont_normalize(self):
        return tuple(
            set(self.phenotypes).difference(self.phenotypes_that_normalize),
        )

    def set_control_surface_offsets(
        self,
        offset: Callable[[], Offsets],
        plate: Optional[int] = None,
    ) -> None:
        """Set which of four offsets is the control surface positions.

        When a new `Phenotyper` instance is created, the offset is assumed to
        be `Offsets.LowerRight`.

        Args:
            offset: The offset used, one of the `.norm.Offsets`.
            plate: Optional, plate index (start at 0 for first plate), default
                is to set offset to all plates.
        """
        if plate is None:
            self._state.reference_surface_positions = [
                offset() for _ in self._state.enumerate_plates
            ]
        else:
            self._state.reference_surface_positions[plate] = offset()

    def get_control_surface_offset(
        self,
        plate: int,
    ) -> Union[Offsets, int]:
        try:
            return self._state.reference_surface_positions[plate]
        except IndexError:
            return 0

    def normalize_phenotypes(
        self,
        method: NormalizationMethod = NormalizationMethod.Log2Difference,
    ):
        """Normalize phenotypes.

        See Also:
            Phenotyper.get_phenotype: Getting phenotypes, including normalized
                versions.
            Phenotyper.set_control_surface_offsets: setting which offset is
                the control surface
            Phenotyper.add_phenotype_to_normalization: Adding phenotype to
                normalization
            Phenotyper.remove_phenotype_from_normalization: Removing phenotype
                from normalization
            Phenotyper.set_phenotype_inclusion_level: Setting which phenotypes
                are extracted.
        """
        if self._state.normalized_phenotypes is None:
            self._state.normalized_phenotypes = np.array(
                [{} for _ in self._state.enumerate_plates],
                dtype=object,
            )

        norm_method = norm_by_log2_diff
        if method == NormalizationMethod.SignalToNoise:
            norm_method = norm_by_signal_to_noise
            self._logger.warning(
                "Using {0} to normalize hasn't been fully vetted".format(
                    method,
                ),
            )
        elif method == NormalizationMethod.Log2DifferenceCorrelationScaled:
            norm_method = norm_by_log2_diff_corr_scaled
            self._logger.warning(
                "Using {0} to normalize hasn't been fully vetted".format(
                    method,
                ),
            )
        elif method == NormalizationMethod.Difference:
            norm_method = norm_by_diff
            self._logger.warning(
                "Using {0} to normalize hasn't been fully vetted".format(
                    method,
                ),
            )

        for phenotype in self._normalizable_phenotypes:
            if self._settings.phenotypes_inclusion(phenotype) is False:
                self._logger.info(
                    "Because {0} has not been extracted it is skipped".format(
                        phenotype,
                    ),
                )
                continue

            try:
                data = self.get_phenotype(phenotype)
            except (ValueError, KeyError):
                self._logger.info(
                    "{0} had not been extracted, so skipping it".format(
                        phenotype,
                    ),
                )
                continue

            if all(v is None for v in data):
                self._logger.info(
                    "{0} had not been extracted, so skipping it".format(
                        phenotype,
                    ),
                )
                continue

            data = [
                None if plate is None else plate.filled() for plate in data
            ]

            for id_plate, plate in enumerate(get_normalized_data(
                data,
                self._state.reference_surface_positions,
                method=norm_method,
            )):
                self._state.normalized_phenotypes[id_plate][phenotype] = plate

    @property
    def number_of_curves(self):
        return sum(
            p.shape[0] * p.shape[1] if (p is not None and p.ndim > 1) else 0
            for p in self._state.raw_growth_data
        )

    def get_number_of_phenotypes(self, normed=False):
        return len(
            self.phenotypes_that_normalize if normed else self.phenotypes
        )

    @property
    def generation_times(self):
        return self.get_phenotype(Phenotypes.GenerationTime)

    def get_reference_median(self, phenotype) -> tuple[float, ...]:
        """ Getting reference position medians per plate.

        Args:
            phenotype: The phenotype of interest.
        """
        return self._state.get_reference_median(self._settings, phenotype)

    def get_phenotype(
        self,
        phenotype: Union[Phenotypes, CurvePhasePhenotypes],
        filtered: bool = True,
        norm_state: NormState = NormState.Absolute,
        reference_values: Optional[tuple[float, ...]] = None,
        **kwargs,
    ) -> list[Optional[Union[FilterArray, np.ndarray]]]:
        """Getting phenotype data

        Args:
            phenotype:/
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
        return self._state.get_phenotype(
            self._settings,
            phenotype,
            filtered=filtered,
            norm_state=norm_state,
            reference_values=reference_values,
            **kwargs,
        )

    @property
    def analysed_phenotypes(self):
        for p in Phenotypes:
            if (
                self._settings.phenotypes_inclusion(p)
                and self._state.has_phenotype_on_any_plate(p)
            ):
                yield p

    @property
    def times(self):
        return self._state.times_data

    @times.setter
    def times(self, value):
        assert (
            isinstance(value, np.ndarray)
            or isinstance(value, list)
            or isinstance(value, tuple)
        ), "Invalid time series {0}".format(value)

        if isinstance(value, np.ndarray) is False:
            value = np.array(value, dtype=float)

        diffs = np.diff(value)
        diffs = np.round(diffs / np.median(diffs)).astype(int)
        if not (diffs == 1).all():
            diffs_where = np.where(diffs > 1)[0]
            self._logger.warning(
                "There are gaps in the time series at times: {0}".format(
                    ", ".join([
                        "{0} - {1}".format(a, b)
                        for a, b in zip(
                            value[diffs_where],
                            value[diffs_where + 1],
                        )
                    ])
                ),
            )
        self._state.times_data = value

    @property
    def times_strided(self):
        return np.lib.stride_tricks.as_strided(
            self._state.times_data,
            shape=(
                self._state.times_data.shape[0]
                - (self._settings.linear_regression_size - 1),
                self._settings.linear_regression_size,
            ),
            strides=(
                self._state.times_data.strides[0],
                self._state.times_data.strides[0],
            ),
        )

    def get_derivative(self, plate, position):
        return get_derivative(
            self._get_plate_linear_regression_strided(
                self.smooth_growth_data[plate][position].reshape(
                    1,
                    1,
                    self.times.size,
                ),
            )[0],
            self.times_strided,
        )[0]

    def get_chapman_richards_data(
        self,
        plate: int,
        position: tuple[int, ...],
    ) -> tuple[
        np.ndarray,
        Optional[tuple[Optional[float], Optional[float]]],
        Optional[tuple[np.ndarray, np.ndarray]],
        Optional[tuple],
    ]:
        """Get the chapman ritchard model information

        Args:
            plate: Plate index
            position: Position tuple

        Returns:
            (`y_hat`, (`fit`, `dydt_fit`), (`data_dydt`, `model_dydt`),
            `params`)

            y_hat:
                Log_2 population size model based on chapman richards
                growth model
            fit:
                The fit of the model (float) or
                `None` if model is missing,
            dydt_fit:
                The fit of the model's first derivative to
                the data's derivative or `None` if model is missing,
            data_dydt:
                First derivative of the growth data
            model_dydt:
                First derivative of the model data
            params:
                The parameter tuple for the model
                or `None` if model is missing
        """
        if not self._state.has_phenotypes_for_plate(plate):
            return np.array([]), None, None, None

        try:
            p1 = self.get_phenotype(Phenotypes.ChapmanRichardsParam1)[plate][
                position
            ]
            p2 = self.get_phenotype(Phenotypes.ChapmanRichardsParam2)[plate][
                position
            ]
            p3 = self.get_phenotype(Phenotypes.ChapmanRichardsParam3)[plate][
                position
            ]
            p4 = self.get_phenotype(Phenotypes.ChapmanRichardsParam4)[plate][
                position
            ]
            d = self.get_phenotype(Phenotypes.ChapmanRichardsParamXtra)[plate][
                position
            ]
            fit = self.get_phenotype(Phenotypes.ChapmanRichardsFit)[plate][
                position
            ]
        except TypeError:
            return np.array([]), None, None, None

        log2_model_y_data = get_chapman_richards_4parameter_extended_curve(
            self.times,
            p1,
            p2,
            p3,
            p4,
            d,
        )
        log2_y_data = np.log2(self.smooth_growth_data[plate][position])

        dydt = convolve(log2_y_data, [-1, 1], mode='valid')
        dydt_model = convolve(log2_model_y_data, [-1, 1], mode='valid')

        finites = np.isfinite(dydt)
        delta = (dydt - dydt_model)[finites]
        dydt_fit = (
            1.0
            - np.square(delta).sum()
            / np.square(dydt[finites] - dydt[finites].mean()).sum()
        )

        return (
            log2_model_y_data,
            (fit, dydt_fit),
            (dydt, dydt_model),
            (p1, p2, p3, p4, d),
        )

    def get_quality_index(self, plate: int):
        shape = self._state.get_plate_shape(plate)

        try:
            gt = self.get_phenotype(Phenotypes.GenerationTime)[plate].data
        except (AttributeError, IndexError, ValueError):
            gt = np.ones(shape)

        try:
            gt_err = self.get_phenotype(
                Phenotypes.GenerationTimeStErrOfEstimate,
            )[plate].data
        except (AttributeError, IndexError, ValueError):
            gt_err = np.ones(shape)

        try:
            cr_fit = self.get_phenotype(
                Phenotypes.ChapmanRichardsFit,
            )[plate].data
        except (AttributeError, IndexError, ValueError):
            cr_fit = np.ones(shape)

        try:
            lag = self.get_phenotype(Phenotypes.GrowthLag)[plate].data
        except (AttributeError, IndexError, ValueError):
            lag = np.ones(shape)

        try:
            growth = self.get_phenotype(
                Phenotypes.ExperimentGrowthYield,
            )[plate].data
        except (AttributeError, IndexError, ValueError):
            growth = np.ones(shape)

        gt_mean = gt[np.isfinite(gt)].mean()
        lag_mean = lag[np.isfinite(lag)].mean()
        growth_mean = growth[np.isfinite(growth)].mean()

        badness = (
            np.abs(gt - gt_mean) / gt_mean
            + gt_err * 100
            + (1 - cr_fit.clip(0, 1)) * 25
            + np.abs(lag - lag_mean) / lag_mean
            + np.abs(growth - growth_mean) / growth
        )

        return np.unravel_index(badness.ravel().argsort()[::-1], badness.shape)

    @staticmethod
    def _data_lacks_data(data):
        """ This checks if there is data in the data.

        Due to https://github.com/numpy/numpy/issues/10328
        this check needs to be overly complex
        """
        def _arr_tester(arr):
            try:
                val = arr.any()
                if isinstance(val, np.bool_):
                    return val
                elif val is None:
                    return False
                else:
                    raise ValueError("Any check failed")
            except ValueError:
                return any(
                    e.any() for e in arr.ravel() if isinstance(e, np.ndarray)
                )

        def _plate_tester(p):
            if p is None:
                return False
            elif isinstance(p, np.ndarray):
                return _arr_tester(p)
            elif isinstance(p, dict):
                return any(
                    False if v is None else _arr_tester(v) for v in p.values()
                )
            else:
                raise ValueError("Unexpected plate data type {} ({})".format(
                    type(p),
                    p,
                ))

        if isinstance(data, np.ndarray):
            return (
                data.size == 0
                or data.ndim == 0
                or not any(_plate_tester(plate) for plate in data)
            )
        return True

    def _set_phenotypes(self, data: Optional[Any]):
        allowed = False
        if self._data_lacks_data(data):
            self._state.phenotypes = None
        else:
            self._state.phenotypes = self._convert_phenotype_to_current(data)
            allowed = True
        self._state.init_remove_filter_and_undo_actions(self._settings)
        self._init_default_offsets()
        return allowed

    def _set_normalized_phenotypes(self, data):
        allowed = False
        if self._data_lacks_data(data):
            self._state.normalized_phenotypes = None
        else:
            self._state.normalized_phenotypes = data
            allowed = True
        self._init_default_offsets()
        return allowed

    def _set_vector_phenotypes(self, data):
        allowed = False
        if self._data_lacks_data(data):
            self._state.vector_phenotypes = None
        else:
            self._state.vector_phenotypes = data
            allowed = True
        self._state.init_remove_filter_and_undo_actions(self._settings)
        self._init_default_offsets()
        return allowed

    def _set_vector_meta_phenotypes(self, data):
        allowed = False
        if self._data_lacks_data(data):
            self._state.vector_meta_phenotypes = None
        else:
            self._state.vector_meta_phenotypes = data
            allowed = True

        self._state.init_remove_filter_and_undo_actions(self._settings)
        self._init_default_offsets()
        return allowed

    def _set_smooth_growth_data(self, data: Optional[np.ndarray]) -> bool:
        if self._data_lacks_data(data):
            self._state.smooth_growth_data = None
            return False
        else:
            self._state.smooth_growth_data = data
            return True

    def _set_phenotype_filter_undo(self, data):
        allowed = False
        if isinstance(data, tuple) and all(isinstance(q, deque) for q in data):
            self._state.phenotype_filter_undo = data
            allowed = True
        else:
            self._logger.warning("Not a proper undo history")

        self._state.init_remove_filter_and_undo_actions(self._settings)
        return allowed

    def _set_phenotype_filter(self, data):
        allowed = False
        if (
            isinstance(data, np.ndarray)
            and (data.size == 0 or data.size == 1 and not data.shape)
        ):
            self._state.phenotype_filter = None
        elif all(
            True if plate is None else isinstance(plate, dict)
            for plate in data
        ):
            self._state.phenotype_filter = data
            allowed = True
        else:
            self._state.phenotype_filter = (
                self._convert_to_current_phenotype_filter(data)
            )
            allowed = True
        self._state.init_remove_filter_and_undo_actions(self._settings)
        return allowed

    def _set_meta_data(self, data):
        if isinstance(data, MetaData2) or data is None:
            self._state.meta_data = data
            return True
        else:
            self._logger.warning("Not a valid meta data type")
            return False

    def set(self, data_type, data):

        if data_type == 'phenotypes':
            return self._set_phenotypes(data)
        elif data_type == 'reference_offsets':
            self._state.reference_surface_positions = data
            return True
        elif data_type == 'normalized_phenotypes':
            return self._set_normalized_phenotypes(data)
        elif data_type == 'vector_phenotypes':
            return self._set_vector_phenotypes(data)
        elif data_type == 'vector_meta_phenotypes':
            return self._set_vector_meta_phenotypes(data)
        elif data_type == 'smooth_growth_data':
            return self._set_smooth_growth_data(data)
        elif data_type == "phenotype_filter_undo":
            return self._set_phenotype_filter_undo(data)
        elif data_type == "phenotype_filter":
            return self._set_phenotype_filter(data)
        elif data_type == "meta_data":
            return self._set_meta_data(data)
        else:
            self._logger.warning('Unknown type of data {0}'.format(data_type))
            return False

    def _convert_phenotype_to_current(self, data):
        has_warned = False
        store = []
        for plate in data:

            if plate is None:
                store.append(None)

            if not isinstance(plate, dict):
                new_plate = {}
                store.append(new_plate)

                if not has_warned:
                    has_warned = True
                    self._logger.warning(
                        "Outdated phenotypes format, guessing which were extracted and converting to current format."  # noqa: E501
                        "To faster load in the future and get rid of this message, save current state."  # noqa: E501
                    )

                try:
                    n_phenotypes = plate.shape[2]
                except IndexError:
                    self._logger.error(
                        "Plate format not understood, old phenotype extraction not accepted",  # noqa: E501
                    )
                    return None

                for id_phenotype in range(n_phenotypes):
                    if plate[..., id_phenotype].any():
                        try:
                            phenotype = Phenotypes(id_phenotype)
                        except ValueError:
                            self._logger.error(
                                "There were phenotypes for index {0} but no known phenotype with that index.".format(  # noqa: E501
                                    id_phenotype
                                ) + " Data omitted.",
                            )
                            continue

                        new_plate[phenotype] = plate[..., id_phenotype]

        if has_warned is False:
            return data

        if np.unique(tuple(
            hash(tuple(p.keys())) for p in store if p is not None
        )) != 1:
            self._logger.warning(
                "The plates don't agree on what phenotypes were extracted, you should tread carefully or better yet:"  # noqa: E501
                " rerun feature extraction.",
            )

        return np.array(store)

    def _convert_to_current_phenotype_filter(self, data):

        self._logger.info("Converting old filter format to new.")
        self._logger.warning(
            "If you save the state the qc-filter will not be readable to old scan-o-matic qc.",  # noqa: E501
        )
        new_data = []
        for id_plate, plate in enumerate(data):
            if plate is None or plate.size == 0:
                new_data.append(None)
                continue

            if plate.ndim == 3:
                new_plate = {}

                for id_phenotype in range(plate.shape[-1]):
                    phenotype = plate[..., id_phenotype]
                    if (
                        phenotype.dtype == bool
                        or np.unique(phenotype).max() == 1
                    ):
                        phenotype = (
                            phenotype.astype(np.uint8)
                            * Filter.UndecidedProblem.value
                        )
                    else:
                        phenotype = phenotype.astype(np.uint8)
                    phenotype.clip(
                        min(f.value for f in Filter),
                        max(f.value for f in Filter),
                    )

                    try:
                        new_plate[Phenotypes(id_phenotype)] = phenotype
                    except ValueError:
                        self._logger.warning(
                            "Saved data had a Phenotype of index {0}, this is not a valid Phenotype".format(  # noqa: E501
                                id_phenotype,
                            ),
                        )

                new_data.append(new_plate)

            else:

                self._logger.error(
                    "Skipping previous phenotype filter of plate {0} because not understood".format(  # noqa: E501
                        id_plate + 1,
                    ),
                )
                new_data.append(None)

        return np.array(new_data)

    def _init_default_offsets(self):
        if (not self._state.has_reference_surface_positions()):
            self.set_control_surface_offsets(Offsets.LowerRight)

    def infer_filter(self, template, *phenotypes):
        """Transfer all marks on one phenotype to other phenotypes.

        Note that the Filter.OK is not transferred, thus not replacing any
        existing non Filter.OK marking for those positions.

        :param template: The phenotype used as source
        :param phenotypes: The phenotypes that should be updated
        """
        self._logger.warning("Inferring is done without ability to undo.")

        template_filt = {
            plate: self._state.phenotype_filter[plate][template]
            for plate in self._state.enumerate_plates
        }

        for mark in Filter:
            if mark == Filter.OK:
                continue

            for phenotype in phenotypes:
                for plate in self._state.enumerate_plates:
                    if phenotype in self._state.phenotype_filter[plate]:
                        self._state.phenotype_filter[plate][phenotype][
                            template_filt[plate] == mark.value
                        ] = mark.value

    def get_curve_qc_filter(self, plate, threshold=0.8):
        filt = self._state.phenotype_filter[plate]
        if filt is None:
            return filt

        filt = np.array(filt.values())
        return (
            (np.sum(filt, axis=0) / filt.shape[0] > threshold)
            | np.any(
                (filt == Filter.NoGrowth.value) | (filt == Filter.Empty.value),
                axis=0,
            )
        )

    def add_position_mark(
        self,
        plate,
        positions,
        phenotype=None,
        position_mark: Filter = Filter.BadData,
        undoable: bool = True,
    ) -> bool:
        """ Adds log2_curve mark for position or set of positions.

        Args:
            plate: The plate index (0 for firs)
            positions: Tuple of positions to be marked. _NOTE_: It must be a
                tuple and first index is 0,
                e.g. `(1, 2)` will mark the the second row, third column.
                If several positions should be marked at once the coordinates
                should be structured as a tuple of two tuples, first with the
                rows and second with the columns.
                e.g. `((0, 0, 1), (0, 1, 0))` will mark the corner triplicate
                excluding the lower right control position.
            phenotype: Optional, which phenotype to mark. If submitted only
                that pheontype will recieve the mark, defaults to placing mark
                for all phenotypes.
            position_mark: Optional, the mark to apply, one of the
                `scanomatic.generics.phenotype_filter.Filter`.
                Defaults to `Filter.BadData`.
            undoable: Optional, if mark should be undoable, default is yes.

        Returns: If query was accepted.

        Notes:
            * If the present module `scanomtic.data_processing.phenotyper`
                was imported, then you can reach the `phenotype_mark` filters
                at `phenotyper.Filter`.
            * If all pheontypes are to be marked at once, the undo-action will
                assume all phenotypes previously were `Filter.OK`. This may of
                may not have been true.
        """
        def _safe_position(p):
            try:
                return int(p)
            except TypeError:
                if isinstance(p, np.ndarray):
                    return p.astype(int)
                else:
                    return p

        self._logger.info("Setting {} for plate {}, position {}".format(
            position_mark,
            plate,
            positions,
        ))

        if (
            position_mark in (Filter.Empty, Filter.NoGrowth)
            and phenotype is not None
        ):
            self._logger.error(
                "{0} can only be set for all phenotypes, not specifically for {1}".format(  # noqa: E501
                    position_mark,
                    phenotype,
                ),
            )
            return False

        positions = tuple(_safe_position(p) for p in positions)
        if phenotype is None:
            for phenotype in self.phenotypes:
                self._set_position_mark(
                    plate,
                    positions,
                    phenotype,
                    position_mark,
                    False,
                )

            if undoable:
                self._logger.warning(
                    "Undoing this mark will assume all phenotypes were previously marked {0}".format(  # noqa: E501
                        Filter.OK,
                    ),
                )

                self._add_undo(plate, positions, None, Filter.OK.value)

        else:
            self._set_position_mark(
                plate,
                positions,
                phenotype,
                position_mark,
                undoable,
            )

        return True

    def _set_position_mark(
        self,
        id_plate,
        positions,
        phenotype,
        position_mark,
        undoable,
    ):

        try:
            previous_state = (
                self._state.phenotype_filter[id_plate][phenotype][positions]
            )
        except KeyError:
            if self._state.phenotype_filter.size <= id_plate:
                self._logger.error(
                    "Filer isn't correctly initialized, missing plates."
                    "Action refursed"
                )
                return False
            self._logger.info(
                "Updating filter to cover all phenotypes, where missing {}"
                .format(phenotype)
            )
            for shape, plate in zip(
                self._state.plate_shapes,
                self._state.phenotype_filter,
            ):
                if phenotype not in plate:
                    plate.update({phenotype: np.zeros(shape, dtype=int)})
            previous_state = False

        if isinstance(previous_state, np.ndarray):
            if np.unique(previous_state).size == 1:
                previous_state = previous_state[0]

        self._state.phenotype_filter[id_plate][phenotype][positions] = (
            position_mark.value
        )

        if undoable:
            self._add_undo(id_plate, positions, phenotype, previous_state)

    def _add_undo(self, plate, position_list, phenotype, previous_state):

        self._state.phenotype_filter_undo[plate].append(
            (position_list, phenotype, previous_state),
        )
        while (
            len(self._state.phenotype_filter_undo[plate])
            > self.UNDO_HISTORY_LENGTH
        ):
            self._state.phenotype_filter_undo[plate].popleft()

    def undo(self, plate: int) -> bool:
        """Undo most recent position mark that was undoable on plate

        Args:
            plate: The plate index (0 for first plate)

        Returns:
            If anything was undone
        """
        if len(self._state.phenotype_filter_undo[plate]) == 0:
            self._logger.info("No more actions to undo")
            return False

        (
            position_list, phenotype, previous_state,
        ) = self._state.phenotype_filter_undo[plate].pop()
        self._logger.info("Setting {0} for positions {1} to state {2}".format(
            phenotype,
            position_list,
            Filter(previous_state)))

        if phenotype is None:
            for phenotype in Phenotypes:
                if (
                    self._settings.phenotypes_inclusion(phenotype)
                    and phenotype in self._state.phenotype_filter[plate]
                ):
                    self._state.phenotype_filter[plate][phenotype][
                        position_list
                    ] = previous_state
        elif phenotype in self._state.phenotype_filter[plate]:
            self._state.phenotype_filter[plate][phenotype][
                position_list
            ] = previous_state
        else:
            self._logger.warning(
                "Could not undo for {0} because no filter present for phenotype".format(  # noqa: E501
                    phenotype,
                ),
            )
            return False
        return True

    def plate_has_any_colonies_removed(self, plate: int) -> bool:
        """Get if plate has anything removed.

        Args:
            plate   Index of plate

        Returns:
            The status of the plate removals
        """
        return self._state.has_any_colony_removed_from_plate(plate)

    def has_any_colonies_removed(self) -> bool:
        """If any plate has anything removed

        Returns:
            The removal status
        """
        return self._state.has_any_colony_removed()

    @staticmethod
    def _make_csv_row(*args):
        for a in args:
            if isinstance(a, str):
                yield a
            else:
                try:
                    for v in Phenotyper._make_csv_row(*a):
                        yield v
                except TypeError:
                    yield a

    def meta_data_headers(self, plate_index):
        if self._state.meta_data is not None:
            self._logger.info("Adding meta-data")
            return self._state.meta_data.get_header_row(plate_index)
        return tuple()

    def get_csv_file_name(self, dir_path, save_data, plate_index):
        path = os.path.join(dir_path, self._paths.phenotypes_csv_pattern)
        return path.format(save_data.name, plate_index + 1)

    def save_phenotypes(
        self,
        dir_path: Optional[str] = None,
        save_data: NormState = NormState.Absolute,
        dialect=csv.excel,
        ask_if_overwrite: bool = True,
        reference_values=None,
    ):
        """Exporting phenotypes to csv format.

        Args:
            dir_path: The directory where to put the data, file names will be
                automatically generated
            save_data: Optional, what data to save.
                One of the `NormState` values.
                Default is raw absolute phenotypes.
            dialect: Optional. The csv-dialect to use, defaults to
                excel-compatible.
            ask_if_overwrite: Optional, if warning before overwriting any
                files, defaults to `True`.
            reference_values:
                Optional, tuple of the means of all comparable plates-medians,
                needed for using non-batched saving of their reference
                positions. One value per plate in the current project.
        """
        if dir_path is None and self._base_name is not None:
            dir_path = self._base_name
        elif dir_path is None:
            self._logger.error("Needs somewhere to save the phenotype")
            return False

        dir_path = os.path.abspath(dir_path)

        phenotypes = self.phenotypes_that_normalize if save_data in (
            NormState.NormalizedAbsoluteBatched,
            NormState.NormalizedAbsoluteNonBatched,
            NormState.NormalizedRelative,
        ) else self.phenotypes

        phenotypes = tuple(
            p for p in phenotypes
            if PhenotypeDataType.Scalar(p) and p in self
        )

        data_source = {
            p: self.get_phenotype(
                p,
                norm_state=save_data,
                reference_values=reference_values,
            )
            for p in phenotypes
        }

        default_meta_data = ('Plate', 'Row', 'Column')

        meta_data = self._state.meta_data
        no_metadata = tuple()

        for plate_index in self._state.enumerate_plates:
            if any(data_source[p][plate_index] is None for p in data_source):
                continue

            plate_path = self.get_csv_file_name(
                dir_path,
                save_data,
                plate_index,
            )

            if os.path.isfile(plate_path) and ask_if_overwrite:
                if (
                    'y' not in input(
                        f"Overwrite existing file '{plate_path}'? (y/N)",
                    ).lower()
                ):
                    continue

            with open(plate_path, 'w') as fh:

                try:
                    # DATA
                    plate = data_source[list(data_source.keys())[0]][
                        plate_index
                    ]
                except IndexError:
                    self._logger.warning(
                        "Output empty file because there were no phenotypes",
                    )
                else:
                    # HEADER ROW
                    meta_data_headers = self.meta_data_headers(plate_index)
                    cw = csv.writer(fh, dialect=dialect)
                    cw.writerow(
                        tuple(
                            self._make_csv_row(
                                default_meta_data,
                                meta_data_headers,
                                list(data_source.keys()),
                            ),
                        ),
                    )

                    filt = self._state.phenotype_filter[plate_index]

                    for idX, X in enumerate(plate):
                        for idY, Y in enumerate(X):
                            cw.writerow(
                                tuple(self._make_csv_row(
                                    (plate_index, idX, idY),
                                    no_metadata if meta_data is None
                                    else meta_data(plate_index, idX, idY),
                                    tuple(
                                        data_source[p][plate_index][idX, idY]
                                        if filt[p][idX, idY] == 0
                                        else Filter(filt[p][idX, idY]).name
                                        for p in data_source
                                    )
                                ))
                            )

                    self._logger.info(
                        "Saved {0}, plate {1} to {2}".format(
                            save_data,
                            plate_index + 1,
                            plate_path,
                        ),
                    )

        return True

    @staticmethod
    def _do_ask_overwrite(path):
        return input(
            "Overwrite '{0}' (y/N)".format(path),
        ).strip().upper().startswith("Y")

    def save_state(self, dir_path: str, ask_if_overwrite: bool = True):
        """Save the `Phenotyper` instance's state for future work.

        Args:
            dir_path: Directory where state should be saved
            ask_if_overwrite: Optional, default is `True`
        """
        save_state(
            self._settings,
            self._state,
            dir_path,
            ask_if_overwrite=ask_if_overwrite,
        )

    def save_state_to_zip(
        self,
        target: Optional[str] = None,
    ) -> Optional[BytesIO]:
        return save_state_to_zip(
            self._base_name,
            self._settings,
            self._state,
            target=target,
        )

    def for_each_call(
        self,
        extra_keyword_args: Union[tuple[dict, ...], dict] = tuple(),
        start_plate: Optional[int] = None,
        start_pos: Optional[tuple[int, int]] = None,
        funcs: tuple[Callable] = tuple(),
    ):
        """For each log2_curve, the supplied functions are called.

        Each function must have the following initial argument order:

            phenotyper_object, plate, position_tuple

        After those, the rest of the arguments should have default values
        and/or have their needed information supplied in the
        ```extra_keyword_args``` parameter.

        Args:
            extra_keyword_args:
                Tuple of dicts or a single dict used as extra keyword
                arguments sent to the functions. Either specific for
                each function or the same for all.
            start_plate: Starting plate to iterate from
            start_pos: Starting position on plate to iterate from
            funcs:
                A list of functions to be called for each position.

        Returns:
            A generator to loop through the calling on the
            positions.

        Examples:

            Interactive plotting of the phase-classification of all
            curves:

            ```
            from matplotlib as plt
            from scanomatic.qc import phenotype_results

            def outer(i):
                for _ in i:
                    f.show()
                    yield
                    for ax in f.axes:
                        if ax is not ax1 and ax is not ax2:
                            f.delaxes(ax)
                        else:
                            ax.cla()

            f = plt.figure()
            ax1 = f.add_subplot(2, 1, 1,)
            ax2 = f.add_subplot(2, 1, 2)
            plt.ion()

            i = P.for_each_call(
                ({'ax': ax1}, {'ax': ax2}),
                phenotype_results.plot_phases,
                phenotype_results.plot_curve_and_derivatives,
            )

            o = outer(i)
            ```

            Then ```next(o)``` can be used to step through the
            generator.
        """
        if not isinstance(extra_keyword_args, tuple):
            extra_keyword_args = tuple(
                extra_keyword_args for _ in range(len(self))
            )

        skip = False if start_pos is None else True

        for plate, shape in enumerate(self._state.plate_shapes):
            if not shape or start_plate is not None and plate < start_plate:
                continue

            for pos in product(*(range(s) for s in shape)):
                if skip:
                    if pos == start_pos:
                        skip = False
                    else:
                        continue

                for idf, f in enumerate(funcs):
                    f(self, plate, pos, **extra_keyword_args[idf])

                yield plate, pos
