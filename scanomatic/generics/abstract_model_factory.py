import copy
import logging
import types
import warnings
from collections.abc import Callable
from logging import Logger
from typing import Any, Optional, Type, Union, cast
from collections.abc import Sequence

from scanomatic.generics.model import Model


class UnserializationError(ValueError):
    pass


def float_list_serializer(enforce=None, serialize=None):
    if enforce is not None:
        if isinstance(enforce, str):
            try:
                return [float(m.strip()) for m in enforce.split(",")]
            except ValueError:
                raise UnserializationError(
                    "Could not parse '{0}' as float list".format(enforce),
                )
        elif isinstance(enforce, list):
            return [
                float(e) for i, e in enumerate(enforce)
                if e or i < len(enforce) - 1
            ]
        else:
            return list(enforce)

    elif serialize is not None:

        if isinstance(serialize, str):
            return serialize
        else:
            try:
                return ", ".join((str(e) for e in serialize))
            except TypeError:
                return str(serialize)

    else:
        return None


def email_serializer(enforce=None, serialize=None) -> str:
    if enforce is not None:
        if isinstance(enforce, str):
            return enforce
        elif isinstance(enforce, Sequence):
            return ', '.join(enforce)

    elif serialize is not None:
        if isinstance(serialize, str):
            return serialize
        elif isinstance(serialize, list):
            return ", ".join(serialize)

    return ''


def _get_coordinates_and_items_to_validate(structure, obj):
    if obj is None or obj is False and structure[0] is not bool:
        return

    is_next_to_leaf = len(structure) == 2
    iterator = iter(obj.items()) if isinstance(obj, dict) else enumerate(obj)

    try:
        for pos, item in iterator:
            if (
                is_next_to_leaf
                and not (
                    item is None or item is False and structure[1] is not bool
                )
            ):
                yield (pos, ), item
            elif not is_next_to_leaf:
                for coord, validation_item in (
                    _get_coordinates_and_items_to_validate(
                        structure[1:],
                        item
                    )
                ):
                    yield (pos,) + coord, validation_item
    except TypeError:
        pass


def _update_object_at(obj, coordinate, value) -> None:

    if obj is None or obj is False:
        warnings.warn(
            "Can't update None using coordinate {0} and value '{1}'".format(
                coordinate,
                value,
            )
        )
    if len(coordinate) == 1:
        obj[coordinate[0]] = value
    else:
        _update_object_at(obj[coordinate[0]], coordinate[1:], value)


def _toggle_tuple(structure, obj, locked):
    is_next_to_leaf = len(structure) == 2
    if obj is None or obj is False and structure[0] is not bool:
        return None
    elif structure[0] is tuple:

        if not locked:
            obj = list(obj)
        if not is_next_to_leaf:
            for idx, item in enumerate(obj):
                obj[idx] = _toggle_tuple(structure[1:], item, locked)
        if locked:
            obj = tuple(obj)
    elif not is_next_to_leaf:
        try:
            iterator = (
                iter(obj.items()) if isinstance(obj, dict) else enumerate(obj)
            )
            for pos, item in iterator:
                obj[pos] = _toggle_tuple(structure[1:], item, locked)

        except TypeError:
            pass
    return obj


SubFactoryDict = dict[Type[Model], Type["AbstractModelFactory"]]


