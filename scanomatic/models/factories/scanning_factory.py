from typing import cast
from scanomatic.generics.abstract_model_factory import (
    AbstractModelFactory,
    email_serializer
)
from scanomatic.models.rpc_job_models import RPCjobModel
from scanomatic.models.scanning_model import (
    CULTURE_SOURCE,
    PLATE_STORAGE,
    PlateDescription,
    ScannerModel,
    ScannerOwnerModel,
    ScanningAuxInfoModel,
    ScanningModel
)


class PlateDescriptionFactory(AbstractModelFactory):
    MODEL = PlateDescription
    STORE_SECTION_SERIALIZERS = {
        'name': str,
        'index': int,
        'description': str
    }

    @classmethod
    def create(cls, **settings) -> PlateDescription:
        return super(cls, PlateDescriptionFactory).create(**settings)


class ScanningAuxInfoFactory(AbstractModelFactory):
    MODEL = ScanningAuxInfoModel
    STORE_SECTION_SERIALIZERS = {
        'stress_level': int,
        'plate_storage': PLATE_STORAGE,
        'plate_age': float,
        'pinning_project_start_delay': float,
        'precultures': int,
        'culture_freshness': int,
        'culture_source': CULTURE_SOURCE
    }

    @classmethod
    def create(cls, **settings) -> ScanningAuxInfoModel:
        return super(cls, ScanningAuxInfoFactory).create(**settings)


class ScanningModelFactory(AbstractModelFactory):
    MODEL = ScanningModel
    _SUB_FACTORIES = {
        ScanningAuxInfoModel: ScanningAuxInfoFactory,
        PlateDescription: PlateDescriptionFactory
    }

    STORE_SECTION_SERIALIZERS = {
        'start_time': float,
        'number_of_scans': int,
        'time_between_scans': float,
        'project_name': str,
        'directory_containing_project': str,
        'description': str,
        'plate_descriptions': (tuple, PlateDescription),
        'email': email_serializer,
        'pinning_formats': (tuple, tuple, int),
        'fixture': str,
        'scanner': int,
        'scanner_hardware': str,
        'mode': str,
        'computer': str,
        'version': str,
        'id': str,
        'cell_count_calibration_id': str,
        'auxillary_info': ScanningAuxInfoModel,
        'scanning_program': str,
        'scanning_program_version': str,
        'scanning_program_params': (tuple, str)
    }

    @classmethod
    def create(cls, **settings) -> ScanningModel:
        if not settings.get('cell_count_calibration_id', None):
            settings['cell_count_calibration_id'] = 'default'
        return super(cls, ScanningModelFactory).create(**settings)


class ScannerOwnerFactory(AbstractModelFactory):
    MODEL = ScannerOwnerModel
    STORE_SECTION_SERIALIZERS = {
        "id": str,
        "pid": int
    }

    @classmethod
    def create(cls, **settings) -> ScannerOwnerModel:
        return cast(
            ScannerOwnerModel,
            super(ScannerOwnerFactory, cls).create(**settings),
        )


class ScannerFactory(AbstractModelFactory):
    MODEL = ScannerModel
    _SUB_FACTORIES = {
        ScannerOwnerModel: ScannerOwnerFactory,
        RPCjobModel: ScannerOwnerFactory
    }
    STORE_SECTION_SERIALIZERS = {
        'socket': int,
        'scanner_name': str,
        'usb': str,
        'power': bool,
        "expected_interval": float,
        "email": email_serializer,
        "warned": bool,
        "owner": ScannerOwnerModel,
        "claiming": bool,
        "power": bool,
        "reported": bool,
        "last_on": int,
        "last_off": int,
    }

    @classmethod
    def create(cls, **settings) -> ScannerModel:
        return cast(
            ScannerModel,
            super(ScannerFactory, cls).create(**settings),
        )
