import itertools
import time
from typing import Any, Union

import numpy as np

from scanomatic.data_processing.calibration import get_image_json_from_ccc
from scanomatic.image_analysis.grayscale import get_grayscale
from scanomatic.io import jsonizer
from scanomatic.io.ccc_data import CCCImage
from scanomatic.io.fixtures import Fixtures, FixtureSettings
from scanomatic.io.logger import get_logger
from scanomatic.models.fixture_models import (
    FixturePlateModel,
    GrayScaleAreaModel
)
from scanomatic.image_analysis.grayscale_detection import (
    detect_grayscale,
    get_grayscale_im_section,
)
from scanomatic.image_analysis.exceptions import GrayscaleError

from . import image_basics, image_fixture
from .image_basics import load_image_to_numpy


def _get_coords_sorted(coords):
    return list(zip(*list(map(sorted, list(zip(*coords))))))


def get_image_scale(im):
    small_error = 0.01
    invalid_scale = -1.0

    if im is not None:

        scale_d1, scale_d2 = [
            im.shape[i] / FixtureImage.EXPECTED_IM_SIZE[i]
            for i in range(2)
        ]
        if abs(scale_d1 - scale_d2) < small_error:

            return (scale_d1 + scale_d2) / 2.0
        return invalid_scale


# def _get_rotated_vector(x, y, rotation):
#    return x * np.cos(rotation), y * np.sin(rotation)


def get_local_fixture_for_image(identifier, image_identifier):
    im_json = get_image_json_from_ccc(identifier, image_identifier)
    if im_json is None:
        return None

    fixture_settings = Fixtures()[im_json[CCCImage.fixture]]
    if fixture_settings is None:
        return None

    fixture = FixtureImage(fixture_settings)
    current_settings = fixture['current']
    current_settings.model.orientation_marks_x = np.array(
        im_json[CCCImage.marker_x],
    )
    current_settings.model.orientation_marks_y = np.array(
        im_json[CCCImage.marker_y],
    )
    issues = {}
    fixture.set_current_areas(issues)

    return {
        "plates": current_settings.model.plates,
        "grayscale": current_settings.model.grayscale,
        "issues": issues,
    }