class AbstractModelFactory:
    _LOGGER = None
    MODEL = Model
    _SUB_FACTORIES: SubFactoryDict = {}
    STORE_SECTION_SERIALIZERS: dict[str, Any] = {}

    def __new__(cls, *args):
        raise Exception("This class is static, can't be instantiated")

    @classmethod
    def get_logger(cls) -> Logger:
        if cls._LOGGER is None:
            cls._LOGGER = Logger(cls.__name__)

        return cls._LOGGER

    @classmethod
    def get_default_model(cls) -> Model:
        return cls.MODEL()

    @classmethod
    def verify_correct_model(cls, model) -> bool:
        if not isinstance(model, cls.MODEL):
            raise TypeError(
                f"Wrong model for factory {cls.MODEL} is not a {model}",
            )

        return True

    @classmethod
    def create(cls, **settings) -> Model:
        valid_keys = tuple(cls.get_default_model().keys())

        cls.drop_keys(settings, valid_keys)
        cls.enforce_serializer_type(
            settings,
            set(valid_keys).intersection(cls.STORE_SECTION_SERIALIZERS.keys()),
        )
        return cls.MODEL(**settings)

    @classmethod
    def all_keys_valid(cls, keys) -> bool:
        expected = set(cls.get_default_model().keys())
        return (
            expected.issuperset(keys)
            and len(expected.intersection(keys)) > 0
        )

    @classmethod
    def drop_keys(
        cls,
        settings: dict[str, Any],
        valid_keys: Sequence[str],
    ) -> None:
        keys = tuple(settings.keys())
        for key in keys:
            if key not in valid_keys:
                cls.get_logger().warning(
                    "Removing key \"{0}\" from {1} creation, since not among {2}".format(  # noqa: E501
                       key,
                       cls.MODEL,
                       tuple(valid_keys),
                    ),
                )
                del settings[key]

    @classmethod
    def enforce_serializer_type(cls, settings, keys=tuple()):
        """Especially good for enums and Models

        :param settings:
        :param keys:
        :return:
        """

        def _enforce_model(factory, obj):
            factories = tuple(
                f for f in list(cls._SUB_FACTORIES.values()) if f != factory
            )
            index = 0
            while True:
                if factory in list(cls._SUB_FACTORIES.values()):
                    try:
                        return factory.create(**obj)
                    except TypeError as e:
                        cls.get_logger().warning(
                            f"Could not use {factory} on key {obj} to create sub-class",  # noqa: E501
                        )
                        raise e

                if index < len(factories):
                    factory = factories[index]
                    index += 1
                else:
                    break

        def _enforce_other(dtype, obj):
            if obj is None or obj is False and dtype is not bool:
                return None
            elif (
                isinstance(dtype, type)
                and issubclass(dtype, AbstractModelFactory)
            ):
                if isinstance(dtype, dtype.MODEL):
                    return obj
                else:
                    try:
                        return dtype.create(**obj)
                    except AttributeError:
                        cls.get_logger().error(
                            f"Contents mismatch between factory {dtype} and model data '{obj}'",  # noqa: E501
                        )
                        return obj
            try:
                return cast(Callable, dtype)(obj)
            except (AttributeError, ValueError, TypeError):
                try:
                    return cast(Sequence, dtype)[obj]
                except (AttributeError, KeyError, IndexError, TypeError):
                    cls.get_logger().error(
                        "Having problems enforcing '{0}' to be type '{1}' in supplied settings '{2}'.".format(  # noqa: E501
                            obj,
                            dtype,
                            settings,
                        ),
                    )
                    return obj

        for key in keys:
            if (
                key not in settings
                or settings[key] is None
                or key not in cls.STORE_SECTION_SERIALIZERS
            ):
                if key in settings and settings[key] is not None:
                    logging.warning(
                        f"'{key}' ({settings[key]}) not enforced when loaded by {cls.__name__}",  # noqa: E501
                    )
                continue

            if isinstance(cls.STORE_SECTION_SERIALIZERS[key], tuple):

                ref_settings = copy.deepcopy(settings[key])
                settings[key] = _toggle_tuple(
                    cls.STORE_SECTION_SERIALIZERS[key],
                    settings[key],
                    False,
                )
                dtype_leaf = cls.STORE_SECTION_SERIALIZERS[key][-1]
                for coord, item in (
                    _get_coordinates_and_items_to_validate(
                        cls.STORE_SECTION_SERIALIZERS[key],
                        ref_settings
                    )
                ):
                    if (
                        isinstance(dtype_leaf, type)
                        and issubclass(dtype_leaf, Model)
                    ):
                        _update_object_at(
                            settings[key],
                            coord,
                            _enforce_model(
                                cls._SUB_FACTORIES[dtype_leaf],
                                item,
                            )
                        )
                    else:
                        _update_object_at(
                            settings[key],
                            coord,
                            _enforce_other(dtype_leaf, item),
                        )

                settings[key] = _toggle_tuple(
                    cls.STORE_SECTION_SERIALIZERS[key],
                    settings[key],
                    True,
                )

            elif isinstance(
                cls.STORE_SECTION_SERIALIZERS[key],
                types.FunctionType,
            ):
                settings[key] = cls.STORE_SECTION_SERIALIZERS[key](
                    enforce=settings[key],
                )

            elif not isinstance(
                settings[key],
                cls.STORE_SECTION_SERIALIZERS[key],
            ):
                dtype = cls.STORE_SECTION_SERIALIZERS[key]
                if (
                    isinstance(dtype, type)
                    and issubclass(dtype, Model)
                    and isinstance(settings[key], dict)
                ):
                    settings[key] = _enforce_model(
                        cls._SUB_FACTORIES[dtype],
                        settings[key],
                    )
                else:
                    settings[key] = _enforce_other(dtype, settings[key])
            # else it is already correct type

    @classmethod
    def to_dict(cls, model) -> dict:
        model_as_dict = dict(**model)
        for k in model_as_dict.keys():
            if k not in cls.STORE_SECTION_SERIALIZERS:
                del model_as_dict[k]
            elif (
                k in cls.STORE_SECTION_SERIALIZERS
                and isinstance(
                    cls.STORE_SECTION_SERIALIZERS[k],
                    types.FunctionType,
                )
            ):
                model_as_dict[k] = cls.STORE_SECTION_SERIALIZERS[k](
                    serialize=model_as_dict[k],
                )
            elif isinstance(model_as_dict[k], Model):
                if type(model_as_dict[k]) in cls._SUB_FACTORIES:
                    model_as_dict[k] = cls._SUB_FACTORIES[
                        type(model_as_dict[k])
                    ].to_dict(model_as_dict[k])
                else:
                    model_as_dict[k] = AbstractModelFactory.to_dict(
                        model_as_dict[k]
                    )
            elif (
                k in cls.STORE_SECTION_SERIALIZERS
                and isinstance(cls.STORE_SECTION_SERIALIZERS[k], tuple)
            ):
                dtype = cls.STORE_SECTION_SERIALIZERS[k]
                dtype_leaf = dtype[-1]
                model_as_dict[k] = _toggle_tuple(dtype, model_as_dict[k], False)
                if (
                    isinstance(dtype_leaf, type)
                    and issubclass(dtype_leaf, Model)
                ):
                    for coord, item in _get_coordinates_and_items_to_validate(
                        dtype,
                        model_as_dict[k]
                    ):
                        _update_object_at(
                            model_as_dict[k],
                            coord,
                            cls._SUB_FACTORIES[dtype_leaf].to_dict(item),
                        )
                model_as_dict[k] = _toggle_tuple(dtype, model_as_dict[k], True)

        return model_as_dict

    @classmethod
    def set_default(cls, model, fields=None) -> None:
        if cls.verify_correct_model(model):
            default_model = cls.MODEL()

            for attr, val in default_model:
                if (
                    fields is None
                    or getattr(default_model.FIELD_TYPES, attr) in fields
                ):
                    setattr(model, attr, val)

    @classmethod
    def populate_with_default_submodels(cls, obj: Union[dict, Model]) -> None:
        """Keys missing models/having None will get default instances of that
        field if possible."""

        for key in cls.STORE_SECTION_SERIALIZERS:
            if (
                (key not in obj or obj[key] is None)
                and cls.STORE_SECTION_SERIALIZERS[key] in cls._SUB_FACTORIES
            ):
                obj[key] = cls._SUB_FACTORIES[
                    cls.STORE_SECTION_SERIALIZERS[key]
                ].get_default_model()

    @classmethod
    def contains_model_type(
        cls,
        key: str,
    ) -> tuple[
        bool,
        Optional[Union[SubFactoryDict, tuple[Any]]]
    ]:
        type_def = cls.STORE_SECTION_SERIALIZERS.get(key)
        if type_def is None:
            return False, None
        if type_def is Model:
            return True, cls._SUB_FACTORIES
        elif issubclass(type_def, Model):
            return True, {type_def: cls._SUB_FACTORIES[type_def]}
        elif isinstance(type_def, tuple):
            if Model in type_def:
                return True, tuple(
                    cls._SUB_FACTORIES if td is Model else td
                    for td in type_def
                )
            return (
                any(issubclass(td, Model) for td in type_def),
                tuple(
                    {td: cls._SUB_FACTORIES[td]}
                    if issubclass(td, Model) else td for td in type_def
                )
            )
        return False, None


def rename_setting(
    settings: dict[str, Any],
    old_name: str,
    new_name: str,
) -> None:
    if old_name in settings:
        if new_name not in settings:
            settings[new_name] = settings[old_name]
        del settings[old_name]
