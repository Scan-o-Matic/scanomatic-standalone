import os
import re
import string
from typing import Type

import scanomatic.io.app_config as app_config
import scanomatic.io.fixtures as fixtures
from scanomatic.data_processing.calibration import get_active_cccs
from scanomatic.models.factories.scanning_factory import ScanningModelFactory
from scanomatic.models.scanning_model import ScanningModel
from scanomatic.models.validators.tools import (
    correct_type_and_in_bounds,
    is_pinning_formats
)

_GET_MIN_MODEL = app_config.Config().get_min_model
_GET_MAX_MODEL = app_config.Config().get_max_model
_ALLOWED_CHARACTERS = string.ascii_letters + string.digits + "_"


def _correct_type_and_in_bounds(
    model: ScanningModel,
    attr: str,
    dtype: Type,
):
    return correct_type_and_in_bounds(
        model,
        attr,
        dtype,
        _GET_MIN_MODEL,
        _GET_MAX_MODEL,
        ScanningModelFactory,
    )


def validate_number_of_scans(model: ScanningModel):
    return _correct_type_and_in_bounds(model, "number_of_scans", int)


def validate_time_between_scans(model: ScanningModel):
    try:
        model.time_between_scans = float(model.time_between_scans)
    except Exception:
        return model.FIELD_TYPES.time_between_scans
    return _correct_type_and_in_bounds(
        model,
        "time_between_scans",
        float,
    )


def validate_project_name(model: ScanningModel):
    if (
        not model.project_name
        or len(model.project_name) != len(tuple(
            c for c in model.project_name
            if c in _ALLOWED_CHARACTERS
        ))
    ):
        return model.FIELD_TYPES.project_name

    try:
        int(model.project_name)
        return model.FIELD_TYPES.project_name
    except (ValueError, TypeError):
        pass

    return True


def validate_directory_containing_project(model: ScanningModel):
    try:
        if os.path.isdir(
            os.path.abspath(model.directory_containing_project),
        ):
            return True
    except Exception:
        pass

    return model.FIELD_TYPES.directory_containing_project


def validate_description(model: ScanningModel):
    if isinstance(model.description, str):
        return True

    return model.FIELD_TYPES.description


def validate_email(model: ScanningModel):
    if not model.email:
        return True

    if isinstance(model.email, str):
        email = ",".split(model.email)
    else:
        email = model.email

    try:
        for address in email:
            if (
                not (
                    isinstance(address, str)
                    and (address == '' or re.match(
                        r'[^@]+@[^@]+\.[^@]+',
                        address,
                    ))
                )
            ):
                raise TypeError
        return True
    except TypeError:
        return model.FIELD_TYPES.email


def validate_pinning_formats(model: ScanningModel):
    if is_pinning_formats(model.pinning_formats):
        return True
    return model.FIELD_TYPES.pinning_formats


def validate_fixture(model: ScanningModel):
    if model.fixture in fixtures.Fixtures() or not model.fixture:
        return True
    return model.FIELD_TYPES.fixture


def validate_scanner(model: ScanningModel):
    if app_config.Config().get_scanner_name(model.scanner) is not None:
        return True

    return model.FIELD_TYPES.scanner


def validate_plate_descriptions(model: ScanningModel):
    if not isinstance(
        model.plate_descriptions,
        ScanningModelFactory.STORE_SECTION_SERIALIZERS[
            "plate_descriptions"
        ][0]
    ):
        return model.FIELD_TYPES.plate_descriptions

    for plate_description in model.plate_descriptions:
        if (
            not isinstance(
                plate_description,
                ScanningModelFactory.STORE_SECTION_SERIALIZERS[
                    "plate_descriptions"
                ][1],
            )
        ):
            return model.FIELD_TYPES.plate_descriptions

    if (
        len(set(
            plate_description.name
            for plate_description in model.plate_descriptions
        )) != len(model.plate_descriptions)
    ):
        return model.FIELD_TYPES.plate_descriptions
    return True


def validate_cell_count_calibration_id(model: ScanningModel):
    if model.cell_count_calibration_id in get_active_cccs():
        return True
    return model.FIELD_TYPES.cell_count_calibration
