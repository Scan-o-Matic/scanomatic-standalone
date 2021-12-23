from collections.abc import Iterator
from enum import Enum, auto
from typing import Literal, Optional, Type, Union, cast

from scanomatic.generics.model import Model
from scanomatic.models.factories.factory_lookup import get_factory
from scanomatic.models.fields_lookup import get_field_types

from .validation_lookup import get_special_validators

ValidationResults = Iterator[Union[Literal[True], Enum]]


class UnknownFields(Enum):
    UNKNOWN_FIELD = auto()


def _produce_validation_error(fields: Optional[Type[Enum]], field: str) -> Enum:
    if fields is None:
        return UnknownFields.UNKNOWN_FIELD
    if field == "name":
        return fields["_name"]
    return fields[field]


def _get_validation_results(model: Model) -> ValidationResults:
    module = get_special_validators(model)
    factory = get_factory(model)
    fields = get_field_types(model)
    # generate validation results for sub-models
    for k in model.keys():
        if factory is None:
            yield _produce_validation_error(fields, k)
            continue
        should_verify, sub_validation = factory.contains_model_type(k)
        if not should_verify or sub_validation is None:
            yield True
            continue
        item = getattr(model, k)
        item_type = type(item)
        if isinstance(sub_validation, dict):
            if (item_type in sub_validation and validate(item)):
                yield True
            else:
                yield _produce_validation_error(fields, k)
        else:
            if len(sub_validation) == 2:
                outer_type, leaf_type = cast(tuple[Type, Type], sub_validation)
                if not isinstance(item, outer_type):
                    yield _produce_validation_error(fields, k)
                else:
                    if isinstance(leaf_type, dict):
                        for i in item:
                            if i is None:
                                continue
                            i_type = type(i)
                            if (i_type not in leaf_type and validate(i)):
                                yield _produce_validation_error(fields, k)
                                break

    # generate specific validation results
    if module is not None:
        for validator in dir(module):
            if not validator.startswith("validate"):
                continue
            yield getattr(module, validator)(model)


def validate(model: Model) -> bool:
    factory = get_factory(model)
    if factory is None:
        return False
    if factory.verify_correct_model(model):
        return all(v is True for v in _get_validation_results(model))
    return False


def get_invalid(model: Model) -> Iterator[Enum]:
    return (
        v for v in set(_get_validation_results(model)) if v is not True
    )


def get_invalid_names(model: Model) -> Iterator[str]:
    return (v.name for v in get_invalid(model))


def get_invalid_as_text(model: Model) -> str:
    return ", ".join(
        f"{key}: '{model[key]}'" for key in get_invalid_names(model)
    )
