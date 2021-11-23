import os
import time
import webbrowser
from socket import error
from threading import Thread

import requests
from flask import Flask, send_from_directory
from flask_cors import CORS  # type: ignore

from scanomatic.io.app_config import Config
from scanomatic.io.logger import get_logger
from scanomatic.io.paths import Paths
from scanomatic.io.rpc_client import get_client
from scanomatic.io.scanstore import ScanStore

from . import (
    analysis_api,
    calibration_api,
    compilation_api,
    data_api,
    experiment_api,
    management_api,
    qc_api,
    scan_api,
    settings_api,
    status_api,
    tools_api,
    ui_pages
)

_URL = None
_LOGGER = get_logger(
    "UI-server",
    Paths().log_ui_server,
)
_DEBUG_MODE = None


def launch_server(host, port, debug):

    global _URL, _DEBUG_MODE
    _DEBUG_MODE = debug
    app = Flask("Scan-o-Matic UI", template_folder=Paths().ui_templates)
    app.config['scanstore'] = ScanStore(Config().paths.projects_root)

    rpc_client = get_client(admin=True)

    if rpc_client.local and rpc_client.online is False:
        rpc_client.launch_local()

    if port is None:
        port = Config().ui_server.port
    if host is None:
        host = Config().ui_server.host

    _URL = f"http://{host}:{port}"
    _LOGGER.info(
        f"Requested to launch UI-server at {_URL} being debug={debug}",
    )

    add_resource_routes(app, rpc_client)

    ui_pages.add_routes(app)

    management_api.add_routes(app, rpc_client)
    tools_api.add_routes(app)
    qc_api.add_routes(app)
    analysis_api.add_routes(app)
    compilation_api.add_routes(app)
    scan_api.add_routes(app)
    status_api.add_routes(app, rpc_client)
    data_api.add_routes(app, rpc_client, debug)
    app.register_blueprint(
        calibration_api.blueprint, url_prefix="/api/calibration",
    )
    settings_api.add_routes(app)
    experiment_api.add_routes(app, rpc_client)

    if debug:
        CORS(app)
        _LOGGER.warning(
            "\nRunning in debug mode, causes sequrity vunerabilities:\n"
            " * Remote code execution\n"
            " * Cross-site request forgery\n"
            "   (https://en.wikipedia.org/wiki/Cross-site_request_forgery)\n"
            "\nAnd possibly more issues"
        )
    try:
        app.run(port=port, host=host, debug=debug)
    except error:
        _LOGGER.warning(
            "Could not bind socket, probably server is already running and"
            " this is nothing to worry about."
            "\n\tIf old server is not responding, try killing its process."
            "\n\tIf something else is blocking the port,"
            " try setting another port"
            " (see `scan-o-matic --help` for instructions)."
        )
        return False
    return True


def add_resource_routes(app, rpc_client):
    """

    :param app: The flask webb app
     :type app: Flask
    :return:
    """

    @app.route("/images/<image_name>")
    def _image_base(image_name=None):
        if image_name:
            return send_from_directory(Paths().images, image_name)

    @app.route("/style/<style>")
    def _css_base(style=None):
        if style:
            return send_from_directory(Paths().ui_css, style)

    @app.route("/js/<js>")
    def _js_base(js=None):
        if js:
            return send_from_directory(Paths().ui_js, js)

    @app.route("/js/<group>/<js>")
    def _js_external(group, js):
        return send_from_directory(os.path.join(Paths().ui_js, group), js)

    @app.route("/fonts/<font>")
    def _font_base(font=None):
        if font:
            return send_from_directory(Paths().ui_font, font)


def launch_webbrowser(delay=0.0) -> None:
    if delay:
        _LOGGER.info(f"Will open webbrowser in {delay} s")
        time.sleep(delay)

    if _URL:
        webbrowser.open(_URL)
    else:
        _LOGGER.error("No server launched")


def launch(host, port, debug, open_browser_url=True) -> None:
    if open_browser_url:
        _LOGGER.info("Getting ready to open browser")
        Thread(target=launch_webbrowser, kwargs={"delay": 2}).start()
    else:
        _LOGGER.info("Will not open browser")

    launch_server(host, port, debug)


def ui_server_responsive() -> bool:

    port = Config().ui_server.port
    if not port:
        port = 5000
    host = Config().ui_server.host
    if not host:
        host = 'localhost'
    try:
        return requests.get(f"http://{host}:{port}").ok
    except requests.ConnectionError:
        return False
