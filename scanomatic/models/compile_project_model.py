from enum import Enum, auto
from collections.abc import Sequence

from scanomatic.generics.model import Model
from scanomatic.models.fixture_models import FixtureModel


class COMPILE_ACTION(Enum):
    Initiate = 0
    Append = 1
    InitiateAndSpawnAnalysis = 10
    AppendAndSpawnAnalysis = 11

    @classmethod
    def from_name(cls, raw_string: str) -> "COMPILE_ACTION":
        for member in COMPILE_ACTION:
            if member.name.upper() == raw_string.upper():
                return member


class FIXTURE(Enum):
    Local = 0
    Global = 1

    @classmethod
    def from_name(cls, raw_string: str) -> "FIXTURE":
        for member in FIXTURE:
            if member.name.upper() == raw_string.upper():
                return member


class CompileInstructionsModelFields(Enum):
    compile_action = auto()
    images = auto()
    path = auto()
    start_time = auto()
    start_condition = auto()
    fixture_type = auto()
    fixture_name = auto()
    email = auto()
    overwrite_pinning_matrices = auto()
    cell_count_calibration_id = auto()


class CompileInstructionsModel(Model):
    def __init__(
        self,
        compile_action=COMPILE_ACTION.InitiateAndSpawnAnalysis,
        start_time=0.0,
        images=tuple(),
        path="",
        start_condition="",
        fixture_type=FIXTURE.Local,
        fixture_name=None,
        email="",
        overwrite_pinning_matrices=None,
        cell_count_calibration_id="default",
    ):
        self.compile_action: COMPILE_ACTION = compile_action
        self.images: Sequence[CompileImageModel] = images
        self.path: str = path
        self.start_time: float = start_time
        self.start_condition: str = start_condition
        self.fixture_type: FIXTURE = fixture_type
        self.fixture_name = fixture_name
        self.email: str = email
        self.overwrite_pinning_matrices = overwrite_pinning_matrices
        self.cell_count_calibration_id: str = cell_count_calibration_id
        super().__init__()


class CompileImageModelFields(Enum):
    index = auto()
    path = auto()
    time_stamp = auto()


class CompileImageModel(Model):
    def __init__(
        self,
        index: int = -1,
        path: str = "",
        time_stamp: float = 0.0,
    ):
        self.index: int = index
        self.path: str = path
        self.time_stamp: float = time_stamp
        super().__init__()


class CompileImageAnalysisModelFields(Enum):
    image = auto()
    fixture = auto()


class CompileImageAnalysisModel(Model):
    def __init__(
        self,
        *,
        image: CompileImageModel,
        fixture: FixtureModel,
    ):
        self.image: CompileImageModel = image
        self.fixture: FixtureModel = fixture
        super().__init__()
