from types import ModuleType
from typing import Optional, Type

from scanomatic.generics.model import Model
from scanomatic.models.analysis_model import AnalysisModel, GridModel
from scanomatic.models.compile_project_model import (
    CompileImageAnalysisModel,
    CompileImageModel,
    CompileInstructionsModel
)
from scanomatic.models.features_model import FeaturesModel
from scanomatic.models.rpc_job_models import RPCjobModel
from scanomatic.models.scanning_model import (
    PlateDescription,
    ScanningAuxInfoModel,
    ScanningModel
)

from . import (
    analysis_model,
    compile_image_analysis_model,
    compile_image_model,
    compile_instructions_model,
    features_model,
    grid_model,
    plate_description,
    rpc_job_model,
    scanning_aux_info_model,
    scanning_model
)

_SPECIAL_VALIDATORS: dict[Type[Model], ModuleType] = {
    AnalysisModel:  analysis_model,
    CompileImageAnalysisModel: compile_image_analysis_model,
    CompileImageModel: compile_image_model,
    CompileInstructionsModel: compile_instructions_model,
    FeaturesModel: features_model,
    GridModel: grid_model,
    PlateDescription: plate_description,
    ScanningAuxInfoModel: scanning_aux_info_model,
    ScanningModel: scanning_model,
    RPCjobModel: rpc_job_model
}


def get_special_validators(model: Model) -> Optional[ModuleType]:
    return _SPECIAL_VALIDATORS.get(type(model))
