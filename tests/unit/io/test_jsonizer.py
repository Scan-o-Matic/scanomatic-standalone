from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Optional, Type, Union

import numpy as np
import pytest

from scanomatic.generics.model import Model, assert_models_deeply_equal
from scanomatic.io import jsonizer
from scanomatic.io.power_manager import POWER_MANAGER_TYPE, POWER_MODES
from scanomatic.models import analysis_model
from scanomatic.models.analysis_model import (
    COMPARTMENTS,
    MEASURES,
    VALUES,
    AnalysisFeatures,
    AnalysisModel
)
from scanomatic.models.compile_project_model import COMPILE_ACTION, FIXTURE
from scanomatic.models.factories.analysis_factories import (
    AnalysisFeaturesFactory,
    AnalysisModelFactory
)
from scanomatic.models.factories.compile_project_factory import (
    CompileImageAnalysisFactory,
    CompileImageFactory,
    CompileProjectFactory
)
from scanomatic.models.factories.features_factory import FeaturesFactory
from scanomatic.models.factories.fixture_factories import (
    FixtureFactory,
    FixturePlateFactory,
    GrayScaleAreaModelFactory
)
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.models.factories.scanning_factory import (
    PlateDescriptionFactory,
    ScannerFactory,
    ScannerOwnerFactory,
    ScanningAuxInfoFactory,
    ScanningModelFactory
)
from scanomatic.models.factories.settings_factories import (
    ApplicationSettingsFactory,
    HardwareResourceLimitsFactory,
    MailFactory,
    PathsFactory,
    PowerManagerFactory,
    RPCServerFactory,
    UIServerFactory,
)
from scanomatic.models.features_model import FeatureExtractionData
from scanomatic.models.fixture_models import FixtureModel
from scanomatic.models.scanning_model import CULTURE_SOURCE, PLATE_STORAGE


@pytest.mark.parametrize("model", (
    RPC_Job_Model_Factory.create(),
    AnalysisModelFactory.create(),
    AnalysisFeaturesFactory.create(shape=(32,), data=[{'a': 1}], index=0),
    AnalysisFeaturesFactory.create(shape=(32,), data={'a': 1}, index=0),
    CompileImageFactory.create(index=1, time_stamp=42., path="image.tiff"),
    CompileProjectFactory.create(
        compile_action=COMPILE_ACTION.Initiate,
        images=(
            CompileImageFactory.create(index=1),
            CompileImageFactory.create(index=2),
        ),
        path='location.file',
        start_condition='good condition',
        email="hello@test.me",
        fixture_type=FIXTURE.Global,
        overwrite_pinning_matrices=((32, 15), (42, 24)),
    ),
    CompileImageAnalysisFactory.create(
        image=CompileImageFactory.create(index=42),
        fixture=FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(
                name="silverfast",
                values=[123.5, 155.1],
                x1=13,
            ),
            orientation_marks_x=(10., 12., 13.),
            plates=(FixturePlateFactory.create(index=1),)
        )
    ),
    FeaturesFactory.create(
        analysis_directory="analysis",
        email="john@doe.org, jane@doe.org",
        extraction_data=FeatureExtractionData.State,
        try_keep_qc=True,
    ),
    FixturePlateFactory.create(index=32),
    GrayScaleAreaModelFactory.create(name='silverfast', width=32.5, values=[]),
    FixtureFactory.create(
        grayscale=GrayScaleAreaModelFactory.create(
            name="silverfast",
            values=[123.5, 155.1],
            x1=13,
        ),
        orientation_marks_x=(10., 12., 13.),
        plates=(FixturePlateFactory.create(index=1),)
    ),
    PlateDescriptionFactory.create(name='hello'),
    ScanningAuxInfoFactory.create(
        plate_storage=PLATE_STORAGE.RoomTemperature,
        culture_source=CULTURE_SOURCE.Novel,
    ),
    ScanningModelFactory.create(
        email="hello@me.me",
        plate_descriptions=(PlateDescriptionFactory.create(name="bye"),),
        pinning_formats=((32, 12), (8, 9)),
        auxillary_info=ScanningAuxInfoFactory.create(
            culture_source=CULTURE_SOURCE.Fridge,
        ),
        scanning_program_params=("run", "forever"),
    ),
    ScannerOwnerFactory.create(id="user", pid=42),
    ScannerFactory.create(
        owner=ScannerOwnerFactory.create(id="admin"),
        reported=True,
    ),
    PowerManagerFactory.create(
        type=POWER_MANAGER_TYPE.USB,
        power_modes=POWER_MODES.Toggle,
        host="localhost",
    ),
    RPCServerFactory.create(port=8888, host="192.168.1.1"),
    UIServerFactory.create(master_key="marmite"),
    HardwareResourceLimitsFactory.create(
        cpu_free_count=13,
    ),
    MailFactory.create(server='localhost'),
    PathsFactory.create(projects_root="/dev/null"),
    ApplicationSettingsFactory.create(
        power_manager=PowerManagerFactory.create(
            host="test.com",
            number_of_sockets=2,
        ),
        rpc_server=RPCServerFactory.create(),
        ui_server=UIServerFactory.create(),
        hardware_resource_limits=HardwareResourceLimitsFactory.create(),
        mail=MailFactory.create(),
        paths=PathsFactory.create(),
        scanner_models=["EPSON V700", "EPSON V800"],
    ),
))
def test_preserves_model(model: Model):
    assert_models_deeply_equal(model, jsonizer.loads(jsonizer.dumps(model)))


