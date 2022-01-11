from enum import Enum
from typing import Optional, Type

from scanomatic.generics.model import Model
from scanomatic.models.analysis_model import (
    AnalysisFeatures,
    AnalysisFeaturesFields,
    AnalysisModel,
    AnalysisModelFields,
    GridModel,
    GridModelFields
)
from scanomatic.models.compile_project_model import (
    CompileImageAnalysisModel,
    CompileImageAnalysisModelFields,
    CompileImageModel,
    CompileImageModelFields,
    CompileInstructionsModel,
    CompileInstructionsModelFields
)
from scanomatic.models.features_model import FeaturesModel, FeaturesModelFields
from scanomatic.models.fixture_models import (
    FixtureModel,
    FixtureModelFields,
    FixturePlateModel,
    FixturePlateModelFields,
    GrayScaleAreaModel,
    GrayScaleAreaModelFields
)
from scanomatic.models.phases_models import (
    SegmentationModel,
    SegmentationModelFields
)
from scanomatic.models.rpc_job_models import RPCjobModel, RPCjobModelFields
from scanomatic.models.scanning_model import (
    PlateDescription,
    PlateDescriptionFields,
    ScannerModel,
    ScannerModelFields,
    ScannerOwnerModel,
    ScannerOwnerModelFields,
    ScanningAuxInfoModel,
    ScanningAuxInfoModelFields,
    ScanningModel,
    ScanningModelEffectorData,
    ScanningModelEffectorDataFields,
    ScanningModelFields
)
from scanomatic.models.settings_models import (
    ApplicationSettingsModel,
    ApplicationSettingsModelFields,
    HardwareResourceLimitsModel,
    HardwareResourceLimitsModelFields,
    MailModel,
    MailModelFields,
    PathsModel,
    PathsModelFields,
    PowerManagerModel,
    PowerManagerModelFields,
    RPCServerModel,
    RPCServerModelFields,
    UIServerModel,
    UIServerModelFields,
    VersionChangesModel,
    VersionChangesModelFields
)

_FIELDS: dict[Type[Model], Type[Enum]] = {
    AnalysisModel: AnalysisModelFields,
    GridModel: GridModelFields,
    AnalysisFeatures: AnalysisFeaturesFields,
    CompileInstructionsModel: CompileInstructionsModelFields,
    CompileImageModel: CompileImageModelFields,
    CompileImageAnalysisModel: CompileImageAnalysisModelFields,
    FeaturesModel: FeaturesModelFields,
    GrayScaleAreaModel: GrayScaleAreaModelFields,
    FixtureModel: FixtureModelFields,
    FixturePlateModel: FixturePlateModelFields,
    SegmentationModel: SegmentationModelFields,
    RPCjobModel: RPCjobModelFields,
    ScanningAuxInfoModel: ScanningAuxInfoModelFields,
    ScanningModel: ScanningModelFields,
    PlateDescription: PlateDescriptionFields,
    ScannerOwnerModel: ScannerOwnerModelFields,
    ScannerModel: ScannerModelFields,
    ScanningModelEffectorData: ScanningModelEffectorDataFields,
    VersionChangesModel: VersionChangesModelFields,
    PowerManagerModel: PowerManagerModelFields,
    RPCServerModel: RPCServerModelFields,
    UIServerModel: UIServerModelFields,
    HardwareResourceLimitsModel: HardwareResourceLimitsModelFields,
    PathsModel: PathsModelFields,
    MailModel: MailModelFields,
    ApplicationSettingsModel: ApplicationSettingsModelFields,
}


def get_field_types(model: Model) -> Optional[Type[Enum]]:
    return _FIELDS.get(type(model))
