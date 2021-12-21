import os

from scanomatic.data_processing.calibration import get_active_cccs
from scanomatic.models.analysis_model import AnalysisModel
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.validators.tools import (
    is_coordinates,
    is_file,
    is_pinning_formats,
    is_real_number,
    is_safe_path,
    is_tuple_or_list
)


def validate_compilation_file(model: AnalysisModel):
    if (
        is_file(model.compilation)
        and os.path.abspath(model.compilation) == model.compilation
    ):
        return True
    return model.FIELD_TYPES.compilation


def validate_compilation_instructions_file(
    model: AnalysisModel,
):
    if (
        model.compile_instructions in (None, "")
        or is_file(model.compile_instructions)
    ):
        return True
    return model.FIELD_TYPES.compile_instructions


def validate_pinning_matrices(model: AnalysisModel):
    if is_pinning_formats(model.pinning_matrices):
        return True
    return model.FIELD_TYPES.pinning_matrices


def validate_use_local_fixture(model: AnalysisModel):
    if isinstance(model.use_local_fixture, bool):
        return True
    return model.FIELD_TYPES.use_local_fixture


def validate_stop_at_image(model: AnalysisModel):
    if isinstance(model.stop_at_image, int):
        return True
    return model.FIELD_TYPES.stop_at_image


def validate_output_directory(model: AnalysisModel):
    if is_safe_path(model.output_directory):
        return True
    return model.FIELD_TYPES.output_directory


def validate_focus_position(model: AnalysisModel):
    if model.focus_position is None:
        return True

    if (
        is_coordinates(model.focus_position)
        and validate_pinning_matrices(model) is True
    ):
        plate_exists = (
            0 <= model.focus_position[0] < len(model.pinning_matrices)
            and model.pinning_matrices[model.focus_position[0]] is not None
        )

        if (
            plate_exists and all(
                0 <= val < dim_max
                for val, dim_max in zip(
                    model.focus_position[1:],
                    model.pinning_matrices[model.focus_position[0]],
                )
            )
        ):
            return True
    return model.FIELD_TYPES.focus_position


def validate_suppress_non_focal(model: AnalysisModel):
    if isinstance(model.suppress_non_focal, bool):
        return True
    return model.FIELD_TYPES.suppress_non_focal


def validate_animate_focal(model: AnalysisModel):
    if isinstance(model.animate_focal, bool):
        return True
    return model.FIELD_TYPES.animate_focal


def validate_grid_images(model: AnalysisModel):
    if (
        model.grid_images is None
        or (
            is_tuple_or_list(model.grid_images)
            and all(
                isinstance(val, int) and 0 <= val for val in
                model.grid_images
            )
        )
    ):
        return True
    return model.FIELD_TYPES.grid_images


def validate_grid_model(model: AnalysisModel):
    if AnalysisModelFactory.is_valid_submodel(model, "grid_model"):
        return True
    return model.FIELD_TYPES.grid_model


def validate_cell_count_calibration_id(
    model: AnalysisModel,
):
    if model.cell_count_calibration_id in get_active_cccs():
        return True
    return model.FIELD_TYPES.cell_count_calibration_id


def validate_cell_count_calibration(
    model: AnalysisModel,
):
    if (
        is_tuple_or_list(model.cell_count_calibration)
        and all(
            is_real_number(c) and c >= 0
            for c in model.cell_count_calibration
        )
    ):
        return True
    return model.FIELD_TYPES.cell_count_calibration
