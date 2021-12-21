import os

from scanomatic.models.features_model import FeaturesModel


def validate_analysis_directory(model: FeaturesModel):
    if not isinstance(model.analysis_directory, str):
        return model.FIELD_TYPES.analysis_directory

    analysis_directory = model.analysis_directory.rstrip("/")
    if (
        os.path.abspath(analysis_directory) == analysis_directory
        and os.path.isdir(model.analysis_directory)
    ):
        return True
    if model.FIELD_TYPES is None:
        raise ValueError("Model not initialized properly")
    return model.FIELD_TYPES.analysis_directory
