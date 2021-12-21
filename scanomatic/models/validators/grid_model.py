from enum import Enum
from typing import Literal, Union

from scanomatic.models.analysis_model import GridModel

ValidationResult = Union[Literal[True], Enum]


def validate_use_utso(model: GridModel) -> ValidationResult:
    if isinstance(model.use_utso, bool):
        return True
    return model.FIELD_TYPES.use_otsu


def validate_median_coefficient(model: GridModel) -> ValidationResult:
    if isinstance(model.median_coefficient, float):
        return True
    return model.FIELD_TYPES.median_coefficient


def validate_manual_threshold(model: GridModel) -> ValidationResult:
    if isinstance(model.manual_threshold, float):
        return True
    return model.FIELD_TYPES.manual_threshold


def validate_grid_offsets(model: GridModel) -> ValidationResult:
    def _valid_correction(value) -> bool:
        return (
            value is None or
            value is False or (
                len(value) == 2
                and all(isinstance(offset, int) for offset in value)
            )
        )

    if model.gridding_offsets is None:
        return True

    try:
        if all(
            _valid_correction(plate) for plate in model.gridding_offsets
        ):
            return True
    except (TypeError, IndexError):
        pass

    return model.FIELD_TYPES.gridding_offsets
