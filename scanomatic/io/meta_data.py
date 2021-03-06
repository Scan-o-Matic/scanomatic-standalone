import csv
from typing import Iterator, Optional, Union, cast

import numpy as np
import pandas as pd

from scanomatic.io.logger import get_logger


class DataLoader:
    _SUFFIXES: tuple[str, ...] = tuple()

    def __init__(self, path):
        self._logger = get_logger("MetaDataLoader")
        self._path = path
        self._sheet = -1
        self._entries = []
        self._row_iterators = []
        self._columns = []
        self._sheet_names = []
        self._headers: list[Optional[str]] = []

    def _reset(self):

        self._sheet = -1
        self._columns = []
        self._entries = []
        self._row_iterators = []
        self._sheet_names = []
        self._headers = []

    @property
    def rows(self):

        return self._entries[self._sheet]

    def get_sheet_name(self, sheet_index: int) -> str:

        return self._sheet_names[sheet_index]

    def get_next(self):

        for row in self._row_iterators[self._sheet]:
            yield self._get_next_row(row)

    @staticmethod
    def _get_next_row(row):
        raise NotImplementedError

    def _get_empty_headers(self):
        return [None for _ in range(self._columns[self._sheet])]

    def get_headers(self, plate_size: int):

        if self._headers[self._sheet] is None:
            if self.sheet_is_valid_with_headers(plate_size):
                self._headers[self._sheet] = self._get_next_row(
                    next(self._row_iterators[self._sheet]),
                )
            elif self.sheet_is_valid_without_headers(plate_size):
                self._headers[self._sheet] = self._get_empty_headers()

        return self._headers[self._sheet]

    @classmethod
    def can_load(cls, path: str) -> bool:
        suffix = path[::-1].split(".", 1)[0][::-1].lower()
        return suffix in cls._SUFFIXES

    @property
    def sheets(self) -> int:
        return len(self._entries)

    def next_sheet(self, plate_size: int) -> Optional[int]:
        self._sheet += 1

        while not self.sheet_is_valid(plate_size):

            if self._sheet >= len(self._entries):
                return None

            self._logger.warning(
                "Sheet {0} ({1} zero-indexed) has {2} and {3} entry rows. This doesn't match plate size {4}".format(  # noqa: E501
                    self._sheet_names[self._sheet],
                    self._sheet,
                    " header row"
                    if self.sheet_is_valid_without_headers(plate_size)
                    else "no headers",
                    self._entries[self._sheet],
                    plate_size,
                ),
            )
            self._sheet += 1

        return self._sheet

    @property
    def has_more_data(self) -> bool:
        return self._sheet < len(self._entries)

    def sheet_is_valid_with_headers(self, plate_size: int) -> bool:
        return (
            plate_size % (self._entries[self._sheet] - 1) == 0
            and (plate_size / (self._entries[self._sheet] - 1)) % 4 == 1
        )

    def sheet_is_valid_without_headers(self, plate_size: int) -> bool:
        return (
            plate_size % self._entries[self._sheet] == 0
            and plate_size / self._entries[self._sheet] % 4 == 1
        )

    def sheet_is_valid(self, plate_size: int) -> bool:
        if 0 <= self._sheet < len(self._entries):
            return (
                self.sheet_is_valid_with_headers(plate_size)
                or self.sheet_is_valid_without_headers(plate_size)
            )
        return False


class ExcelLoader(DataLoader):

    _SUFFIXES = ('xls', 'xlsx')

    def __init__(self, path):

        super(ExcelLoader, self).__init__(path)
        self._data = []
        self._load()

    def _load(self) -> None:

        self._data = []
        self._reset()
        doc = pd.ExcelFile(self._path)
        for n in doc.sheet_names:
            self._sheet_names.append(n)
            self._load_sheet(doc.parse(n, header=None).fillna(value=''))

    def _load_sheet(self, df: pd.DataFrame) -> None:
        self._data.append(df)
        self._entries.append(df.shape[0])
        self._columns.append(df.shape[1])
        self._headers.append(None)
        self._row_iterators.append(df.iterrows())

    @staticmethod
    def _get_next_row(row):
        return row[1].tolist()


