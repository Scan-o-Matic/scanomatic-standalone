import os
from typing import IO


def safe_load(path, return_string=False):
    version_compatibility = _RefactoringPhases()
    fh = SafeProxyFileObject(path, version_compatibility)
    version_compatibility.io = fh
    if return_string:
        return os.linesep.join(fh.readlines())
    else:
        return fh


class _RefactoringPhases:
    def __init__(self):
        """Rewrites pickled data to match refactorings"""
        self._next = None
        self.io = None

    def __call__(self, line: bytes):
        """
        Args:
            line (str): A pickled line
        """
        if not isinstance(self.io, IO):
            raise AttributeError("Attribute 'io' not initialized properly")
        if self._next is None:
            if line.endswith(
                b"scanomatic.data_processing.curve_phase_phenotypes",
            ):
                tell = self.io.tell()
                _next = self.io.readline()
                self.io.seek(tell)

                if _next.startswith(b'VectorPhenotypes'):
                    return (
                        line[:-49]
                        + b"scanomatic.data_processing.phases.features"
                    )
                elif _next.startswith(b'CurvePhasePhenotypes'):
                    return (
                        line[:-49]
                        + b"scanomatic.data_processing.phases.analysis"
                    )
                elif _next.startswith(b'CurvePhases'):
                    return (
                        line[:-49]
                        + b"scanomatic.data_processing.phases.segmentation"
                    )
                elif _next.startswith(b'CurvePhaseMetaPhenotypes'):
                    return (
                        line[:-49]
                        + b"scanomatic.data_processing.phases.features"
                    )
            return line
        else:
            ret = self._next
            self._next = None
            return ret


class SafeProxyFileObject:

    def __init__(self, name, *validation_functions):
        self.__dict__["__file"] = open(name, mode='rb')
        self.__dict__["__validation_functions"] = validation_functions

    def readline(self):
        line = self.__dict__['__file'].readline().rstrip(b"\r\n")
        for validation_func in self.__dict__['__validation_functions']:
            line = validation_func(line)
        return line + "\n"

    def readlines(self):
        def yielder():
            size = os.fstat(self.fileno()).st_size
            while size != self.tell():
                yield self.readline()
        return [line for line in yielder()]

    def __getattr__(self, item):
        return getattr(self.__dict__['__file'], item)
