import json
import logging
from collections.abc import Callable
from enum import Enum, unique
from typing import Any, Type, Union

import numpy as np

from scanomatic.generics.model import Model
from scanomatic.io.power_manager import POWER_MANAGER_TYPE, POWER_MODES
from scanomatic.models.analysis_model import COMPARTMENTS, MEASURES, VALUES
from scanomatic.models.compile_project_model import COMPILE_ACTION, FIXTURE
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
    VersionChangeFactory
)
from scanomatic.models.features_model import FeatureExtractionData
from scanomatic.models.rpc_job_models import JOB_STATUS, JOB_TYPE
from scanomatic.models.scanning_model import CULTURE_SOURCE, PLATE_STORAGE


class JSONSerializationError(ValueError):
    pass


class JSONDecodingError(JSONSerializationError):
    pass


class JSONEncodingError(JSONSerializationError):
    pass


CONTENT = "__CONTENT__"


MODEL_CLASSES: dict[str, Callable[..., Model]] = {
    # From analysis_factories.py
    "GridModel": GridModelFactory.create,
    "AnalysisModel": AnalysisModelFactory.create,
    "AnalysisFeatures": AnalysisFeaturesFactory.create,
    # From compile_project_factory.py
    "CompileImageModel": CompileImageFactory.create,
    "CompileInstructionsModel": CompileProjectFactory.create,
    "CompileImageAnalysisModel": CompileImageAnalysisFactory.create,
    # From features_factory.py
    "FeaturesModel": FeaturesFactory.create,
    # From fixture_factories.py
    "FixturePlateModel": FixturePlateFactory.create,
    "GrayScaleAreaModel": GrayScaleAreaModelFactory.create,
    "FixtureModel": FixtureFactory.create,
    # From rpc_job_factory.py
    "RPCjobModel": RPC_Job_Model_Factory.create,
    # From scanning_factory.py
    "PlateDescription": PlateDescriptionFactory.create,
    "ScanningAuxInfoModel": ScanningAuxInfoFactory.create,
    "ScanningModel": ScanningModelFactory.create,
    "ScannerOwnerModel": ScannerOwnerFactory.create,
    "ScannerModel": ScannerFactory.create,
    # From settings_factories.py
    "VersionChangesModel": VersionChangeFactory.create,
    "PowerManagerModel": PowerManagerFactory.create,
    "RPCServerModel": RPCServerFactory.create,
    "UIServerModel": UIServerFactory.create,
    "HardwareResourceLimitsModel": HardwareResourceLimitsFactory.create,
    "MailModel": MailFactory.create,
    "PathsModel": PathsFactory.create,
    "ApplicationSettingsModel": ApplicationSettingsFactory.create,
}


def decode_model(obj: dict) -> Model:
    encoding = SOMSerializers.MODEL.encoding
    try:
        creator = MODEL_CLASSES[obj[encoding]]
    except KeyError:
        msg = f"'{obj.get(encoding)}' is not a recognized model"
        logging.error(msg)
        raise JSONDecodingError(msg)
    try:
        content: dict = obj[CONTENT]
    except KeyError:
        msg = f"Serialized model {obj[encoding]} didn't have any content"
        logging.error(msg)
        raise JSONDecodingError(msg)

    try:
        return creator(**{
            k: object_hook(v) if isinstance(v, dict) else v
            for k, v in content.items()
        })
    except (TypeError, AttributeError):
        msg = f"Serialized model {obj[encoding]} couldn't parse content: {content}"  # noqa: E501
        logging.exception(msg)
        raise JSONDecodingError(msg)


ENUM_CLASSES: dict[str, Type[Enum]] = {
    "COMPARTMENTS": COMPARTMENTS,
    "VALUES": VALUES,
    "MEASURES": MEASURES,
    "JOB_TYPE": JOB_TYPE,
    "JOB_STATUS": JOB_STATUS,
    "COMPILE_ACTION": COMPILE_ACTION,
    "FIXTURE": FIXTURE,
    "FeatureExtractionData": FeatureExtractionData,
    "PLATE_STORAGE": PLATE_STORAGE,
    "CULTURE_SOURCE": CULTURE_SOURCE,
    "POWER_MANAGER_TYPE": POWER_MANAGER_TYPE,
    "POWER_MODES": POWER_MODES,
}


def decode_enum(obj: dict) -> Enum:
    encoding = SOMSerializers.ENUM.encoding
    try:
        e = ENUM_CLASSES[obj[encoding]]
    except KeyError:
        msg = f"'{obj.get(encoding)}' is not a recognized enum"
        logging.error(msg)
        raise JSONDecodingError(msg)
    content = obj.get(CONTENT)
    if not isinstance(content, str):
        msg = f"'{content}' is not one of the allowed string values for {type(e).__name__}"  # noqa: E501
        logging.error(msg)
        raise JSONDecodingError(msg)
    try:
        return e[content]
    except KeyError:
        msg = f"'{content}' is not a recognized enum value of {type(e).__name__}"  # noqa: E501
        logging.error(msg)
        raise JSONDecodingError(msg)


def decode_array(obj: dict) -> np.ndarray:
    encoding = SOMSerializers.ARRAY.encoding
    try:
        dtype = np.dtype(obj[encoding])
    except TypeError:
        msg = f"'{obj[encoding]}' is not a recognized array type"
        logging.error(msg)
        raise JSONDecodingError(msg)
    try:
        content = obj[CONTENT]
    except KeyError:
        msg = "Array data missing from serialized object"
        logging.error(msg)
        raise JSONDecodingError(msg)

    try:
        return np.array(content, dtype=dtype)
    except TypeError:
        msg = f"Array could not be created with {dtype}"
        logging.error(msg)
        raise JSONDecodingError(msg)


Creator = Callable[[dict], Any]


@unique
class SOMSerializers(Enum):
    MODEL = ("__MODEL__", decode_model)
    ENUM = ("__ENUM__", decode_enum)
    ARRAY = ("__ARRAY__", decode_array)

    @property
    def encoding(self) -> str:
        return self.value[0]

    @property
    def decoder(self) -> Creator:
        return self.value[1]


class SOMEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        name = type(o).__name__
        if isinstance(o, Model):
            if name not in MODEL_CLASSES:
                msg = f"'{name}' not a recognized serializable model"
                logging.error(msg)
                raise JSONEncodingError(msg)
            return {
                SOMSerializers.MODEL.encoding: name,
                CONTENT: {k: o[k] for k in o.keys()},
            }
        elif isinstance(o, Enum):
            if name not in ENUM_CLASSES:
                msg = f"'{name}' not a recognized serializable enum"
                logging.error(msg)
                raise JSONEncodingError(msg)
            return {
                SOMSerializers.ENUM.encoding: name,
                CONTENT: o.name,
            }
        elif isinstance(o, np.ndarray):
            return {
                SOMSerializers.ARRAY.encoding: o.dtype.name,
                CONTENT: o.tolist()
            }
        return super().default(o)


def dumps(o: Any) -> str:
    return json.dumps(o, cls=SOMEncoder)


def object_hook(obj: dict) -> Union[dict, Enum, Model]:
    for special in SOMSerializers:
        if special.encoding in obj:
            return special.decoder(obj)
    return obj


def loads(s: Union[str, bytes]) -> Any:
    return json.loads(s, object_hook=object_hook)
