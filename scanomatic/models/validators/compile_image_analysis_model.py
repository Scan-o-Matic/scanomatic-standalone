from scanomatic.models.compile_project_model import CompileImageAnalysisModel


def validate_fixture(
    model: CompileImageAnalysisModel,
):
    if model.fixture is not None:
        return True
    else:
        return model.FIELD_TYPES.fixture


def validate_image(
    model: CompileImageAnalysisModel,
):
    if model.image is not None:
        return True
    else:
        return model.FIELD_TYPES.image