class CSVLoader(DataLoader):

    _SUFFIXES = ("csv", "tsv", "tab", "txt")

    def __init__(self, path):
        super(CSVLoader, self).__init__(path)
        self._load()

    def _load(self) -> None:
        self._reset()
        with open(self._path) as fh:
            raw_data = fh.readlines()

        dialect = csv.Sniffer().sniff(raw_data[0])
        data = list(csv.reader(raw_data, dialect=dialect))
        self._columns.append(max(len(row) for row in data))
        self._entries.append(len(data))
        self._headers.append(None)
        self._row_iterators.append((row for row in data))

    @staticmethod
    def _get_next_row(row):
        return row


class MetaData2:

    _LOADERS = (ExcelLoader, CSVLoader)

    def __init__(self, plate_shapes, *paths):

        self._logger = get_logger("MetaData")
        self._plate_shapes = plate_shapes

        self._data = tuple(
            None if shape is None else np.empty(shape, dtype=object)
            for shape in plate_shapes
        )

        self._headers: list[Optional[list[str]]] = [
            None for _ in plate_shapes
        ]
        self._loading_plate = 0
        self._loading_offset = []
        self._paths = paths

        self._load(*paths)

        if not self.loaded:
            self._logger.warning("Not enough meta-data to fill all plates")

    def __call__(self, plate, outer, inner):
        return self._data[plate][outer, inner]

    def __getitem__(self, plate):
        return self._data[plate].tolist()

    def __eq__(self, other):
        if hasattr(other, "shapes") and self.shapes != other.shapes:
            return False

        for plate, outer, inner in self.generate_coordinates():

            if self(plate, outer, inner) != other(plate, outer, inner):
                return False
        return True

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k != "_logger"}

    def __setstate__(self, state):
        self.__dict__.update(state)

    def get_column_index_from_all_plates(
        self,
        index,
    ) -> list[list[list[list]]]:
        plates: list[list[list[list]]] = []
        for id_plate, (outers, inners) in enumerate(self._plate_shapes):
            plate: list[list[list]] = []
            plates.append(plate)
            for id_outer in range(outers):
                data: list[list] = []
                plate.append(data)

                for id_inner in range(inners):
                    data.append(self(id_plate, id_outer, id_inner)[index])
        return plates

    def get_header_row(self, plate: int) -> Optional[list[str]]:
        """
        Args:
            plate: Plate index

        Returns: Header row
        """
        return self._headers[plate]

    @property
    def shapes(self) -> list[np.ndarray]:
        return self._plate_shapes

    @property
    def loaded(self) -> bool:
        return self._loading_plate >= len(self._plate_shapes)

    @property
    def _plate_completed(self) -> bool:
        return len(self._loading_offset) == 0

    @staticmethod
    def _get_loader(path):
        for loader in MetaData2._LOADERS:
            if loader.can_load(path):
                return loader(path)

        return None

    def _load(self, *paths) -> None:
        for path in paths:

            if self.loaded:
                return

            loader = MetaData2._get_loader(path)
            if loader is None:
                self._logger.warning(
                    "Unknown file format, can't load {0}".format(path),
                )
                continue

            size = self._get_sought_size()

            while loader.has_more_data:

                sheet_id = loader.next_sheet(size)
                if sheet_id is None:
                    break

                headers = loader.get_headers(size)

                if not self._has_matching_headers(headers):
                    self._logger.warning(
                        "Sheet {0} ({1}) of {2} headers don't match {3} != {4}".format(  # noqa: E501
                            loader.get_sheet_name(sheet_id),
                            sheet_id,
                            path,
                            headers,
                            self._headers[self._loading_plate],
                        ),
                    )
                    continue

                self._logger.info("Using {0}:{1} for plate {2}".format(
                    path,
                    loader.get_sheet_name(sheet_id),
                    self._loading_plate,
                ))
                self._update_headers_if_needed(headers)
                self._update_meta_data(loader)
                self._update_loading_offsets()

                if self._plate_completed:
                    self._loading_plate += 1

                if self.loaded:
                    return

                size = self._get_sought_size()

    def _get_sought_size(self) -> int:
        size = np.prod(self._plate_shapes[self._loading_plate])
        return size // 4 ** len(self._loading_offset)

    def _update_loading_offsets(self) -> None:
        if not self._loading_offset:
            return
        outer, inner = self._loading_offset[-1]
        inner += 1
        if inner > 1:
            inner %= 2
            outer += 1
            if outer > 1:
                self._loading_offset = self._loading_offset[:-1]
                self._update_loading_offsets()
                return

        self._loading_offset[-1] = (outer, inner)

    def _has_matching_headers(self, headers) -> bool:
        plate_header = self._headers[self._loading_plate]
        if plate_header is None:
            return True
        elif len(plate_header) != len(headers):
            return False
        elif all(h is None for h in plate_header):
            return True
        else:
            return all(
                a == b for a, b in zip(plate_header, headers)
            )

    def _update_headers_if_needed(self, headers) -> None:
        loading_plate = self._headers[self._loading_plate]
        if (
            loading_plate is None
            or all(h is None for h in loading_plate)
        ):
            self._headers[self._loading_plate] = headers

    def _update_meta_data(self, loader) -> None:
        slotter = self._get_slotting_iter(loader)
        for meta_data in loader.get_next():
            cast(
                tuple[np.ndarray],
                self._data,
            )[self._loading_plate][next(slotter)] = meta_data

    def _get_slotting_iter(self, loader: DataLoader):
        """
        Returns:
            Coordinate iterator
            :rtype : iter
        """
        def coord_lister(outer, inner, max_outer, max_inner):
            yield outer, inner
            inner += factor
            if inner >= max_inner:
                inner %= max_inner
                outer += factor
                if outer >= max_outer:
                    outer %= max_outer
        plate_data = cast(
            np.ndarray,
            self._data[self._loading_plate],
        )
        plate_shape = cast(
            np.ndarray,
            self._plate_shapes[self._loading_plate],
        )
        factor = np.log2(
            plate_data.size /
            (
                loader.rows - loader.sheet_is_valid_with_headers(
                    np.prod(plate_shape),
                )
            )
        )

        if factor != int(factor):
            return None

        elif factor == 0:
            # Full plate
            return zip(*np.unravel_index(
                np.arange(plate_data.size),
                plate_shape,
            ))

        else:
            # Partial plate
            factor = int(factor)
            if factor > len(self._loading_offset):

                self._loading_offset += [
                    (0, 0) for _ in range(factor - len(self._loading_offset))
                ]

            outer, inner = map(
                sum,
                zip(*(
                    (o*2**line, i*2**line) for line, (o, i) in
                    enumerate(self._loading_offset)
                ))
            )

            factor = 2 ** len(self._loading_offset)
            max_outer, max_inner = plate_shape

            return coord_lister(outer, inner, max_outer, max_inner)

    def get_data_from_numpy_where(self, plate, selection):
        selection = list(zip(*selection))
        for outer, inner in selection:
            yield self(plate, outer, inner)

    def find(
        self,
        value: str,
        column: Optional[Union[str, int]] = None,
    ) -> Iterator[Iterator[tuple[int, ...]]]:
        """Generate coordinate tuples for where key matches meta-data

        :param value : Search criteria
            :type value : str
        :param column : Optional column name to limit search to)
            searches all columns

        Returns
        -------

        generator
            Each item being a (plate, row, column)-tuple.

        """

        for id_plate, _ in enumerate(self._plate_shapes):

            yield self.find_on_plate(id_plate, value, column=column)

    def find_on_plate(
        self,
        plate: int,
        value: str,
        column: Optional[Union[str, int]] = None,
    ) -> Iterator[tuple[int, ...]]:
        if isinstance(column, str):
            column = self.get_header_index(plate, column)

            if column < 0:
                yield tuple()

        for id_plate, id_row, id_col in self.generate_coordinates(plate=plate):
            data = self(id_plate, id_row, id_col)
            if column is None:
                if value in data:
                    yield (id_row, id_col)
            else:
                if value == data[column]:
                    yield (id_row, id_col)

    def get_header_index(self, plate, header) -> int:
        header_row = cast(
            list[str],
            self.get_header_row(plate),
        )
        for i, column_header in enumerate(header_row):
            if column_header.lower() == header.lower():
                return i
        return -1

    def generate_coordinates(self, plate=None):
        plates = (
            (i, p) for i, p in enumerate(self._plate_shapes)
            if plate is None or i is plate
        )

        for id_plate, shape in plates:

            if shape is not None:

                for id_row in range(shape[0]):

                    for id_col in range(shape[1]):

                        yield id_plate, id_row, id_col