class FixtureImage:
    MARKER_DETECTION_DPI = 150
    EXPECTED_IM_SIZE = (6000, 4800)
    EXPECTED_IM_DPI = 600

    def __init__(
        self,
        fixture: FixtureSettings = None,
        reference_overwrite_mode: bool = False
    ):
        self._logger = get_logger("Fixture Image")
        self._reference_fixture_settings = fixture
        self._current_fixture_settings = None
        self._reference_overwrite_mode = reference_overwrite_mode
        self.im = None
        self.im_path = None
        self._original_dpi = None
        self._name = "default"

    def __getitem__(self, key):
        if key in ['current']:
            if self._current_fixture_settings is None:
                self._current_fixture_settings = FixtureSettings(
                    self.name,
                    overwrite=False,
                )
            return self._current_fixture_settings

        elif key in ['fixture', 'reference']:
            if self._reference_fixture_settings is None:
                self._reference_fixture_settings = FixtureSettings(
                    self.name, overwrite=self._reference_overwrite_mode,
                )
                self._name = self.name
            return self._reference_fixture_settings

        else:
            raise KeyError(key)

    @property
    def name(self):
        if self._reference_fixture_settings:
            return self._reference_fixture_settings.model.name
        else:
            return self._name

    @name.setter
    def name(self, value):

        if self._reference_fixture_settings:
            self._reference_fixture_settings.model.name = value
        else:
            self._name = value

    def get_dpi_factor_to_target(self, target_scale):

        return target_scale / self._original_dpi

    @staticmethod
    def coordinate_to_original_dpi(coordinate, as_ints=False, scale=1.0):
        rtype = type(coordinate)
        if as_ints:
            return rtype(int(round(val / scale)) for val in coordinate)

        return rtype(val / scale for val in coordinate)

    @staticmethod
    def coordinate_to_local_dpi(coordinate, as_ints=False, scale=1.0):
        rtype = type(coordinate)
        if as_ints:
            return rtype(int(round(val * scale)) for val in coordinate)

        return rtype(val * scale for val in coordinate)

    def set_image(self, image=None, image_path=None, dpi=None):
        self.im_path = image_path
        if image is not None:
            self.im = image

        elif image_path is not None:
            try:
                self.im = load_image_to_numpy(image_path, dtype=np.uint8)
            except IOError:
                self.im = None

            if self.im is None:
                self._logger.error(
                    "Could not load image at '{0}'".format(image_path),
                )

            else:
                self._logger.info(
                    "Loaded image {0} with shape {1}".format(
                        image_path,
                        self.im.shape,
                    ),
                )
        else:
            self._logger.warning(
                "No information supplied about how to load image, thus none loaded",  # noqa : E501
            )
            self.im = None

        if self.im is None:
            self._original_dpi = None
        else:
            self._original_dpi = dpi if dpi else self.guess_dpi()

    def guess_dpi(self):
        dpi = (
            (a / b) * self.EXPECTED_IM_DPI
            for a, b in zip(self.im.shape, self.EXPECTED_IM_SIZE)
        )
        if dpi:
            guess = 0
            for val in dpi:
                if guess > 0 and guess != val:
                    self._logger.warning(
                        "Image dimensions don't agree with expected size "
                        "X {1} != Y {2} on image '{3}', can't guess DPI, using {0}".format(  # noqa: E501
                            self.EXPECTED_IM_DPI,
                            guess,
                            val,
                            self.im_path,
                        ))
                    return self.EXPECTED_IM_DPI

                guess = val

            if guess > 0:
                return guess

        return self.EXPECTED_IM_DPI

    def analyse_current(self):
        logger = self._logger
        t = time.time()
        logger.debug("Threading invokes marker analysis")

        self.run_marker_analysis()
        logger.debug(
            "Threading marker detection complete,"
            "invokes setting area positions (acc-time {0} s)".format(
                time.time() - t,
            ),
        )

        self.set_current_areas(issues={})
        logger.debug(
            "Threading areas set(acc-time: {0} s)".format(
                time.time() - t,
            ),
        )

        self.analyse_grayscale()
        logger.debug(
            "Grayscale ({0}) analysed (acc-time: {1} s)".format(
                self['grayscale_type'],
                time.time() - t,
            ),
        )

        logger.debug(
            "Threading done (took: {0} s)".format(time.time() - t),
        )

    def run_marker_analysis(self, markings=None):
        _logger = self._logger

        t = time.time()
        if markings is None:
            markings = len(self["fixture"].model.orientation_marks_x)

        analysis_img = self._get_image_in_correct_scale(
            self.MARKER_DETECTION_DPI,
        )
        scale_factor = self.get_dpi_factor_to_target(
            self.MARKER_DETECTION_DPI,
        )

        _logger.info(
            "Running marker detection ({0} markers on {1} ({2}) using {3}, scale {4})".format(  # noqa: E501
                markings,
                self.im_path,
                analysis_img.shape,
                self["reference"].get_marker_path(),
                scale_factor,
            ),
        )

        im_analysis = image_fixture.FixtureImage.from_image(
            image=analysis_img,
            pattern_image_path=self["reference"].get_marker_path(),
            scale=scale_factor,
        )

        (
            x_positions_correct_scale,
            y_positions_correct_scale
        ) = im_analysis.find_pattern(markings=markings)

        self["current"].model.orientation_marks_x = x_positions_correct_scale
        self["current"].model.orientation_marks_y = y_positions_correct_scale

        _logger.debug(
            "Marker Detection complete (acc {0} s)".format(time.time() - t),
        )

    def _get_image_in_correct_scale(self, target_dpi):
        if self._original_dpi != target_dpi:
            return image_basics.Quick_Scale_To_im(
                im=self.im,
                scale=self.get_dpi_factor_to_target(target_dpi),
            )

        return self.im

    def _set_current_mark_order(self):
        x_centered, y_centered = self._get_centered_mark_positions(
            "current",
        )
        x_centered_ref, y_centered_ref = self._get_centered_mark_positions(
            "reference",
        )

        if all(
            o is not None and o.size > 0 for o in
            (x_centered, y_centered, x_centered_ref, y_centered_ref)
        ):
            length = np.sqrt(x_centered ** 2 + y_centered ** 2)
            length_ref = np.sqrt(x_centered_ref ** 2 + y_centered_ref ** 2)
            sort_order, sort_error = self._get_sort_order(length, length_ref)

            self._logger.debug(
                "Found sort order that matches the reference {0} (error {1})".format(  # noqa: E501
                    sort_order,
                    sort_error,
                ),
            )
            self.__set_current_mark_order(sort_order)

        else:
            self._logger.critical("Missmatch in number of markings!")

    def __set_current_mark_order(self, sort_order):
        current_model = self["current"].model
        current_model.orientation_marks_x = (
            current_model.orientation_marks_x[sort_order]
        )
        current_model.orientation_marks_y = (
            current_model.orientation_marks_y[sort_order]
        )

    def _get_centered_mark_positions(self, source="current"):
        x_positions = self[source].model.orientation_marks_x
        y_positions = self[source].model.orientation_marks_y

        if x_positions is None or y_positions is None:
            return None, None

        x_positions = np.array(x_positions)
        y_positions = np.array(y_positions)

        marking_center = np.array(
            (x_positions.mean(), y_positions.mean())
        )
        x_centered = x_positions - marking_center[0]
        y_centered = y_positions - marking_center[1]

        return x_centered, y_centered

    @staticmethod
    def _get_sort_order(length, reference_length):
        s = list(range(len(length)))

        length_deltas = []
        sort_orders = []
        for sort_order in itertools.permutations(s):

            length_deltas.append(
                (length[list(sort_order)] - reference_length) ** 2,
            )
            sort_orders.append(sort_order)

        length_deltas = np.array(length_deltas).sum(1)
        return (
            list(sort_orders[length_deltas.argmin()]),
            np.sqrt(length_deltas.min()),
        )

    def _get_rotation(self):
        x_centered, y_centered = self._get_centered_mark_positions("current")
        x_centered_ref, y_centered_ref = self._get_centered_mark_positions(
            "reference",
        )
        length = np.sqrt(x_centered ** 2 + y_centered ** 2)
        length_ref = np.sqrt(x_centered_ref ** 2 + y_centered_ref ** 2)

        rotations = np.arccos(x_centered / length)
        rotations = (
            rotations * (y_centered > 0)
            + -1 * rotations * (y_centered < 0)
        )

        rotations_ref = np.arccos(x_centered_ref / length_ref)
        rotations_ref = (
            rotations_ref * (y_centered_ref > 0)
            + -1 * rotations_ref * (y_centered_ref < 0)
        )

        rotation: float = (rotations - rotations_ref).mean()
        if np.abs(rotation) < 0.001:
            return 0
        else:
            return rotation

    def _get_offset(self):
        current_model = self['current'].model
        ref_model = self['reference'].model
        x_delta = (
            current_model.orientation_marks_x - ref_model.orientation_marks_x
        )
        y_delta = (
            current_model.orientation_marks_y - ref_model.orientation_marks_y
        )
        return x_delta.mean(), y_delta.mean()

    def get_plate_im_section(
        self,
        plate_model: FixturePlateModel,
        scale: float = 1.0,
    ):
        im = self.im

        if im is not None and plate_model is not None:
            try:
                return im[
                    max(plate_model.y1 * scale, 0):
                    min(plate_model.y2 * scale, im.shape[0]),
                    max(plate_model.x2 * scale, 0):
                    min(plate_model.x2 * scale, im.shape[1])
                ]

            except (IndexError, TypeError):

                return None

    def analyse_grayscale(self) -> None:
        current_model = self["current"].model
        try:
            grayscale_im = get_grayscale_im_section(
                self.im,
                current_model.grayscale,
            )
            grayscale_config = get_grayscale(current_model.grayscale.name)
            current_model.grayscale.section_values = detect_grayscale(
                grayscale_im,
                grayscale_config,
            )

        except GrayscaleError:
            self._logger.warning("Failed analysing grayscale")

    def _set_area_relative(
        self,
        area: Union[FixturePlateModel, GrayScaleAreaModel],
        rotation=None,
        offset: tuple[int, int] = (0, 0),
        issues: dict[str, Any] = {},
    ):

        if area is None:
            self._logger.error(
                "Area is None, can't set if area isn't specified",
            )

        if offset is None:
            self._logger.error(
                "Offset is None, this doesn't make any sense",
            )

        if rotation and np.abs(rotation) > 0.01:
            self._logger.warning(
                "Not supporting rotations yet (got {0})".format(rotation),
            )
            # area.x1, area.y1 = _get_rotated_vector(area.x1, area.y1, rotation)
            # area.x2, area.y2 = _get_rotated_vector(area.x2, area.y2, rotation)

        for dim, keys in list({1: ('x1', 'x2'), 0: ('y1', 'y2')}.items()):
            for key in keys:
                area[key] = round(area[key] + offset[dim])
                if area[key] > self.EXPECTED_IM_SIZE[dim]:
                    self._logger.warning(
                        "{0} value ({1}) outside image, setting to img border".format(  # noqa: E501
                            key,
                            area[key],
                        ),
                    )
                    area[key] = self.EXPECTED_IM_SIZE[dim]
                    issues['overflow'] = (
                        area.index if hasattr(area, "index") else "Grayscale"
                    )
                elif area[key] < 0:
                    self._logger.warning(
                        "{0} value ({1}) outside image, setting to img border".format(  # noqa: E501
                            key,
                            area[key],
                        ),
                    )
                    area[key] = 0
                    issues['overflow'] = (
                        area.index if hasattr(area, "index") else "Grayscale"
                    )

    def set_current_areas(self, issues: dict[str, Any]):
        """
        :param issues: reported issues
        """

        self._set_current_mark_order()
        offset = self._get_offset()
        rotation = self._get_rotation()
        if abs(rotation) > 0.05:
            issues['rotation'] = rotation
        current_model = self["current"].model
        ref_model = self["fixture"].model

        self._logger.info(
            "Positions on current '{0}' will be moved {1} and rotated {2} due to diff to reference {3}".format(  # noqa: E501
                current_model.name,
                offset,
                rotation,
                ref_model.name,
            ),
        )

        current_model.plates = type(current_model.plates)(
            jsonizer.copy(plate) for plate in ref_model.plates
        )

        for plate in current_model.plates:
            self._set_area_relative(plate, rotation, offset, issues)

        self._set_area_relative(
            current_model.grayscale,
            rotation,
            offset,
            issues,
        )
