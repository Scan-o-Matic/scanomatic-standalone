from enum import Enum
from logging import Logger
from typing import Any, Optional
from collections.abc import Callable

import numpy as np
import numpy.typing as npt
from scipy.stats import norm  # type: ignore


class EdgeCondition(Enum):
    Reflect = 0
    Symmetric = 1
    Nearest = 2
    Valid = 3


FilterArray = npt.NDArray[np.bool_]


def edge_condition(
    arr: np.ndarray,
    mode: EdgeCondition = EdgeCondition.Reflect,
    kernel_size: int = 3,
):
    if not kernel_size % 2 == 1:
        raise ValueError("Only odd-size kernels supported")

    origin = (kernel_size - 1) // 2
    idx = 0

    # First edge:
    if mode is EdgeCondition.Symmetric:
        while idx < origin:
            yield np.hstack((arr[:origin - idx][::-1], arr[:idx + 1 + origin]))
            idx += 1

    elif mode is EdgeCondition.Nearest:
        while idx < origin:
            yield np.hstack((
                tuple(arr[0] for _ in range(origin - idx)),
                arr[:idx + 1 + origin],
            ))
            idx += 1

    elif mode is EdgeCondition.Reflect:
        while idx < origin:
            yield np.hstack((
                arr[1: origin - idx + 1][::-1],
                arr[:idx + 1 + origin],
            ))
            idx += 1
    elif mode is EdgeCondition.Valid:
        pass

    # Valid range
    while arr.size - idx > origin:
        yield arr[idx - origin: idx + origin + 1]
        idx += 1

    # Second edge
    if mode is EdgeCondition.Symmetric:
        while idx < arr.size:
            yield np.hstack((
                arr[idx - origin:],
                arr[arr.size - idx - origin - 1:][::-1],
            ))
            idx += 1

    elif mode is EdgeCondition.Nearest:
        while idx < arr.size:
            yield np.hstack((
                arr[idx - origin:],
                tuple(
                    arr[-1] for _ in range(-1*(arr.size - idx - origin - 1))
                ),
            ))
            idx += 1

    elif mode is EdgeCondition.Reflect:
        while idx < arr.size:
            yield np.hstack((
                arr[idx - origin:],
                arr[arr.size - idx - origin - 2: -1][::-1],
            ))
            idx += 1
    elif mode is EdgeCondition.Valid:
        pass


def time_based_gaussian_weighted_mean(
    data: np.ndarray,
    time: np.ndarray,
    sigma: float = 1,
):
    center = (time.size - time.size % 2) // 2
    delta_time = np.abs(time - time[center])
    kernel = norm.pdf(delta_time, loc=0, scale=sigma)
    finite = np.isfinite(data)
    if not finite.any() or not finite[center]:
        return np.nan
    kernel /= kernel[finite].sum()
    return (data[finite] * kernel[finite]).sum()


def merge_convolve(
    arr1: np.ndarray,
    arr2: np.ndarray,
    edge_condition_mode: EdgeCondition = EdgeCondition.Reflect,
    kernel_size: int = 5,
    func: Callable = time_based_gaussian_weighted_mean,
    func_kwargs: Optional[dict[str, Any]] = None,
):
    if not func_kwargs:
        func_kwargs = {}

    return tuple(func(v1, v2, **func_kwargs) for v1, v2 in zip(
        edge_condition(
            arr1,
            mode=edge_condition_mode,
            kernel_size=kernel_size,
        ),
        edge_condition(
            arr2,
            mode=edge_condition_mode,
            kernel_size=kernel_size,
        ),
    ))


def get_edge_condition_timed_filter(
    times: np.ndarray,
    half_window: float,
    edge_condition: EdgeCondition,
):
    left = times < (times[0] + half_window)
    right = times > (times[-1] - half_window)

    if edge_condition is EdgeCondition.Symmetric:
        return left, right
    else:
        left[0] = False
        right[-1] = False
        return left, right


def filter_edge_condition(
    y: np.ndarray,
    left_filt: FilterArray,
    right_filt: FilterArray,
    mode: EdgeCondition,
    extrapolate_values: bool = False,
    logger: Optional[Logger] = None,
):
    if mode is EdgeCondition.Valid:
        return y
    elif mode is EdgeCondition.Symmetric or mode is EdgeCondition.Reflect:
        return np.hstack((
            y[0]
            - y[left_filt][::-1] if extrapolate_values else y[left_filt][::-1],
            y,
            y[-1]
            + (
                y[right_filt][::-1] if extrapolate_values
                else y[right_filt][::-1]
            ),
        ))

    elif mode is EdgeCondition.Nearest:
        return np.hstack((
            [y[0]] * left_filt.sum(),
            y,
            y[-1] * right_filt.sum(),
        ))
    else:
        if logger is not None:
            logger.warning(
                "Unsupported edge condition {0}, will use `Valid`".format(
                    edge_condition.name
                ),
            )
        return y
