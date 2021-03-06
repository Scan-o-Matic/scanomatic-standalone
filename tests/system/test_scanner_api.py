import fnmatch
import http.client
from collections import namedtuple
from hashlib import sha256
from io import BytesIO
from typing import Union

import pytest
import requests


@pytest.fixture
def image():
    data = b'I am an image'
    return namedtuple('image', ['image', 'filename', 'digest'])(
        BytesIO(data), 'my_image.tiff', sha256(data).hexdigest()
    )


def get_number_of_images(scanomatic, project):
    params: dict[str, Union[str, int]] = {
        'suffix': '.tiff',
        'isDirectory': 0,
        'checkHasAnalysis': 0,
    }
    response = requests.get(
        scanomatic + '/api/tools/path/root/{}/'.format(project),
        params=params,
    )
    suggestions = fnmatch.filter(response.json()['suggestions'], '*.tiff')
    return len(suggestions)


def test_upload_image(scanomatic, image):
    project = 'my/project'
    assert get_number_of_images(scanomatic, project) == 0
    response = requests.post(
        scanomatic + '/api/scans',
        data={
            'project': project,
            'scan_index': 5,
            'timedelta': 789,
            'digest': image.digest,
        },
        files={
            'image': (image.filename, image.image, 'image/tiff'),
        },
    )
    assert response.status_code == http.client.CREATED, response.content
    assert get_number_of_images(scanomatic, project) == 1


def test_upload_image_unknown_project(scanomatic, image):
    project = 'unknown/project'
    response = requests.post(
        scanomatic + '/api/scans',
        data={
            'project': project,
            'scan_index': 5,
            'timedelta': 789,
            'digest': image.digest,
        },
        files={
            'image': (image.filename, image.image, 'image/tiff'),
        },
    )
    assert response.status_code == http.client.BAD_REQUEST, response.content
    assert get_number_of_images(scanomatic, project) == 0
