from enum import Enum
from typing import Any, Literal, Optional, Type, Union
from numbers import Real

import os
from scanomatic.generics.abstract_model_factory import AbstractModelFactory

from scanomatic.generics.model import Model


def is_file(path: Optional[str]) -> bool:
    return isinstance(path, str) and os.path.isfile(path)


def is_pinning_format(pinning_format: Any) -> bool:
    try:
        return all(
            isinstance(val, int)
            and val > 0
            for val in pinning_format
        ) and len(pinning_format) == 2
    except Exception:
        pass

    return False


def is_pinning_formats(pinning_formats: Any) -> bool:
    try:
        return all(
            pinning_format is None
            or pinning_format is False
            or is_pinning_format(pinning_format)
            for pinning_format in pinning_formats
        )
    except Exception:
        pass
    return False


def is_safe_path(path: Optional[str]) -> bool:
    return (
        path is None
        or isinstance(path, str) and os.sep not in path
    )


def is_tuple_or_list(obj: Any) -> bool:
    return isinstance(obj, tuple) or isinstance(obj, list)


def is_coordinates(obj: Any) -> bool:
    return (
        is_tuple_or_list(obj)
        and all(isinstance(value, int) for value in obj)
        and len(obj) == 3
    )


def is_real_number(obj: Any) -> bool:
    return isinstance(obj, Real)


def is_numeric_positive_or_neg_one(obj: Any) -> bool:
    if isinstance(obj, int) or isinstance(obj, float):
        return obj == -1 or obj > 0
    return False


def is_int_positive_or_neg_one(obj: Any, allow_zero: bool = False) -> bool:
    if isinstance(obj, int):
        return obj == -1 or obj > 0 or obj == 0 and allow_zero
    return False


def in_bounds(model, lower_bounds, upper_bounds, attr: str) -> bool:
    val = getattr(model, attr)
    min_val = getattr(lower_bounds, attr)
    max_val = getattr(upper_bounds, attr)

    if min_val is not None and val < min_val:
        return False
    elif max_val is not None and val > max_val:
        return False
    else:
        return True


def correct_type_and_in_bounds(
    model: Model,
    attr: Enum,
    dtype: Type[Any],
    min_model_caller,
    max_model_caller,
    factory: Type[AbstractModelFactory]
) -> Union[Literal[True], Enum]:
    if not isinstance(getattr(model, attr.name), dtype):
        return attr

    elif not in_bounds(
        model,
        min_model_caller(model, factory=factory),
        max_model_caller(model, factory=factory),
        attr.name,
    ):
        return attr

    else:
        return True
