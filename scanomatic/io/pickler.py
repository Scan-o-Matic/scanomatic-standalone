import os
from pickle import load
from typing import IO


def unpickle(path: str):
    """Unpickles data safely
    Returns: Unpickled object
    """
    return load(safe_load(path))


def safe_load(path, return_string=False):
    version_compatibility = _RefactoringPhases()
    fh = SafeProxyFileObject(path, version_compatibility)
    version_compatibility.io = fh
    if return_string:
        return os.linesep.join(fh.readlines())
    else:
        return fh


def unpickle_with_unpickler(unpickler, path, *args, **kwargs):
    """Compatibility unpickler that handles problems

    This is used for

    1) Dealing with errors in line-endings in data sent between different OS
    2) Dealing with SoM refactoring import errors

    Args:
        unpickler (func): A function that unpickles a string of data
        path (str): Path to the data to be unpickled
        *args: Optional extra arguments for the unpickler
        **kwargs: Opional extra keyword arguments for the unpickler

    Returns: Unpickled object
    """
    return unpickler(safe_load(path), *args, **kwargs)


class _RefactoringPhases:
    def __init__(self):
        """Rewrites pickled data to match refactorings"""
        self._next = None
        self.io = None

    def __call__(self, line: str):
        """
        Args:
            line (str): A pickled line
        """
        if not isinstance(self.io, IO):
            raise AttributeError("Attribute 'io' not initialized properly")
        if self._next is None:
            if line.endswith(
                "scanomatic.data_processing.curve_phase_phenotypes",
            ):
                tell = self.io.tell()
                _next = self.io.readline()
                self.io.seek(tell)

                if _next.startswith('VectorPhenotypes'):
                    return (
                        line[:-49]
                        + "scanomatic.data_processing.phases.features"
                    )
                elif _next.startswith('CurvePhasePhenotypes'):
                    return (
                        line[:-49]
                        + "scanomatic.data_processing.phases.analysis"
                    )
                elif _next.startswith('CurvePhases'):
                    return (
                        line[:-49]
                        + "scanomatic.data_processing.phases.segmentation"
                    )
                elif _next.startswith('CurvePhaseMetaPhenotypes'):
                    return (
                        line[:-49]
                        + "scanomatic.data_processing.phases.features"
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
        line = self.__dict__['__file'].readline().rstrip("\r\n")
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
