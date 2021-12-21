from scanomatic.models.scanning_model import PlateDescription


def validate_index(model: PlateDescription):
    if not isinstance(model.index, int):
        return model.FIELD_TYPES.index
    elif model.index >= 0:
        return True
    else:
        return model.FIELD_TYPES.index


def validate_name(model: PlateDescription):
    if isinstance(model.name, str):
        return True
    return model.FIELD_TYPES.name


def validate_description(model: PlateDescription):
    if isinstance(model.description, str):
        return True
    return model.FIELD_TYPES.description
