from typing import Literal, Union
from scanomatic.models.scanning_model import (
    CULTURE_SOURCE,
    PLATE_STORAGE,
    ScanningAuxInfoModel,
    ScanningAuxInfoModelFields
)
from scanomatic.models.validators.tools import (
    is_int_positive_or_neg_one,
    is_numeric_positive_or_neg_one
)


ValidationResult = Union[Literal[True], ScanningAuxInfoModelFields]


def validate_stress_level(model: ScanningAuxInfoModel) -> ValidationResult:
    if not isinstance(model.stress_level, int):
        return ScanningAuxInfoModelFields.stress_level
    elif is_int_positive_or_neg_one(model.stress_level):
        return True
    else:
        return ScanningAuxInfoModelFields.stress_level


def validate_plate_storage(model: ScanningAuxInfoModel) -> ValidationResult:
    if isinstance(model.plate_storage, PLATE_STORAGE):
        return True
    return ScanningAuxInfoModelFields.plate_storage


def validate_plate_age(model: ScanningAuxInfoModel) -> ValidationResult:
    if is_numeric_positive_or_neg_one(model.plate_age):
        return True
    else:
        return ScanningAuxInfoModelFields.plate_age


def validate_pinnig_proj_start_delay(
    model: ScanningAuxInfoModel,
) -> ValidationResult:
    if is_numeric_positive_or_neg_one(model.pinning_project_start_delay):
        return True
    else:
        return ScanningAuxInfoModelFields.pinning_project_start_delay


def validate_precultures(model: ScanningAuxInfoModel) -> ValidationResult:
    if is_int_positive_or_neg_one(model.precultures, allow_zero=True):
        return True
    else:
        return ScanningAuxInfoModelFields.precultures


def validate_culture_freshness(model: ScanningAuxInfoModel) -> ValidationResult:
    if is_int_positive_or_neg_one(model.culture_freshness):
        return True
    else:
        return ScanningAuxInfoModelFields.culture_freshness


def validate_culture_source(model: ScanningAuxInfoModel) -> ValidationResult:
    if isinstance(model.culture_source, CULTURE_SOURCE):
        return True
    else:
        return ScanningAuxInfoModelFields.culture_source
