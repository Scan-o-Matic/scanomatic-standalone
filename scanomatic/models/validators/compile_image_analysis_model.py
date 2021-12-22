from typing import Literal, Union

from scanomatic.models.compile_project_model import (
    CompileImageAnalysisModel,
    CompileImageAnalysisModelFields,
)

ValidationResult = Union[Literal[True], CompileImageAnalysisModelFields]


def validate_fixture(
    model: CompileImageAnalysisModel,
) -> ValidationResult:
    if model.fixture is not None:
        return True
    else:
        return CompileImageAnalysisModelFields.fixture


def validate_image(
    model: CompileImageAnalysisModel,
) -> ValidationResult:
    if model.image is not None:
        return True
    else:
        return CompileImageAnalysisModelFields.image
