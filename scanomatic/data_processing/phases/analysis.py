from enum import Enum
from typing import Optional

import numpy as np
from scipy.ndimage import label  # type: ignore
from scipy.stats import linregress  # type: ignore

from scanomatic.data_processing import growth_phenotypes
from scanomatic.data_processing.phases.segmentation import (
    DEFAULT_THRESHOLDS,
    CurvePhases,
    get_data_needed_for_segmentation,
    is_detected_linear,
    is_detected_non_linear,
    is_undetermined,
    segment
)


class CurvePhasePhenotypes(Enum):
    """Phenotypes for individual log2_curve phases.

    _NOTE_ Some apply only to some `CurvePhases`.

    Attributes:
        CurvePhasePhenotypes.PopulationDoublingTime: The average population
            doubling time of the segment
        CurvePhasePhenotypes.Duration: The length of the segment in time.
        CurvePhasePhenotypes.Yield: The gain in population size.
        CurvePhasePhenotypes.PopulationDoublings: The population doublings for
            the entire experiment that this segment is responsible for
        CurvePhasePhenotypes.Start: Start time of the segment
        CurvePhasePhenotypes.LinearModelSlope: The slope of the linear model
            fitted to the segment
        CurvePhasePhenotypes.LinearModelIntercept: The intercept of the linear
            model fitted to the segment
        CurvePhasePhenotypes.AsymptoteAngle: The angle between the initial
            point slope and the final point slope of the segment
        CurvePhasePhenotypes.AsymptoteIntersection: The intercept between the
            asymptotes as fraction of the `Duration` of the segment.
    """

    PopulationDoublingTime = 1
    Duration = 2
    Start = 4
    LinearModelSlope = 5
    LinearModelIntercept = 6
    AsymptoteAngle = 7
    AsymptoteIntersection = 8
    Yield = 9
    PopulationDoublings = 10


def number_of_phenotypes(phase: CurvePhases) -> int:
    if is_detected_linear(phase):
        return 6
    elif is_detected_non_linear(phase):
        return 5
    else:
        return 3


def get_phenotypes_tuple(phase: CurvePhases) -> tuple[CurvePhasePhenotypes]:
    if is_detected_linear(phase):
        return (
            CurvePhasePhenotypes.Start,
            CurvePhasePhenotypes.Duration,
            CurvePhasePhenotypes.Yield,
            CurvePhasePhenotypes.PopulationDoublings,
            CurvePhasePhenotypes.LinearModelIntercept,
            CurvePhasePhenotypes.LinearModelSlope,
            CurvePhasePhenotypes.PopulationDoublingTime,
        )
    elif is_detected_non_linear(phase):
        return (
            CurvePhasePhenotypes.Start,
            CurvePhasePhenotypes.Duration,
            CurvePhasePhenotypes.Yield,
            CurvePhasePhenotypes.PopulationDoublings,
            CurvePhasePhenotypes.AsymptoteAngle,
            CurvePhasePhenotypes.AsymptoteIntersection,
        )
    else:
        return (
            CurvePhasePhenotypes.Start,
            CurvePhasePhenotypes.Duration,
            CurvePhasePhenotypes.Yield,
            CurvePhasePhenotypes.PopulationDoublings,
        )


def _phenotype_phases(model, doublings):

    phenotypes = []

    for phase in CurvePhases:

        labels, label_count = label(model.phases == phase.value)
        for id_label in range(1, label_count + 1):

            if is_undetermined(phase):
                phenotypes.append((phase, None))
                continue

            filt = labels == id_label
            left, right = _locate_segment(filt)
            time_right = model.times[right - 1]
            time_left = model.times[left]
            current_phase_phenotypes = {}

            if is_detected_non_linear(phase):
                assign_non_linear_phase_phenotypes(
                    current_phase_phenotypes,
                    model,
                    left,
                    right,
                    time_left,
                    time_right
                )

            elif is_detected_linear(phase):
                assign_linear_phase_phenotypes(
                    current_phase_phenotypes,
                    model,
                    filt,
                )

            assign_common_phase_phenotypes(
                current_phase_phenotypes,
                model,
                left,
                right,
            )

            phenotypes.append((phase, current_phase_phenotypes))

    # Phenotypes sorted on phase start rather than type of phase
    return sorted(
        phenotypes,
        key=lambda t_p: (
            t_p[1][CurvePhasePhenotypes.Start] if t_p[1] is not None else 9999
        )
    )


