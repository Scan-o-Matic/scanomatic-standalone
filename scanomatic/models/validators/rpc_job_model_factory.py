from scanomatic.models.rpc_job_models import JOB_STATUS, JOB_TYPE, RPCjobModel


def validate_pid(model: RPCjobModel):
    if model.pid is None or isinstance(model.pid, int) and model.pid > 0:
        return True

    return model.FIELD_TYPES.pid


def validate_id(model: RPCjobModel):
    if isinstance(model.id, str):
        return True
    return model.FIELD_TYPES.id


def validate_type(model: RPCjobModel):
    if model.type in JOB_TYPE:
        return True
    return model.FIELD_TYPES.type


def validate_priority(model: RPCjobModel):
    return isinstance(model.priority, int)


def validate_status(model: RPCjobModel):
    if model.status in JOB_STATUS:
        return True
    return model.FIELD_TYPES.model


def validate_content_model(model: RPCjobModel):
    if RPCjobModel.is_valid_submodel(model, 'content_model'):
        return True
    return model.FIELD_TYPES.content_model
