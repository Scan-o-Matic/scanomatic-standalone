import re
from typing import Optional, Union
import logging
from scanomatic.io.paths import Paths

_FORMAT = '%(asctime)s -- %(levelname)s\t**%(name)s** %(msg)s'
_DATEFMT = '%Y-%m-%d %H:%M:%S'
_FORMATTER = logging.Formatter(fmt=_FORMAT, datefmt=_DATEFMT)
_HANDLERS: dict[str, Union[logging.FileHandler, logging.StreamHandler]] = {}
"""
_USERS: defaultdict[
    logging.FileHandler,
    list[logging.Logger],
] = defaultdict(list)
"""

logging.basicConfig(
    Paths().log_ui_server,
    encoding='utf-8',
    level=logging.INFO,
    datefmt=_DATEFMT,
    format=_FORMAT
)

LOG_RECYCLE_TIME = 60 * 60 * 24
LOG_PARSING_EXPRESSION = re.compile(
    r"(\d{4}-\d{1,2}-\d{1,2}) (\d{1,2}:\d{1,2}:\d{1,2}) -- (\w+)\t\*{2}([^\*]+)\*{2}(.*)",  # noqa: E501
)


def get_file_handler(file_path: str) -> logging.FileHandler:
    if file_path in _HANDLERS:
        return _HANDLERS[file_path]
    handler = logging.FileHandler(
        file_path,
        mode='w',
        encoding='utf-8',
    )
    handler.setFormatter(_FORMATTER)
    _HANDLERS[file_path]
    return handler


def get_logger(name: str, file_path: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if file_path is not None:
        handler = get_file_handler(file_path)
        logger.addHandler(handler)
        # _USERS[handler].append(logger)
    return logger


def set_logging_target(logger: logging.Logger, path: str):
    """
    while logger.handlers:
        logger.removeHandler(logger.handlers[0])
    handler = logging.FileHandler(path, encoding='utf-8')
    logger.addHandler(handler)
    """
    raise ValueError("Those loggers should be using get_logger...")


class XLogger:
    _LOGFORMAT = "%Y-%m-%d %H:%M:%S -- {lvl}\t**{name}** "

    @property
    def surpress_prints(self) -> bool:
        return self._suppressPrints

    @surpress_prints.setter
    def surpress_prints(self, value: bool):
        self._suppressPrints = value


def parse_log_file(path, seek=0, max_records=-1, filter_status=None):
    with open(path, 'r') as fh:

        if seek:
            fh.seek(seek)

        n = 0
        pattern = LOG_PARSING_EXPRESSION

        records = []
        tell = fh.tell()
        garbage = []
        record = {}
        eof = False
        while n < max_records or max_records < 0:

            line = fh.readline()
            if tell == fh.tell():
                eof = True
                break
            else:
                tell = fh.tell()

            match = pattern.match(line)

            if match:
                if (
                    record
                    and (
                        filter_status is None
                        or record['status'] in filter_status
                    )
                ):
                    records.append(record)
                    n += 1
                groups = match.groups()
                record = {
                    'date': groups[0],
                    'time': groups[1],
                    'status': groups[2],
                    'source': groups[3],
                    'message': groups[4].strip()
                }
            elif record:
                record['message'] += '\n{0}'.format(line.rstrip())
            else:
                garbage.append(line.rstrip())

        return {
            'file': path,
            'start_position': seek,
            'end_position': tell,
            'end_of_file': eof,
            'records': records,
            'garbage': garbage
        }
