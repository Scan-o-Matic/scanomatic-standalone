from typing import Optional, Union

import pytest

from scanomatic.generics.abstract_model_factory import (
    AbstractModelFactory,
    email_serializer
)


class TestEmailSerializer:
    @pytest.mark.parametrize("data,expected", (
        ('I@mail.com', 'I@mail.com'),
        (['I@mail.com', 'u@mail.com'], 'I@mail.com, u@mail.com'),
        (None, ''),
    ))
    def test_serializing_returns_string(
        self,
        data: Optional[Union[str, list[str]]],
        expected: str,
    ):
        assert email_serializer(serialize=data) == expected

    @pytest.mark.parametrize("serialized,expected", (
        ('I@mail.com', 'I@mail.com'),
        (['I@mail.com', 'u@mail.com'], 'I@mail.com, u@mail.com'),
        (None, ''),
    ))
    def test_enforce_returns_string(
        self,
        serialized: Optional[Union[str, list[str]]],
        expected: str,
    ):
        assert email_serializer(enforce=serialized) == expected


class TestValidators:
    @pytest.mark.parametrize("num,expected", [
        (-1, True),
        (0, True),
        (2.42, True),
        (1j, False),
        ('a', False),
        (None, False),
    ])
    def test_is_number(self, num, expected):
        assert AbstractModelFactory._is_real_number(num) == expected

    @pytest.mark.parametrize("tup,expected", [
        (tuple(), True),
        ([], True),
        ("foo", False),
        (42, False),
        (None, False),
    ])
    def test_is_tuple_or_list(self, tup, expected):
        assert AbstractModelFactory._is_tuple_or_list(tup) == expected
