from typing import cast

import scanomatic.models.features_model as features_model
from scanomatic.generics.abstract_model_factory import (
    AbstractModelFactory,
    email_serializer,
)


class FeaturesFactory(AbstractModelFactory):
    MODEL = features_model.FeaturesModel
    STORE_SECTION_SERIALIZERS = {
        "analysis_directory": str,
        "email": email_serializer,
        "extraction_data": features_model.FeatureExtractionData,
        "try_keep_qc": bool
    }

    @classmethod
    def create(cls, **settings) -> features_model.FeaturesModel:
        return cast(
            features_model.FeaturesModel,
            super(FeaturesFactory, cls).create(**settings)
        )
