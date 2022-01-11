from typing import Optional, Union

import pytest

from scanomatic.generics.abstract_model_factory import (
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
