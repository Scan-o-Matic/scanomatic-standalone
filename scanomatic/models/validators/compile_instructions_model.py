import os
from typing import Literal, Union

from scanomatic.data_processing.calibration import get_active_cccs
from scanomatic.io.fixtures import Fixtures
from scanomatic.io.paths import Paths
from scanomatic.models.compile_project_model import (
    FIXTURE,
    CompileInstructionsModel,
    CompileInstructionsModelFields,
)

ValidationResult = Union[Literal[True], CompileInstructionsModelFields]


def validate_images(
    model: CompileInstructionsModel,
) -> ValidationResult:
    if model.images:
        return True
    else:
        return CompileInstructionsModelFields.images


def validate_path(
    model: CompileInstructionsModel,
) -> ValidationResult:
    basename = os.path.basename(model.path)
    dirname = os.path.dirname(model.path)
    if (
        model.path != dirname
        and os.path.isdir(dirname)
        and os.path.abspath(dirname) == dirname
        and basename
    ):
        return True
    return CompileInstructionsModelFields.path


def validate_fixture(model: CompileInstructionsModel) -> ValidationResult:
    if model.fixture_type is FIXTURE.Local:
        if os.path.isfile(
            os.path.join(
                model.path,
                Paths().experiment_local_fixturename,
            ),
        ):
            return True
        else:
            return CompileInstructionsModelFields.fixture_type
    elif model.fixture_type is FIXTURE.Global:
        if model.fixture_name in Fixtures():
            return True
        else:
            return CompileInstructionsModelFields.fixture_name
    else:
        return CompileInstructionsModel.fixture_type


def validate_cell_count_calibration_id(
    model: CompileInstructionsModel,
) -> ValidationResult:
    if model.cell_count_calibration_id in get_active_cccs():
        return True
    return CompileInstructionsModelFields.cell_count_calibration_id
