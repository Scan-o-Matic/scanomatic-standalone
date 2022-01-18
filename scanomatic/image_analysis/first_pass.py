from typing import Any
from scanomatic.image_analysis.first_pass_image import FixtureImage
from scanomatic.io.fixtures import FixtureSettings
from scanomatic.io.logger import get_logger
from scanomatic.models.compile_project_model import (
    CompileImageAnalysisModel,
    CompileImageModel
)
from scanomatic.models.factories.compile_project_factory import (
    CompileImageAnalysisFactory
)
from scanomatic.models.factories.fixture_factories import FixtureFactory

_logger = get_logger("1st Pass Analysis")


class MarkerDetectionFailed(Exception):
    pass


def analyse(
    compile_image_model: CompileImageModel,
    fixture_settings: FixtureSettings,
    issues: dict[str, Any],
) -> CompileImageAnalysisModel:
    compile_analysis_model = CompileImageAnalysisFactory.create(
        image=compile_image_model,
        fixture=FixtureFactory.copy(fixture_settings.model),
    )

    fixture_image = FixtureImage(fixture=fixture_settings)

    _do_image_preparation(compile_analysis_model, fixture_image)

    _do_markers(compile_analysis_model, fixture_image)

    _logger.info("Setting current fixture_image areas for {0}".format(
        compile_image_model,
    ))

    fixture_image.set_current_areas(issues)

    _do_grayscale(compile_analysis_model, fixture_image)

    _logger.info("First pass analysis done for {0}".format(
        compile_analysis_model,
    ))
    return compile_analysis_model


def _do_image_preparation(
    compile_analysis_model: CompileImageAnalysisModel,
    image: FixtureImage
) -> None:
    image['current'].model = compile_analysis_model.fixture
    image.set_image(image_path=compile_analysis_model.image.path)


def _do_markers(
    compile_analysis_model: CompileImageAnalysisModel,
    image: FixtureImage,
) -> None:
    _logger.info(f"Running marker analysis on {compile_analysis_model}")
    image.run_marker_analysis()

    _logger.info("Marker analysis run")
    if compile_analysis_model.fixture.orientation_marks_x is None:
        raise MarkerDetectionFailed()


def _do_grayscale(
    compile_analysis_model: CompileImageAnalysisModel,
    image: FixtureImage,
) -> None:
    image.analyse_grayscale()

    _logger.info("Grayscale analysed for {0}".format(compile_analysis_model))

    if compile_analysis_model.fixture.grayscale.section_values is None:
        _logger.error(
            "Grayscale not properly set up (used {0})".format(
                compile_analysis_model.fixture.grayscale.name,
            ),
        )
