from typing import Any
import pytest

from scanomatic.models.validators.tools import (
    is_real_number,
    is_tuple_or_list,
)


@pytest.mark.parametrize("obj,expected", [
    (-1, True),
    (0, True),
    (2.42, True),
    (1j, False),
    ('a', False),
    (None, False),
])
def test_is_number(obj: Any, expected: bool):
    assert is_real_number(obj) == expected


@pytest.mark.parametrize("obj,expected", [
    (tuple(), True),
    ([], True),
    ("foo", False),
    (42, False),
    (None, False),
])
def test_is_tuple_or_list(obj: Any, expected: bool):
    assert is_tuple_or_list(obj) == expected
