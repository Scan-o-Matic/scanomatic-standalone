from typing import Any, Sequence

import pytest

from scanomatic.models.factories.fixture_factories import (
    GrayScaleAreaModelFactory
)


@pytest.mark.parametrize("settings,values", (
    ({'values': [1, 2, 3]}, [1, 2, 3]),
    ({'section_values': [1, 2, 3]}, [1, 2, 3]),
))
def test_create_grayscale_area_model_handles_values_field_change(
    settings: dict[str, Any],
    values: Sequence[float],
):
    assert GrayScaleAreaModelFactory.create(
        **settings,
    ).section_values == values
