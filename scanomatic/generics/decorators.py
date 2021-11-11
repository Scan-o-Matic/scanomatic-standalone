import datetime
import multiprocessing
import time
from inspect import ismethod
from logging import Logger
from threading import Thread
from multiprocessing.synchronize import RLock


class UnknownLock(KeyError):
    pass


def _get_id_tuple(f, args, kwargs, mark=object()):
    ids = [id(f)]
    for arg in args:
        ids.append(id(arg))
    ids.append(id(mark))
    for k, v in kwargs:
        ids.append(k)
        ids.append(id(v))
    return tuple(ids)


_MEMOIZED = {}


def memoize(f):
    def memoized(*args, **kwargs):
        key = _get_id_tuple(f, args, kwargs)
        if key not in _MEMOIZED:
            _MEMOIZED[key] = f(*args, **kwargs)
        return _MEMOIZED[key]
    return memoized


_TIME_LOGGER = Logger("Time It")


def timeit(f):

    def timer(*args, **kwargs):
        t = time.time()
        _TIME_LOGGER.info("Calling {0}".format(f))
        ret = f(*args, **kwargs)
        _TIME_LOGGER.info("Call to {0} lasted {1}".format(
            f,
            str(datetime.timedelta(seconds=time.time() - t)),
        ))
        return ret

    return timer


_PATH_LOCK: dict[str, RLock] = {}


def path_lock(f):

    def _acquire(path):
        global _PATH_LOCK
        try:
            while not _PATH_LOCK[path].acquire(False):
                time.sleep(0.05)
        except KeyError:
            raise UnknownLock(
                "Path '{0}' not registered by {1}".format(
                    path,
                    register_path_lock,
                )
            )

    def locking_wrapper_method(self_cls, path, *args, **kwargs):
        global _PATH_LOCK
        _acquire(path)
        ret = f(self_cls, path, *args, **kwargs)
        _PATH_LOCK[path].release()
        return ret

    def locking_wrapper_function(path, *args, **kwargs):
        global _PATH_LOCK
        _acquire(path)
        try:
            result = f(path, *args, **kwargs)
        except Exception as e:
            _PATH_LOCK[path].release()
            raise e
        _PATH_LOCK[path].release()
        return result

    if ismethod(f):
        return locking_wrapper_method
    else:
        return locking_wrapper_function


def register_path_lock(path):
    global _PATH_LOCK
    _PATH_LOCK[path] = multiprocessing.RLock()


_TYPE_LOCK = {}


def register_type_lock(object_instance):
    global _TYPE_LOCK
    _TYPE_LOCK[type(object_instance)] = multiprocessing.RLock()


def type_lock(f):
    def _acquire(object_type):
        global _TYPE_LOCK
        try:
            while not _TYPE_LOCK[object_type].acquire():
                time.sleep(0.05)
        except KeyError:
            raise UnknownLock("{0} never registered by {1}".format(
                object_type,
                register_type_lock,
            ))

    def locking_wrapper(self, *args, **kwargs):
        global _TYPE_LOCK
        object_type = type(self)
        _acquire(object_type)
        try:
            result = f(self, *args, **kwargs)
        except Exception as e:
            Logger("Type Lock").critical(
                "Something failed attempting to call {0} with '{1}' as args and '{2}' as kwargs".format(  # noqa: E501
                    f,
                    args,
                    kwargs,
                ))
            _TYPE_LOCK[object_type].release()
            raise e
        _TYPE_LOCK[object_type].release()
        return result

    return locking_wrapper


def threaded(f):

    def _threader(*args, **kwargs):
        thread = Thread(target=f, args=args, kwargs=kwargs)
        thread.start()

    return _threader
