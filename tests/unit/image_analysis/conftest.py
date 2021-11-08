import os

import numpy as np
import pytest
from PIL import Image

TESTDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata')


@pytest.fixture(scope='session')
def easy_plate():
    return np.array(Image.open(
        os.path.join(TESTDATA, 'test_fixture_easy.tiff'),
    ))


@pytest.fixture(scope='session')
def hard_plate():
    return np.array(Image.open(
        os.path.join(TESTDATA, 'test_fixture_difficult.tiff'),
    ))
