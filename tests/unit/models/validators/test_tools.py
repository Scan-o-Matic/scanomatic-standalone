import math
from os import sep
from pathlib import Path
from typing import Any, Literal, Optional, Type, Union

import pytest

from scanomatic.generics.abstract_model_factory import AbstractModelFactory
from scanomatic.generics.model import Model
from scanomatic.models.analysis_model import GridModel, GridModelFields
from scanomatic.models.factories.analysis_factories import GridModelFactory
from scanomatic.models.validators.tools import (
    correct_type_and_in_bounds,
    in_bounds,
    is_coordinates,
    is_file,
    is_int_positive_or_neg_one,
    is_numeric_positive_or_neg_one,
    is_pinning_format,
    is_pinning_formats,
    is_real_number,
    is_safe_path,
    is_tuple_or_list
)


def test_is_file_when_not(tmpdir: Path):
    assert is_file(str(tmpdir)) is False


def test_is_file(tmpdir: Path):
    p = tmpdir / 'test.txt'
    p.write_text('hello', 'utf-8')
    assert is_file(str(p))


@pytest.mark.parametrize("fmt,expect", (
    (None, False),
    (1, False),
    ("test", False),
    ((20,), False),
    ((12, 23.5), False),
    ((12, 23), True),
))
def test_is_pinning_format(fmt: Any, expect: bool):
    assert is_pinning_format(fmt) is expect


@pytest.mark.parametrize("fmt,expect", (
    (None, False),
    (1, False),
    ("test", False),
    ((20,), False),
    ((12, 23), False),
    (((12, 23), None, (12, 3)), True),
    (((12, 23), False, (12, 3)), True),
    (((12, 23), [], (12, 3)), False),
))
def test_is_pinning_formats(fmt: Any, expect: bool):
    assert is_pinning_formats(fmt) is expect


@pytest.mark.parametrize("path,expect", (
    (None, True),
    ('', True),
    ('this.path  ', True),
    (f'this{sep}path', False),
    (42, False),
))
def test_is_safe_path(path: Any, expect: bool):
    assert is_safe_path(path) is expect


@pytest.mark.parametrize("obj,expected", [
    (tuple(), True),
    ([], True),
    ("foo", False),
    (42, False),
    (None, False),
])
def test_is_tuple_or_list(obj: Any, expected: bool):
    assert is_tuple_or_list(obj) == expected


@pytest.mark.parametrize("obj,expected", [
    (tuple(), False),
    ("foo", False),
    (42, False),
    (None, False),
    ([1, 2], False),
    ([1, 2, 3], True),
    ((1, 2, 3), True),
    ((1.123, 2, 3), False),
])
def test_is_coordinates(obj: Any, expected: bool):
    assert is_coordinates(obj) is expected


@pytest.mark.parametrize("obj,expected", [
    (-1, True),
    (0, True),
    (2.42, True),
    (1j, False),
    ('a', False),
    (None, False),
    (math.inf, False),
    (math.nan, False),
    (-math.inf, False),
])
def test_is_real_number(obj: Any, expected: bool):
    assert is_real_number(obj) == expected


@pytest.mark.parametrize("obj,expected", [
    (-2, False),
    (-1, True),
    (0, False),
    (2.42, True),
    ('a', False),
    (None, False),
])
def test_numeric_positive_or_neg_one(obj: Any, expected: bool):
    assert is_numeric_positive_or_neg_one(obj) is expected


@pytest.mark.parametrize("obj,zero,expected", [
    (-2, False, False),
    (-2, True, False),
    (-1, False, True),
    (0, False, False),
    (0, True, True),
    (2.42, False, False),
    ('a', False, False),
    (None, False, False),
])
def test_int_positive_or_neg_one(
    obj: Any,
    zero: bool,
    expected: bool,
):
    assert is_int_positive_or_neg_one(obj, allow_zero=zero) is expected


@pytest.mark.parametrize("value,min_value,max_value,expected", (
    (5, 1, 10, True),
    (0, 1, 10, False),
    (0, None, 10, True),
    (11, None, 10, False),
    (11, 1, 10, False),
    (11, 1, None, True),
    (0, 1, None, False),
))
def test_in_bounds(
    value: float,
    min_value: Optional[float],
    max_value: Optional[float],
    expected: bool,
):
    model = GridModelFactory.create(manual_threshold=value)
    min_model = GridModelFactory.create(manual_threshold=min_value)
    max_model = GridModelFactory.create(manual_threshold=max_value)
    assert in_bounds(
        model,
        min_model,
        max_model,
        'manual_threshold',
    ) is expected


@pytest.mark.parametrize("value,wanted_type,expected", (
    (5., float, True),
    (5., list, GridModelFields.manual_threshold),
    (-1., float, GridModelFields.manual_threshold),
    (11., float, GridModelFields.manual_threshold),
))
def test_correct_type_and_in_bounds(
    value: Any,
    wanted_type: Type,
    expected: Union[Literal[True], GridModelFields],
):
    def min_maker(m: Model, factory: Type[AbstractModelFactory]) -> Model:
        assert isinstance(m, Model)
        assert issubclass(factory, AbstractModelFactory)
        return GridModelFactory.create(manual_threshold=1.)

    def max_maker(m: Model, factory: Type[AbstractModelFactory]) -> Model:
        assert isinstance(m, Model)
        assert issubclass(factory, AbstractModelFactory)
        return GridModelFactory.create(manual_threshold=10.)

    model: GridModel = GridModelFactory.create(manual_threshold=value)
    assert correct_type_and_in_bounds(
        model,
        GridModelFields.manual_threshold,
        wanted_type,
        min_model_caller=min_maker,
        max_model_caller=max_maker,
        factory=GridModelFactory,
    ) is expected
