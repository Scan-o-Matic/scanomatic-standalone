from typing import Optional, Union
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
    data = get_finite_data(data)
    center_points = int(np.floor(data.size * 0.5))
    flank = int(np.floor((data.size - center_points) / 2))
    data.sort()
    return data[flank:-flank].mean()


def quantiles_stable(data: np.ndarray) -> tuple[float, float]:
    data = get_finite_data(data)
    threshold = int(np.floor(data.size * 0.25))
    data.sort()
    return data[threshold], data[-threshold]


def get_finite_data(
    data: Union[np.ndarray, np.ma.MaskedArray]
) -> np.ndarray:
    masked_data = (
        np.ma.masked_invalid(data) if not isinstance(data, np.ma.MaskedArray)
        else data
    )
    return masked_data[~masked_data.mask]
