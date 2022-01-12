from enum import Enum, auto
from typing import Optional, Union
from collections.abc import Sequence
from uuid import uuid1

import scanomatic.generics.model as model
from scanomatic.io.power_manager import POWER_MANAGER_TYPE, POWER_MODES


class VersionChangesModelFields(Enum):
    first_pass_change_1 = auto()
    oldest_allow_fixture = auto()


class VersionChangesModel(model.Model):
    def __init__(self, **kwargs):
        self.first_pass_change_1: float = 0.997
        self.oldest_allow_fixture: float = 0.9991
        super().__init__()


class PowerManagerModelFields(Enum):
    type = auto()
    number_of_sockets = auto()
    host = auto()
    password = auto()
    _name = auto()
    verify_name = auto()
    mac = auto()
    power_mode = auto()


class PowerManagerModel(model.Model):
    def __init__(
        self,
        type: POWER_MANAGER_TYPE = POWER_MANAGER_TYPE.LAN,
        number_of_sockets: int = 4,
        host: str = "192.168.0.100",
        password: str = "1",
        verify_name: bool = False,
        mac: Optional[str] = None,
        name: str = "Server 1",
        power_mode: POWER_MODES = POWER_MODES.Toggle,
    ):
        self.type: POWER_MANAGER_TYPE = type
        self.number_of_sockets: int = number_of_sockets
        self.host: str = host
        self.password: str = password
        self.name: str = name
        self.verify_name: bool = verify_name
        self.mac = mac
        self.power_mode: POWER_MODES = power_mode
        super().__init__()


class RPCServerModelFields(Enum):
    port = auto()
    host = auto()
    admin = auto()
    config = auto()


class RPCServerModel(model.Model):
    def __init__(
        self,
        port: Optional[int] = None,
        host: Optional[str] = None,
        admin: Optional[str] = None,
        config=None,
    ):
        self.port = port
        self.host = host
        self.admin = admin
        self.config = config  # Might not be used?
        super().__init__()


class UIServerModelFields(Enum):
    port = auto()
    host = auto()
    master_key = auto()


class UIServerModel(model.Model):
    def __init__(
        self,
        port: int = 5000,
        host: str = "0.0.0.0",
        master_key: Optional[str] = None,
    ):
        self.port: int = port
        self.host: str = host
        self.master_key: str = master_key if master_key else str(uuid1())
        super().__init__()


class HardwareResourceLimitsModelFields(Enum):
    memory_minimum_percent = auto()
    cpu_total_percent_free = auto()
    cpu_single_free = auto()
    cpu_free_count = auto()
    checks_pass_needed = auto()


class HardwareResourceLimitsModel(model.Model):
    def __init__(
        self,
        memory_minimum_percent: float = 30,
        cpu_total_percent_free: float = 30,
        cpu_single_free: float = 75,
        cpu_free_count: int = 1,
        checks_pass_needed: int = 3,
    ):
        self.memory_minimum_percent: float = memory_minimum_percent
        self.cpu_total_percent_free: float = cpu_total_percent_free
        self.cpu_single_free: float = cpu_single_free
        self.cpu_free_count: int = cpu_free_count
        self.checks_pass_needed: int = checks_pass_needed
        super().__init__()


class PathsModelFields(Enum):
    projects_root = auto()


class PathsModel(model.Model):
    def __init__(self, projects_root: str = "/somprojects"):
        self.projects_root: str = projects_root
        super().__init__()


class MailModelFields(Enum):
    server = auto()
    user = auto()
    port = auto()
    password = auto()
    warn_scanning_done_minutes_before = auto()


class MailModel(model.Model):
    def __init__(
        self,
        server: Optional[str] = None,
        user: Optional[str] = None,
        port: int = 0,
        password: Optional[str] = None,
        warn_scanning_done_minutes_before: float = 30,
    ):

        self.server: Optional[str] = server
        self.user: Optional[str] = user
        self.port: int = port
        self.password: Optional[str] = password
        self.warn_scanning_done_minutes_before: float = (
            warn_scanning_done_minutes_before
        )
        super().__init__()


class ApplicationSettingsModelFields(Enum):
    versions = auto()
    power_manager = auto()
    rpc_server = auto()
    ui_server = auto()
    hardware_resource_limits = auto()
    paths = auto()
    computer_human_name = auto()
    mail = auto()
    number_of_scanners = auto()
    scanner_name_pattern = auto()
    scanner_names = auto()
    scan_program = auto()
    scan_program_version_flag = auto()
    scanner_models = auto()
    scanner_sockets = auto()


class ApplicationSettingsModel(model.Model):
    def __init__(
        self,
        number_of_scanners: int = 3,
        scanner_name_pattern: str = "Scanner {0}",
        scan_program: str = "scanimage",
        scan_program_version_flag: str = "-V",
        scanner_models: Union[tuple[str, ...], dict[str, str]] = tuple(),
        power_manager: Optional[PowerManagerModel] = None,
        rpc_server: Optional[RPCServerModel] = None,
        ui_server: Optional[UIServerModel] = None,
        hardware_resource_limits: Optional[HardwareResourceLimitsModel] = (
            None
        ),
        computer_human_name: str = "Unnamed Computer",
        mail: Optional[MailModel] = None,
        paths: Optional[PathsModel] = None,
        scanner_names: Optional[Sequence[str]] = None,
        scanner_sockets: Optional[dict[str, int]] = None,
    ):
        self.versions: VersionChangesModel = VersionChangesModel()
        self.power_manager: Optional[PowerManagerModel] = power_manager
        self.rpc_server: Optional[RPCServerModel] = rpc_server
        self.ui_server: Optional[UIServerModel] = ui_server
        self.hardware_resource_limits: Optional[HardwareResourceLimitsModel] = (  # noqa: E501
            hardware_resource_limits
        )
        self.paths: Optional[PathsModel] = paths
        self.computer_human_name: str = computer_human_name
        self.mail: Optional[MailModel] = mail
        self.number_of_scanners: int = number_of_scanners
        self.scanner_name_pattern: str = scanner_name_pattern

        if scanner_names is not None:
            self.scanner_names = scanner_names
        if power_manager is not None:
            self.scanner_names = [
                self.scanner_name_pattern.format(i + 1) for i
                in range(power_manager.number_of_sockets)
            ]
        else:
            self.scanner_names = []

        self.scan_program: str = scan_program
        self.scan_program_version_flag: str = scan_program_version_flag
        if isinstance(scanner_models, dict):
            self.scanner_models = scanner_models
        else:
            scanner_models += tuple(
                'EPSON V700' for _ in range(
                    len(self.scanner_names) - len(scanner_models)
                )
            )
            self.scanner_models = {
                name: scanner_model for name, scanner_model
                in zip(self.scanner_names, scanner_models)
            }
        if scanner_sockets is not None:
            self.scanner_sockets = scanner_sockets
        else:
            self.scanner_sockets = {
                name: socket for name, socket in
                zip(self.scanner_names, list(range(len(self.scanner_models))))
            }
        super().__init__()
