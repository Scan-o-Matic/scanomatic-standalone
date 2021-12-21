from collections.abc import Iterator
from enum import Enum
from types import ModuleType
from typing import Literal, Optional, Type, Union

from scanomatic.generics.abstract_model_factory import AbstractModelFactory
from scanomatic.generics.model import Model

ValidationResults = Iterator[Union[Literal[True], Enum]]


def _get_validation_results(
    model: Model,
    factory: Type[AbstractModelFactory],
    module: Optional[ModuleType] = None,
) -> ValidationResults:
    # generate validation results for sub-models
    for k in model.keys():
        should_verify, sub_validation = factory.contains_model_type(k)
        if not should_verify or sub_validation is None:
            yield True
        item = getattr(model, k)
        item_type = type(item)
        if isinstance(sub_validation, dict):
            if (
                item_type in sub_validation
                # TODO: Does not include extra validation yet
                and validate(item, sub_validation[item_type])
            ):
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
                            if (
                                i_type not in leaf_type
                                # TODO: Does not include extra validation yet
                                and validate(i, leaf_type[i_type])
                            ):
                                yield model.FIELD_TYPES[k]
                                break

    # generate specific validation results
    if module is not None:
        for validator in dir(module):
            if not validator.startswith("validate"):
                continue
            yield getattr(module, validator)(model)


def validate(
    model: Model,
    factory: Type[AbstractModelFactory],
    module: Optional[ModuleType] = None,
) -> bool:
    if factory.verify_correct_model(model):
        return all(
            v is True for v
            in _get_validation_results(
                model,
                factory,
                module,
            )
        )


def get_invalid(
    model: Model,
    factory: Type[AbstractModelFactory],
    module: Optional[ModuleType] = None,
) -> Iterator[Enum]:
    return (
        v for v in set(_get_validation_results(model, factory, module))
        if v is not True
    )


def get_invalid_names(
    model: Model,
    factory: Type[AbstractModelFactory],
    module: Optional[ModuleType] = None,
) -> Iterator[str]:
    return (v.name for v in get_invalid(model, factory, module))


def get_invalid_as_text(
    model: Model,
    factory: Type[AbstractModelFactory],
    module: Optional[ModuleType] = None,
) -> str:
    return ", ".join([
        f"{key}: '{model[key]}'" for key in get_invalid_names(
            model,
            factory,
            module
        )
    ])
