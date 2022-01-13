from typing import Union
import numpy as np
import pytest

from scanomatic.generics.maths import quantiles_stable, get_finite_data


def test_quantiles_stable():
    data = np.arange(100)
    assert quantiles_stable(data) == (25, 75)


@pytest.mark.parametrize("data,expect", (
    (
        np.array([0, 1, np.nan, np.inf, 5]),
        np.array([0, 1, 5]),
    ),
    (
        np.ma.masked_invalid(np.array([np.nan, 1, np.inf, 4, 5])),
        np.array([1, 4, 5]),
    ),
))
def test_get_finite_data(
    data: Union[np.ndarray, np.ma.MaskedArray],
    expect: np.ndarray,
):
    assert (get_finite_data(data) == expect).all()