def assign_common_phase_phenotypes(
    current_phase_phenotypes,
    model,
    left,
    right,
):
    # C. Get duration
    current_phase_phenotypes[CurvePhasePhenotypes.Duration] = (
        (
            model.times[right - 1]
            + model.times[min(right, model.log2_curve.size - 1)]
        ) / 2
        - (model.times[left] + model.times[max(0, left - 1)]) / 2
    )

    # D. Get Population Doublings
    current_phase_phenotypes[CurvePhasePhenotypes.PopulationDoublings] = (
        (
            model.log2_curve[right - 1]
            + model.log2_curve[min(right, model.log2_curve.size - 1)]
        ) / 2
        - (
            model.log2_curve[left] + model.log2_curve[max(0, left - 1)]
        ) / 2
    )

    # E. Get Yield
    current_phase_phenotypes[CurvePhasePhenotypes.Yield] = (
        np.power(
            2,
            (
                model.log2_curve[right - 1]
                + model.log2_curve[min(right, model.log2_curve.size - 1)]
            ) / 2,
        ) - np.power(
            2,
            (model.log2_curve[left] + model.log2_curve[max(0, left - 1)]) / 2,
        )
    )

    # F. Get start of phase
    current_phase_phenotypes[CurvePhasePhenotypes.Start] = (
        (model.times[left] + model.times[max(0, left - 1)]) / 2
    )

    if (
        not np.isfinite(model.log2_curve[left])
        or not np.isfinite(model.log2_curve[max(0, right - 1)])
    ):

        current_phase_phenotypes[CurvePhasePhenotypes.Duration] = np.nan
        current_phase_phenotypes[CurvePhasePhenotypes.Yield] = np.nan
        current_phase_phenotypes[
            CurvePhasePhenotypes.PopulationDoublings
        ] = np.nan

        if not np.isfinite(model.log2_curve[left]):
            current_phase_phenotypes[CurvePhasePhenotypes.Start] = np.nan


def assign_linear_phase_phenotypes(current_phase_phenotypes, model, filt):
    # B. For linear phases get the doubling time
    slope, intercept, _, _, _ = linregress(
        model.times[filt],
        model.log2_curve[filt]
    )
    current_phase_phenotypes[
        CurvePhasePhenotypes.PopulationDoublingTime
    ] = 1 / slope
    current_phase_phenotypes[CurvePhasePhenotypes.LinearModelSlope] = slope
    current_phase_phenotypes[
        CurvePhasePhenotypes.LinearModelIntercept
    ] = intercept


def assign_non_linear_phase_phenotypes(
    current_phase_phenotypes,
    model,
    left,
    right,
    time_left,
    time_right,
):
    # A. For non-linear phases use the X^2 coefficient as curvature measure

    # TODO: Verify that values fall within the defined range of 0.5pi and pi

    k1 = model.dydt[max(0, left - model.offset)]
    k2 = model.dydt[right - 1 - model.offset]
    m1 = model.log2_curve[left] - k1 * time_left
    m2 = model.log2_curve[right - 1] - k2 * time_right
    i_x = (m2 - m1) / (k1 - k2)
    current_phase_phenotypes[
        CurvePhasePhenotypes.AsymptoteIntersection
    ] = (i_x - time_left) / (time_right - time_left)

    # Taking k2 - k1 here should imply positive values for Counter Clock-Wise
    # rotations

    if (
        not np.isfinite(k1)
        or not np.isfinite(k2)
        or np.ma.is_masked(k1)
        or np.ma.is_masked(k2)
    ):
        current_phase_phenotypes[CurvePhasePhenotypes.AsymptoteAngle] = np.nan
        current_phase_phenotypes[
            CurvePhasePhenotypes.AsymptoteIntersection
        ] = np.nan

    else:
        current_phase_phenotypes[
            CurvePhasePhenotypes.AsymptoteAngle
        ] = np.arctan2(k2, 1) - np.arctan2(k1, 1)

        if (
            current_phase_phenotypes[CurvePhasePhenotypes.AsymptoteAngle]
            > np.pi
        ):
            current_phase_phenotypes[CurvePhasePhenotypes.AsymptoteAngle] = (
                2 * np.pi
                - current_phase_phenotypes[CurvePhasePhenotypes.AsymptoteAngle]
            )


def _locate_segment(filt: np.ndarray) -> tuple[Optional[int], Optional[int]]:
    """
    Args:
        filt: a boolean array

    Returns:
        Left and exclusive right indices of filter
    """
    labels, n = label(filt)
    if n == 1:
        where = np.where(labels == 1)[0]
        return where[0], where[-1] + 1
    elif n > 1:
        raise ValueError(
            "Filter is not homogeneous, contains {0} segments ({1})".format(
                n,
                labels.tolist(),
            )
        )
    else:
        return None, None


def get_phase_analysis(
    phenotyper_object,
    plate,
    pos,
    thresholds=None,
    experiment_doublings=None,
):

    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    model = get_data_needed_for_segmentation(
        phenotyper_object,
        plate,
        pos,
        thresholds,
    )

    for _ in segment(model, thresholds):
        pass

    if experiment_doublings is None:

        experiment_doublings = phenotyper_object.get_phenotype(
            growth_phenotypes.Phenotypes.ExperimentPopulationDoublings,
        )[plate][pos]

    # TODO: ensure it isn't unintentionally smoothed dydt that is uses for
    # values, good for location though
    return model.phases, _phenotype_phases(model, experiment_doublings)
