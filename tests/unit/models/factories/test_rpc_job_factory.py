import pytest

from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory


def test_can_hash():
    model = RPC_Job_Model_Factory.create(id='hello')
    assert hash(model)


def test_can_not_hash_without_id():
    model = RPC_Job_Model_Factory.create()
    with pytest.raises(ValueError):
        hash(model)
