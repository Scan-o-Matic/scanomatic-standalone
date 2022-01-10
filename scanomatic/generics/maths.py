from typing import Optional
import numpy as np
from scipy.stats.mstats import mquantiles  # type: ignore


def iqr_mean(data: np.ndarray, *args, **kwargs) -> Optional[np.ndarray]:
    quantiles = mquantiles(data, prob=(0.25, 0.75))
    if quantiles.any():
        val = np.ma.masked_outside(data, *quantiles).mean(*args, **kwargs)
        if isinstance(val, np.ma.MaskedArray):
            return val.filled(np.nan)
        return val
    return None


def mid50_mean(data: np.ndarray) -> float:

    if not isinstance(data, np.ma.masked_array):
        data = np.ma.masked_invalid(data)

    data = data.data[data.mask == False]  # noqa: E712
    center_points = int(np.floor(data.size * 0.5))
    flank = int(np.floor((data.size - center_points) / 2))
    data.sort()
    return data[flank:-flank].mean()


def quantiles_stable(data: np.ndarray) -> tuple[float, float]:

    if not isinstance(data, np.ma.masked_array):
        data = np.ma.masked_invalid(data)

    data = data[data.mask == False]  # noqa: E712
    threshold = int(np.floor(data.size * 0.25))
    data.sort()
    return data[threshold], data[-threshold]
