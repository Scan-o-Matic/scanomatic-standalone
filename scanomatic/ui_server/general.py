import base64
import glob
import os
import re
import zipfile
from collections.abc import Sequence
from io import BytesIO, IOBase
from itertools import chain
from typing import Optional, Union
from urllib.parse import quote, unquote

import numpy as np
from flask import jsonify, render_template, send_file
from PIL import Image
from werkzeug.datastructures import FileStorage

from scanomatic.image_analysis.first_pass_image import FixtureImage
from scanomatic.image_analysis.grayscale_detection import is_valid_grayscale
from scanomatic.image_analysis.grayscale import Grayscale
from scanomatic.io.app_config import Config
from scanomatic.io.jsonizer import load_first
from scanomatic.io.logger import get_logger, parse_log_file
from scanomatic.io.paths import Paths
from scanomatic.models.factories.fixture_factories import (
    FixturePlateFactory,
    GrayScaleAreaModelFactory
)
from scanomatic.models.fixture_models import (
    FixturePlateModel,
    GrayScaleAreaModel
)

_safe_dir = re.compile(
    r"^[A-Za-z_0-9.%/ \\]*$" if os.sep == "\\" else r"^[A-Za-z_0-9.%/ ]*$",
)
_no_super = re.compile(r"/?\.{2}/")
_logger = get_logger("UI API helpers")
_ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.tiff'}
_TOO_LARGE_GRAYSCALE_AREA = 300000


def json_abort(
    status_code,
    success=False,
    is_endpoint=True,
    reason="",
    *args,
    **kwargs,
):
    response = jsonify(
        success=success,
        is_endpoint=is_endpoint,
        reason=reason,
        *args,
        **kwargs,
    )
    response.status_code = status_code
    return response


def image_is_allowed(ext):
    """Validates that the image extension is allowed

    :param ext: The image file's extension
    :type ext: str
    :returns bool
    """
    global _ALLOWED_EXTENSIONS
    return ext.lower() in _ALLOWED_EXTENSIONS


def string_parse_2d_list(data_string, dtype=float):

    if not isinstance(data_string, str):
        return None

    p1 = re.compile(r'\[[^\]\[]+\]')
    p2 = re.compile(r'(\d+\.?\d*|\.\d+)')

    parsed = [p2.findall(f) for f in p1.findall(data_string)]
    if all(len(p) == len(parsed[0]) for p in parsed):
        try:
            return [[dtype(v) for v in item] for item in parsed]
        except ValueError:
            return []


def get_2d_list(
    data,
    key,
    getlist_kwargs=None,
    use_fallback=True,
    dtype=float,
):
    """

    :param data: Example a request.values
    :param key: The key used without list marks
    :return: Nested tuples.
    """

    key += "[{0}][]"

    if getlist_kwargs is None:
        getlist_kwargs = {}

    def _list_enumerator():
        i = 0
        while True:
            tmp = key.format(i)
            if tmp in data:
                yield tmp
                i += 1
            else:
                break

    value = tuple(
        data.getlist(k, **getlist_kwargs) for k in _list_enumerator()
    )

    if not value and use_fallback:
        value = string_parse_2d_list(data.get(key, type=dtype))

    return value


def valid_array_dimensions(dims, *arrs):
    for arr in arrs:
        try:
            if arr.ndim != dims:
                return False
        except (AttributeError, TypeError):
            return False
    return True


def get_area_too_large_for_grayscale(
    grayscale_area_model: GrayScaleAreaModel,
) -> bool:
    global _TOO_LARGE_GRAYSCALE_AREA
    area_size = (
        (grayscale_area_model.x2 - grayscale_area_model.x1)
        * (grayscale_area_model.y2 - grayscale_area_model.y1)
    )
    return area_size > _TOO_LARGE_GRAYSCALE_AREA


def get_grayscale_is_valid(values, grayscale: Grayscale):
    if values is None:
        return False
    return is_valid_grayscale(grayscale.targets, values)


def usable_plates(plates):

    def usable_plate(plate: FixturePlateModel):
        return plate.x2 > plate.x1 and plate.y2 > plate.y1

    def unique_valid_indices():
        return tuple(
            sorted(plate.index - 1 for plate in plates)
        ) == tuple(range(len(plates)))

    if not all(usable_plate(plate) for plate in plates):
        _logger.warning("Some plate coordinates are wrong")
        return False
    elif not unique_valid_indices():
        _logger.warning("Plate indices are bad")
        return False
    elif len(plates) == 0:
        _logger.warning("No plates")
        return False
    return True


