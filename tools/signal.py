
import numpy as np
import numpy.typing as npt
from scipy.ndimage import binary_dilation, binary_erosion  # type: ignore
from scipy.signal import convolve, fftconvolve  # type: ignore

from scanomatic.io.logger import get_logger

_logger = get_logger("Resource Signal")

SpikesArray = npt.NDArray[np.bool_]


class SignalError(Exception):
    pass


def get_position_of_spike(spike, signal_start, frequency: float) -> float:
    """
    Gives the spike position as a float point indicating which signal it
    is relative the signal start.

    @args: spike: The point where the spike is detected.

    @args: signal_start: The known or guessed start of the signal

    @args: frequency: The frequency of the signal

    @returns: Float point value for the closest position in the signal.
    """
    return (spike - signal_start) / frequency


def move_signal(signals, shifts, frequencies=None, freq_offset=1):
    if len(shifts) != len(signals):
        _logger.error("1st Dimension missmatch between signal and shift-list")
        return None

    else:
        if frequencies is None:
            frequencies = [None] * len(shifts)
            for i in range(len(shifts)):
                frequencies[i] = (
                    np.array(signals[i][1:]) - np.array(signals[i][:-1])
                ).mean()

        for i, s in enumerate(map(int, shifts)):
            if s != 0:
                f = frequencies[(i + freq_offset) % len(signals)]
                if s > 0:
                    signal = list(signals[i][s:])
                    for i in range(s):
                        signal.append(signal[-1] + f)
                else:
                    signal = signals[i][:s]
                    for i in range(-s):
                        signal.insert(0, signal[0] - f)

                signals[i][:] = np.array(signal)

        for i, s in enumerate([s - int(s) for s in shifts]):
            if s != 0:
                signals[i][:] = np.array(
                    [sign + s * frequencies[i] for sign in signals[i]]
                )
        return signals


def get_continuous_slopes(
    s: np.ndarray,
    min_slope_length: int = 20,
    noise_reduction: int = 4,
) -> tuple[SpikesArray, SpikesArray]:
    """Function takes a 1D noisy signal, e.g. from taking mean of image slice
    in one dimension and gets regions of continious slopes.

    Returns two arrays, first with all continious up hits
    Second with all continious down hits"""

    # Get derivative of signal without catching high freq noise
    ds = fftconvolve(s, np.array([-1, -1, 1, 1]), mode="same")

    # Look for positive slopes
    s_up = ds > 0
    continious_s_up = fftconvolve(
        s_up,
        np.ones((min_slope_length,)),
        mode='same',
    ) == min_slope_length

    # Look for negative slopes
    s_down = ds < 0
    continious_s_down = fftconvolve(
        s_down,
        np.ones((min_slope_length,)),
        mode='same',
    ) == min_slope_length

    # Reduce noise 2
    for i in range(noise_reduction):
        continious_s_up = binary_dilation(continious_s_up)
        continious_s_down = binary_dilation(continious_s_down)
    for i in range(noise_reduction):
        continious_s_up = binary_erosion(continious_s_up)
        continious_s_down = binary_erosion(continious_s_down)

    return continious_s_up, continious_s_down


