import os

from scanomatic.io.paths import Paths
from scanomatic.models.scan import Scan


class UnknownProjectError(Exception):
    pass


class ScanStore:
    def __init__(self, path: str):
        self._path = path

    def add_scan(self, project_fullname, scan: Scan) -> None:
        project_dir = os.path.join(self._path, project_fullname)
        if not os.path.isdir(project_dir):
            raise UnknownProjectError()
        project_name = os.path.basename(project_fullname)
        filename = Paths().experiment_scan_image_pattern.format(
            project_name,
            '{:04d}'.format(scan.index),
            scan.timedelta.total_seconds(),
        )
        path = os.path.join(self._path, project_fullname, filename)
        with open(path, 'wb') as f:
            f.write(scan.image.read())
            f.flush()
            os.fsync(f)
