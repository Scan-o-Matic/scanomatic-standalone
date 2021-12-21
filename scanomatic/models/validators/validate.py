from collections.abc import Iterator
from enum import Enum
from typing import Literal, Union

from scanomatic.generics.model import Model
from scanomatic.models.factories.factory_lookup import get_factory

from .validation_lookup import get_special_validators

ValidationResults = Iterator[Union[Literal[True], Enum]]


def _get_validation_results(model: Model) -> ValidationResults:
    module = get_special_validators(model)
    factory = get_factory(model)
    # generate validation results for sub-models
    for k in model.keys():
        if factory is None:
            yield model.FIELD_TYPES[k]
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
            yield model.FIELD_TYPES[k]
        else:
            if len(sub_validation) == 2:
                if not isinstance(item, sub_validation[0]):
                    yield model.FIELD_TYPES[k]
                else:
                    leaf_type = sub_validation[1]
                    if isinstance(leaf_type, dict):
                        for i in item:
                            if i is None:
                                continue
                            i_type = type(i)
                            if (i_type not in leaf_type and validate(i)):
                                yield model.FIELD_TYPES[k]
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


def get_invalid(model: Model) -> Iterator[Enum]:
    return (
        v for v in set(_get_validation_results(model)) if v is not True
    )


def get_invalid_names(model: Model) -> Iterator[str]:
    return (v.name for v in get_invalid(model))


def get_invalid_as_text(model: Model) -> str:
    return ", ".join([
        f"{key}: '{model[key]}'" for key in get_invalid_names(model)
    ])
