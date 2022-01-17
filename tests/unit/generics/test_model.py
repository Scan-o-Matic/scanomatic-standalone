from typing import Optional
import pytest

from scanomatic.generics.model import Model, assert_models_deeply_equal
from scanomatic.models.analysis_model import GridModel
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory


def test_identical_models_dont_raise():
    m = GridModel()
    assert_models_deeply_equal(m, m)


@pytest.mark.parametrize("a,b", (
    (GridModel(), GridModel()),
    (AnalysisModelFactory.create(), AnalysisModelFactory.create()),
))
def test_equal_models_dont_raise(a: Model, b: Model):
    assert_models_deeply_equal(a, b)


@pytest.mark.parametrize("a,b", (
    (GridModel(), None),
    (None, GridModel()),
    (
        AnalysisModelFactory.create(animate_focal=True),
        AnalysisModelFactory.create(),
    ),
    (
        AnalysisModelFactory.create(grid_model=GridModel(use_utso=False)),
        AnalysisModelFactory.create(grid_model=GridModel()),
    ),
))
def test_unequal_models_raises(
    a: Optional[Model],
    b: Optional[Model],
):
    with pytest.raises(ValueError):
        assert_models_deeply_equal(a, b)
