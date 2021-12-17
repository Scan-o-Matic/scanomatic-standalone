from collections import namedtuple
from collections.abc import Sequence
from typing import Optional, Union

import pytest

from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.server.proc_effector import ProcessEffector

EffectorInfo = namedtuple("EffectorInfo", ["effector", "job"])


@pytest.fixture
def info() -> EffectorInfo:
    job = RPC_Job_Model_Factory.create(
        content_model=AnalysisModelFactory.create(
            email="me@you.we",
        ),
    )
    return EffectorInfo(ProcessEffector(job), job)


@pytest.mark.parametrize("new_mail,success,mails", (
    (None, False, "me@you.we"),
    ("me@you.we", True, "me@you.we"),
    ("test@example.com", True, "me@you.we, test@example.com"),
    (["me@you.we", "test@example.com"], True, "me@you.we, test@example.com"),
))
def test_add_email(
    info: EffectorInfo,
    new_mail: Optional[Union[str, Sequence[str]]],
    success: bool,
    mails: str,
):
    assert info.effector.email(add=new_mail) is success
    assert info.job.content_model.email == mails


@pytest.mark.parametrize("new_mail,success,mails", (
    (None, False, "me@you.we"),
    ("me@you.we", True, ""),
    ("test@example.com", False, "me@you.we"),
))
def test_remove_email(
    info: EffectorInfo,
    new_mail: Optional[Union[str, Sequence[str]]],
    success: bool,
    mails: str,
):
    assert info.effector.email(remove=new_mail) is success
    assert info.job.content_model.email == mails
