from typing import Union
import pytest
from flask import Flask
from pathlib import Path

from scanomatic.ui_server import general


@pytest.fixture(scope='module')
def app():
    _app = Flask("--dummy--")
    with _app.app_context():
        yield _app


class TestJsonAbort:
    @pytest.mark.parametrize(
        "status_code,args,kwargs",
        [
            (300, [], {}),
            (400, [1, 2], {}),
            (500, [], {'3': 1, '1': 20}),
        ],
    )
    def test_json_abort(self, app, status_code, args, kwargs):
        with app.test_request_context():
            assert general.json_abort(
                status_code, *args, **kwargs).status_code == status_code


@pytest.mark.parametrize("data,expect", (
    ('aGVsbG8=', b'hello'),
    ('aGVsbG8', b'hello'),
    (b'aGVsbG8', b'hello'),
))
def test_pad_decode_base64(data: Union[bytes, str], expect: bytes):
    assert general.pad_decode_base64(data) == expect


@pytest.mark.parametrize("data,expect", (
    ('aGVsbG8====', b'hello'),
    (b'aGVsbG8====', b'hello'),
))
def test_remove_pad_decode_base64(data: Union[bytes, str], expect: bytes):
    assert general.remove_pad_decode_base64(data) == expect


def test_get_image_data_as_array_from_str():
    im_str = (Path(__file__).parent / 'data' / 'image.b64').read_text()
    im = general.get_image_data_as_array(im_str)
    assert im.shape == (10, 10, 3)
    assert (im == 1).all()
