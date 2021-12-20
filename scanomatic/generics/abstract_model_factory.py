import copy
import logging
import os
import pickle
import types
import warnings
from collections import defaultdict
from collections.abc import Callable
from configparser import ConfigParser, NoSectionError
from enum import Enum
from logging import Logger
from numbers import Real
from types import GeneratorType
from typing import Any, Generator, Optional, Type, Union, cast
from collections.abc import Sequence

import scanomatic.generics.decorators as decorators
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


def _toggleTuple(structure, obj, locked):
    is_next_to_leaf = len(structure) == 2
    if obj is None or obj is False and structure[0] is not bool:
        return None
    elif structure[0] is tuple:

        if not locked:
            obj = list(obj)
        if not is_next_to_leaf:
            for idx, item in enumerate(obj):
                obj[idx] = _toggleTuple(structure[1:], item, locked)
        if locked:
            obj = tuple(obj)
    elif not is_next_to_leaf:
        try:
            iterator = (
                iter(obj.items()) if isinstance(obj, dict) else enumerate(obj)
            )
            for pos, item in iterator:
                obj[pos] = _toggleTuple(structure[1:], item, locked)

        except TypeError:
            pass
    return obj


class AbstractModelFactory:
    MODEL = Model

    _LOGGER = None
    _SUB_FACTORIES: dict[Type[Model], Type["AbstractModelFactory"]] = {}
    STORE_SECTION_HEAD: Union[str, tuple[str]] = ""
    STORE_SECTION_SERIALIZERS: dict[str, Any] = {}

    def __new__(cls, *args):
        raise Exception("This class is static, can't be instantiated")

    @classmethod
    def get_logger(cls) -> Logger:
        if cls._LOGGER is None:
            cls._LOGGER = Logger(cls.__name__)

        return cls._LOGGER

    @classmethod
    def get_serializer(cls) -> "Serializer":
        return Serializer(cls)

    @classmethod
    def get_default_model(cls) -> Model:
        return cls.MODEL()

    @classmethod
    def get_sub_factory(cls, model: Model) -> Type["AbstractModelFactory"]:
        model_type = type(model)
        if model_type not in cls._SUB_FACTORIES:
            cls.get_logger().warning(
                f"Unknown subfactory for model-type {model_type}",
            )
            return AbstractModelFactory
        return cls._SUB_FACTORIES[model_type]

    @classmethod
    def _verify_correct_model(cls, model) -> bool:
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
    def drop_keys(cls, settings, valid_keys) -> None:
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
                settings[key] = _toggleTuple(
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

                settings[key] = _toggleTuple(
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
    def update(cls, model, **settings) -> None:
        for parameter, value in list(settings.items()):
            if parameter in model:
                setattr(model, parameter, value)

    @classmethod
    def copy(cls, model):
        if cls._verify_correct_model(model):
            serializer = cls.get_serializer()
            return serializer.load_serialized_object(
                copy.deepcopy(serializer.serialize(model))
            )[0]

    @classmethod
    def copy_iterable_of_model(cls, models):
        gen = (cls.copy(model) for model in models)
        if isinstance(models, GeneratorType):
            return gen
        else:
            return type(models)(gen)

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
                model_as_dict[k] = _toggleTuple(dtype, model_as_dict[k], False)
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
                model_as_dict[k] = _toggleTuple(dtype, model_as_dict[k], True)

        return model_as_dict

    @classmethod
    def validate(cls, model) -> bool:
        if cls._verify_correct_model(model):
            return all(v is True for v in cls._get_validation_results(model))

        return False

    @classmethod
    def get_invalid(cls, model):
        return (
            v for v in set(cls._get_validation_results(model))
            if v is not True
        )

    @classmethod
    def get_invalid_names(cls, model):
        return (v.name for v in cls.get_invalid(model))

    @classmethod
    def get_invalid_as_text(cls, model):
        return ", ".join([
            "{0}: '{1}'".format(key, model[key])
            for key in cls.get_invalid_names(model)
        ])

    @classmethod
    def _get_validation_results(cls, model):
        return (
            getattr(cls, attr)(model)
            for attr in dir(cls) if attr.startswith("_validate")
        )

    @classmethod
    def set_invalid_to_default(cls, model) -> None:
        if cls._verify_correct_model(model):
            cls.set_default(model, fields=tuple(cls.get_invalid(model)))

    @classmethod
    def set_default(cls, model, fields=None) -> None:
        if cls._verify_correct_model(model):
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
    def clamp(cls, model) -> None:
        pass

    @classmethod
    def _clamp(cls, model, min_model, max_model) -> None:
        if (
            cls._verify_correct_model(model)
            and cls._verify_correct_model(min_model)
            and cls._verify_correct_model(max_model)
        ):
            for attr, val in model:
                min_val = getattr(min_model, attr)
                max_val = getattr(max_model, attr)

                if min_val is not None and val < min_val:
                    setattr(model, attr, min_val)
                elif max_val is not None and val > max_val:
                    setattr(model, attr, max_val)

    @classmethod
    def _correct_type_and_in_bounds(
        cls,
        model,
        attr,
        dtype,
        min_model_caller,
        max_model_caller,
    ):
        if not isinstance(getattr(model, attr), dtype):
            return getattr(model.FIELD_TYPES, attr)

        elif not AbstractModelFactory._in_bounds(
            model,
            min_model_caller(model, factory=cls),
            max_model_caller(model, factory=cls),
            attr,
        ):
            return getattr(model.FIELD_TYPES, attr)

        else:
            return True

    @classmethod
    def _is_valid_submodel(cls, model, key) -> bool:
        sub_model = getattr(model, key)
        sub_model_type = type(sub_model)
        if (
            isinstance(sub_model, Model)
            and sub_model_type in cls._SUB_FACTORIES
        ):
            return cls._SUB_FACTORIES[sub_model_type].validate(sub_model)
        return False

    @staticmethod
    def _in_bounds(model, lower_bounds, upper_bounds, attr) -> bool:
        val = getattr(model, attr)
        min_val = getattr(lower_bounds, attr)
        max_val = getattr(upper_bounds, attr)

        if min_val is not None and val < min_val:
            return False
        elif max_val is not None and val > max_val:
            return False
        else:
            return True

    @staticmethod
    def _is_pinning_formats(pinning_formats) -> bool:
        try:
            return all(
                pinning_format is None
                or pinning_format is False
                or _is_pinning_format(pinning_format)
                for pinning_format in pinning_formats
            )
        except Exception:
            pass
        return False

    @staticmethod
    def _is_file(path) -> bool:
        return isinstance(path, str) and os.path.isfile(path)

    @staticmethod
    def _is_tuple_or_list(obj) -> bool:
        return isinstance(obj, tuple) or isinstance(obj, list)

    @staticmethod
    def _is_enum_value(obj, enum) -> bool:
        if obj in enum:
            return True

        try:
            enum(obj)
        except ValueError:
            pass
        else:
            return True

        try:
            enum[obj]
        except KeyError:
            return False
        else:
            return True

    @staticmethod
    def _is_real_number(obj) -> bool:
        return isinstance(obj, Real)


def _is_pinning_format(pinning_format) -> bool:
    try:
        return all(
            isinstance(val, int)
            and val > 0
            for val in pinning_format
        ) and len(pinning_format) == 2
    except Exception:
        pass

    return False


class _SectionsLink:
    _CONFIGS: defaultdict[Any, set] = defaultdict(set)
    _LINKS: dict[Model, "_SectionsLink"] = {}

    def __init__(self, subfactory: AbstractModelFactory, submodel: Model):
        self._subfactory = subfactory
        self._section_name = subfactory.get_serializer().get_section_name(
            submodel,
        )
        self._locked_name = False
        _SectionsLink._LINKS[submodel] = self

    @staticmethod
    def get_link(model: Model) -> "_SectionsLink":
        return _SectionsLink._LINKS[model]

    @staticmethod
    def clear_links(config_parser) -> None:
        for link in _SectionsLink._CONFIGS[config_parser.id]:
            for m, l in list(_SectionsLink._LINKS.items()):
                if link is l:
                    del _SectionsLink._LINKS[m]
                    break
        del _SectionsLink._CONFIGS[config_parser.id]

    @staticmethod
    def set_link(subfactory, submodel, config_parser: "LinkerConfigParser"):
        link = _SectionsLink(subfactory, submodel)
        link.config_parser = config_parser
        return link

    @staticmethod
    def has_link(model) -> bool:
        return model in _SectionsLink._LINKS

    @property
    def config_parser(self) -> Optional[ConfigParser]:
        try:
            return next(
                (
                    k for k, v in list(_SectionsLink._CONFIGS.items())
                    if self in v
                )
            )
        except StopIteration:
            return None

    @config_parser.setter
    def config_parser(self, value: "LinkerConfigParser"):
        if not isinstance(value, LinkerConfigParser):
            raise ValueError("not a LinkerConfigParser")

        self._get_section(value)
        _SectionsLink._CONFIGS[value.id].add(self)

    @property
    def section(self) -> str:
        if self._locked_name:
            return self._section_name

        parser = self.config_parser
        if parser is None:
            raise AttributeError("config_parser not set")

        return self._get_section(parser)

    def _get_section(self, parser):
        if self._locked_name:
            return self._section_name

        self._locked_name = True
        self._section_name = _SectionsLink.get_next_free_section(
            parser,
            self._section_name,
        )

        return self._section_name

    @staticmethod
    def get_next_free_section(
        parser: "LinkerConfigParser",
        section_name: str,
    ):
        section = "{0}{1}"
        enumerator: Optional[int] = None
        my_section = section_name
        sections = set(
            s.section if hasattr(s, 'section') else s
            for s in _SectionsLink._CONFIGS[parser.id]
        )
        sections = sections.union(parser.sections())
        while my_section in sections:
            my_section = section.format(
                section_name,
                " #{0}".format(enumerator) if enumerator is not None else ''
            )
            if my_section in sections:
                if enumerator is not None:
                    enumerator += 1
                else:
                    enumerator = 2

        return my_section

    @staticmethod
    def add_section_for_non_link(parser: "LinkerConfigParser", section: str):
        _SectionsLink._CONFIGS[parser.id].add(section)

    def retrieve_items(self, config_parser):
        return config_parser.items(self._section_name)

    def retrieve_model(self, config_parser):
        return self._subfactory.get_serializer().unserialize_section(
            config_parser,
            self._section_name,
        )

    def __getstate__(self):
        return {'_section_name': self.section, '_subfactory': self._subfactory}

    def __setstate__(self, state):
        self._section_name = state['_section_name']
        self._subfactory = state['_subfactory']
        self._locked_name = True


class LinkerConfigParser(ConfigParser):
    def __init__(self, id, clear_links=True, *args, **kwargs):
        ConfigParser.__init__(self, *args, **kwargs)
        self.id = id
        self._clear_links = clear_links

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._clear_links:
            _SectionsLink.clear_links(self)

    def _read(self, fp, fpname):
        val = ConfigParser._read(self, fp, fpname)
        self._nonzero = True
        return val

    def __bool__(self) -> bool:
        return (
            self._nonzero
            if hasattr(self, '_nonzero')
            else len(self.sections()) > 0
        )


class MockConfigParser:
    def __init__(self, serialized_object):
        self._so = serialized_object

    def sections(self):
        return tuple(name for name, _ in self._so)

    def options(self, section):
        return next((
            list(contents.keys()) for name, contents in self._so
            if section == name
        ))

    def items(self, section):
        return next((
            list(contents.items()) for name, contents in self._so
            if section == name
        ))

    def get(self, section, item):
        return next((
            contents[item] for name, contents in self._so
            if section == name
        ))


@decorators.memoize
class Serializer:
    def __init__(self, factory: Type[AbstractModelFactory]):
        self._factory = factory
        self._logger = Logger(factory.__name__)

    def dump(self, model, path, overwrite=False) -> bool:
        if self._has_section_head_and_is_valid(model):
            if overwrite:
                conf = LinkerConfigParser(id=path, allow_no_value=True)
                section = self.get_section_name(model)
                self.serialize_into_conf(model, conf, section)
                return SerializationHelper.save_config(conf, path)

            else:
                with SerializationHelper.get_config(path) as conf:
                    self._purge_tree(conf, model)
                    section = self.get_section_name(model)
                    self.serialize_into_conf(model, conf, section)
                    return SerializationHelper.save_config(conf, path)

        return False

    def dump_to_filehandle(
        self,
        model,
        filehandle,
        as_if_appending: bool = False,
    ) -> bool:
        if self._has_section_head_and_is_valid(model):
            section = self.get_section_name(model)
            with LinkerConfigParser(
                id=id(filehandle),
                clear_links=False,
                allow_no_value=True,
            ) as conf:
                if 'r' in filehandle.mode:
                    fh_pos = filehandle.tell()
                    filehandle.seek(0)
                    conf.read_file(filehandle)
                    if as_if_appending:
                        filehandle.seek(0, 2)
                    else:
                        filehandle.seek(fh_pos)

                section = _SectionsLink.get_next_free_section(conf, section)
                _SectionsLink.add_section_for_non_link(conf, section)
                self.serialize_into_conf(model, conf, section)

                if 'r' in filehandle.mode:
                    filehandle.seek(0)
                    filehandle.truncate()

                conf.write(filehandle)
            return True
        return False

    def _has_section_head(self, model) -> bool:
        head = self.get_section_name(model)
        return bool(len(head))

    def _has_section_head_and_is_valid(self, model) -> bool:
        factory = self._factory
        valid = factory.validate(model)

        if self._has_section_head(model) and valid:
            return True

        if not self._has_section_head(model):
            self._logger.warning("Factory does not know head for sections")

        if not valid:
            self._logger.warning(
                f"Model {model} does not have valid data",
            )
            for invalid in factory.get_invalid_names(model):
                self._logger.error(
                    "Faulty value in model {0} for {1} as {2}".format(
                        model,
                        invalid,
                        model[invalid],
                    ),
                )
        return False

    def purge(self, model, path) -> bool:
        with SerializationHelper.get_config(path) as conf:
            if conf:
                self._purge_tree(conf, model)
                return SerializationHelper.save_config(conf, path)

        return False

    def _purge_tree(self, conf, model):
        def add_if_points_to_subsection():
            obj = SerializationHelper.unserialize(
                conf.get(section, key),
                object,
            )

            try:
                sections.append(obj.section)
            except AttributeError:
                try:
                    # TODO: Should really use datastructure
                    for item in obj:
                        sections.append(
                            SerializationHelper.unserialize(
                                item,
                                object,
                            ).section
                        )
                except (AttributeError, TypeError):
                    pass

        sections = [self.get_section_name(model)]
        index = 0
        while index < len(sections):
            section = sections[index]
            if not conf.has_section(section):
                index += 1
                continue

            for key in conf.options(section):
                add_if_points_to_subsection()

            conf.remove_section(section)

    @staticmethod
    def purge_all(path):
        with SerializationHelper.get_config(None) as conf:
            return SerializationHelper.save_config(conf, path)

    def load(self, path) -> tuple:
        with SerializationHelper.get_config(path) as conf:
            if conf:
                return tuple(self._unserialize(conf))

        return tuple()

    def load_first(self, path):
        with SerializationHelper.get_config(path) as conf:
            if conf:
                try:
                    return next(self._unserialize(conf))
                except StopIteration:
                    self._logger.error(f"No model in file '{path}'")
            else:
                self._logger.error("No file named '{0}'".format(path))
        return None

    def _unserialize(self, conf):
        for section in conf.sections():
            try:
                if self._factory.all_keys_valid(conf.options(section)):
                    yield self.unserialize_section(conf, section)

            except UnserializationError:
                self._logger.error("Parsing section '{0}': {1}".format(
                    section,
                    conf.options(section),
                ))
                raise

    def unserialize_section(self, conf, section):
        factory = self._factory
        try:
            if not factory.all_keys_valid(conf.options(section)):
                self._logger.warning(
                    "{1} Refused section {0} because keys {2}".format(
                        section,
                        factory,
                        conf.options(section),
                    ),
                )
                return None
        except NoSectionError:
            self._logger.warning(
                "Refused section {0} because missing in file, though claimed to be there".format(  # noqa: E501
                    section,
                ),
            )
            return None
        model = {}

        for key, dtype in list(factory.STORE_SECTION_SERIALIZERS.items()):
            if key in conf.options(section):
                try:
                    value = conf.get(section, key)
                except ValueError:
                    self._logger.critical(
                        "Could not parse section {0}, key {1}".format(
                            section,
                            key,
                        ),
                    )
                    value = None

                if isinstance(dtype, tuple):
                    value = SerializationHelper.unserialize_structure(
                        value,
                        dtype,
                        conf,
                    )

                elif isinstance(dtype, types.FunctionType):
                    value = SerializationHelper.unserialize(value, dtype)

                elif (
                    isinstance(dtype, type)
                    and issubclass(dtype, Model)
                    and value is not None
                ):
                    obj = SerializationHelper.unserialize(value, _SectionsLink)
                    if isinstance(obj, _SectionsLink):
                        value = obj.retrieve_model(conf)
                    else:
                        # This handles backward compatibility when models were
                        # pickled
                        value = obj

                else:
                    value = SerializationHelper.unserialize(value, dtype)
                model[key] = value

        return factory.create(**model)

    def load_serialized_object(self, serialized_object):
        return tuple(self._unserialize(MockConfigParser(serialized_object)))

    def serialize(self, model):
        if not self._has_section_head(model):
            raise ValueError("Need a section head for serialization")

        with LinkerConfigParser(id=id(model), allow_no_value=True) as conf:
            conf = self.serialize_into_conf(
                model,
                conf,
                self.get_section_name(model),
            )
            return tuple(
                (section, {k: v for k, v in conf.items(section)})
                for section in conf.sections()
            )

    def serialize_into_conf(self, model, conf, section):
        if conf.has_section(section):
            conf.remove_section(section)

        conf.add_section(section)

        factory = self._factory
        for key, dtype in factory.STORE_SECTION_SERIALIZERS.items():
            self._serialize_item(model, key, dtype, conf, section, factory)

        return conf

    @staticmethod
    def _serialize_item(model, key, dtype, conf, section, factory):
        obj = copy.deepcopy(model[key])

        if isinstance(dtype, tuple):

            obj = _toggleTuple(dtype, obj, False)
            dtype_leaf = dtype[-1]
            for coord, item in _get_coordinates_and_items_to_validate(
                dtype,
                model[key],
            ):
                if (
                    isinstance(dtype_leaf, type)
                    and issubclass(dtype_leaf, Model)
                ):
                    subfactory = factory.get_sub_factory(item)
                    link = _SectionsLink.set_link(subfactory, item, conf)
                    subfactory.get_serializer().serialize_into_conf(
                        item,
                        conf,
                        link.section,
                    )
                    _update_object_at(
                        obj,
                        coord,
                        SerializationHelper.serialize(link, _SectionsLink),
                    )
                else:
                    _update_object_at(
                        obj,
                        coord,
                        SerializationHelper.serialize(item, dtype_leaf),
                    )

            conf.set(
                section,
                key,
                SerializationHelper.serialize_structure(obj, dtype),
            )

        elif (
            isinstance(dtype, type)
            and issubclass(dtype, Model)
            and obj is not None
        ):
            subfactory = factory.get_sub_factory(obj)

            conf.set(
                section,
                key,
                SerializationHelper.serialize(
                    _SectionsLink.set_link(subfactory, obj, conf),
                    _SectionsLink,
                ),
            )
            subfactory.get_serializer().serialize_into_conf(
                obj,
                conf,
                _SectionsLink.get_link(obj).section,
            )

        else:
            conf.set(section, key, SerializationHelper.serialize(obj, dtype))

    def get_section_name(self, model):

        if isinstance(self._factory.STORE_SECTION_HEAD, str):
            return self._factory.STORE_SECTION_HEAD
        elif isinstance(self._factory.STORE_SECTION_HEAD, list):
            heads = [
                (str(model[head]) if model[head] is not None else '')
                for head in self._factory.STORE_SECTION_HEAD
            ]
            if '' in heads:
                return ''
            else:
                return ", ".join(heads)
        elif isinstance(self._factory.STORE_SECTION_HEAD, tuple):
            for key in self._factory.STORE_SECTION_HEAD:
                try:
                    if key in model:
                        model = model[key]
                    else:
                        return ''
                except TypeError:
                    return ''

            return str(model) if model is not None else ''
        else:
            return ''


class SerializationHelper:
    def __new__(cls, *args):
        raise Exception("This class is static, can't be instantiated")

    @staticmethod
    def serialize_structure(obj, structure):
        if obj is None:
            return None

        elif len(structure) == 1:
            return SerializationHelper.serialize(
                obj,
                structure[0] if (
                    not isinstance(structure[0], type)
                    or not issubclass(structure[0], Model)
                ) else _SectionsLink)
        else:
            return SerializationHelper.serialize(
                (
                    SerializationHelper.serialize_structure(
                        item,
                        structure[1:],
                    )
                    for item in obj
                ),
                structure[0]
            )

    @staticmethod
    def serialize(obj, dtype) -> Optional[str]:
        if obj is None:
            return None

        elif isinstance(obj, Enum):
            return obj.name

        elif dtype is _SectionsLink:
            return pickle.dumps(obj).decode('iso-8859-1')

        elif dtype in (int, float, str, bool):
            return str(obj)

        elif isinstance(dtype, types.FunctionType):
            return pickle.dumps(dtype(serialize=obj)).decode('iso-8859-1')

        else:
            if not isinstance(obj, dtype):
                obj = dtype(obj)
            return pickle.dumps(obj).decode('iso-8859-1')

    @staticmethod
    def isvalidtype(o, dtype) -> bool:
        return (
            isinstance(o, dtype)
            or not any({type(o), dtype}.difference((list, tuple)))
        )

    @staticmethod
    def unserialize_structure(obj, structure, conf):
        if obj is None or obj is False and structure[0] is not bool:
            return None
        elif len(structure) == 1:
            if (
                isinstance(structure[0], type)
                and issubclass(structure[0], Model)
            ):
                while not isinstance(obj, _SectionsLink) and obj is not None:
                    obj = SerializationHelper.unserialize(obj, _SectionsLink)

                if obj:
                    return obj.retrieve_model(conf)
                return obj
            else:
                return SerializationHelper.unserialize(obj, structure[0])
        else:
            outer_obj: Any = -1
            while (
                outer_obj is not None
                and not SerializationHelper.isvalidtype(
                    outer_obj,
                    structure[0],
                )
            ):
                outer_obj = SerializationHelper.unserialize(obj, structure[0])
            if outer_obj is None:
                return None
            return SerializationHelper.unserialize(
                (
                    SerializationHelper.unserialize_structure(
                        item,
                        structure[1:],
                        conf,
                    )
                    for item in outer_obj
                ),
                structure[0],
            )

    @staticmethod
    def unserialize(serialized_obj: Union[str, bool, Generator], dtype):
        if (
            serialized_obj is None
            or serialized_obj is False
            and dtype is not bool
        ):
            return None

        elif isinstance(dtype, type) and issubclass(dtype, Enum):
            try:
                return dtype[cast(str, serialized_obj)]
            except (KeyError, SyntaxError):
                logging.exception(
                    f"Could not parse {serialized_obj} with type {dtype}",
                )
                return None

        elif dtype is bool:
            try:
                return bool(eval(cast(str, serialized_obj)))
            except (NameError, AttributeError, SyntaxError):
                logging.exception(
                    f"Could not parse {serialized_obj} with type {dtype}",
                )
                return False

        elif dtype in (int, float, str):
            try:
                return cast(Callable, dtype)(serialized_obj)
            except (TypeError, ValueError):
                try:
                    return cast(Callable, dtype)(
                        eval(cast(str, serialized_obj)),
                    )
                except (
                    SyntaxError,
                    NameError,
                    AttributeError,
                    TypeError,
                    ValueError,
                ):
                    logging.exception(
                        f"Could not parse {serialized_obj} with type {dtype}",
                    )
                    return None

        elif isinstance(dtype, types.FunctionType):
            try:
                return dtype(enforce=pickle.loads(
                    cast(str, serialized_obj).encode('iso-8859-1'),
                ))
            except (pickle.PickleError, EOFError):
                logging.exception(
                    f"Could not parse {serialized_obj} with type {dtype}",
                )
                return None

        elif isinstance(serialized_obj, types.GeneratorType):
            return cast(Callable, dtype)(serialized_obj)

        elif (
            isinstance(serialized_obj, _SectionsLink)
            or isinstance(serialized_obj, dtype)
        ):
            return serialized_obj

        elif SerializationHelper.isvalidtype(serialized_obj, dtype):
            return serialized_obj

        else:
            if (dtype is tuple and serialized_obj == ''):
                return None
            if (dtype is list and serialized_obj == ''):
                return None

            try:
                return pickle.loads(
                    cast(str, serialized_obj).encode('iso-8859-1'),
                )
            except (pickle.PickleError, TypeError, EOFError):
                logging.exception(
                    f"Could not parse '{serialized_obj}' with type {dtype}",
                )
                return None

    @staticmethod
    def get_config(path) -> LinkerConfigParser:
        conf = LinkerConfigParser(id=path, allow_no_value=True)

        if isinstance(path, str):
            try:
                with open(path, 'r') as fh:
                    conf.read_file(fh)
            except IOError:
                pass

        return conf

    @staticmethod
    def save_config(conf, path) -> bool:
        try:
            with open(path, 'w') as fh:
                conf.write(fh)
        except IOError:
            return False
        return True


def rename_setting(settings, old_name, new_name):
    if old_name in settings:
        if new_name not in settings:
            settings[new_name] = settings[old_name]
        del settings[old_name]


def split_and_replace(
    settings,
    key,
    new_key_pattern: str,
    new_key_index_names
):
    if key in settings:
        for index, new_key_index_name in enumerate(new_key_index_names):
            try:
                settings[
                    new_key_pattern.format(new_key_index_name)
                ] = settings[key][index]
            except (IndexError, TypeError):
                pass

        del settings[key]
