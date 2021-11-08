import os
import sys
import time
from logging import Logger

import numpy as np
from PIL import Image

import scanomatic.io.app_config as app_config

_logger = Logger("Resource Analysis Support")


def save_image_as_png(from_path, **kwargs):

    file, _ = os.path.splitext(from_path)
    im = Image.open(from_path)
    try:
        im.save(os.path.extsep.join((file, "png")), **kwargs)
    except IOError:
        if im.mode == 'I;16':
            im2 = im.point(lambda i: i * (1. / 256))
            im2.mode = 'L'
            data = np.array(
                im2.getdata(),
                dtype=np.uint8,
            ).reshape(im2.size[::-1])
            Image.fromarray(data).save(
                os.path.extsep.join((file, "png")),
                **kwargs,
            )
            _logger.info("Attempted conversion to 8bit PNG format")
        else:
            raise TypeError(
                "Don't know how to process images of type {0}".format(im.mode),
            )


def get_first_rotated(A, B):
    """Evaluates if both have the same orientation (lanscape or standing)
    returns the first so it matches the orientation of the second

    A   numpy arrray to be evaluted
    B   reference array or a shape-tuple

    returns A
    """
    landscapeA = A.shape[0] > A.shape[1]
    if isinstance(B, tuple):
        landscapeB = B[0] > B[1]
    else:
        landscapeB = B.shape[0] > B.shape[1]

    if landscapeA == landscapeB:
        return A
    else:
        return A.T


def get_active_plates(
    meta_data,
    suppress_analysis,
    graph_watch,
    config=None,
):
    """Makes list of only relevant plates according to how
    analysis was started"""

    if config is None:
        config = app_config.Config()

    plate_position_keys = []

    if meta_data['Version'] >= config.versions.first_pass_change_1:
        v_offset = 1
    else:
        v_offset = 0

    for i in range(len(meta_data['Pinning Matrices'])):
        if (
            (suppress_analysis is False or graph_watch[0] == i)
            and meta_data['Pinning Matrices'][i] is not None
        ):
            plate_position_keys.append("plate_{0}_area".format(i + v_offset))

    plates = len(plate_position_keys)

    return plates, plate_position_keys


def verify_outdata_directory(outdata_directory):
    """Verifies that outdata directory exists and if not tries to create
    one. Also corrects path so that it doesn't end with separator"""

    if not os.path.isdir(outdata_directory):
        dir_OK = False
        if not os.path.exists(outdata_directory):
            try:
                os.makedirs(outdata_directory)
                dir_OK = True
            except Exception:
                pass
        if not dir_OK:
            _logger.critical(
                "ANALYSIS, Could not construct outdata directory,"
                " could be a conflict"
            )
            sys.exit()

    if outdata_directory[-1] == os.sep:
        return outdata_directory[:-1]
    else:
        return outdata_directory


def get_pinning_matrices(query, sep=':'):
    """The function takes a string and parses it
    for known pinning matrix formats"""
    PINNING_MATRICES = {
        (8, 12): ['8,12', '96'],
        (16, 24): ['16,24', '384'],
        (32, 48): ['32,48', '1536'],
        (64, 96): ['64,96', '6144'],
        None: ['none', 'no', 'n', 'empty', '-', '--']
    }

    plate_strings = query.split(sep)
    plates = len(plate_strings) * [None]

    for i, p in enumerate(plate_strings):

        result = [
            k for k, v in list(PINNING_MATRICES.items())
            if p.lower().replace(" ", "").strip("()") in v
        ]

        if len(result) == 1:
            plates[i] = result[0]
        elif len(result) > 1:
            _logger.warning(
                f"Ambigous plate pinning matrix statement '{p}'",
            )
        else:
            _logger.warning(
                f"Bad pinning pattern '{p}' - ignoring that plate"
            )

    return plates


def print_progress_bar(fraction=0.0, size=40, start_time=None):
    """Prints an ascii progress bar"""
    prog_str = "["
    percent = 100 * fraction
    pfraction = fraction * size
    pfraction = int(round(pfraction))

    prog_str = "[" + pfraction * "=" + (size - pfraction) * " " + "]"
    perc_str = "%.1f" % (percent) + " %"

    prog_l = len(prog_str)
    perc_l = len(perc_str)

    prog_str = (
        prog_str[:prog_l / 2 - perc_l / 2]
        + perc_str
        + prog_str[prog_l / 2 + perc_l:]
    )
    print("\r{0}".format(prog_str), end=' ')

    if start_time is not None:

        elapsed = time.time() - start_time
        eta = elapsed / fraction + start_time
        print(" ETA: {0}".format(time.asctime(time.localtime(eta))), end=' ')

    sys.stdout.flush()


