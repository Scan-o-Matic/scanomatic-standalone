from enum import Enum, auto

import scanomatic.generics.model as model


class FeatureExtractionData(Enum):
    Default = 0
    State = 1

    @classmethod
    def from_name(cls, raw_string: str) -> "FeatureExtractionData":
        for member in FeatureExtractionData:
            if member.name.upper() == raw_string.upper():
                return member


class FeaturesModelFields(Enum):
    analysis_directory = auto()
    email = auto()
    extraction_data = auto()
    try_keep_qc = auto()


class FeaturesModel(model.Model):
    def __init__(
        self,
        analysis_directory: str = "",
        email: str = "",
        extraction_data: FeatureExtractionData = FeatureExtractionData.Default,
        try_keep_qc: bool = False,
    ):

        self.analysis_directory: str = analysis_directory
        self.email: str = email
        self.extraction_data: FeatureExtractionData = extraction_data
        self.try_keep_qc: bool = try_keep_qc
        super().__init__()
