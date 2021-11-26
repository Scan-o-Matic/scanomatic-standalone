import os
from typing import cast

import scanomatic.models.features_model as features_model
from scanomatic.generics.abstract_model_factory import (
    AbstractModelFactory,
    email_serializer
)


class FeaturesFactory(AbstractModelFactory):
    MODEL = features_model.FeaturesModel
    STORE_SECTION_HEAD = ("analysis_directory", )
    STORE_SECTION_SERIALIZERS = {
        "analysis_directory": str,
        "email": email_serializer,
        "extraction_data": features_model.FeatureExtractionData,
        "try_keep_qc": bool
    }

    @classmethod
    def _validate_analysis_directory(cls, model: features_model.FeaturesModel):

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

    @classmethod
    def create(cls, **settings) -> features_model.FeaturesModel:
        return cast(
            features_model.FeaturesModel,
            super(FeaturesFactory, cls).create(**settings)
        )
