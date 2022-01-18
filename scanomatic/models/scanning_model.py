from enum import Enum, auto
from typing import Optional, Union
from collections.abc import Sequence

import scanomatic
import scanomatic.generics.model as model
from scanomatic.generics.enums import MinorMajorStepEnum
from scanomatic.models.compile_project_model import CompileInstructionsModel


class SCAN_CYCLE(MinorMajorStepEnum):
    Unknown = -1
    Wait = 0
    RequestScanner = 10
    WaitForUSB = 11
    ReportNotObtainedUSB = 12
    Scan = 20
    WaitForScanComplete = 21
    ReportScanError = 22
    RequestScannerOff = 30
    VerifyImageSize = 41
    VerifyDiskspace = 42
    RequestProjectCompilation = 50

    @classmethod
    def get_default(cls) -> "SCAN_CYCLE":
        return cls.Unknown


class SCAN_STEP(Enum):
    Wait = 0
    NextMinor = 1
    NextMajor = 2
    TruncateIteration = 3


class PLATE_STORAGE(Enum):
    Unknown = -1
    Fresh = 0
    Cold = 1
    RoomTemperature = 2


class CULTURE_SOURCE(Enum):
    Unknown = -1
    Freezer80 = 0
    Freezer20 = 1
    Fridge = 2
    Shipped = 3
    Novel = 4


class COMPILE_STATE(Enum):
    NotInitialized = 0
    Initialized = 1
    Finalized = 2


class ScanningAuxInfoModelFields(Enum):
    stress_level = auto()
    plate_storage = auto()
    plate_age = auto()
    pinning_project_start_delay = auto()
    precultures = auto()
    culture_freshness = auto()
    culture_source = auto()


class ScanningAuxInfoModel(model.Model):
    def __init__(
        self,
        stress_level=-1,
        plate_storage: PLATE_STORAGE = PLATE_STORAGE.Unknown,
        plate_age: float = -1.0,
        pinning_project_start_delay: Union[int, float] = -1,
        precultures=-1,
        culture_freshness=-1,
        culture_source: CULTURE_SOURCE = CULTURE_SOURCE.Unknown,
    ):
        self.stress_level = stress_level
        self.plate_storage: PLATE_STORAGE = plate_storage
        self.plate_age: float = plate_age
        self.pinning_project_start_delay: Union[int, float] = (
            pinning_project_start_delay
        )
        self.precultures = precultures
        self.culture_freshness = culture_freshness
        self.culture_source: CULTURE_SOURCE = culture_source
        super().__init__()


class ScanningModelFields(Enum):
    number_of_scans = auto()
    time_between_scans = auto()
    project_name = auto()
    directory_containing_project = auto()
    id = auto()
    description = auto()
    plate_descriptions = auto()
    email = auto()
    pinning_formats = auto()
    fixture = auto()
    scanner = auto()
    scanner_hardware = auto()
    scanning_program = auto()
    scanning_program_version = auto()
    scanning_program_params = auto()
    mode = auto()
    computer = auto()
    start_time = auto()
    cell_count_calibration_id = auto()
    auxillary_info = auto()
    version = auto()


class ScanningModel(model.Model):
    def __init__(
        self,
        *,
        number_of_scans: int = 217,
        time_between_scans: float = 20,
        project_name: str = "",
        directory_containing_project: str = "",
        id: str = "",
        start_time: float = 0.0,
        description: str = "",
        email: str = "",
        pinning_formats: tuple[tuple[int, int], ...] = tuple(),
        fixture: str = "",
        scanner: int = 1,
        scanner_hardware: str = "EPSON V700",
        mode: str = "TPU",
        computer: str = "",
        auxillary_info: ScanningAuxInfoModel,
        plate_descriptions: tuple["PlateDescription", ...] = tuple(),
        version: str = scanomatic.__version__,
        scanning_program: str = "",
        scanning_program_version: str = "",
        scanning_program_params: Sequence[str] = tuple(),
        cell_count_calibration_id=None,
    ):
        self.number_of_scans: int = number_of_scans
        self.time_between_scans: float = time_between_scans
        self.project_name: str = project_name
        self.directory_containing_project: str = directory_containing_project
        self.id: str = id
        self.description: str = description
        self.plate_descriptions: tuple[PlateDescription, ...] = (
            plate_descriptions
        )
        self.email: str = email
        self.pinning_formats: tuple[tuple[int, int], ...] = pinning_formats
        self.fixture: str = fixture
        self.scanner: int = scanner
        self.scanner_hardware: str = scanner_hardware
        self.scanning_program: str = scanning_program
        self.scanning_program_version: str = scanning_program_version
        self.scanning_program_params: Sequence[str] = scanning_program_params
        self.mode: str = mode
        self.computer: str = computer
        self.start_time: float = start_time
        self.cell_count_calibration_id = cell_count_calibration_id
        self.auxillary_info: ScanningAuxInfoModel = auxillary_info
        self.version: str = version
        super().__init__()


