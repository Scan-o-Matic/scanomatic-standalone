from typing import Literal, Union

from scanomatic.models.rpc_job_models import (
    JOB_STATUS,
    JOB_TYPE,
    RPCjobModel,
    RPCjobModelFields,
)

ValidationResult = Union[Literal[True], RPCjobModelFields]


def validate_pid(model: RPCjobModel) -> ValidationResult:
    if model.pid is None or isinstance(model.pid, int) and model.pid > 0:
        return True

    return RPCjobModelFields.pid


def validate_id(model: RPCjobModel) -> ValidationResult:
    if isinstance(model.id, str):
        return True
    return RPCjobModelFields.id


def validate_type(model: RPCjobModel) -> ValidationResult:
    if model.type in JOB_TYPE:
        return True
    return RPCjobModelFields.type


def validate_priority(model: RPCjobModel) -> ValidationResult:
    if isinstance(model.priority, int):
        return True
    return RPCjobModelFields.priority


def validate_status(model: RPCjobModel) -> ValidationResult:
    if model.status in JOB_STATUS:
        return True
    return RPCjobModelFields.status


def validate_content_model(model: RPCjobModel) -> ValidationResult:
    if model.content_model is not None:
        return True
    return RPCjobModelFields.content_model
