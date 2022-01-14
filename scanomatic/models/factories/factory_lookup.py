from typing import Optional, Type
from scanomatic.generics.abstract_model_factory import AbstractModelFactory

from scanomatic.generics.model import Model
from scanomatic.models.analysis_model import (
    AnalysisFeatures,
    AnalysisModel,
    GridModel
)
from scanomatic.models.compile_project_model import (
    CompileImageAnalysisModel,
    CompileImageModel,
    CompileInstructionsModel
)
from scanomatic.models.factories.analysis_factories import (
    AnalysisFeaturesFactory,
    AnalysisModelFactory,
    GridModelFactory
)
from scanomatic.models.factories.compile_project_factory import (
    CompileImageAnalysisFactory,
    CompileImageFactory,
    CompileProjectFactory
)
from scanomatic.models.factories.features_factory import FeaturesFactory
from scanomatic.models.factories.fixture_factories import (
    FixtureFactory,
    FixturePlateFactory,
    GrayScaleAreaModelFactory
)
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.models.factories.scanning_factory import (
    PlateDescriptionFactory,
    ScannerFactory,
    ScannerOwnerFactory,
    ScanningAuxInfoFactory,
    ScanningModelFactory
)
from scanomatic.models.factories.settings_factories import (
    ApplicationSettingsFactory,
    HardwareResourceLimitsFactory,
    MailFactory,
    PathsFactory,
    PowerManagerFactory,
    RPCServerFactory,
    UIServerFactory,
)
from scanomatic.models.features_model import FeaturesModel
from scanomatic.models.fixture_models import (
    FixtureModel,
    FixturePlateModel,
    GrayScaleAreaModel
)
from scanomatic.models.rpc_job_models import RPCjobModel
from scanomatic.models.scanning_model import (
    PlateDescription,
    ScannerModel,
    ScannerOwnerModel,
    ScanningAuxInfoModel,
    ScanningModel
)
from scanomatic.models.settings_models import (
    ApplicationSettingsModel,
    HardwareResourceLimitsModel,
    MailModel,
    PathsModel,
    PowerManagerModel,
    RPCServerModel,
    UIServerModel,
)

_FACTORIES: dict[Type[Model], Type[AbstractModelFactory]] = {
    # From analysis_factories.py
    GridModel: GridModelFactory,
    AnalysisModel: AnalysisModelFactory,
    AnalysisFeatures: AnalysisFeaturesFactory,
    # From compile_project_factory.py
    CompileImageModel: CompileImageFactory,
    CompileInstructionsModel: CompileProjectFactory,
    CompileImageAnalysisModel: CompileImageAnalysisFactory,
    # From features_factory.py
    FeaturesModel: FeaturesFactory,
    # From fixture_factories.py
    FixturePlateModel: FixturePlateFactory,
    GrayScaleAreaModel: GrayScaleAreaModelFactory,
    FixtureModel: FixtureFactory,
    # From rpc_job_factory.py
    RPCjobModel: RPC_Job_Model_Factory,
    # From scanning_factory.py
    PlateDescription: PlateDescriptionFactory,
    ScanningAuxInfoModel: ScanningAuxInfoFactory,
    ScanningModel: ScanningModelFactory,
    ScannerOwnerModel: ScannerOwnerFactory,
    ScannerModel: ScannerFactory,
    # From settings_factories.py
    # Versions shouldn't serialize or load so excluded
    # VersionChangesModel: VersionChangeFactory
    PowerManagerModel: PowerManagerFactory,
    RPCServerModel: RPCServerFactory,
    UIServerModel: UIServerFactory,
    HardwareResourceLimitsModel: HardwareResourceLimitsFactory,
    MailModel: MailFactory,
    PathsModel: PathsFactory,
    ApplicationSettingsModel: ApplicationSettingsFactory,
}


def get_factory(model: Model) -> Optional[Type[AbstractModelFactory]]:
    return _FACTORIES.get(type(model))
