import glob
import os

import numpy as np

import scanomatic.io.paths as paths
from scanomatic.io import jsonizer
from scanomatic.io.logger import get_logger
from scanomatic.io.pickler import safe_load

_logger = get_logger("Project")


def path_has_saved_project_state(
    directory_path: str,
    require_phenotypes=True,
):
    if not directory_path:
        return False

    _p = paths.Paths()

    if require_phenotypes:
        try:
            np.load(
                safe_load(os.path.join(directory_path, _p.phenotypes_raw_npy)),
                allow_pickle=True,
            )
        except IOError:
            return False

    try:
        np.load(
            safe_load(os.path.join(directory_path,  _p.phenotypes_input_data)),
            allow_pickle=True,
        )
        np.load(
            safe_load(os.path.join(directory_path, _p.phenotype_times)),
            allow_pickle=True,
        )
        np.load(
            safe_load(os.path.join(directory_path, _p.phenotypes_input_smooth)),
            allow_pickle=True,
        )
        jsonizer.load(os.path.join(directory_path, _p.phenotypes_extraction_params))
    except IOError:
        return False
    return True


def get_project_dates(directory_path):
    def most_recent(stat_result):
        return max(
            stat_result.st_mtime,
            stat_result.st_atime,
            stat_result.st_ctime,
        )

    analysis_date = None
    _p = paths.Paths()
    image_data_files = glob.glob(os.path.join(
        directory_path,
        _p.image_analysis_img_data.format("*"),
    ))
    if image_data_files:
        analysis_date = max(most_recent(os.stat(p)) for p in image_data_files)
    try:
        phenotype_date = most_recent(os.stat(os.path.join(
            directory_path,
            _p.phenotypes_raw_npy,
        )))
    except OSError:
        phenotype_date = None

    state_date = phenotype_date

    for path in (
        _p.phenotypes_input_data,
        _p.phenotype_times,
        _p.phenotypes_input_smooth,
        _p.phenotypes_extraction_params,
        _p.phenotypes_filter,
        _p.phenotypes_filter_undo,
        _p.phenotypes_meta_data,
        _p.normalized_phenotypes,
        _p.vector_phenotypes_raw,
        _p.vector_meta_phenotypes_raw,
        _p.phenotypes_reference_offsets,
    ):
        try:
            state_date = max(
                state_date,
                most_recent(os.stat(os.path.join(directory_path, path))),
            )
        except OSError:
            pass

    return analysis_date, phenotype_date, state_date


def remove_state_from_path(directory_path):
    _p = paths.Paths()
    n = 0

    for path in (
        _p.phenotypes_input_data,
        _p.phenotype_times,
        _p.phenotypes_input_smooth,
        _p.phenotypes_extraction_params,
        _p.phenotypes_filter,
        _p.phenotypes_filter_undo,
        _p.phenotypes_meta_data,
        _p.normalized_phenotypes,
        _p.vector_phenotypes_raw,
        _p.vector_meta_phenotypes_raw,
        _p.phenotypes_reference_offsets,
    ):
        file_path = os.path.join(directory_path, path)
        try:
            os.remove(file_path)
        except (IOError, OSError):
            pass
        else:
            n += 1

    if n:
        _logger.info(f"Removed {n} pre-existing phenotype state files")
