import scanomatic.models.rpc_job_models as rpc_job_models
from scanomatic.generics.abstract_model_factory import AbstractModelFactory
from scanomatic.generics.model import Model
from scanomatic.models.analysis_model import AnalysisModel
from scanomatic.models.compile_project_model import CompileInstructionsModel
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.factories.compile_project_factory import (
    CompileProjectFactory
)
from scanomatic.models.factories.features_factory import FeaturesFactory
from scanomatic.models.factories.scanning_factory import (
    ScanningModel,
    ScanningModelFactory
)
from scanomatic.models.features_model import FeaturesModel


class RPC_Job_Model_Factory(AbstractModelFactory):
    MODEL = rpc_job_models.RPCjobModel
    _SUB_FACTORIES = {
        ScanningModel: ScanningModelFactory,
        AnalysisModel: AnalysisModelFactory,
        CompileInstructionsModel: CompileProjectFactory,
        FeaturesModel: FeaturesFactory
    }
    STORE_SECTION_SERIALIZERS = {
        'id': str,
        'type': rpc_job_models.JOB_TYPE,
        'status': rpc_job_models.JOB_STATUS,
        'priority': int,
        'content_model': Model,
        'pid': int}

    @classmethod
    def create(cls, **settings) -> rpc_job_models.RPCjobModel:
        return super(RPC_Job_Model_Factory, cls).create(**settings)