@pytest.mark.parametrize("arr", (
    np.arange(3),
    np.ones((2, 2)),
))
def test_preserves_arrays(arr: np.ndarray):
    arr2 = jsonizer.loads(jsonizer.dumps(arr))
    assert arr2.dtype == arr.dtype
    np.testing.assert_equal(arr, arr2)


def test_preserves_object_array():
    arr = np.array([None, 4, np.array([2, 1])])
    arr2 = jsonizer.loads(jsonizer.dumps(arr))
    assert arr2.dtype == arr.dtype
    assert arr[0] is arr2[0]
    assert arr[1] == arr2[1]
    assert arr[2].dtype == arr2[2].dtype
    np.testing.assert_equal(arr[2], arr2[2])


@pytest.mark.parametrize("test_enum", (
    COMPARTMENTS.Blob,
    VALUES.Pixels,
    MEASURES.Centroid,
))
def test_preserves_enums(test_enum: Enum):
    assert jsonizer.loads(jsonizer.dumps(test_enum)) is test_enum


def test_raises_on_unknown_enum_dumping():
    class E(Enum):
        A = 1

    with pytest.raises(jsonizer.JSONEncodingError):
        jsonizer.dumps(E.A)


@pytest.mark.parametrize('s', (
    '{"__ENUM__": "MEASURES", "__CONTENT__": "Sumzzz"}',
    '{"__ENUM__": "MEASUREZZZ", "__CONTENT__": "Sum"}',
    '{"__ENUM__": "MEASUREZZZ"}',
    '{"__ENUM__": "MEASUREZZZ", "__CONTENT__": null}',
))
def test_raises_on_unkown_enum_loading(s: str):
    with pytest.raises(jsonizer.JSONDecodingError):
        jsonizer.loads(s)


def test_raises_on_unknown_model_dumping():
    with pytest.raises(jsonizer.JSONEncodingError):
        jsonizer.dumps(Model())


@pytest.mark.parametrize('s', (
    '{"__MODEL__": "Model", "__CONTENT__": {}}',
    '{"__MODEL__": "Model", "__CONTENT__": null}',
))
def test_raises_on_unkown_model_loading(s: str):
    with pytest.raises(jsonizer.JSONDecodingError):
        jsonizer.loads(s)