class PlateDescriptionFields(Enum):
    _name = auto()
    index = auto()
    description = auto()


class PlateDescription(model.Model):
    def __init__(
        self,
        name: str = '',
        index: int = -1,
        description: str = '',
    ):
        if name == '':
            name = "Plate {0}".format(index + 1)
        self.name: str = name
        self.index: int = index
        self.description: str = description
        super().__init__()


class ScannerOwnerModelFields(Enum):
    id = auto()
    pid = auto()


class ScannerOwnerModel(model.Model):
    def __init__(self, id=None, pid: int = 0):
        self.id = id
        self.pid: int = pid
        super().__init__()


class ScannerModelFields(Enum):
    socket = auto()
    scanner_name = auto()
    usb = auto()
    power = auto()
    model = auto()
    last_on = auto()
    last_off = auto()
    expected_interval = auto()
    email = auto()
    warned = auto()
    owner = auto()
    claiming = auto()
    reported = auto()


class ScannerModel(model.Model):
    def __init__(
        self,
        socket: int = -1,
        scanner_name: str = "",
        owner=None,
        usb: str = "",
        model: str = '',
        power: bool = False,
        last_on=-1,
        last_off=-1,
        expected_interval=0,
        email: str = "",
        warned: bool = False,
        claiming: bool = False,
        reported: bool = False,
    ):
        self.socket: int = socket
        self.scanner_name: str = scanner_name
        self.usb: str = usb
        self.power: bool = power
        self.model: str = model
        self.last_on = last_on
        self.last_off = last_off
        self.expected_interval = expected_interval
        self.email: str = email
        self.warned: bool = warned
        self.owner: Optional[ScannerOwnerModel] = owner
        self.claiming: bool = claiming
        self.reported: bool = reported
        super().__init__()


class ScanningModelEffectorDataFields(Enum):
    current_cycle_step = auto()
    current_step_start_time = auto()
    current_image = auto()
    current_image_path = auto()
    current_image_path_pattern = auto()
    previous_scan_cycle_start = auto()
    current_scan_time = auto()
    scanning_thread = auto()
    scan_success = auto()
    scanning_image_name = auto()
    usb_port = auto()
    scanner_model = auto()
    compile_project_model = auto()
    known_file_size = auto()
    warned_file_size = auto()
    warned_scanner_error = auto()
    warned_scanner_usb = auto()
    warned_discspace = auto()
    warned_terminated = auto()
    compilation_state = auto()
    informed_close_to_end = auto()


class ScanningModelEffectorData(model.Model):
    def __init__(
        self,
        *,
        current_cycle_step: SCAN_CYCLE = SCAN_CYCLE.Wait,
        current_step_start_time: float = -1,
        current_image: int = -1,
        current_image_path: str = "",
        current_image_path_pattern: str = "",
        previous_scan_cycle_start: float = -1.0,
        current_scan_time: float = -1.0,
        scanner_model: str = '',
        scanning_image_name: str = "",
        usb_port: str = "",
        scanning_thread=None,
        scan_success: bool = False,
        compile_project_model: CompileInstructionsModel,
        known_file_size=0,
        warned_file_size: bool = False,
        warned_scanner_error: bool = False,
        warned_terminated: bool = False,
        warned_scanner_usb: bool = False,
        warned_discspace: bool = False,
        informed_close_to_end: bool = False,
        compilation_state: COMPILE_STATE = COMPILE_STATE.NotInitialized,
    ):
        self.current_cycle_step: SCAN_CYCLE = current_cycle_step
        self.current_step_start_time: float = current_step_start_time
        self.current_image: int = current_image
        self.current_image_path: str = current_image_path
        self.current_image_path_pattern: str = current_image_path_pattern
        self.previous_scan_cycle_start: float = previous_scan_cycle_start
        self.current_scan_time: float = current_scan_time
        self.scanning_thread = scanning_thread
        self.scan_success: bool = scan_success
        self.scanning_image_name: str = scanning_image_name
        self.usb_port: str = usb_port
        self.scanner_model: str = scanner_model
        self.compile_project_model: Optional[CompileInstructionsModel] = (
            compile_project_model
        )
        self.known_file_size = known_file_size
        self.warned_file_size: bool = warned_file_size
        self.warned_scanner_error: bool = warned_scanner_error
        self.warned_scanner_usb: bool = warned_scanner_usb
        self.warned_discspace: bool = warned_discspace
        self.warned_terminated: bool = warned_terminated
        self.compilation_state: COMPILE_STATE = compilation_state
        self.informed_close_to_end: bool = informed_close_to_end
        super().__init__()
