import os
from scanomatic.models.compile_project_model import CompileImageModel


def validate_index(model: CompileImageModel):
    if model.index >= 0:
        return True
    return model.FIELD_TYPES.index


def validate_path(model: CompileImageModel):
    if (
        os.path.abspath(model.path) == model.path
        and os.path.isfile(model.path)
    ):
        return True
    return model.FIELD_TYPES.path


def validate_time_stamp(model: CompileImageModel):
    if model.time_stamp >= 0.0:
        return True
    return model.FIELD_TYPES.time_stamp
