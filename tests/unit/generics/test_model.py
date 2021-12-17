from typing import Optional
import pytest

from scanomatic.generics.model import Model, assert_models_deeply_equal
from scanomatic.models.analysis_model import GridModel, AnalysisModel


def test_identical_models_dont_raise():
    m = GridModel()
    assert_models_deeply_equal(m, m)


@pytest.mark.parametrize("a,b", (
    (GridModel(), GridModel()),
    (AnalysisModel(), AnalysisModel()),
))
def test_equal_models_dont_raise(a: Model, b: Model):
    assert_models_deeply_equal(a, b)


@pytest.mark.parametrize("a,b", (
    (GridModel(), None),
    (None, GridModel()),
    (AnalysisModel(animate_focal=True), AnalysisModel()),
    (
        AnalysisModel(grid_model=GridModel(use_utso=False)),
        AnalysisModel(grid_model=GridModel()),
    ),
))
def test_unequal_models_raises(
    a: Optional[Model],
    b: Optional[Model],
):
    with pytest.raises(ValueError):
        assert_models_deeply_equal(a, b)
