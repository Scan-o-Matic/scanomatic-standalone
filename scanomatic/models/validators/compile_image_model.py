import os
from typing import Literal, Union

from scanomatic.models.compile_project_model import (
    CompileImageModel,
    CompileImageModelFields,
)

ValidationResult = Union[Literal[True], CompileImageModelFields]


def validate_index(model: CompileImageModel) -> ValidationResult:
    if model.index >= 0:
        return True
    return CompileImageModelFields.index


def validate_path(model: CompileImageModel) -> ValidationResult:
    if (
        os.path.abspath(model.path) == model.path
        and os.path.isfile(model.path)
    ):
        return True
    return CompileImageModelFields.path


def validate_time_stamp(model: CompileImageModel) -> ValidationResult:
    if model.time_stamp >= 0.0:
        return True
    return CompileImageModelFields.time_stamp
