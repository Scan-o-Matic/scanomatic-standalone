from collections.abc import Iterator
from enum import Enum
from types import ModuleType
from typing import Literal, Type, Union

from scanomatic.generics.abstract_model_factory import AbstractModelFactory
from scanomatic.generics.model import Model

ValidationResults = Iterator[Union[Literal[True], Enum]]


def _get_validation_results(
    model: Model,
    module: ModuleType
) -> ValidationResults:
    return (
        getattr(module, attr)(model)
        for attr in dir(module)
        if attr.startswith("validate")
    )


def validate(
    model: Model,
    factory: Type[AbstractModelFactory],
    module: ModuleType,
) -> bool:
    if factory.verify_correct_model(model):
        return all(
            v is True for v in _get_validation_results(model, module)
        )


def get_invalid(model: Model, module: ModuleType) -> Iterator[Enum]:
    return (
        v for v in set(_get_validation_results(model, module))
        if v is not True
    )


def get_invalid_names(model: Model, module: ModuleType) -> Iterator[str]:
    return (v.name for v in get_invalid(model, module))


def get_invalid_as_text(model: Model, module: ModuleType) -> str:
    return ", ".join([
        f"{key}: '{model[key]}'" for key in get_invalid_names(model, module)
    ])
