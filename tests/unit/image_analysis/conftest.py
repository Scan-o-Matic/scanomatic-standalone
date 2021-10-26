import os

import pytest  # type: ignore
from scipy import ndimage  # type: ignore

TESTDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata')


@pytest.fixture(scope='session')
def easy_plate():
    return ndimage.io.imread(
        os.path.join(TESTDATA, 'test_fixture_easy.tiff'),
    )


@pytest.fixture(scope='session')
def hard_plate():
    return ndimage.io.imread(
        os.path.join(TESTDATA, 'test_fixture_difficult.tiff'),
    )
