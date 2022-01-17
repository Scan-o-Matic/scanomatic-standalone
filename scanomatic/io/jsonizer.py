import json
from collections.abc import Callable
from enum import Enum, unique
from typing import Any, Optional, TextIO, Type, TypeVar, Union
from pathlib import Path

import numpy as np

from scanomatic.generics.model import Model, assert_models_deeply_equal
from scanomatic.io.logger import get_logger
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


_LOGGER = get_logger("Jsonizer")
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
        _LOGGER.error(msg)
        raise JSONDecodingError(msg)
    try:
        content: dict = obj[CONTENT]
    except KeyError:
        msg = f"Serialized model {obj[encoding]} didn't have any content"
        _LOGGER.error(msg)
        raise JSONDecodingError(msg)

    try:
        return creator(**{
            k: object_hook(v) if isinstance(v, dict) else v
            for k, v in content.items()
        })
    except (TypeError, AttributeError):
        msg = f"Serialized model {obj[encoding]} couldn't parse content: {content}"  # noqa: E501
        _LOGGER.exception(msg)
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
        _LOGGER.error(msg)
        raise JSONDecodingError(msg)
    content = obj.get(CONTENT)
    if not isinstance(content, str):
        msg = f"'{content}' is not one of the allowed string values for {type(e).__name__}"  # noqa: E501
        _LOGGER.error(msg)
        raise JSONDecodingError(msg)
    try:
        return e[content]
    except KeyError:
        msg = f"'{content}' is not a recognized enum value of {type(e).__name__}"  # noqa: E501
        _LOGGER.error(msg)
        raise JSONDecodingError(msg)


def decode_array(obj: dict) -> np.ndarray:
    encoding = SOMSerializers.ARRAY.encoding
    try:
        dtype = np.dtype(obj[encoding])
    except TypeError:
        msg = f"'{obj[encoding]}' is not a recognized array type"
        _LOGGER.error(msg)
        raise JSONDecodingError(msg)
    try:
        content = obj[CONTENT]
    except KeyError:
        msg = "Array data missing from serialized object"
        _LOGGER.error(msg)
        raise JSONDecodingError(msg)

    try:
        return np.array(content, dtype=dtype)
    except TypeError:
        msg = f"Array could not be created with {dtype}"
        _LOGGER.error(msg)
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
                _LOGGER.error(msg)
                raise JSONEncodingError(msg)
            return {
                SOMSerializers.MODEL.encoding: name,
                CONTENT: {k: o[k] for k in o.keys()},
            }
        elif isinstance(o, Enum):
            if name not in ENUM_CLASSES:
                msg = f"'{name}' not a recognized serializable enum"
                _LOGGER.error(msg)
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


T = TypeVar('T')


def copy(o: T) -> T:
    return loads(dumps(o))


def load(path: Union[str, Path]) -> Any:
    if isinstance(path, str):
        path = Path(path)
    try:
        return loads(path.read_text())
    except IOError:
        _LOGGER.warning(
            f"Attempted to load model from '{path}', but failed",
        )
        return None


def load_first(path: Union[str, Path]) -> Any:
    content = load(path)
    if isinstance(content, list):
        if len(content) > 0:
            return content[0]
        return None
    return content


def _merge(model: Model, update: Model) -> bool:
    for key in model.keys():
        item = model[key]
        if type(item) == type(update):
            model[key] = update
            return True
        elif isinstance(item, Model):
            if _merge(item, update):
                return True
    return False


def merge_into(
    model: Optional[Union[Model, list[Model]]],
    update: Union[list[Model], Model],
) -> Union[list[Model], Model]:
    """Merges update with or into the model.

    There's currently a limitation that when the update
    is a list, it simply replaces model without checking
    if there's a reasonable type match. The feature is
    needed to cover all type cases, but should not be
    in use in the code.
    """
    if isinstance(update, list):
        _LOGGER.warning(
            f"Mergining {update} into {model} not implemented."
            " Will simply replace."
        )
        return update
    elif isinstance(model, list):
        ret = []
        merged = False
        for m in model:
            if merged:
                ret.append(m)
            elif type(m) == type(update):
                ret.append(update)
                merged = True
            else:
                merged = _merge(m, update)
                ret.append(m)
        return ret
    elif model is None or type(model) == type(update):
        return update
    elif not _merge(model, update):
        _LOGGER.warning(
            f"Attempted to update {model} with {update}, but found no matching part of the model",  # noqa: E501
        )
    return model


def dump(
    model: Union[Model, list[Model]],
    path: Union[str, Path],
    overwrite: bool = False,
) -> bool:
    if overwrite:
        model = merge_into(load(path), model)
    try:
        with open(path, 'w') as fh:
            fh.write(dumps(model))
    except IOError:
        _LOGGER.exception(f'Could not save {model} to: {path}')
        return False
    return True


def dump_to_stream(
    model: Model,
    stream: TextIO,
    as_if_appending: bool = False,
):
    if as_if_appending:
        stream.seek(0)
        contents = stream.read().strip()
        if contents:
            previous = loads(contents)
        else:
            previous = []
        if not isinstance(previous, list):
            previous = [previous]
        previous.append(model)
        stream.seek(0)
        stream.write(dumps(previous))
    else:
        stream.write(dumps(model))


def _models_equal(a: Any, b: Model) -> bool:
    try:
        assert_models_deeply_equal(a, b)
        return True
    except (ValueError, AssertionError):
        return False


def _purge(original: Any, model: Any) -> Any:
    if isinstance(original, list):
        return [
            _purge(item, model) for item in original
            if not _models_equal(item, model)
        ]
    elif isinstance(original, tuple):
        return tuple(
            _purge(item, model) for item in original
            if not _models_equal(item, model)
        )
    elif isinstance(original, Model):
        if _models_equal(original, model):
            return None
        elif type(original) != type(model):
            for key in original.keys():
                original[key] = _purge(original[key], model)
    return original


def purge(model: Model, path: Union[str, Path]) -> bool:
    try:
        original = load(path)
    except IOError:
        return False

    updated = _purge(original, model)
    if _models_equal(updated, original):
        return False
    else:
        with open(path, 'w') as fh:
            fh.write(dumps(updated))
        return True
