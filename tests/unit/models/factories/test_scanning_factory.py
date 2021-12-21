import pytest

from scanomatic.models.factories.scanning_factory import ScanningModelFactory
from scanomatic.models.validators import (
    scanning_model as scanning_model_validators,
)
from scanomatic.models.validators.validate import validate


@pytest.fixture(scope='function')
def scanning_model():
    return ScanningModelFactory.create()


class TestCreatingScanningModel:
    def test_creating_valid_minimal_model(self):
        model = ScanningModelFactory.create(project_name='Test')
        assert validate(model, ScanningModelFactory, scanning_model_validators)
        assert model.project_name == 'Test'

    def test_create_valid_minimal_model_with_deprecated_fields(self):
        model = ScanningModelFactory.create(
            project_name='Tests',
            scanner_tag='are',
            project_tag='annoying',
        )

        assert validate(model, ScanningModelFactory, scanning_model_validators)
        with pytest.raises(AttributeError):
            model.scanner_tag
        with pytest.raises(AttributeError):
            model.project_tag

    def test_model_without_project_name_doesnt_validate(self):
        model = ScanningModelFactory.create()
        assert validate(
            model,
            ScanningModelFactory,
            scanning_model_validators,
        ) is False

    def test_model_has_ccc_id(self, scanning_model):
        assert hasattr(scanning_model, 'cell_count_calibration_id')

    def test_can_create_using_default_ccc(self, scanning_model):
        assert scanning_model.cell_count_calibration_id == 'default'

    def test_can_create_using_ccc_id(self):
        model = ScanningModelFactory.create(cell_count_calibration_id='foo')
        assert model.cell_count_calibration_id == 'foo'
