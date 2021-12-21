from scanomatic.models.compile_project_model import CompileImageAnalysisModel


def validate_fixture(
    model: CompileImageAnalysisModel,
):
    if CompileImageAnalysisModel.is_valid_submodel(model, "fixture"):
        return True
    else:
        return model.FIELD_TYPES.fixture


def validate_image(
    model: CompileImageAnalysisModel,
):
    if CompileImageAnalysisModel.is_valid_submodel(model, "image"):
        return True
    else:
        return model.FIELD_TYPES.image
