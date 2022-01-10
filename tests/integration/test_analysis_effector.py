from collections import namedtuple

import numpy
import pytest

from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.models.validators.validate import validate
from scanomatic.server.analysis_effector import AnalysisEffector


@pytest.fixture(scope='session')
def proj1(pytestconfig):
    return pytestconfig.rootdir.join('tests/integration/fixtures/proj1')


ProjInfo = namedtuple('ProjInfo', ['job', 'workdir'])


@pytest.fixture
def proj1_analysis(proj1, tmpdir):
    workdir = tmpdir.mkdir('proj1')
    files = [
        'fixture.config',
        'proj1.project.compilation',
        'proj1.project.compilation.instructions',
        'proj1.scan.instructions',
        'proj1_0215_258418.2895.tiff',
    ]
    for filename in files:
        proj1.join(filename).copy(workdir)

    analysis_model = AnalysisModelFactory.create(
        compilation=str(workdir.join('proj1.project.compilation')),
        compile_instructions=str(workdir.join('proj1.project.compilation.instructions')),
        chain=False,
    )
    assert validate(analysis_model)
    job = RPC_Job_Model_Factory.create(id='135', content_model=analysis_model)
    assert validate(job)
    return ProjInfo(job, workdir)


def test_number_of_images(proj1_analysis: ProjInfo):
    analysis_effector = AnalysisEffector(proj1_analysis.job)
    analysis_effector.setup(proj1_analysis.job)
    assert analysis_effector.current_image_index == -1
    assert analysis_effector.total == -1
    assert analysis_effector.progress == 0
    assert analysis_effector.ready_to_start


def test_colony_sizes(proj1, proj1_analysis: ProjInfo):
    analysis_effector = AnalysisEffector(proj1_analysis.job)
    analysis_effector.setup(proj1_analysis.job)
    for _ in analysis_effector:
        pass

    expected = numpy.load(str(proj1.join('analysis/image_0_data.npy')))
    actual = numpy.load(
        str(proj1_analysis.workdir.join('analysis/image_0_data.npy')))
    numpy.testing.assert_allclose(expected, actual, rtol=.01)


def test_grid_plate(proj1, proj1_analysis: ProjInfo):
    analysis_effector = AnalysisEffector(proj1_analysis.job)
    analysis_effector.setup(proj1_analysis.job)
    for _ in analysis_effector:
        pass

    expected = numpy.load(str(proj1.join('analysis/grid_plate___1.npy')))
    actual = numpy.load(
        str(proj1_analysis.workdir.join('analysis/grid_plate___1.npy')),
    )
    numpy.testing.assert_allclose(expected, actual, atol=3)


def test_grid_size(proj1, proj1_analysis: ProjInfo):
    analysis_effector = AnalysisEffector(proj1_analysis.job)
    analysis_effector.setup(proj1_analysis.job)
    for _ in analysis_effector:
        pass

    expected = numpy.load(str(proj1.join('analysis/grid_size___1.npy')))
    actual = numpy.load(
        str(proj1_analysis.workdir.join('analysis/grid_size___1.npy')),
    )
    assert (expected == actual).all()
