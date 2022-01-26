import os
import pickle
import zipfile
from collections.abc import Callable
from io import BufferedWriter, BytesIO
from typing import Any, Optional

import numpy as np

import scanomatic.io.paths as paths
import scanomatic.io.jsonizer as jsonizer
from scanomatic.data_processing.pheno.state import (
    PhenotyperSettings,
    PhenotyperState
)
from scanomatic.io.logger import get_logger

_logger = get_logger("Phenotype Saver")
_paths = paths.Paths()


def _do_ask_overwrite(path: str) -> bool:
    return input(f"Overwrite '{path}' (y/N)").strip().upper().startswith("Y")


def save_state(
    settings: PhenotyperSettings,
    state: PhenotyperState,
    dir_path: str,
    ask_if_overwrite: bool = True
):
    """Save the `Phenotyper` instance's state for future work."""
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)

    p = os.path.join(dir_path, _paths.phenotypes_raw_npy)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.phenotypes)

    p = os.path.join(dir_path, _paths.vector_phenotypes_raw)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.vector_phenotypes)

    p = os.path.join(dir_path, _paths.vector_meta_phenotypes_raw)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.vector_meta_phenotypes)

    p = os.path.join(dir_path, _paths.normalized_phenotypes)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.normalized_phenotypes)

    p = os.path.join(dir_path, _paths.phenotypes_input_data)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.raw_growth_data)

    p = os.path.join(dir_path, _paths.phenotypes_input_smooth)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.smooth_growth_data)

    p = os.path.join(dir_path, _paths.phenotypes_filter)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.phenotype_filter)

    p = os.path.join(dir_path, _paths.phenotypes_reference_offsets)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.reference_surface_positions)

    p = os.path.join(dir_path, _paths.phenotypes_filter_undo)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        with open(p, 'wb') as fh:
            pickle.dump(state.phenotype_filter_undo, fh)

    p = os.path.join(dir_path, _paths.phenotype_times)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        np.save(p, state.times_data)

    p = os.path.join(dir_path, _paths.phenotypes_meta_data)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        with open(p, 'wb') as fh:
            pickle.dump(state.meta_data, fh)

    p = os.path.join(dir_path, _paths.phenotypes_extraction_params)
    if (
        not ask_if_overwrite
        or not os.path.isfile(p)
        or _do_ask_overwrite(p)
    ):
        jsonizer.dump(settings, p)

    _logger.info("State saved to '{0}'".format(dir_path))


def save_state_to_zip(
    base_name: str,
    settings: PhenotyperSettings,
    state: PhenotyperState,
    target: Optional[str] = None,
) -> Optional[BytesIO]:
    StateWriter = Callable[[BufferedWriter, Any], Any]
    save_jsonizer: StateWriter = (
        lambda fh, obj: fh.write(jsonizer.dumps(obj).encode())
    )
    save_pickle: StateWriter = lambda fh, obj: pickle.dump(obj, fh)

    def zipit(save_functions, data, zip_paths):
        zip_buffer = BytesIO()
        zf = zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False)

        for save_func, d, zpath in zip(save_functions, data, zip_paths):
            _logger.info("Zipping {0}".format(zpath))

            file_buffer = BytesIO()
            save_func(file_buffer, d)
            file_buffer.flush()
            file_buffer.seek(0)

            zf.writestr(zpath, file_buffer.read())

        for zfile in zf.filelist:
            zfile.create_system = 0

        zip_buffer.flush()
        zf.close()
        zip_buffer.seek(0)

        return zip_buffer

    _logger.info(
        "Note that this does not change the saved state in the analysis folder",  # noqa: E501
    )

    try:
        dir_path = os.sep.join(base_name.split(os.sep)[-2:])
    except (TypeError, ValueError):
        dir_path = ""
    if not dir_path or not dir_path.strip() or dir_path == ".":
        dir_path = "analysis"

    save_functions: list[StateWriter] = []
    data: list[Any] = []
    zip_paths: list[str] = []

    # Phenotypes
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_raw_npy),
    )
    save_functions.append(np.save)
    data.append(state.phenotypes)

    # Vector phenotypes
    zip_paths.append(
        os.path.join(dir_path, _paths.vector_phenotypes_raw),
    )
    save_functions.append(np.save)
    data.append(state.vector_phenotypes)

    # Meta phenotypes
    zip_paths.append(
        os.path.join(dir_path, _paths.vector_meta_phenotypes_raw),
    )
    save_functions.append(np.save)
    data.append(state.vector_meta_phenotypes)

    # Normalized phenotypes
    zip_paths.append(
        os.path.join(dir_path, _paths.normalized_phenotypes),
    )
    save_functions.append(np.save)
    data.append(state.normalized_phenotypes)

    # Raw growth data
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_input_data),
    )
    save_functions.append(np.save)
    data.append(state.raw_growth_data)

    # Smooth growth data
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_input_smooth),
    )
    save_functions.append(np.save)
    data.append(state.smooth_growth_data)

    # Phenotypes filter (qc-markings)
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_filter),
    )
    save_functions.append(np.save)
    data.append(state.phenotype_filter)

    # Reference surface positions
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_reference_offsets),
    )
    save_functions.append(np.save)
    data.append(state.reference_surface_positions)

    # Undo filter (qc undo)
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_filter_undo),
    )
    save_functions.append(save_pickle)
    data.append(state.phenotype_filter_undo)

    # Time stamps
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotype_times),
    )
    save_functions.append(np.save)
    data.append(state.times_data)

    # Meta-data (strain info)
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_meta_data),
    )
    save_functions.append(save_pickle)
    data.append(state.meta_data)

    # Internal settings
    zip_paths.append(
        os.path.join(dir_path, _paths.phenotypes_extraction_params),
    )
    save_functions.append(save_jsonizer)
    data.append(settings)

    zip_stream = zipit(save_functions, data, zip_paths)
    if target:
        with open(target, 'wb') as fh:
            fh.write(zip_stream.read())
        zip_stream.close()
        _logger.info("Zip file saved to {0}".format(target))
        return None
    else:
        return zip_stream
