import logging
import re
from os import makedirs
from pathlib import Path
from typing import Optional
from collections import Sequence

_FORMAT = '%(asctime)s -- %(levelname)s\t**%(name)s** %(msg)s'
_DATEFMT = '%Y-%m-%d %H:%M:%S'
_FORMATTER = logging.Formatter(fmt=_FORMAT, datefmt=_DATEFMT)
_HANDLERS: dict[str, logging.FileHandler] = {}
_LOG_PARSING_EXPRESSION = re.compile(
    r"(\d{4}-\d{1,2}-\d{1,2}) (\d{1,2}:\d{1,2}:\d{1,2}) -- (\w+)\t\*{2}([^\*]+)\*{2}(.*)",  # noqa: E501
)

logging.basicConfig(
    level=logging.INFO,
    datefmt=_DATEFMT,
    format=_FORMAT
)


def get_file_handler(file_path: str) -> logging.FileHandler:
    if file_path in _HANDLERS:
        return _HANDLERS[file_path]
    makedirs(Path(file_path).parent, exist_ok=True)
    handler = logging.FileHandler(
        file_path,
        mode='w',
        encoding='utf-8',
    )
    handler.setFormatter(_FORMATTER)
    _HANDLERS[file_path] = handler
    return handler


def get_logger(name: str, file_path: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if file_path is not None:
        handler = get_file_handler(file_path)
        logger.addHandler(handler)
    return logger


def parse_log_file(path, seek=0, max_records=-1, filter_status=None):
    with open(path, 'r') as fh:

        if seek:
            fh.seek(seek)

        n = 0
        pattern = _LOG_PARSING_EXPRESSION

        records = []
        tell = fh.tell()
        garbage = []
        record: dict[str, str] = {}
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
                groups: Sequence[str] = match.groups()
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
