from typing import Literal, Union

from scanomatic.models.scanning_model import (
    PlateDescription,
    PlateDescriptionFields,
)

ValidationResult = Union[Literal[True], PlateDescriptionFields]


def validate_index(model: PlateDescription) -> ValidationResult:
    if not isinstance(model.index, int):
        return PlateDescriptionFields.index
    elif model.index >= 0:
        return True
    else:
        return PlateDescriptionFields.index


def validate_name(model: PlateDescription) -> ValidationResult:
    if isinstance(model.name, str):
        return True
    return PlateDescriptionFields._name


def validate_description(model: PlateDescription) -> ValidationResult:
    if isinstance(model.description, str):
        return True
    return PlateDescriptionFields.description
