from enum import Enum

import numpy as np
import pytest

from scanomatic.generics.model import Model, assert_models_deeply_equal
from scanomatic.io import jsonizer
from scanomatic.models.analysis_model import COMPARTMENTS, MEASURES, VALUES
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory


@pytest.mark.parametrize("model", (
    RPC_Job_Model_Factory.create(),
    AnalysisModelFactory.create(),
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
