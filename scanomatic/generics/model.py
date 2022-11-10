from collections.abc import Mapping, Generator
from itertools import chain
from typing import Any


class Model(Mapping):
    _INITIALIZED = "_initialized"
    _RESERVED_WORDS = ('keys', 'values')
    _STR_PATTERN = "<{0} {1}={2}>"

    def __init__(self):
        content = [attribute for attribute in self]
        if content:
            fields, _ = zip(*content)

            if any(field in self._RESERVED_WORDS for field in fields):
                raise AttributeError(
                    "Attributes {0} are reserved and can't be defined".format(
                        self._RESERVED_WORDS,
                    ),
                )

            if any(k for k in fields if k.startswith("_")):
                raise AttributeError("Model attributes may not be hidden")

        self._set_initialized()

    def __iter__(self) -> Generator[tuple[str, Any], None, None]:
        for attr, value in self.__dict__.items():
            if not attr.startswith("_"):
                yield attr, value

    def __setattr__(self, attr, value) -> None:
        if attr == Model._INITIALIZED:
            raise AttributeError(
                "Can't directly set model to initialized state",
            )
        elif self._is_initialized() and not hasattr(self, attr):
            raise AttributeError(
                "Can't add new attributes after initialization",
            )
        elif attr in self._RESERVED_WORDS:
            raise AttributeError("Can't set reserved words")
        else:
            self.__dict__[attr] = value

    def __contains__(self, item) -> bool:
        return item in self.__dict__

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value) -> None:

        setattr(self, key, value)

    def __eq__(self, other) -> bool:
        try:
            _ = (e for e in other)
        except TypeError:
            return False

        for key in self.keys():
            if key not in other or not (self[key] == other[key]):
                return False
        return True

    def __str__(self) -> str:

        classname = str(type(self)).split(".")[-1].rstrip("'>")
        value = None
        key = None

        for key in ("name", "id", "path"):
            if key in self and self[key]:
                value = self[key]
                break

        if value is None:

            for key in [
                key for key in self.keys()
                if key.endswith("id")
                or key.endswith("name")
            ]:
                if self[key]:
                    value = self[key]
                    break

        if value is None:
            key = None
            for key in self.keys():
                if self[key]:
                    value = self[key]
                    break

        return Model._STR_PATTERN.format(classname, key, value)

    def __len__(self) -> int:
        return len(tuple(self.keys()))

    def _set_initialized(self) -> None:
        self.__dict__[Model._INITIALIZED] = True

    def _is_initialized(self) -> bool:

        if Model._INITIALIZED not in self.__dict__:
            self.__dict__[Model._INITIALIZED] = False

        return self.__dict__[Model._INITIALIZED]

    def keys(self):
        return (
            k for k in list(self.__dict__.keys())
            if not k.startswith("_") and k != "keys"
        )


class UnionModel(Model):
    _MODELS_KEY = "_models"

    def __init__(self, *models):
        """UnionModel unifies several models referencing orignial models data

        **NOTE:** Model order takes presidence when getting and setting
        attributes"""
        self._models = models
        super(UnionModel, self).__init__()

    def __setattr__(self, attr, value):

        if attr == Model._INITIALIZED:
            raise AttributeError(
                "Can't directly set model to initialized state",
            )
        elif self._is_initialized() and not hasattr(self, attr):
            raise AttributeError(
                "Can't add new attributes after initialization",
            )
        elif not self._is_initialized() and attr == UnionModel._MODELS_KEY:
            self.__dict__[UnionModel._MODELS_KEY] = value
        elif attr in self._RESERVED_WORDS:
            raise AttributeError("Can't set reserved words")
        else:
            for model in self.__dict__[UnionModel._MODELS_KEY]:
                if attr in model:
                    setattr(model, attr, value)
                    return

    def __getattr__(self, item):
        for model in self.__dict__[UnionModel._MODELS_KEY]:
            if item in model:
                return getattr(model, item)

        raise AttributeError("Unknown attribute {0} in {1}".format(item, self))

    def __str__(self):
        classname = str(type(self)).split(".")[-1].rstrip("'>")
        key = "models"
        value = list(map(str, self.__dict__[UnionModel._MODELS_KEY]))
        return Model._STR_PATTERN.format(classname, key, value)

    def __contains__(self, item):
        for model in self.__dict__[UnionModel._MODELS_KEY]:
            if item in model:
                return True
        return False

    def __dir__(self):
        return list(self.keys())

    def keys(self):

        return chain(
            *(model.keys() for model in self.__dict__[UnionModel._MODELS_KEY])
        )


def assert_models_deeply_equal(a: Any, b: Any) -> None:
    if a is b:
        return
    elif type(a) != type(b):
        raise ValueError(f'Model not equal types: {type(a)} != {type(b)}')

    assert isinstance(a, Model) and isinstance(b, Model), (
        f'Neither side is a model: {type(a).__name__} & {type(b).__name__}'
    )

    for key in a.keys():
        a_val = a[key]
        b_val = b[key]
        if isinstance(a_val, Model) or isinstance(b_val, Model):
            assert_models_deeply_equal(a_val, b_val)
        if a_val != b_val:
            raise ValueError(f"Model not equal on '{key}': {a_val} != {b_val}")
