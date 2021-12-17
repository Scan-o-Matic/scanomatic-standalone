import json
from enum import Enum, unique
import logging
from typing import Any, Type, Union
from collections.abc import Callable
import numpy as np

from scanomatic.generics.model import Model
from scanomatic.models.factories.analysis_factories import (
    AnalysisModelFactory,
    GridModelFactory,
)
from scanomatic.models.analysis_model import COMPARTMENTS, VALUES, MEASURES
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.models.rpc_job_models import JOB_STATUS, JOB_TYPE


class JSONSerializationError(ValueError):
    pass


class JSONDecodingError(JSONSerializationError):
    pass


class JSONEncodingError(JSONSerializationError):
    pass


CONTENT = "__CONTENT__"


MODEL_CLASSES: dict[str, Callable[..., Model]] = {
    "AnalysisModel": AnalysisModelFactory.create,
    "GridModel": GridModelFactory.create,
    "RPCjobModel": RPC_Job_Model_Factory.create,
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
        msg = f"Serialized model {obj[encoding]} didn't contain a dict as content: {content}"  # noqa: E501
        logging.error(msg)
        raise JSONDecodingError(msg)


ENUM_CLASSES: dict[str, Type[Enum]] = {
    "COMPARTMENTS": COMPARTMENTS,
    "VALUES": VALUES,
    "MEASURES": MEASURES,
    "JOB_TYPE": JOB_TYPE,
    "JOB_STATUS": JOB_STATUS,
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
        msg = f"'{content}' is not one of the allowed string values fro {type(e).__name__}"  # noqa: E501
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
        msg = "Array could not created with {dtype}"
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