def get_closest_signal_pair(
    s1: np.ndarray,
    s2: np.ndarray,
    s1_value: int = -1,
    s2_value: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """The function returns the positions in s1 and s2 for where pairs of
    patterns s1-value -> s2-value are found (s1-value is assumed to preceed
    s2-value)."""

    s1_positions = np.where(s1 == s1_value)[0]
    s2_positions = np.where(s2 == s2_value)[0]

    # Match all
    signals: list[tuple[int, int]] = []
    for p in s1_positions:
        tmp_diff = s2_positions - p
        tmp_diff = tmp_diff[tmp_diff > 0]
        if tmp_diff.size > 0:
            p2 = tmp_diff.min() + p
            if len(signals) > 0 and p2 == signals[-1][1]:
                if p2 - p < signals[-1][1] - signals[-1][0]:
                    del signals[-1]
                    signals.append((p, p2))
            else:
                signals.append((p, p2))

    signals_arr = np.array(signals)
    if signals_arr.size == 0:
        raise SignalError("No signal pairs found")

    return signals_arr[:, 0], signals_arr[:, 1]


def get_signal_spikes(
    down_slopes: np.ndarray,
    up_slopes: np.ndarray,
) -> np.ndarray:
    """Returns where valleys are in a signal based on down and up slopes"""
    # combined_signal = (
    #     down_slopes.astype(int) * -1 + up_slopes.astype(int)
    # )

    # Edge-detect so that signal start is >0 and signal end <0
    kernel = np.array([-1, 1])
    d_down = np.round(
        fftconvolve(down_slopes, kernel, mode='same'),
    ).astype(int)
    d_up = np.round(
        fftconvolve(up_slopes, kernel, mode='same'),
    ).astype(int)

    s1, s2 = get_closest_signal_pair(d_up, d_down, s1_value=-1, s2_value=1)
    return (s1 + s2) / 2.0


def _get_closest(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    dist = np.abs(np.subtract.outer(X, Y))
    idx1 = np.argmin(dist, axis=0)
    idx2 = np.argmin(dist, axis=1)
    Z = np.c_[
        X[idx1[idx2] == np.arange(len(X))],
        Y[idx2[idx1] == np.arange(len(Y))]
    ].ravel()
    return Z


def _get_orphans(X: np.ndarray, shortX: np.ndarray) -> np.ndarray:
    return X[np.abs(np.subtract.outer(X, shortX)).min(axis=1).astype(bool)]


def get_offset_quality(
    s,
    offset: int,
    expected_spikes: int,
    wl: float,
    raw_signal,
) -> float:
    # Get the ideal signal from parameters
    ideal_signal = np.arange(expected_spikes) * wl + offset

    Z = _get_closest(s, ideal_signal)

    # Making arrays
    # X  is s positions
    # Y  is ideal_signal positions
    X = Z[0::2]
    Y = Z[1::2]

    new_signal = np.r_[X, _get_orphans(ideal_signal, Y)]
    new_signal_val = raw_signal[new_signal.astype(int)]

    dXY = np.abs(
        np.r_[(Y - X), np.ones(ideal_signal.size - X.size) * (0.5 * wl)],
    )

    X_val = raw_signal[X.astype(int)]
    dV = 3 * np.abs(new_signal_val - np.median(X_val))
    dV[new_signal_val > np.median(X_val) * 0.8] *= 0.25
    q = -0.1 * dXY * dV

    return q.sum()


def _get_wave_length_and_errors(s) -> tuple[float, float]:

    diff = np.subtract.outer(s, s)
    # -1 gets step to the right
    proxy_step = diff.diagonal(offset=-1)
    # Scaled to proxy step sizes
    bis_proxy_step = diff.diagonal(offset=-2) / 2.0

    # Getting wl from IQR-mean of proximate signal step lengths
    ps_order = proxy_step.argsort()
    wl = proxy_step[ps_order[ps_order.size / 4: ps_order.size * 3 / 4]].mean()

    # Get the errors in step sizes
    ps_error = np.abs(proxy_step - wl)
    bps_error = np.abs(bis_proxy_step - wl)

    # Extend bps-error so it has equal size as ps_error
    bps_error = np.r_[bps_error, ps_error[-1]]

    # Get the best mesure (In other words, let one vary in size)
    s_error = np.c_[ps_error, bps_error].min(1)

    return wl, s_error


def _insert_spikes_where_missed(
    s,
    s_error,
    expected_spikes: int,
    wl: float,
):
    # Get distances in terms of k waves:
    k_wave_d = np.arange(expected_spikes) * wl

    # Investigate if a spike seems to be missed?
    insert_spikes = np.abs(
        np.subtract.outer(s_error, k_wave_d),
    ).argmin(axis=1)

    inserted_spikes = 0
    for pos in np.where(insert_spikes > 0)[0]:

        s = np.r_[
            # What is leftside of the missed spike(s)
            s[:pos + 1 + inserted_spikes],
            # Assumed positions for missed spikes
            s[pos + inserted_spikes] + k_wave_d[1: insert_spikes[pos] + 1],
            # Right-side of the missed spike(s)
            s[pos + inserted_spikes:]
        ]
        inserted_spikes += insert_spikes[pos]

    return s


def _remove_false_inter_spikes(
    s,
    expected_spikes: int,
    wl: float,
):

    # Get distances in terms of k waves:
    k_wave_d = np.arange(expected_spikes) * wl
    steps = np.abs(np.subtract.outer(
        np.abs(np.subtract.outer(s, s)),
        k_wave_d,
    )).argmin(2)
    inter_spikes = (steps == 0).sum(1) > 1

    subtracted = 0
    for pos in range(inter_spikes.size - 1):
        if inter_spikes[pos: pos + 2].sum() == 2:
            s = np.r_[s[:pos + 1 - subtracted], s[pos + 2 - subtracted:]]
            subtracted += 1

    return s


def _get_candidate_validation(
    s,
    s_error,
    expected_spikes: int,
    raw_signal: np.ndarray,
):
    # Get goodness of distances
    goodness1 = convolve(
        s_error,
        np.ones(expected_spikes // 4),
        'same',
    )
    g = [goodness1[0]]
    for g_pos in range(s_error.size - 1):
        g.append(goodness1[g_pos: g_pos + 2].min())
    g.append(goodness1[-1])
    goodness1 = np.array(g)

    # goodness1r = np.r_[[0], goodness1]
    # goodness1 = np.c_[goodness1l, goodness1r].mean(1)

    # Get goodness of values
    candidate_vals = raw_signal[s.astype(int)]
    m_c_val = np.median(candidate_vals)
    goodness2 = candidate_vals - m_c_val
    goodness2[goodness2 > 0] *= 0.5
    goodness2 = np.abs(goodness2)

    # General goodness
    goodness = goodness1 * (goodness2 ** 2)
    g_order = goodness.argsort()

    # Validated positions
    s_val = np.zeros(s.size, dtype=bool)

    # Validate positions
    tmp_2_slice = np.array((0, -1))
    pos = 0
    while (
        s_val.sum() < expected_spikes and pos < g_order.size
    ):  # Steps is one less

        if s_val[g_order[pos]] == 0:
            eval_s_val = s_val.copy()
            eval_s_val[g_order[pos]] = True
            es_true_range = np.where(
                eval_s_val == True,  # noqa: E712
            )[0][tmp_2_slice]
            eval_s_val[es_true_range[0]: es_true_range[1] + 1] = True
            if eval_s_val.sum() < expected_spikes:
                s_val = eval_s_val
        pos += 1

    sb = np.where(s_val == True)[0][tmp_2_slice]  # noqa: E712
    if sb[1] == s_val.size - 1:
        s_val[sb[0] - 1] = True
    else:
        s_val[sb[1] + 1] = True

    return s_val


def get_best_signal_candidates_and_wave_length(
    s,
    expected_spikes: int,
    raw_signal: np.ndarray,
):
    # We might rewrite the signal and should not mess with original
    s = s.copy()

    # Get how candidates err and what is the reasonably assumed wave-length
    wl, s_error = _get_wave_length_and_errors(s)

    # Remove spikes if there seems to be bonus ones inbetween good ones
    s = _remove_false_inter_spikes(s, expected_spikes, wl)

    # Update s_error
    s_error = _get_wave_length_and_errors(s)[1]

    # Insert spikes if there seems to be missed ones
    s = _insert_spikes_where_missed(s, s_error, expected_spikes, wl)

    # Update s_error
    s_error = _get_wave_length_and_errors(s)[1]

    # Validate candidates
    s_val = _get_candidate_validation(s, s_error, expected_spikes, raw_signal)

    return s[s_val], wl


def get_grid_signal(
    raw_signal: np.ndarray,
    expected_spikes: int,
):
    """Gives grid signals according to number of expected spikes
    (rows or columns) on 1D raw signal"""

    # Get slopes
    up_slopes, down_slopes = get_continuous_slopes(
        raw_signal,
        min_slope_length=10,
        noise_reduction=4,
    )

    # Get signal from slopes
    s = get_signal_spikes(down_slopes, up_slopes)

    # Wave-length 'frequency'
    # wl = get_perfect_frequency2(s, get_signal_frequency(s))

    s, wl = get_best_signal_candidates_and_wave_length(
        s,
        expected_spikes,
        raw_signal,
    )

    """
    # Signal length is wave-length * expected signals
    l = wl * expected_spikes

    # Evaluating all allowed offsets:
    grid_scores = []
    for offset in range(int(raw_signal.size - l)):
        grid_scores.append(
            get_offset_quality(
                s,
                offset,
                expected_spikes,
                wl,
                raw_signal,
            ),
        )

    GS = np.array(grid_scores)
    offset = GS.argmax()

    # Make signal here
    """

    return s, wl