@pytest.fixture
def fixture() -> FixtureModel:
    return FixtureFactory.create(
        grayscale=GrayScaleAreaModelFactory.create(
            name="silverfast",
            values=[123.5, 155.1],
            x1=13,
        ),
        orientation_marks_x=(10., 12., 13.),
        plates=(FixturePlateFactory.create(index=1),)
    )


def test_copy_makes_new_object(fixture: FixtureModel):
    new_fixture: FixtureModel = jsonizer.copy(fixture)
    assert new_fixture is not fixture
    assert new_fixture.grayscale is not fixture.grayscale
    assert (
        new_fixture.grayscale.section_values
        == fixture.grayscale.section_values
    )


@pytest.mark.parametrize('filename,expect', (
    ('analysis.model', AnalysisModel),
    ('analysis.model-list', list),
    ('not-a-file', None),
))
def test_load(filename: str, expect: Optional[Type]):
    data = jsonizer.load(
        Path(__file__).parent / 'fixtures' / filename,
    )
    if expect is None:
        assert data is None
    else:
        assert isinstance(data, expect)


@pytest.mark.parametrize('filename,expect', (
    ('analysis.model', AnalysisModel),
    ('analysis.model-list', AnalysisModel),
    ('not-a-file', None),
))
def test_load_first(filename: str, expect: Optional[Type]):
    data = jsonizer.load_first(
        Path(__file__).parent / 'fixtures' / filename,
    )
    if expect is None:
        assert data is None
    else:
        assert isinstance(data, expect)


@pytest.mark.parametrize("previous,update,expect", (
    (
        None,
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=13),
            orientation_marks_x=(10., 12., 13.),
            plates=(FixturePlateFactory.create(index=1),)
        ),
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=13),
            orientation_marks_x=(10., 12., 13.),
            plates=(FixturePlateFactory.create(index=1),)
        ),
    ),
    (
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=44),
            orientation_marks_x=(10., 42., 13.),
            plates=(FixturePlateFactory.create(index=12),)
        ),
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=13),
            orientation_marks_x=(10., 12., 13.),
            plates=(FixturePlateFactory.create(index=1),)
        ),
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=13),
            orientation_marks_x=(10., 12., 13.),
            plates=(FixturePlateFactory.create(index=1),)
        ),
    ),
    (  # Replaces the existing model of same type
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=44),
            orientation_marks_x=(10., 42., 13.),
            plates=(FixturePlateFactory.create(index=12),)
        ),
        GrayScaleAreaModelFactory.create(x1=13),
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=13),
            orientation_marks_x=(10., 42., 13.),
            plates=(FixturePlateFactory.create(index=12),)
        ),
    ),
    (  # Lists as update assume overwrite
        None,
        [
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=13),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
        ],
        [
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=13),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
        ],
    ),
    (  # Updates first item if right type
        [
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=42),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=13),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
        ],
        FixtureFactory.create(
            grayscale=GrayScaleAreaModelFactory.create(x1=1),
            orientation_marks_x=(10., 42., 13.),
            plates=(FixturePlateFactory.create(index=12),)
        ),
        [
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=1),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=13),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
        ],
    ),
    (  # Updates insert first item
        [
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=42),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=13),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
        ],
        GrayScaleAreaModelFactory.create(x1=1),
        [
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=1),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
            FixtureFactory.create(
                grayscale=GrayScaleAreaModelFactory.create(x1=13),
                orientation_marks_x=(10., 42., 13.),
                plates=(FixturePlateFactory.create(index=12),)
            ),
        ],
    ),
))
def test_merge_into(
    previous: Optional[Union[Model, list[Model]]],
    update: Union[list[Model], Model],
    expect: Union[list[Model], Model],
):
    updated = jsonizer.merge_into(previous, update)
    assert jsonizer.dumps(updated) == jsonizer.dumps(expect)


def test_dump(tmp_path, fixture: FixtureModel):
    assert jsonizer.dump(fixture, tmp_path / 'my.file') is True


