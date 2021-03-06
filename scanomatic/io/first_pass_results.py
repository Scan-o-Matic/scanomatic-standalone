import os
from enum import Enum
from glob import glob
from typing import Optional, cast
from collections.abc import Sequence
from scanomatic.io.jsonizer import copy, dump, dump_to_stream, load, load_first
from scanomatic.io.logger import get_logger

from scanomatic.io.paths import Paths
from scanomatic.models.compile_project_model import (
    CompileImageAnalysisModel,
    CompileInstructionsModel
)
from scanomatic.models.scanning_model import ScanningModel
from scanomatic.models.validators.validate import validate


class FIRST_PASS_SORTING(Enum):
    Index = 1
    Time = 2


class CompilationResults:
    def __init__(
        self,
        compilation_path=None,
        compile_instructions_path=None,
        scanner_instructions_path=None,
        sort_mode: FIRST_PASS_SORTING = FIRST_PASS_SORTING.Time,
    ):
        self._logger = get_logger("Compilation results")
        self._compilation_path = compilation_path
        self._compile_instructions: Optional[CompileInstructionsModel] = None
        self._scanner_instructions: Optional[ScanningModel] = None
        self.load_scanner_instructions(scanner_instructions_path)
        self._plates = None
        self._plate_position_keys = None
        self._image_models: list[CompileImageAnalysisModel] = []
        self._used_models: list[CompileImageAnalysisModel] = []
        self._current_model: Optional[CompileImageAnalysisModel] = None
        self._loading_length = 0
        if compile_instructions_path:
            self._load_compile_instructions(compile_instructions_path)
        if compilation_path:
            self._load_compilation(self._compilation_path, sort_mode=sort_mode)

    @classmethod
    def create_from_data(
        cls,
        path,
        compile_instructions,
        image_models,
        used_models=None,
        scan_instructions=None,
    ):
        if used_models is None:
            used_models = []

        new = cls()
        new._compilation_path = path
        new._compile_instructions = cast(
            CompileInstructionsModel,
            copy(compile_instructions),
        )
        new._image_models = cast(
            list[CompileImageAnalysisModel],
            copy(list(image_models)),
        )
        new._used_models = cast(
            list[CompileImageAnalysisModel],
            copy(list(used_models)),
        )
        new._loading_length = len(new._image_models)
        new._scanner_instructions = scan_instructions
        return new

    def load_scanner_instructions(self, path: Optional[str] = None):
        if path is None:
            try:
                path = glob(os.path.join(
                    os.path.dirname(self._compilation_path),
                    Paths().scan_project_file_pattern.format('*'),
                ))[0]
            except IndexError:
                self._logger.warning(
                    "No information of start time of project, can't safely be joined with others",  # noqa: E501
                )
                return

        self._scanner_instructions = load_first(path)

    def _load_compile_instructions(self, path: str):
        self._compile_instructions = load_first(path)
        if self._compile_instructions is None:
            self._logger.error(f"Could not load path {path}")

    def _load_compilation(
        self,
        path: str,
        sort_mode: FIRST_PASS_SORTING = FIRST_PASS_SORTING.Time
    ):
        images: Optional[list[CompileImageAnalysisModel]] = load(path)
        if images is None:
            self._logger.error(f"Could not load any images from {path}")
            images = []
        else:
            self._logger.info(f"Loaded {len(images)} compiled images")

        self._reindex_plates(images)

        models = copy(images)
        if sort_mode is FIRST_PASS_SORTING.Time:
            for (index, m) in enumerate(sorted(
                models,
                key=lambda x: x.image.time_stamp,
            )):
                m.image.index = index
            self._image_models = models
        else:
            inject_time = 0.
            previous_time = 0.
            for (index, m) in enumerate(models):
                m.image.index = index
                if m.image.time_stamp < previous_time:
                    inject_time += previous_time - m.image.time_stamp
                m.image.time_stamp += inject_time
            self._image_models = models
        self._loading_length = len(self._image_models)

    @staticmethod
    def _reindex_plates(images):
        for image in images:
            if image and image.fixture and image.fixture.plates:
                for plate in image.fixture.plates:
                    plate.index -= 1

    def __len__(self) -> int:
        return self._loading_length

    def __getitem__(self, item: int) -> Optional[CompileImageAnalysisModel]:
        if not self._image_models:
            return None

        if item < 0:
            item %= len(self._image_models)

        try:
            return sorted(
                self._image_models,
                key=lambda x: x.image.time_stamp
            )[item]
        except (ValueError, IndexError):
            return None

    def keys(self) -> Sequence[int]:
        if self._image_models is None:
            return []
        return list(range(len(self._image_models)))

    def __add__(self, other: "CompilationResults") -> "CompilationResults":
        start_time_difference = other.start_time - self.start_time

        other_start_index = len(self)
        other_image_models = []
        other_directory = os.path.dirname(other._compilation_path)
        for index in range(len(other)):
            model: CompileImageAnalysisModel = copy(other[index])
            model.image.time_stamp += start_time_difference
            model.image.index += other_start_index
            self._update_image_path_if_needed(model, other_directory)
            other_image_models.append(model)

        other_image_models += self._image_models
        other_image_models = sorted(
            other_image_models,
            key=lambda x: x.image.time_stamp,
        )

        return CompilationResults.create_from_data(
            self._compilation_path,
            self._compile_instructions,
            other_image_models,
            self._used_models,
            self._scanner_instructions,
        )

    def _update_image_path_if_needed(self, model, directory):
        if not os.path.isfile(model.image.path):
            image_name = os.path.basename(model.image.path)
            if os.path.isfile(os.path.join(directory, image_name)):
                model.image.path = os.path.join(directory, image_name)
                return
        self._logger.warning(
            "Couldn't locate the file {0}".format(model.image.path),
        )

    @property
    def start_time(self) -> float:
        if self._scanner_instructions:
            return self._scanner_instructions.start_time
        self._logger.warning(
            "No scanner instructions have been loaded, start time unknown",
        )
        return 0.

    @property
    def compile_instructions(self) -> CompileInstructionsModel:
        return self._compile_instructions

    @property
    def plates(self) -> Optional[Sequence]:
        res = self[-1]
        if res:
            return res.fixture.plates
        return None

    @property
    def last_index(self) -> int:
        return len(self._image_models) - 1

    @property
    def total_number_of_images(self) -> int:
        return len(self._image_models) + len(self._used_models)

    @property
    def current_image(self) -> CompileImageAnalysisModel:
        return self._current_model

    @property
    def current_absolute_time(self) -> float:
        return (
            self.current_image.image.time_stamp
            + self.compile_instructions.start_time
        )

    def recycle(self):
        self._image_models += self._used_models
        self._used_models = []
        self._current_model = None

    def get_next_image_model(self) -> Optional[CompileImageAnalysisModel]:
        model = self[-1]
        self._current_model = model
        if model:
            self._image_models.remove(model)
            self._used_models.append(model)
        return model

    def dump(
        self,
        directory,
        new_name=None,
        force_dump_scan_instructions=False,
    ):
        self._logger.warning(
            """This functionality has not fully been tested,
            if you test it and it works fine let Martin know.
            If it doesn't work, let him know too.""",
        )
        directory = os.path.abspath(directory)
        os.makedirs(directory)
        if new_name is None:
            new_name = os.path.basename(directory)

        try:
            with open(
                os.path.join(
                    directory,
                    Paths().project_compilation_pattern.format(new_name),
                ),
                'w',
            ) as fh:
                while True:
                    model: CompileImageAnalysisModel = copy(
                        self.get_next_image_model(),
                    )
                    self._update_image_path_if_needed(model, directory)
                    if model is None:
                        break
                    if validate(model):
                        dump_to_stream(model, fh)
        except IOError:
            self._logger.error("Could not save to directory")
            return

        compile_instructions = os.path.join(
            directory,
            Paths().project_compilation_pattern.format(new_name),
        )
        dump(
            self._compile_instructions,
            compile_instructions,
        )

        if (
            not glob(os.path.join(
                directory,
                Paths().scan_project_file_pattern.format('*'),
            ))
            or force_dump_scan_instructions
        ):

            scan_instructions = os.path.join(
                directory,
                Paths().scan_project_file_pattern.format(new_name),
            )
            dump(
                self._scanner_instructions,
                scan_instructions,
            )
