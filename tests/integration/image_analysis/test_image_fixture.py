import numpy as np
import pytest

from scanomatic.image_analysis.image_basics import load_image_to_numpy
from scanomatic.image_analysis.image_fixture import FixtureImage
from scanomatic.image_analysis.exceptions import FixtureImageError


@pytest.fixture
def image_path(pytestconfig) -> str:
    return str(pytestconfig.rootdir.join(
        "tests/integration/fixtures/proj1/proj1_0215_258418.2895.tiff"
    ))


@pytest.fixture
def image(image_path) -> np.ndarray:
    return load_image_to_numpy(image_path, dtype=np.uint8)


@pytest.fixture
def pattern_path(pytestconfig) -> str:
    return str(pytestconfig.rootdir.join(
        "scanomatic/images/orientation_marker.png"
    ))


@pytest.fixture
def fixture_image(image, pattern_path) -> FixtureImage:
    return FixtureImage.from_image(image, pattern_path)


class TestFixtureImage:

    def test_from_image(self, image: np.ndarray, pattern_path: str):
        fixture_image = FixtureImage.from_image(image, pattern_path)
        assert len(fixture_image._img.shape) == 2
        assert len(fixture_image._pattern_img.shape) == 2
        assert fixture_image._conversion_factor == 1.

    def test_from_image_raises_bad_pattern_path(self, image: np.ndarray):
        with pytest.raises(FixtureImageError) as err:
            FixtureImage.from_image(image, "not/a/path")
        assert "Could not open orientation guide image" in str(err)

    def test_from_image_path(self, image_path: str, pattern_path: str):
        fixture_image = FixtureImage.from_image_path(
            image_path,
            pattern_path,
            2.0
        )
        assert len(fixture_image._img.shape) == 2
        assert len(fixture_image._pattern_img.shape) == 2
        assert fixture_image._conversion_factor == 1 / 2.0

    def test_from_image_path_raises_bad_image_path(self, pattern_path: str):
        with pytest.raises(FixtureImageError) as err:
            FixtureImage.from_image_path("not/a/path", pattern_path)
        assert "Could not open image" in str(err)

    def test_from_image_path_raises_bad_pattern_path(self, image_path: str):
        with pytest.raises(FixtureImageError) as err:
            FixtureImage.from_image_path(image_path, "not/a/path")
        assert "Could not open orientation guide image" in str(err)

    def test_resize(self, fixture_image: FixtureImage):
        conversion_factor = 2.

        orig_size = fixture_image._img.shape
        assert fixture_image._conversion_factor != conversion_factor
        fixture_image.resize(conversion_factor)
        assert fixture_image._conversion_factor == conversion_factor

        np.testing.assert_array_equal(
            fixture_image._img.shape,
            np.array(orig_size) * conversion_factor,
        )

    def test_load_new_image(
        self,
        fixture_image: FixtureImage,
        image_path: str,
    ):
        prev_img = np.zeros(0)
        fixture_image._img = prev_img
        fixture_image.load_new_image(image_path)
        assert fixture_image._img != prev_img

    def test_load_new_image_raises(self, fixture_image: FixtureImage):
        with pytest.raises(FixtureImageError) as err:
            fixture_image.load_new_image("not/a/path")
        assert "Could not open image" in str(err)