def get_finds_fixture(name, directory=None):
    return True


def get_run_will_do_something(
    suppress_analysis,
    graph_watch,
    meta_data,
    image_dictionaries,
):
    # Verifying sanity of request: Suppression requires watching?
    if suppress_analysis:
        if graph_watch is None or len(graph_watch) == 0:
            _logger.critical(
                "ANALYSIS: You are effectively requesting to"
                " do nothing,\nso I guess I'm done...\n(If you suppress"
                " analysis of non-watched colonies, then you need to watch"
                " one as well!)"
            )
            return False

        elif (
            graph_watch[0] >= len(meta_data['Pinning Matrices'])
            or graph_watch[0] < 0
            or meta_data['Pinning Matrices'][graph_watch[0]] is None
        ):

            _logger.critical(
                "ANALYSIS: That plate ({0}) does not exist".format(
                    graph_watch[0]
                ) + " or doesn't have a pinning!",
            )
            return False

        else:
            pm = meta_data['Pinning Matrices'][graph_watch[0]]

            if (
                graph_watch[1] >= pm[0]
                or graph_watch[1] < 0
                or graph_watch[2] >= pm[1]
                or graph_watch[2] < 0
            ):
                _logger.critical(
                    "ANALYSIS: The watch colony cordinate"
                    " ({0}) is out of bounds on plate {1}.".format(
                        graph_watch[1:],
                        graph_watch[0],
                    ),
                )
                return False

        return True


class Watch_Graph:
    """The Watch Graph is a composite data graph for a colony"""

    PLATE = 0
    X = 1
    Y = 1
    IM_WIDTH = -1
    IM_HEIGHT = -2
    IMAGES = 0

    def __init__(self, watch_id, outdata_directory, nBins=128):
        self._watch = watch_id
        self._path = os.path.join(
            outdata_directory,
            "watch_image__plate_{0}_pos_{1}_{2}".format(
                self._watch[self.PLATE],
                self._watch[self.X],
                self._watch[self.Y],
            ),
        )
        self._data = None
        self._bigIM = None
        self._nBins = nBins
        self._histogramCounts = None
        self._histogramBins = None

    def _save_npy(self):
        np.save("{0}.npy".format(self._path), self._data)

    def _save_image(self):

        img = Image.fromarray(
            np.clip(
                self._bigIM / self._bigIM.max() * 255,
                0,
                255,
            ).astype("uint8"),
            "L",
        )
        # img = Image.fromarray(
        #     np.asarray(
        #         np.clip(self._bigIM, 0, 255),
        #         dtype="uint8",
        #     ),
        #     "L",
        # )
        img.save("{0}.tiff".format(self._path))

    def _save_histograms(self):

        np.save(self._path + "HistCounts.npy", self._histogramCounts)
        np.save(self._path + "HistBins.npy", self._histogramBins)

    def _build_image(self):

        padding = 2
        vPadding = np.zeros((self._data.shape[self.IM_HEIGHT], padding))
        hPadding = np.zeros((
            padding,
            2 * self._data.shape[self.IM_WIDTH] + padding,
        ))

        for imageIndex in range(self._data.shape[self.IMAGES]):
            A = self._data[imageIndex][0]
            B = self._data[imageIndex][1]

            if A.max() > 0:
                A = A / float(A.max()) * 255

            curImage = np.c_[A, vPadding, (B * 255).astype(int)]

            if self._bigIM is None:
                self._bigIM = curImage

            else:
                self._bigIM = np.r_[curImage, hPadding, self._bigIM]

    def add_image(self, im, detection):

        if im is None or detection is None:
            return
        composite = np.array(((im, detection),))
        if self._data is None:
            self._data = composite
        else:
            self._data = np.r_[self._data, composite]

    def finalize(self):

        self._save_npy()
        self._build_image()
        self._save_image()
        # self._save_histograms()
