import os
import uuid
from collections.abc import Sequence
from configparser import ConfigParser, NoOptionError, NoSectionError
from typing import Any, Literal, Optional, Type, Union

import scanomatic.models.scanning_model as scanning_model
from scanomatic.generics.abstract_model_factory import AbstractModelFactory
from scanomatic.generics.model import Model
from scanomatic.generics.singleton import SingeltonOneInit
from scanomatic.io.jsonizer import copy, dump, load_first
from scanomatic.io.logger import get_logger
from scanomatic.models.factories.settings_factories import (
    ApplicationSettingsFactory
)
from scanomatic.models.settings_models import (
    ApplicationSettingsModel,
    HardwareResourceLimitsModel,
    MailModel,
    PathsModel,
    PowerManagerModel,
    RPCServerModel,
    UIServerModel,
)

from . import paths, power_manager

MinMaxModelSettings = dict[
    Type[Model],
    dict[Literal['min', 'max'], dict[str, Any]]
]


class Config(SingeltonOneInit):
    SCANNER_PATTERN = "Scanner {0}"
    POWER_DEFAULT = power_manager.POWER_MODES.Toggle

    def __one_init__(self):
        self._paths = paths.Paths()
        self._logger = get_logger("Application Config")
        # TODO: Extend functionality to toggle to remote connect
        self._use_local_rpc_settings = True
        self._minMaxModels: MinMaxModelSettings = {
            scanning_model.ScanningModel: {
                "min": {
                    "time_between_scans": 7.0,
                    "number_of_scans": 1,
                    "project_name": None,
                    "directory_containing_project": None,
                    "description": None,
                    "email": None,
                    "pinning_formats": None,
                    "fixture": None,
                    "scanner": 1,
                },
                "max": {
                    "time_between_scans": None,
                    "number_of_scans": 999999,
                    "project_name": None,
                    "directory_containing_project": None,
                    "description": None,
                    "email": None,
                    "pinning_formats": None,
                    "fixture": None,
                    "scanner": 1,
                },
            }
        }
        self.reload_settings()

    @staticmethod
    def _safe_get(conf_parser, section, key, default, type):
        try:
            return type(conf_parser.get(section, key))
        except (NoOptionError, NoSectionError):
            return default

    @property
    def power_manager(self) -> PowerManagerModel:
        return self._settings.power_manager

    @property
    def rpc_server(self) -> RPCServerModel:
        return self._settings.rpc_server

    @property
    def ui_server(self) -> UIServerModel:
        return self._settings.ui_server

    @property
    def hardware_resource_limits(self) -> HardwareResourceLimitsModel:
        return self._settings.hardware_resource_limits

    @property
    def mail(self) -> MailModel:
        return self._settings.mail

    @property
    def paths(self) -> PathsModel:
        return self._settings.paths

    @property
    def computer_human_name(self) -> str:
        return self._settings.computer_human_name

    @computer_human_name.setter
    def computer_human_name(self, value: str):
        self._settings.computer_human_name = str(value)

    @property
    def number_of_scanners(self) -> int:
        return self._settings.number_of_scanners

    @number_of_scanners.setter
    def number_of_scanners(self, value: Any) -> None:
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                pass
        if isinstance(value, int) and value >= 0:
            self._settings.number_of_scanners = value
            if len(self._settings.scanner_names) != value:
                self._settings.scanner_names = [
                    self.scanner_name_pattern.format(i + 1)
                    for i in range(value)
                ]
        else:
            self._logger.warning(
                "Refused to set number of scanners '{0}', only 0 or positive ints allowed".format(  # noqa: E501
                    value,
                ),
            )

    @property
    def scanner_name_pattern(self) -> str:
        return self._settings.scanner_name_pattern

    @scanner_name_pattern.setter
    def scanner_name_pattern(self, value: str) -> None:
        self._settings.scanner_name_pattern = str(value)

    @property
    def scanner_names(self) -> Sequence[str]:
        return self._settings.scanner_names

    @property
    def scan_program(self) -> str:
        return self._settings.scan_program

    @property
    def scan_program_version_flag(self) -> str:
        return self._settings.scan_program_version_flag

    @property
    def scanner_models(self) -> dict[str, str]:
        return self._settings.scanner_models

    @property
    def scanner_sockets(self) -> dict[str, int]:
        return self._settings.scanner_sockets

    @property
    def application_settings(self) -> Optional[ApplicationSettingsModel]:
        return self._settings

    def model_copy(self) -> ApplicationSettingsModel:
        return copy(self._settings)

    def get_scanner_name(self, scanner: Union[int, str]) -> Optional[str]:
        if isinstance(scanner, int) and 0 < scanner <= self.number_of_scanners:
            scanner = self.SCANNER_PATTERN.format(scanner)

        for s in self.scanner_names:
            if s == scanner:
                return str(scanner)
        return None

    def reload_settings(self) -> None:
        if os.path.isfile(self._paths.config_main_app):
            self._settings = load_first(self._paths.config_main_app)
            if self._settings is None:
                self._settings = ApplicationSettingsFactory.create()
        else:
            self._settings = ApplicationSettingsFactory.create()

        if not self._settings:
            self._logger.info(
                "We'll use default settings for now.",
            )
            self._settings = ApplicationSettingsFactory.create()

        if self._use_local_rpc_settings:
            self.apply_local_rpc_settings()

        self._PM = power_manager.get_pm_class(
            self._settings.power_manager.type,
        )

    def apply_local_rpc_settings(self) -> None:
        rpc_conf = ConfigParser(allow_no_value=True)
        if not rpc_conf.read(self._paths.config_rpc):
            self._logger.warning(
                "Could not read from '{0}',".format(self._paths.config_rpc) +
                "though local settings were indicated to exist")

        self._settings.rpc_server.host = Config._safe_get(
            rpc_conf,
            "Communication",
            "host",
            '127.0.0.1',
            str,
        )
        self._settings.rpc_server.port = Config._safe_get(
            rpc_conf,
            "Communication",
            "port",
            12451,
            int,
        )

        try:
            self._settings.rpc_server.admin = open(
                self._paths.config_rpc_admin,
                'r',
            ).read().strip()
        except IOError:
            self._settings.rpc_server.admin = self._generate_admin_uuid()
        else:
            if not self._settings.rpc_server.admin:
                self._settings.rpc_server = self._generate_admin_uuid()

    def _generate_admin_uuid(self) -> Optional[str]:
        val = str(uuid.uuid1())
        try:
            with open(self._paths.config_rpc_admin, 'w') as fh:
                fh.write(val)
                self._logger.info("New admin user identifier generated")
        except IOError:
            self._logger.critical(
                f"Could not write to file '{self._paths.config_rpc_admin}'"
                ", you won't be able to perform any actions on Scan-o-Matic"
                " until fixed."
                " If you are really lucky, it works if rebooted, "
                "but it seems your installation is corrupt."
            )
            return None

        return val

    def save_current_settings(self) -> None:
        """Settings should be validated beforehand."""
        dump(
            self.application_settings,
            self._paths.config_main_app,
            merge=True,
        )

    def get_scanner_socket(self, scanner: Union[int, str]) -> Optional[int]:
        scanner_name = self.get_scanner_name(scanner)
        if scanner_name:
            return self.scanner_sockets[scanner_name]
        return None

    def get_pm(self, socket: Optional[int]):
        if socket is None or socket < 1 or socket > 4:
            self._logger.error("Socket '{0}' is unknown, {1} known".format(
                socket,
                f"sockets 1-{self.power_manager.number_of_sockets}" if
                self.power_manager.number_of_sockets else "no sockets"
            ))
            return power_manager.PowerManagerNull(0)

        self._logger.info(
            "Creating scanner PM for socket {0} and settings {1}".format(
                socket,
                dict(**self.power_manager),
            ),
        )
        return self._PM(socket, **self.power_manager)

    def get_min_model(self, model: Model, factory: Type[AbstractModelFactory]):
        return factory.create(**self._minMaxModels[type(model)]['min'])

    def get_max_model(self, model: Model, factory: Type[AbstractModelFactory]):
        return factory.create(**self._minMaxModels[type(model)]['max'])
