from enum import Enum

import scanomatic.generics.model as model


class FeatureExtractionData(Enum):
    Default = 0
    State = 1


class FeaturesModel(model.Model):

    def __init__(
        self,
        analysis_directory: str = "",
        email: str = "",
        extraction_data:FeatureExtractionData = FeatureExtractionData.Default,
        try_keep_qc: bool = False,
    ):

        self.analysis_directory: str = analysis_directory
        self.email: str = email
        self.extraction_data: FeatureExtractionData = extraction_data
        self.try_keep_qc: bool = try_keep_qc
        super(FeaturesModel, self).__init__()