def test_dump_to_bad_location(tmp_path, fixture: FixtureModel):
    assert jsonizer.dump(
        fixture,
        tmp_path / 'no-dir' / 'my.file',
    ) is False


def test_dump_to_stream(fixture: FixtureModel):
    stream = StringIO()
    jsonizer.dump_to_stream(fixture, stream)
    stream.flush()
    stream.seek(0)
    serialized = stream.read()
    assert serialized
    model = jsonizer.loads(serialized)
    assert isinstance(model, FixtureModel)


def test_dump_to_stream_appending(fixture: FixtureModel):
    stream = StringIO()
    jsonizer.dump_to_stream(fixture, stream, as_if_appending=True)
    stream.flush()
    stream.seek(0)
    models = jsonizer.loads(stream.read())
    assert isinstance(models, list)
    assert len(models) == 1
    assert all(isinstance(m, FixtureModel) for m in models)
    jsonizer.dump_to_stream(fixture, stream, as_if_appending=True)
    stream.flush()
    stream.seek(0)
    models = jsonizer.loads(stream.read())
    assert isinstance(models, list)
    assert len(models) == 2
    assert all(isinstance(m, FixtureModel) for m in models)


def test_dump_to_stream_appending_first_normal(fixture: FixtureModel):
    stream = StringIO()
    jsonizer.dump_to_stream(fixture, stream, as_if_appending=False)
    stream.flush()
    stream.seek(0)
    model = jsonizer.loads(stream.read())
    assert isinstance(model, FixtureModel)
    jsonizer.dump_to_stream(fixture, stream, as_if_appending=True)
    stream.flush()
    stream.seek(0)
    models = jsonizer.loads(stream.read())
    assert isinstance(models, list)
    assert len(models) == 2
    assert all(isinstance(m, FixtureModel) for m in models)


def test_purge_non_existing(tmp_path, fixture: FixtureModel):
    assert jsonizer.purge(fixture, tmp_path / 'no-file') is False


def test_purge(tmp_path, fixture: FixtureModel):
    path = tmp_path / 'my.fixtures'
    jsonizer.dump([fixture], path)
    assert jsonizer.purge(fixture, path) is True
    assert jsonizer.load(path) == []


def test_purge_custom_equality(tmp_path):
    path = tmp_path / 'jobs.cfg'
    job = RPC_Job_Model_Factory.create(
        id="hello",
        content_model=AnalysisFeaturesFactory.create(),
    )
    analysis_model: AnalysisFeatures = job.content_model
    other_job = RPC_Job_Model_Factory.create(id='other-id'),
    # Rogue job with same id of different type shouldn't happen
    rogue_job = RPC_Job_Model_Factory.create(
        id='hello',
        content_model=ScannerFactory.create(),
    )
    jobs = [other_job, job, rogue_job]
    jsonizer.dump(jobs, path)
    # Update conentent model
    analysis_model.index = 42
    assert jsonizer.purge(job, path, RPC_Job_Model_Factory.is_same_job) is True
    saved_jobs = jsonizer.load(path)
    assert len(saved_jobs) == 2
    assert jsonizer.dumps(saved_jobs) == jsonizer.dumps([other_job, rogue_job])



def test_purge_field(tmp_path, fixture: FixtureModel):
    path = tmp_path / 'my.fixtures'
    jsonizer.dump([fixture], path)
    assert jsonizer.purge(fixture.grayscale, path) is True
    models: list[FixtureModel] = jsonizer.load(path)
    assert len(models) == 1
    assert (
        jsonizer.dumps(models[0].grayscale)
        != jsonizer.dumps(fixture.grayscale)
    )


def test_purge_field_item(tmp_path, fixture: FixtureModel):
    path = tmp_path / 'my.fixtures'
    jsonizer.dump([fixture], path)
    assert jsonizer.purge(fixture.plates[0], path) is True
    models: list[FixtureModel] = jsonizer.load(path)
    assert len(models) == 1
    assert models[0].plates == tuple()
