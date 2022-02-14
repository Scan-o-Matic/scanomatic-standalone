import re
from enum import Enum, auto

import scanomatic.generics.model as model


class DefaultPinningFormats(Enum):
    Format_96__8x12 = (8, 12)
    Format_384__16x24 = (16, 24)
    Format_1536__32x48 = (32, 48)
    Format_6144__64x96 = (64, 96)

    def human_readable(self) -> str:
        return re.sub(
            r'Format_(\d+)__(\d+)x(\d+)',
            r'\2 x \3 (\1)',
            self.name
        )


class IMAGE_ROTATIONS(Enum):
    Landscape = 0
    Portrait = 1
    Unknown = 2

    @classmethod
    def from_name(cls, raw_string: str) -> "IMAGE_ROTATIONS":
        for member in IMAGE_ROTATIONS:
            if member.name.upper() == raw_string.upper():
                return member


class COMPARTMENTS(Enum):
    Total = 0
    Background = 1
    Blob = 2

    @classmethod
    def from_name(cls, raw_string: str) -> "COMPARTMENTS":
        for member in COMPARTMENTS:
            if member.name.upper() == raw_string.upper():
                return member


class MEASURES(Enum):
    Count = 0
    Sum = 1
    Mean = 2
    Median = 3
    Perimeter = 4
    IQR = 5
    IQR_Mean = 6
    Centroid = 7

    @classmethod
    def from_name(cls, raw_string: str) -> "MEASURES":
        for member in MEASURES:
            if member.name.upper() == raw_string.upper():
                return member


class VALUES(Enum):
    Pixels = 0
    Grayscale_Targets = 1
    Cell_Estimates = 2

    @classmethod
    def from_name(cls, raw_string: str) -> "VALUES":
        for member in VALUES:
            if member.name.upper() == raw_string.upper():
                return member


class AnalysisModelFields(Enum):
    cell_count_calibration = auto()
    cell_count_calibration_id = auto()
    compilation = auto()
    compile_instructions = auto()
    pinning_matrices = auto()
    use_local_fixture = auto()
    email = auto()
    stop_at_image = auto()
    output_directory = auto()
    focus_position = auto()
    suppress_non_focal = auto()
    animate_focal = auto()
    one_time_positioning = auto()
    one_time_grayscale = auto()
    grid_images = auto()
    grid_model = auto()
    image_data_output_item = auto()
    image_data_output_measure = auto()
    chain = auto()
    plate_image_inclusion = auto()


class AnalysisModel(model.Model):
    def __init__(
        self,
        *,
        compilation: str = "",
        compile_instructions: str = "",
        pinning_matrices: tuple[tuple[int, int], ...] = (
            (32, 48), (32, 48), (32, 48), (32, 48)
        ),
        use_local_fixture: bool = False,
        email: str = "",
        stop_at_image: int = -1,
        output_directory: str = "analysis",
        focus_position=None,
        suppress_non_focal: bool = False,
        animate_focal: bool = False,
        one_time_positioning: bool = True,
        one_time_grayscale: bool = False,
        grid_images=None,
        grid_model: "GridModel",
        image_data_output_item: COMPARTMENTS = COMPARTMENTS.Blob,
        image_data_output_measure: MEASURES = MEASURES.Sum,
        chain: bool = True,
        plate_image_inclusion=None,
        cell_count_calibration=None,
        cell_count_calibration_id=None,
    ):
        self.cell_count_calibration = cell_count_calibration
        self.cell_count_calibration_id = cell_count_calibration_id
        self.compilation: str = compilation
        self.compile_instructions: str = compile_instructions
        self.pinning_matrices: tuple[tuple[int, int], ...] = pinning_matrices
        self.use_local_fixture: bool = use_local_fixture
        self.email: str = email
        self.stop_at_image: int = stop_at_image
        self.output_directory: str = output_directory
        self.focus_position = focus_position
        self.suppress_non_focal: bool = suppress_non_focal
        self.animate_focal: bool = animate_focal
        self.one_time_positioning: bool = one_time_positioning
        self.one_time_grayscale: bool = one_time_grayscale
        self.grid_images = grid_images
        self.grid_model: GridModel = grid_model
        self.image_data_output_item = image_data_output_item
        self.image_data_output_measure = image_data_output_measure
        self.chain = chain
        self.plate_image_inclusion = plate_image_inclusion
        super().__init__()


class GridModelFields(Enum):
    use_utso = auto()
    median_coefficient = auto()
    manual_threshold = auto()
    grid = auto()
    gridding_offsets = auto()
    reference_grid_folder = auto()


class GridModel(model.Model):
    def __init__(
        self,
        use_utso: bool = True,
        median_coefficient: float = 0.99,
        manual_threshold: float = 0.05,
        grid=None,
        gridding_offsets=None,
        reference_grid_folder=None,
    ):
        self.use_utso: bool = use_utso
        self.median_coefficient: float = median_coefficient
        self.manual_threshold: float = manual_threshold
        self.grid = grid
        self.gridding_offsets = gridding_offsets
        self.reference_grid_folder = reference_grid_folder
        super().__init__()

    def __hash__(self):
        return id(self)


class AnalysisFeaturesFields(Enum):
    data = auto()
    shape = auto()
    index = auto()


class AnalysisFeatures(model.Model):
    def __init__(self, index: int = -1, data=None, shape=tuple()):
        self.data = data
        self.shape = shape
        self.index: int = index
        super().__init__()

    def __hash__(self):
        return id(self)