def safe_directory_name(name):
    return _safe_dir.match(name) is not None and _no_super.search(name) is None


def convert_url_to_path(url):
    if url is None:
        url = ""
    else:
        url = unquote(url).split("/")
    root = Config().paths.projects_root
    return os.path.abspath(os.path.join(*chain([root], url)))


def convert_path_to_url(prefix, path):
    if prefix:
        path = "/".join(chain(
            [prefix],
            os.path.relpath(path, Config().paths.projects_root).split(os.sep),
        ))
    else:
        path = "/".join(
            os.path.relpath(path, Config().paths.projects_root).split(os.sep),
        )

    path = quote(path.encode('utf8'))
    if safe_directory_name(path):
        return path
    return None


def path_is_in_jail(path):
    return Config().paths.projects_root in path


def get_search_results(path, url_prefix):
    projects = _get_possible_paths(path)
    names = list(get_project_name(p) for p in projects)
    urls = list(convert_path_to_url(url_prefix, p) for p in projects)
    if None in urls:
        try:
            names, urls = zip(
                *tuple((n, u) for n, u in zip(names, urls) if u is not None),
            )
        except ValueError:
            pass
    return {'names': names, 'urls': urls}


def _get_possible_paths(path):
    dirs = tuple()
    root = None
    for root, dirs, _ in os.walk(path, followlinks=True):
        break

    if root is None:
        return tuple()
    return tuple(os.path.join(root, d) for d in dirs)


def get_project_name(project_path):
    no_name = None
    if not path_is_in_jail(project_path):
        return no_name

    candidates = glob.glob(
        os.path.join(
            project_path,
            Paths().scan_project_file_pattern.format("*"),
        ),
    )
    if candidates:
        for candidate in candidates:
            model = load_first(candidate)
            if model:
                return model.project_name if model.project_name else no_name

    if project_path:
        return get_project_name(os.path.dirname(project_path))

    return no_name


def strip_empty_exits(exits: list[str], data: dict):
    """
        :param exits : Exit keys
        :type exits : list[str]

        :param data : Data dict
        :type data : dict
    """
    all_exits = [e for e in exits]

    for e in all_exits:
        if e in data and (data[e] is None or len(data[e]) == 0):
            _logger.info(f"Removing {e} from exits because {data[e]} is empty")
            del data[e]
            exits.remove(e)
            _logger.info(f"Exits now {exits}")
        elif e not in data:
            exits.remove(e)
            _logger.info(
                f"Removing {e} from exits because not in data {data}, exits now {exits}",  # noqa: E501
            )


def json_response(exits, data, success=True):
    strip_empty_exits(exits, data)
    is_endpoint = len(exits) == 0
    data["is_endpoint"] = is_endpoint

    if success is not None:
        data["success"] = success

    if is_endpoint:
        if "exits" in data:
            del data["exits"]
    else:
        data["exits"] = exits

    return data


def get_common_root_and_relative_paths(*file_list):

    dir_list = set(tuple(
        os.path.dirname(f) if os.path.isfile(f) else f
        for f in file_list
    ))
    common_test = zip(*(p.split(os.sep) for p in dir_list))
    root = ""
    for d_list in common_test:
        if all(d == d_list[0] for d in d_list):
            root = os.path.join(root, d_list[0])
        else:
            break
        if not root:
            root = os.path.sep

    root += os.path.sep
    start_at = len(root)
    return root, tuple(f[start_at:] for f in file_list)


def serve_zip_file(zip_name, *file_list):
    """Serves a zip-file created from a file list

    Code inspired by:
    http://stackoverflow.com/questions/2463770/python-in-memory-zip-library#2463818

    The filesystem in the zip will use the deepest common denominator in the
    filelist as its root.

    :param file_list: local paths
    :return: Flask sending of data
    """

    # file_list = tuple(str(f) for f in file_list)
    data_buffer = BytesIO()
    zf = zipfile.ZipFile(data_buffer, 'a', zipfile.ZIP_DEFLATED, False)
    root, local_names = get_common_root_and_relative_paths(*file_list)
    for local_file in local_names:
        print("{0}  {1}".format(local_file, os.path.join(root, local_file)))
        zf.write(os.path.join(root, local_file), local_file)

    for zfile in zf.filelist:
        zfile.create_system = 0

    zf.close()

    data_buffer.flush()
    data_buffer.seek(0)

    return send_file(
        data_buffer,
        mimetype='application/zip, application/octet-stream',
        as_attachment=True,
        attachment_filename=str(zip_name),
    )


