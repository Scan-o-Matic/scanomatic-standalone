import pytest

from scanomatic.generics.model import Model
from scanomatic.models.factories.analysis_factories import (
    AnalysisFeaturesFactory
)
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.models.factories.scanning_factory import ScannerFactory


def test_can_hash():
    model = RPC_Job_Model_Factory.create(id='hello')
    assert hash(model)


def test_can_not_hash_without_id():
    model = RPC_Job_Model_Factory.create()
    with pytest.raises(ValueError):
        hash(model)


@pytest.mark.parametrize("left,right,expect", (
    (
        ScannerFactory.create(),
        RPC_Job_Model_Factory.create(),
        False,
    ),
    (
        RPC_Job_Model_Factory.create(),
        ScannerFactory.create(),
        False,
    ),
    (
        RPC_Job_Model_Factory.create(
            content_model=ScannerFactory.create(),
        ),
        RPC_Job_Model_Factory.create(
            content_model=ScannerFactory.create(),
        ),
        False,
    ),
    (
        RPC_Job_Model_Factory.create(
            id='hello',
            content_model=ScannerFactory.create(),
        ),
        RPC_Job_Model_Factory.create(
            content_model=ScannerFactory.create(),
        ),
        False,
    ),
    (
        RPC_Job_Model_Factory.create(
            id='hello',
            content_model=ScannerFactory.create(),
        ),
        RPC_Job_Model_Factory.create(
            id='hello',
            content_model=AnalysisFeaturesFactory.create(),
        ),
        False,
    ),
    (
        RPC_Job_Model_Factory.create(
            id='hello',
            content_model=ScannerFactory.create(),
        ),
        RPC_Job_Model_Factory.create(
            id='hello',
            content_model=ScannerFactory.create(),
        ),
        True,
    ),
))
def test_is_same_job(left: Model, right: Model, expect: bool):
    assert RPC_Job_Model_Factory.is_same_job(left, right) is expect
