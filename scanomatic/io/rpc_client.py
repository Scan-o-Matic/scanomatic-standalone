import enum
import socket
import xmlrpc.client
from collections.abc import Callable
from http.client import CannotSendRequest, ResponseNotReady
from subprocess import Popen
from types import GeneratorType
from typing import Optional

import scanomatic.io.app_config as app_config
from scanomatic.io.logger import get_logger


def sanitize_communication(obj):
    if isinstance(obj, dict):
        return {
            str(k): sanitize_communication(v) for k, v in obj.items()
            if v is not None
        }
    elif (
        isinstance(obj, list)
        or isinstance(obj, tuple)
        or isinstance(obj, set)
    ):
        return type(obj)(
            False if v is None else sanitize_communication(v) for v in obj
        )
    elif isinstance(obj, enum.Enum):
        return obj.name
    elif isinstance(obj, GeneratorType):
        return tuple(
            False if v is None else sanitize_communication(v) for v in obj
        )
    elif obj is None:
        return False
    elif isinstance(obj, type(None)):
        return str(obj)
    else:
        return obj


def get_client() -> "_ClientProxy":
    config = app_config.Config()
    port = config.rpc_server.port
    host = config.rpc_server.host
    user_id = config.rpc_server.admin
    assert isinstance(port, int), "RPC Server port not known"
    assert isinstance(host, str), "RPC Server host not known"
    assert isinstance(user_id, str), "RPC Client user id not known"
    return _ClientProxy(host, port, user_id)


class _ClientProxy:
    def __init__(self, host: str, port: int, user_id: str):

        self._logger = get_logger("Client Proxy")
        self._user_id = user_id
        self._admin_methods = (
            'get_power_manager_info',
            'communicate',
            'create_feature_extract_job',
            'create_compile_project_job',
            'create_analysis_job',
            'create_scanning_job',
            'restart',
            'shutdown',
            'request_scanner_opteration',
            'remove_from_queue',
            'flush_queue',
            'reestablish_process',
        )

        self._client = None
        self._host = None
        self._port = None

        self.host = host
        self.port = port

    def launch_local(self) -> None:
        if self.online is False and self.local:
            self._logger.info("Launching new local server")
            Popen(["scan-o-matic_server"])
        else:
            self._logger.warning(
                "Can't launch because server is {0}".format(
                    ['not local', 'online'][self.online],
                )
            )

    def __getattr__(self, key):
        if key in self._allowed_methods() and self._client is not None:
            m = self.user_id_decorator(getattr(self._client, key))
            m.__doc__ = (
                self._client.system.methodHelp(key) +
                ["", "\n\nNOTE: user_id is already supplied"][
                    self._user_id is not None
                ]
            )
            return m
        raise AttributeError(f"Client doesn't support attribute {key}")

    def __dir__(self):
        return list(self._allowed_methods())

    def _setupClient(self):
        if (self._host is None or self._port is None):
            self._client = None
            self._logger.info("No client active")
        else:
            address = "{0}:{1}/".format(self._host, self._port)
            self._logger.info("Communicates with '{0}'".format(address))
            self._client = xmlrpc.client.ServerProxy(address)

    def user_id_decorator(self, f: Callable):

        def _wrapped(*args, **kwargs):

            if self._user_id is not None:
                args = (self._user_id,) + args

            args = sanitize_communication(args)
            kwargs = sanitize_communication(kwargs)

            try:
                return f(*args, **kwargs)
            except xmlrpc.client.Fault:
                self._logger.critical(
                    "Failed to communicate with {}({}, **{})".format(
                        f.__name__,
                        args,
                        kwargs,
                    ),
                )
                raise

        return _wrapped

    def _allowed_methods(self):

        ret: tuple[str, ...] = tuple()

        if not(
            self._client is None
            or hasattr(self._client, "system") is False
        ):

            try:
                ret = tuple(
                    str(v) for v in self._client.system.listMethods()
                    if not v.startswith("system.")
                    and not (self._user_id is None and v in self._admin_methods)
                )
            except socket.error:
                self._logger.warning("Connection Refused for '{0}:{1}'".format(
                    self.host,
                    self.port,
                ))
                return ("launch_local",)

        return ret

    @property
    def working_on_job_or_has_queue(self) -> bool:
        return (
            self.online
            and (self.get_job_status() or self.get_queue_status())
        )

    @property
    def online(self) -> bool:
        if self._client is not None:
            try:
                return bool(dir(self._client.system.listMethods()))
            except (socket.error, CannotSendRequest, ResponseNotReady):
                return False
        return False

    @property
    def local(self) -> bool:
        if self.host is None:
            return False
        return "127.0.0.1" in self.host or "localhost" in self.host

    @property
    def host(self) -> Optional[str]:
        return self._host

    @host.setter
    def host(self, value):
        if not isinstance(value, str):
            value = str(value)

        value = "{0}{1}".format(
            ['', 'http://'][not value.startswith('http://')],
            value,
        )

        self._host = value
        self._setupClient()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value
        self._setupClient()
