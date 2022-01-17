from typing import Any, cast

import scanomatic.models.settings_models as settings_models
from scanomatic.generics.abstract_model_factory import (
    AbstractModelFactory,
    SubFactoryDict,
)
from scanomatic.io.power_manager import POWER_MANAGER_TYPE, POWER_MODES


class VersionChangeFactory(AbstractModelFactory):
    MODEL = settings_models.VersionChangesModel
    STORE_SECTION_SERIALIZERS: dict[str, Any] = {}

    @classmethod
    def create(cls, **settings) -> settings_models.VersionChangesModel:
        return cast(
            settings_models.VersionChangesModel,
            super(VersionChangeFactory, cls).create(),
        )


class PowerManagerFactory(AbstractModelFactory):
    MODEL = settings_models.PowerManagerModel
    STORE_SECTION_SERIALIZERS = {
        "type": POWER_MANAGER_TYPE,
        "number_of_sockets": int,
        "host": str,
        "password": str,
        "name": str,
        "verify_name": bool,
        "mac": str,
        "power_mode": POWER_MODES
    }

    @classmethod
    def create(cls, **settings) -> settings_models.PowerManagerModel:
        return cast(
            settings_models.PowerManagerModel,
            super(PowerManagerFactory, cls).create(**settings),
        )


class RPCServerFactory(AbstractModelFactory):
    MODEL = settings_models.RPCServerModel
    STORE_SECTION_SERIALIZERS = {
        "port": int,
        "host": str,
        "admin": bool,
    }

    @classmethod
    def create(cls, **settings) -> settings_models.RPCServerModel:
        return cast(
            settings_models.RPCServerModel,
            super(RPCServerFactory, cls).create(**settings),
        )


class UIServerFactory(AbstractModelFactory):
    MODEL = settings_models.UIServerModel
    STORE_SECTION_SERIALIZERS = {
        "port": int,
        "host": str,
        "master_key": str,
    }

    @classmethod
    def create(cls, **settings) -> settings_models.UIServerModel:
        return cast(
            settings_models.UIServerModel,
            super(UIServerFactory, cls).create(**settings),
        )


class HardwareResourceLimitsFactory(AbstractModelFactory):
    MODEL = settings_models.HardwareResourceLimitsModel
    STORE_SECTION_SERIALIZERS = {
        "memory_minimum_percent": float,
        "cpu_total_percent_free": float,
        "cpu_single_free": float,
        "cpu_free_count": int,
        "checks_pass_needed": int
    }

    @classmethod
    def create(cls, **settings) -> settings_models.HardwareResourceLimitsModel:
        return cast(
            settings_models.HardwareResourceLimitsModel,
            super(HardwareResourceLimitsFactory, cls).create(**settings),
        )


class MailFactory(AbstractModelFactory):
    MODEL = settings_models.MailModel
    STORE_SECTION_SERIALIZERS = {
        "server": str,
        "user": str,
        "port": int,
        "password": str,
        "warn_scanning_done_minutes_before": float
    }

    @classmethod
    def create(cls, **settings) -> settings_models.MailModel:
        return cast(
            settings_models.MailModel,
            super(MailFactory, cls).create(**settings),
        )


class PathsFactory(AbstractModelFactory):
    MODEL = settings_models.PathsModel
    STORE_SECTION_SERIALIZERS = {
        "projects_root": str,
    }

    @classmethod
    def create(cls, **settings) -> settings_models.PathsModel:
        return cast(
            settings_models.PathsModel,
            super(PathsFactory, cls).create(**settings),
        )


def _scanner_model_serializer(enforce=None, serialize=None):
    return (
        (
            [serialize[name] for name in sorted(serialize.keys())]
            if isinstance(serialize, dict) else None
        )
        if serialize is not None else
        (
            enforce if not isinstance(enforce, tuple) else list(enforce)
        )
    )


class ApplicationSettingsFactory(AbstractModelFactory):
    MODEL = settings_models.ApplicationSettingsModel
    _SUB_FACTORIES: SubFactoryDict = {
        settings_models.PathsModel: PathsFactory,
        settings_models.HardwareResourceLimitsModel:
            HardwareResourceLimitsFactory,
        settings_models.PowerManagerModel: PowerManagerFactory,
        settings_models.RPCServerModel: RPCServerFactory,
        settings_models.UIServerModel: UIServerFactory,
        settings_models.MailModel: MailFactory,
    }

    STORE_SECTION_SERIALIZERS = {
        "power_manager": settings_models.PowerManagerModel,
        "rpc_server": settings_models.RPCServerModel,
        "ui_server": settings_models.UIServerModel,
        "hardware_resource_limits":
            settings_models.HardwareResourceLimitsModel,
        "mail": settings_models.MailModel,
        "paths": settings_models.PathsModel,
        "number_of_scanners": int,
        "scanner_name_pattern": str,
        "scan_program": str,
        "scan_program_version_flag": str,
        "computer_human_name": str,
        "scanner_models": _scanner_model_serializer
    }

    @classmethod
    def create(cls, **settings) -> settings_models.ApplicationSettingsModel:
        if 'versions' in settings:
            del settings['versions']
        return cast(
            settings_models.ApplicationSettingsModel,
            super(ApplicationSettingsFactory, cls).create(**settings),
        )
