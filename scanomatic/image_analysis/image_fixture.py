from typing import Optional

import numpy as np
from scipy.ndimage import center_of_mass  # type: ignore
from scipy.signal import fftconvolve  # type: ignore

from scanomatic.io.logger import get_logger

from . import image_basics
from .image_basics import load_image_to_numpy
from .exceptions import FixtureImageError


_logger = get_logger("Resource Image Analysis")


class FixtureImage:
    def __init__(
        self,
        image: np.ndarray,
        pattern_image: np.ndarray,
        scale: float,
    ):
        self._img = image
        self._pattern_img = pattern_image
        self._transformed = False
        self._conversion_factor = 1.0 / scale

    @classmethod
    def from_image(
        cls,
        image: np.ndarray,
        pattern_image_path: str,
        scale: float = 1.0,
    ) -> "FixtureImage":
        if len(image.shape) > 2:
            image = image[:, :, 0]

        try:
            pattern_image = load_image_to_numpy(
                pattern_image_path,
                dtype=np.uint8,
            )
        except IOError:
            msg = f"Could not open orientation guide image at {pattern_image_path}"  # noqa: E501
            _logger.error(msg)
            raise FixtureImageError(msg)

        if len(pattern_image.shape) > 2:
            pattern_image = pattern_image[:, :, 0]

        return cls(image, pattern_image, scale)

    @classmethod
    def from_image_path(
        cls,
        image_path: str,
        pattern_image_path: str,
        scale: float = 1.0,
    ) -> "FixtureImage":
        try:
            image = load_image_to_numpy(image_path, dtype=np.uint8)

        except IOError:
            msg = f"Could not open image at {image_path}"
            _logger.error(msg)
            raise FixtureImageError(msg)

        if len(image.shape) > 2:
            image = image[:, :, 0]

        try:
            pattern_image = load_image_to_numpy(
                pattern_image_path,
                dtype=np.uint8,
            )
        except IOError:
            msg = f"Could not open orientation guide image at {pattern_image_path}"  # noqa: E501
            _logger.error(msg)
            raise FixtureImageError(msg)

        if len(pattern_image.shape) > 2:
            pattern_image = pattern_image[:, :, 0]

        return cls(image, pattern_image, scale)

    def resize(
        self,
        conversion_factor: float
    ) -> None:
        _logger.info(f"Scaling to {conversion_factor}")
        self._conversion_factor = conversion_factor
        self._img = image_basics.Quick_Scale_To_im(
            im=self._img, scale=conversion_factor
        )
        _logger.info("Scaled")

    def load_new_image(
        self,
        path: str,
    ) -> None:
        try:
            self._img = load_image_to_numpy(path, dtype=np.uint8)
        except IOError:
            msg = f"Could not open image at {path}"
            _logger.error(msg)
            raise FixtureImageError(msg)

    @staticmethod
    def get_hit_refined(
        local_hit,
        conv_img,
        coordinates=None,
        gaussian_weight_size_fraction: float = 2.0,
    ) -> tuple[int, int]:
        """
        Use half-size to select area and give each pixel the weight of the
        convolution result of that coordinate times the 2D gaussian value
        based on offset of distance to hit (sigma = ?).

        Refined hit is the hit + mass-center offset from hit

        :param hit:
        :param conv_img:
        :param half_stencil_size:
        :return: refined hit
        """

        def make_2d_guass_filter(size, fwhm, center):
            """ Make a square gaussian kernel.

            size is the length of a side of the square
            fwhm is full-width-half-maximum, which
            can be thought of as an effective radius.
            """

            x = np.arange(0, size, 1, float)
            y = x[:, np.newaxis]

            x0 = center[1]
            y0 = center[0]

            return np.exp(-4*np.log(2) * ((x-x0)**2 + (y-y0)**2) / fwhm**2)

        if coordinates is None:
            image_slice = conv_img
        else:
            image_slice = conv_img[
                int(round(coordinates['d0_min'])):
                int(round(coordinates['d0_max'])),
                int(round(coordinates['d1_min'])):
                int(round(coordinates['d1_max']))
            ]
        gauss_size = max(image_slice.shape)
        gauss = make_2d_guass_filter(
            gauss_size,
            gauss_size / gaussian_weight_size_fraction,
            local_hit,
        )

        return np.array(
            center_of_mass(
                image_slice
                * gauss[: image_slice.shape[0], : image_slice.shape[1]]
            )
        ) - local_hit

    def get_convolution(self, threshold: float = 127) -> np.ndarray:
        t_img = (self._img > threshold).astype(np.int8) * 2 - 1
        marker = self._pattern_img

        if len(marker.shape) == 3:
            marker = marker[:, :, 0]

        t_mrk = (marker > 0) * 2 - 1
        return fftconvolve(t_img, t_mrk, mode='same')

    @staticmethod
    def get_best_location(
        conv_img: np.ndarray,
        stencil_size: tuple[int, ...],
        refine_hit_gauss_weight_size_fraction: float = 2.0,
        max_refinement_iterations: int = 20,
        min_refinement_sq_distance: float = 0.0001,
    ) -> tuple[Optional[np.ndarray], np.ndarray]:
        """This whas hidden and should be taken care of, is it needed"""

        hit = np.where(conv_img == conv_img.max())

        if len(hit[0]) == 0:
            return None, conv_img

        hit = np.array((hit[0][0], hit[1][0]), dtype=float)

        # Zeroing out hit
        half_stencil_size = [x / 2.0 for x in stencil_size]

        coordinates = {
            'd0_min': max(0, hit[0] - half_stencil_size[0] - 1),
            'd0_max': min(conv_img.shape[0], hit[0] + half_stencil_size[0]),
            'd1_min': max(0, hit[1] - half_stencil_size[1] - 1),
            'd1_max': min(conv_img.shape[1], hit[1] + half_stencil_size[1]),
        }

        for _ in range(max_refinement_iterations):
            offset = FixtureImage.get_hit_refined(
                hit - (coordinates['d0_min'], coordinates['d1_min']),
                conv_img,
                coordinates,
                refine_hit_gauss_weight_size_fraction
            )
            hit += offset

            if (np.array(offset) ** 2).sum() < min_refinement_sq_distance:
                break

        coordinates = {
            'd0_min': int(round(max(0, hit[0] - half_stencil_size[0] - 1))),
            'd0_max': int(round(min(
                conv_img.shape[0],
                hit[0] + half_stencil_size[0],
            ))),
            'd1_min': int(round(max(0, hit[1] - half_stencil_size[1] - 1))),
            'd1_max': int(round(min(
                conv_img.shape[1],
                hit[1] + half_stencil_size[1],
            ))),
        }

        conv_img[
            coordinates['d0_min']: coordinates['d0_max'],
            coordinates['d1_min']: coordinates['d1_max']
        ] = conv_img.min() - 1
        return hit, conv_img

    def get_best_locations(
        self,
        conv_img: np.ndarray,
        stencil_size: tuple[int, ...],
        n: int,
        refine_hit_gauss_weight_size_fraction: float = 2.0,
    ) -> list[Optional[np.ndarray]]:
        """This returns the best locations as a list of coordinates on the
        CURRENT IMAGE regardless of if it was scaled"""

        m_locations = []
        c_img = conv_img.copy()
        i = 0
        try:
            n = int(n)
        except Exception:
            n = 3

        while i < n:

            m_loc, c_img = self.get_best_location(
                c_img,
                stencil_size,
                refine_hit_gauss_weight_size_fraction,
            )
            m_locations.append(m_loc)

            i += 1

        return m_locations

    def find_pattern(
        self,
        markings: int = 3,
        img_threshold: float = 127,
    ) -> tuple[np.ndarray, np.ndarray]:
        """This function returns the image positions as numpy arrays that
        are scaled to match the ORIGINAL IMAGE size"""

        c1 = self.get_convolution(threshold=img_threshold)

        m1 = np.array(self.get_best_locations(
            c1,
            self._pattern_img.shape,
            markings,
            refine_hit_gauss_weight_size_fraction=3.5,
        )) * self._conversion_factor

        try:
            return m1[:, 1], m1[:, 0]
        except (IndexError, TypeError):
            msg = f"Detecting markings failed, location object:\n{m1}"
            _logger.error(msg)
            raise FixtureImageError(msg)