def serve_pil_image(pil_img: Image):
    img_io = BytesIO()
    pil_img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')


def serve_numpy_as_image(data):
    return serve_pil_image(Image.fromarray(data))


def get_fixture_image_by_name(name, ext="tiff"):

    fixture_file = Paths().get_fixture_path(name)
    image_path = os.path.extsep.join((fixture_file, ext))
    return get_fixture_image(name, image_path)


def get_fixture_image(name, image_path) -> FixtureImage:
    fixture = FixtureImage(reference_overwrite_mode=True)
    fixture.name = name
    fixture.set_image(image_path=image_path)
    return fixture


def pad_decode_base64(data: Union[bytes, str]) -> bytes:
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += b'=' * (4 - missing_padding)
    return base64.b64decode(data)


def remove_pad_decode_base64(data: Union[bytes, str]) -> bytes:
    if isinstance(data, str):
        data = data.encode("utf-8")

    remainder = len(data) % 4
    return base64.b64decode(data[:-remainder if remainder else 4])


def get_image_data_as_array(
    image_data: Union[list, IOBase, FileStorage, str, np.array],
    reshape: Optional[Union[list[int], tuple[int, ...]]] = None,
) -> np.array:
    if isinstance(image_data, str):
        stream = BytesIO()
        stream.write(image_data.encode())
        stream.flush()
        stream.seek(0)
        try:
            return np.array(Image.open(stream))
        except (UnicodeDecodeError, IOError):
            try:
                im_bytes = pad_decode_base64(image_data)
            except Exception:
                im_bytes = remove_pad_decode_base64(image_data)
            stream = BytesIO()
            stream.write(im_bytes)
            stream.flush()
            stream.seek(0)
            return np.array(Image.open(stream))
    elif isinstance(image_data, list):
        if reshape is None:
            return np.array(image_data)
        else:
            return np.array(image_data).reshape(reshape)
    elif (
        isinstance(image_data, IOBase)
        or isinstance(image_data, FileStorage)
    ):
        return np.array(Image.open(image_data))

    else:
        return image_data


def get_fixture_image_from_data(
    name: str,
    image_data: FileStorage,
) -> FixtureImage:
    fixture = FixtureImage(reference_overwrite_mode=True)
    fixture.name = name
    fixture.set_image(image=get_image_data_as_array(image_data))
    return fixture


def usable_markers(markers, image):

    def marker_inside_image(marker):
        """Compares marker to image shape

        Note that image shape comes in y, x order while markers come in x, y
        order

        Args:
            marker: (x, y) coordinates
        """
        val = (
            (marker > 0).all()
            and marker[0] < image.shape[1]
            and marker[1] < image.shape[0]
        )
        if not val:
            _logger.error(f"Marker {marker} is outside image {image.shape}")
        return val

    try:
        markers_array = np.array(markers, dtype=float)
    except ValueError:
        return False

    if (
        markers_array.ndim != 2
        or markers_array.shape[0] < 3
        or markers_array.shape[1] != 2
    ):
        _logger.error(f"Markers have bad shape {markers}")
        return False

    if len(set(map(tuple, markers_array))) != len(markers):
        _logger.error(f"Some marker is duplicated {markers}")
        return False

    return all(marker_inside_image(marker) for marker in markers_array)


def split_areas_into_grayscale_and_plates(
    areas: Sequence,
) -> tuple[GrayScaleAreaModel, list[FixturePlateModel]]:
    gs = None
    plates = []
    for area in areas:
        try:
            if area['grayscale']:
                gs = GrayScaleAreaModelFactory.create(
                    x1=area['x1'],
                    x2=area['x2'],
                    y1=area['y1'],
                    y2=area['y2'],
                )
            else:
                plates.append(
                    FixturePlateFactory.create(
                        x1=area['x1'],
                        x2=area['x2'],
                        y1=area['y1'],
                        y2=area['y2'],
                        index=area['plate']
                    ),
                )

        except (AttributeError, KeyError, TypeError):
            _logger.warning(
                f"Bad data: '{area}' does not have the expected area attributes",  # noqa: E501
            )

    return gs, plates


def serve_log_as_html(log_path, title):
    data = parse_log_file(log_path)
    data['garbage'] = [line.replace("\n", "<br>") for line in data['garbage']]
    for e in data['records']:
        e['message'] = e['message'].split("\n")

    if data:
        return render_template(
            Paths().ui_log_template,
            title=title,
            **data,
        )
    else:
        return render_template(
            Paths().ui_log_not_found_template,
            title=title,
        )
