from scanomatic.models.scanning_model import (
    CULTURE_SOURCE,
    PLATE_STORAGE,
    ScanningAuxInfoModel
)
from scanomatic.models.validators.tools import (
    is_int_positive_or_neg_one,
    is_numeric_positive_or_neg_one
)


def validate_stress_level(model: ScanningAuxInfoModel):
    if not isinstance(model.stress_level, int):
        return model.FIELD_TYPES.stress_level
    elif model.stress_level == -1 or model.stress_level > 0:
        return True
    else:
        return model.FIELD_TYPES.stress_level


def validate_plate_storage(model: ScanningAuxInfoModel):
    if isinstance(model.plate_storage, PLATE_STORAGE):
        return True
    return model.FIELD_TYPES.plate_storage


def validate_plate_age(model: ScanningAuxInfoModel):
    if is_numeric_positive_or_neg_one(model.plate_age):
        return True
    else:
        return model.FIELD_TYPES.plate_age


def validate_pinnig_proj_start_delay(model: ScanningAuxInfoModel):
    if is_numeric_positive_or_neg_one(model.pinning_project_start_delay):
        return True
    else:
        return model.FIELD_TYPES.pinning_project_start_delay


def validate_precultures(model: ScanningAuxInfoModel):
    if is_int_positive_or_neg_one(model.precultures, allow_zero=True):
        return True
    else:
        return model.FIELD_TYPES.precultures


def validate_culture_freshness(model: ScanningAuxInfoModel):
    if is_int_positive_or_neg_one(model.culture_freshness):
        return True
    else:
        return model.FIELD_TYPES.culture_freshness


def validate_culture_source(model: ScanningAuxInfoModel):
    if isinstance(model.culture_source, CULTURE_SOURCE):
        return True
    else:
        return model.FIELD_TYPES.culture_source
