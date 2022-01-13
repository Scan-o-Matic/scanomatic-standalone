from typing import Optional, cast

import numpy as np
import numpy.typing as npt

from scanomatic.image_analysis.grayscale import Grayscale
from scanomatic.io.logger import get_logger

_logger = get_logger("Resource Signal")

SpikesArray = npt.NDArray[np.bool_]


def get_higher_second_half_order_according_to_first(first, *others):
    if (
        len(first) > 0
        and (
            np.mean(first[:len(first) // 2])
            > np.mean(first[len(first) // 2:])
        )
    ):
        first = first[::-1]
        others = tuple(other[::-1] for other in others)

    return (first,) + others


def get_signal(
    data: np.ndarray,
    detection_threshold: float,
    kernel: tuple[float, ...] = (-1, 1),
) -> np.ndarray:
    up_spikes = np.abs(np.convolve(data, kernel, "same")) > detection_threshold
    return np.array(get_center_of_spikes(up_spikes))


def get_signal_data(
    strip_values,
    up_spikes,
    grayscale: Grayscale,
    delta_threshold
):
    expected_slice_size = grayscale.sections * grayscale.length
    expected_spikes = (
        np.arange(0, grayscale.sections + 1)
        * grayscale.length
    )

    offset = (expected_slice_size - strip_values.size) / 2.0
    expected_spikes += offset

    observed_spikes = np.where(up_spikes)[0]

    observed_to_expected_index_map = np.abs(np.subtract.outer(
        observed_spikes,
        expected_spikes,
    )).argmin(axis=1)

    deltas = []
    for observed_i, expected_i in enumerate(observed_to_expected_index_map):
        deltas.append(abs(
            expected_spikes[expected_i]
            - observed_spikes[observed_i]
        ))
        if deltas[-1] > delta_threshold:
            deltas[-1] = np.nan

    return np.array(deltas), observed_spikes, observed_to_expected_index_map


def get_signal_edges(
    observed_to_expected_index_map,
    deltas,
    observed_spikes,
    number_of_segments: int,
) -> np.ndarray:
    edges = np.ones((number_of_segments + 1,)) * np.nan

    for edge_i in range(number_of_segments + 1):
        candidate_indices = np.where(observed_to_expected_index_map == edge_i)
        if not np.any(candidate_indices):
            continue

        candidates = deltas[candidate_indices]
        best = candidate_indices[0][candidates.argmin()]
        if candidates.any() and np.isfinite(deltas[best]):
            edges[edge_i] = observed_spikes[best]

    nan_edges = np.isnan(edges)
    fin_edges = np.isfinite(edges)
    if fin_edges.any() and nan_edges.any():
        edge_ordinals = np.arange(edges.size, dtype=float) + 1
        edges[nan_edges] = np.interp(
            edge_ordinals[nan_edges],
            edge_ordinals[fin_edges],
            edges[fin_edges],
            left=np.nan,
            right=np.nan,
        )

    elif nan_edges.any():
        _logger.warning("No finite edges")

    return edges


def extrapolate_edges(
    edges: np.ndarray,
    frequency: float,
    signal_length: float,
) -> np.ndarray:
    fin_edges = np.isfinite(edges)
    where_fin_edges = np.where(fin_edges)[0]
    for i in range(where_fin_edges[0] - 1, -1, -1):
        edges[i] = max(edges[i + 1] - frequency, 0)
    for i in range(where_fin_edges[-1] + 1, edges.size):
        edges[i] = min(edges[i - 1] + frequency, signal_length)

    return edges


def get_perfect_frequency(
    best_measures: SpikesArray,
    guess_frequency: float,
    tolerance: float = 0.15,
) -> float:
    dists = get_spike_distances(best_measures)

    good_measures = []
    tol = (1 - tolerance, 1 + tolerance)

    for d in dists:
        if tol[0] < d / guess_frequency < tol[1]:
            good_measures.append(d)
        elif tol[0] < d / (2 * guess_frequency) < tol[1]:
            good_measures.append(d / 2.0)
    return np.mean(good_measures)


def get_perfect_frequency2(
    best_measures: SpikesArray,
    guess_frequency: float,
    tolerance: float = 0.15,
) -> float:
    where_measure = np.where(best_measures == True)[0]  # noqa: E712
    if where_measure.size < 1:
        return guess_frequency

    tol = (1 - tolerance, 1 + tolerance)
    f = where_measure[-1] - where_measure[0]

    f /= (np.round(f / guess_frequency))

    if tol[1] > f / guess_frequency > tol[0]:
        return f

    return get_perfect_frequency(best_measures, guess_frequency, tolerance)


def get_signal_frequency(measures: SpikesArray) -> float:
    """
        get_signal_frequency returns the median distance between two
        consecutive measures.

        The function takes the following arguments:

        @measures       An array of spikes as returned from get_spikes

    """
    tmp_array = np.asarray(measures)
    return np.median(tmp_array[1:] - tmp_array[:-1])


def get_best_offset(
    n: int,
    measures: SpikesArray,
    frequency: Optional[float] = None,
):
    """
    get_best_offset returns a optimal starting-offset for a hypthetical
    signal with frequency as specified by frequency-variable
    and returns a distance-value for each measure in measures to this
    signal at the optimal over-all offset.

    The function takes the following arguments:

    @n              The number of peaks expected

    @measures       An array of spikes as returned from get_spikes

    @frequency      The frequency of the signal, if not submitted
                    it is derived as the median inter-measure
                    distance in measures.

    """

    dist_results = []

    if sum(measures.shape) == 0:
        _logger.warning(
            "No spikes where passed, so best offset can't be found.",
        )
        return None

    if n > measures.size:
        n = measures.size

    if measures.max() == 1:
        m_where = np.where(measures == True)[0]  # noqa: E712
    else:
        m_where = measures

    if frequency is None:
        frequency = get_signal_frequency(measures)

    if np.isnan(frequency):
        return None

    for offset in range(int(np.ceil(frequency))):
        quality = []

        for m in m_where:

            # IMPROVE THIS ONE...
            # n_signal_dist is peak index of the closest signal peak
            n_signal_dist = np.round((m - offset) / frequency)

            signal_diff = offset + frequency * n_signal_dist - m
            if abs(signal_diff) > 0:
                quality.append(signal_diff ** 2)
            else:
                quality.append(0)
        dist_results.append(np.sum(np.sort(np.asarray(quality))[:n]))

    # print np.argsort(np.asarray(dist_results))
    # print np.sort(np.asarray(dist_results))
    return np.asarray(dist_results).argmin()


def get_spike_quality(
    measures: SpikesArray,
    n: Optional[int] = None,
    offset: Optional[int] = None,
    frequency: Optional[float] = None,
):
    """
    get_spike_quality returns a quality-index for each spike
    as to how well it fits the signal.

    If no offset is supplied, it is derived from measures.

    Equally so for the frequency.

    The function takes the following arguments:

    @measures       An array of spikes as returned from get_spikes

    @n              The number of peaks expected (needed if offset
                    is not given)

    @offset         Optional. Sets the offset of signal start

    @frequency      The frequency of the signal, if not submitted
                    it is derived as the median inter-measure
                    distance in measures.
    """
    if frequency is None:
        frequency = get_signal_frequency(measures)

    if offset is None and n is not None:
        offset = get_best_offset(n, measures, frequency)

    if offset is None:
        print("*** ERROR: You must provide n if you don't provide offset")
        return None

    quality_results = []

    for m in measures:
        # n_signal_dist is peak number of the closest signal peak
        n_signal_dist = np.round((m - offset) / frequency)

        quality_results.append((m - offset + frequency * n_signal_dist) ** 2)

    return quality_results


def get_true_signal(
    max_value: int,
    n: int,
    measures: SpikesArray,
    measures_qualities=None,
    offset: Optional[int] = None,
    frequency: Optional[float] = None,
    offset_buffer_fraction: int = 0,
):
    """
    get_true_signal returns the best spike pattern n peaks that
    describes the signal (described by offset and frequency).

    The function takes the following arguments:

    @max_value      The number of pixel in the current dimension

    @n              The number of peaks expected

    @measures       An array of spikes as returned from get_spikes

    @measures_qualities
                    Optional. A quality-index for each measure,
                    high values representing bad quality. If not
                    set, it will be derived from signal.

    @offset         Optional. Sets the offset of signal start

    @frequency      The frequency of the signal, if not submitted
                    it is derived as the median inter-measure
                    distance in measures.
    @offset_buffer_fraction     Default 0, buffer to edge on
                    both sides in which signal is not allowed
    """

    if frequency is None:
        frequency = get_signal_frequency(measures)

    if frequency == 0:
        return None

    if offset is None:
        offset = get_best_offset(n, measures, frequency)

    if measures.max() == 1:
        m_array = np.where(np.asarray(measures) == True)[0]  # noqa: E712
    else:
        m_array = np.asarray(measures)

    if measures_qualities is None:
        measures_qualities = get_spike_quality(
            m_array,
            n,
            offset,
            frequency,
        )

    mq_array = np.asarray(measures_qualities)

    if offset is None:
        return None

    start_peak = 0
    start_position_qualities: list[float] = []
    while (
        offset_buffer_fraction * frequency
        >= offset + frequency * ((n - 1) + start_peak)
    ):
        start_peak += 1
        start_position_qualities.append(0)

    while (
        offset_buffer_fraction * frequency
        < offset + frequency * ((n - 1) + start_peak)
        < max_value - offset_buffer_fraction * frequency
    ):
        covered_peaks = 0
        quality = 0
        ideal_peaks = (np.arange(n) + start_peak) * frequency + offset

        for pos in range(n):
            distances = (m_array - ideal_peaks[pos]) ** 2
            closest = distances.argmin()

            if (
                np.round((m_array[closest] - offset) / frequency)
                == pos + start_peak
            ):
                # Most difference with small errors... should work ok.
                quality += distances[closest]
                # if distances[closest] >= 1:
                #     quality += np.log2(distances[closest])
                # quality += (
                #     (
                #         m_array
                #         - (offset + frequency * (n + pos + start_peak))
                #     ).min()
                # )**2
                # quality += np.log2((
                #     (
                #         m_array
                #         - (offset + frequency * (n + pos + start_peak))
                #     )**2
                # ).min())
                covered_peaks += 1

        if covered_peaks > 0:
            start_position_qualities.append(
                covered_peaks + 1 / ((quality + 1) / covered_peaks)
            )
        else:
            start_position_qualities.append(0)
        start_peak += 1

    # If there simply isn't anything that looks good, the we need to stop here.
    if len(start_position_qualities) == 0:
        return None

    best_start_pos = int(np.asarray(start_position_qualities).argmax())

    _logger.info("Quality at start indices {0}".format(
        start_position_qualities,
    ))

    quality_threshold = np.mean(mq_array) + np.std(mq_array) * 3

    ideal_signal = (
        np.arange(n) * frequency + offset + best_start_pos * frequency
    )

    best_fit = []

    for pos in range(len(ideal_signal)):
        best_measure = float(
            m_array[((m_array - ideal_signal[pos]) ** 2).argmin()],
        )
        if (ideal_signal - best_measure).argmin() == pos:
            if (ideal_signal[pos] - best_measure) ** 2 < quality_threshold:
                best_fit.append(best_measure)
            else:
                best_fit.append(ideal_signal[pos])
        else:
            best_fit.append(ideal_signal[pos])

    return ideal_signal


def get_center_of_spikes(spikes: SpikesArray):
    """
    The function returns the an array matching the input-array but
    for each stretch of consequtive truth-values, only the center
    is kept true.

    @args : signal (numpy, 1D boolean array)
    """

    up_spikes = spikes.copy()
    t_zone = False
    t_low: Optional[int] = None

    for pos in range(up_spikes.size):
        if t_zone:
            t_low = cast(int, t_low)
            if up_spikes[pos] is False or pos == up_spikes.size - 1:
                if pos == up_spikes.size - 1:
                    pos += 1
                up_spikes[t_low: pos] = False
                up_spikes[t_low + (t_low - pos) // 2] = True
                t_zone = False
        else:
            if up_spikes[pos] is True:
                t_zone = True
                t_low = pos

    return up_spikes


def get_spike_distances(spikes: SpikesArray) -> npt.NDArray[np.int_]:
    spikes_where = np.where(spikes == True)[0]  # noqa: E712
    if spikes_where.size == 0:
        return np.array([])

    return np.append(spikes_where[0], spikes_where[1:] - spikes_where[:-1])


def get_best_spikes(
    spikes: SpikesArray,
    frequency: float,
    tolerance: float = 0.05,
    require_both_sides: bool = False,
) -> SpikesArray:
    """
    Looks through a spikes-array for spikes with expected distance to
    their neighbours (with a tolerance) and returns these

    @args: spikes (numpy 1D boolean array of spikes)

    @args: frequency (expected frequency (float))

    @args: tolerance (error tolerance (float))

    @args: require_both_sides (boolean)
    """
    best_spikes = spikes.copy()
    spikes_dist = get_spike_distances(spikes)

    accumulated_pos = 0
    tol = (1 - tolerance, 1 + tolerance)

    for pos in range(spikes_dist.size):

        accumulated_pos += spikes_dist[pos]
        good_sides = (
            tol[0] < spikes_dist[pos] / frequency < tol[1]
        )
        good_sides += (
            tol[0] < spikes_dist[pos] / (2 * frequency) < tol[1]
        )

        if pos + 1 < spikes_dist.size:
            good_sides += (
                tol[0] < spikes_dist[pos + 1] / frequency < tol[1]
            )

        if (
            good_sides >= require_both_sides + 1 - (
                require_both_sides is True and pos + 1 == spikes_dist.size
            )
        ):
            pass
        else:
            best_spikes[accumulated_pos] = False

    return best_spikes
