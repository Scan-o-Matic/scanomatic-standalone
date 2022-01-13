"""Resource module for handling basic images operations."""
from typing import Optional, Type

import numpy as np
from PIL import Image
from scanomatic.io.logger import get_logger
from scipy.ndimage import zoom  # type: ignore

from scanomatic.models.analysis_model import IMAGE_ROTATIONS
from .exceptions import LoadImageError

_logger = get_logger("Basic Image Utils")


def scale_16bit_to_8bit_range(data: np.ndarray) -> np.ndarray:
    return data / (2 ** 16 - 1.) * 255


def round_to_8bit(data: np.ndarray) -> np.ndarray:
    return np.round(data).astype(np.uint8)


def load_image_to_numpy(
    path: str,
    orientation: IMAGE_ROTATIONS = IMAGE_ROTATIONS.Portrait,
    dtype: Type = np.float64,
) -> np.ndarray:
    im = Image.open(path)
    data = np.array(im)

    if data.dtype == np.uint16:
        data = scale_16bit_to_8bit_range(data)

    data_orientation = (
        IMAGE_ROTATIONS.Portrait if max(data.shape) == data.shape[0]
        else IMAGE_ROTATIONS.Landscape
    )

    if data_orientation == orientation:
        if dtype is None or data.dtype == dtype:
            return data
        elif dtype == np.uint8:
            return np.round(data).astype(dtype)
        else:
            return data.astype(dtype)
    else:
        if dtype is None or data.dtype == dtype:
            return data.T
        elif dtype == np.uint8:
            return np.round(data).T.astype(dtype)
        else:
            return data.T.astype(dtype)


def Quick_Scale_To_im(
    path: Optional[str] = None,
    im: Optional[np.ndarray] = None,
    source_dpi: int = 600,
    target_dpi: int = 150,
    scale: Optional[float] = None,
) -> np.ndarray:
    if im is None:
        if path is None:
            msg = "No image or path supplied"
            _logger.error(msg)
            raise LoadImageError(msg)

        try:
            im = load_image_to_numpy(path, dtype=np.uint8)
        except Exception:
            msg = f"Could not open source with path {path}"
            _logger.error(msg)
            raise LoadImageError(msg)

    if scale is None:
        scale = target_dpi / source_dpi

    small_im = zoom(im, scale, order=1)
    return small_im


class Image_Transpose:

    def __init__(self, sourceValues=None, targetValues=None, polyCoeffs=None):

        self._logger = get_logger("Image Transpose")
        self._source = sourceValues
        self._target = targetValues
        self._polyCoeffs = polyCoeffs

        if (self._polyCoeffs is None and self._target is not None and
                self._source is not None):

            try:
                self._polyCoeffs = np.polyfit(self._source, self._target, 3)
            except Exception as e:
                self._logger.critical(
                    "Could not produce polynomial from source " +
                    "{0} and target {1}".format(
                        self._source,
                        self._target,
                    ),
                )
                raise e

        if self._polyCoeffs is not None:
            self._poly = np.poly1d(self._polyCoeffs)
        else:
            errorCause = ""
            if self._source is None:
                errorCause += "No source "
            if self._target is None:
                errorCause += "No target "
            if self._polyCoeffs is None:
                errorCause += "No Coefficients"
            raise Exception(
                "Polynomial not initiated; can't transpose image: {0}".format(
                    errorCause
                ),
            )

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    @property
    def coefficients(self):
        return self._polyCoeffs

    @property
    def polynomial(self):
        return self._poly

    def __call__(self, im):
        return self._poly(im)
