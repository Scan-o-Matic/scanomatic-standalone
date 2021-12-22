import os
from typing import Literal, Union

from scanomatic.models.features_model import FeaturesModel, FeaturesModelFields


ValidationResult = Union[Literal[True], FeaturesModelFields]


def validate_analysis_directory(model: FeaturesModel) -> ValidationResult:
    if not isinstance(model.analysis_directory, str):
        return FeaturesModelFields.analysis_directory

    analysis_directory = model.analysis_directory.rstrip("/")
    if (
        os.path.abspath(analysis_directory) == analysis_directory
        and os.path.isdir(model.analysis_directory)
    ):
        return True
    return FeaturesModelFields.analysis_directory
