import os
from enum import Enum
from typing import Any

import pytest

from scanomatic.generics.model import Model
from scanomatic.io.jsonizer import dumps
from scanomatic.models.analysis_model import (
    AnalysisModelFields,
    GridModelFields
)
from scanomatic.models.factories.analysis_factories import (
    AnalysisModelFactory,
    GridModelFactory
)
from scanomatic.models.factories.fixture_factories import (
    FixtureFactory,
    FixturePlateFactory,
    GrayScaleAreaModelFactory
)
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.models.factories.scanning_factory import ScanningModelFactory
from scanomatic.models.factories.settings_factories import (
    ApplicationSettingsFactory
)
from scanomatic.models.fixture_models import FixtureModelFields
from scanomatic.models.rpc_job_models import RPCjobModelFields
from scanomatic.models.validators.validate import (
    get_invalid,
    get_invalid_as_text,
    get_invalid_names,
    validate
)


@pytest.mark.parametrize('model,updates,expect', (
    (GridModelFactory.create(), {}, True),
    (  # bad type, should be boolean
        GridModelFactory.create(),
        {'use_utso': 5},
        False,
    ),
    (  # failing special validator
        GridModelFactory.create(gridding_offsets=[[2, 3, 4]]),
        {},
        False,
    ),
    (AnalysisModelFactory.create(), {}, False),
    (
        AnalysisModelFactory.create(
            compilation=os.path.abspath(__file__),
            grid_model=GridModelFactory.create(),
        ),
        {},
        True,
    ),
    (  # invalid sub-model (grid_model)
        AnalysisModelFactory.create(
            compilation=os.path.abspath(__file__),
            grid_model=GridModelFactory.create(gridding_offsets=((2, 3, 4),)),
        ),
        {},
        False,
    ),
    (
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(),
        ),
        {},
        True,
    ),
    (
        FixturePlateFactory.create(),
        {},
        True,
    ),
    (
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(),
            plates=(FixturePlateFactory.create(),),
        ),
        {},
        True,
    ),
    (  # Wrong plate model
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(),
        ),
        {
            "plates": (GridModelFactory.create(),),
        },
        False,
    ),
    (
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(),
        ),
        {
            "plates": (FixturePlateFactory.create(), None),
        },
        True,
    ),
    (
        ApplicationSettingsFactory.create(),
        {},
        True,
    ),
))
def test_validate(model: Model, updates: dict[str, Any], expect: bool):
    for field, value in updates.items():
        setattr(model, field, value)
    assert validate(model) is expect, (
        get_invalid_as_text(model) if expect else dumps(model)
    )


@pytest.mark.parametrize('model,updates,expect', (
    (GridModelFactory.create(), {}, set()),
    (
        GridModelFactory.create(),
        {'use_utso': 5},
        {GridModelFields.use_utso},
    ),
    (
        GridModelFactory.create(),
        {'gridding_offsets': ((2., 0), None)},
        {GridModelFields.gridding_offsets},
    ),
    (
        AnalysisModelFactory.create(),
        {},
        {AnalysisModelFields.compilation},
    ),
    (
        AnalysisModelFactory.create(
            grid_model=GridModelFactory.create(
                gridding_offsets=[[1, 2, 3]],
            ),
        ),
        {},
        {AnalysisModelFields.compilation, AnalysisModelFields.grid_model},
    ),
    (
        FixtureFactory.create(grayscale=AnalysisModelFactory.create()),
        {
            "plates": (GridModelFactory.create(),),
        },
        {FixtureModelFields.grayscale, FixtureModelFields.plates},
    ),
    (
        RPC_Job_Model_Factory.create(id='aaa'),
        {},
        {RPCjobModelFields.content_model},
    ),
    (
        ScanningModelFactory.create(project_name="NaCl"),
        {},
        set(),
    ),
    (
        RPC_Job_Model_Factory.create(
            id='aaa',
            content_model=ScanningModelFactory.create(project_name="NaCl"),
        ),
        {},
        set(),
    ),
))
def test_get_invalid(model: Model, updates: dict[str, Any], expect: set[Enum]):
    for field, value in updates.items():
        setattr(model, field, value)
    assert set(get_invalid(model)) == expect


def test_get_invalid_names():
    assert list(get_invalid_names(FixtureFactory.create(
        grayscale=AnalysisModelFactory.create(),
    ))) == ["grayscale"]


def test_get_invalid_as_text():
    m = GridModelFactory.create()
    m.use_utso = 5  # type: ignore
    m.manual_threshold = -10
    assert get_invalid_as_text(m) == "manual_threshold: '-10', use_utso: '5'"
