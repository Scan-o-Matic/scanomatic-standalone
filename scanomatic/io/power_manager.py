import os
import re
import time
import types
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from logging import Logger
from subprocess import PIPE, Popen
from typing import Any, Optional, Type
from urllib.parse import urlencode

# FURTHER LAN-specific dependenies further down


class InvalidInit(Exception):
    pass


URL_TIMEOUT = 2
MAX_CONNECTION_TRIES = 10
POWER_MANAGER_TYPE = Enum(
    "POWER_MANAGER_TYPE",
    names=("notInstalled", "USB", "LAN", "linuxUSB", "windowsUSB"),
)
POWER_MODES = Enum("POWER_MODES", names=("Toggle", "Impulse"))
POWER_FLICKER_DELAY = 0.25


def _impulse_scanner(self) -> bool:
    on_success = self._on()
    time.sleep(POWER_FLICKER_DELAY)
    return self._off() and on_success


def _toggle_scanner_on(self) -> bool:
    return self._on()


def _toggle_scanner_off(self) -> bool:
    return self._off()


def has_value(enum, value):
    return any(elem for elem in enum if elem.value == value)


def get_enum_name_from_value(enum, value):
    return list(elem for elem in enum if elem.value == value)[0]


def get_pm_class(
    pm_type: Optional[POWER_MANAGER_TYPE]
) -> Type["PowerManagerNull"]:

    if pm_type is POWER_MANAGER_TYPE.notInstalled:
        return PowerManagerNull
    elif pm_type is POWER_MANAGER_TYPE.LAN:
        return PowerManagerLan
    elif pm_type is POWER_MANAGER_TYPE.USB:
        return PowerManagerUsb
    elif pm_type is POWER_MANAGER_TYPE.linuxUSB:
        return PowerManagerUsbLinux
    elif pm_type is POWER_MANAGER_TYPE.windowsUSB:
        return PowerManagerUsbWin
    return PowerManagerNull


class PowerManagerNull:
    def __init__(
        self,
        socket: int,
        power_mode: POWER_MODES = POWER_MODES.Toggle,
        name: str = "not installed",
        **kwargs,
    ):
        if power_mode is POWER_MODES.Impulse:
            self.powerUpScanner = types.MethodType(_impulse_scanner, self)
            self.powerDownScanner = types.MethodType(_impulse_scanner, self)

        elif power_mode is POWER_MODES.Toggle:
            self.powerUpScanner = types.MethodType(_toggle_scanner_on, self)
            self.powerDownScanner = types.MethodType(_toggle_scanner_off, self)

        self._power_mode = power_mode
        self._socket = socket
        self.name = name
        self._logger = Logger("Power Manager {0}".format(name))

    @property
    def socket(self):
        return self._socket

    @property
    def power_mode(self) -> str:
        return str(self._power_mode)

    def _on(self) -> bool:
        return True

    def _off(self) -> bool:
        return True

    def status(self) -> Optional[bool]:
        self._logger.warning("claiming to be off")
        return False

    def could_have_power(self) -> bool:
        return (
            self._power_mode is POWER_MODES.Impulse
            or self.status() is not False
        )

    def sure_to_have_power(self) -> bool:
        return (
            self._power_mode is not POWER_MODES.Impulse
            and self.status() is not False
        )


class PowerManagerUsb(PowerManagerNull):
    """Base Class for USB-connected PM:s. Not intended to be used directly."""
    def __init__(
        self,
        socket: int,
        path,
        on_args=None,
        off_args=None,
        power_mode: POWER_MODES = POWER_MODES.Toggle,
        name: str = "USB",
        **kwargs,
    ):

        if not off_args:
            off_args = []
        if not on_args:
            on_args = []

        super(PowerManagerUsb, self).__init__(
            socket,
            power_mode=power_mode,
            name=name,
        )

        self._on_cmd = [path] + on_args
        self._off_cmd = [path] + off_args
        self._fail_error = "No GEMBIRD SiS-PM found"

    def _on(self) -> bool:

        on_success = self._exec(self._on_cmd)
        self._logger.info('USB PM, Turning on socket {0} ({1})'.format(
            self._socket,
            on_success,
        ))
        return on_success

    def _off(self) -> bool:

        off_success = self._exec(self._off_cmd)
        self._logger.info('USB PM, Turning off socket {0} ({1})'.format(
            self._socket,
            off_success,
        ))
        return off_success

    def _exec(self, cmd) -> bool:
        exec_err = False
        stderr = b""
        try:
            proc = Popen(cmd, shell=False, stdout=PIPE, stderr=PIPE)
            _, stderr = proc.communicate()
        except Exception:
            exec_err = True
        if self._fail_error in stderr.decode() or exec_err:
            return False

        return True


class PowerManagerUsbLinux(PowerManagerUsb):
    """Class for handling USB connected PM:s on linux."""

    ON_TEXT = "on"
    OFF_TEXT = "off"

    def __init__(
        self,
        socket: int,
        path: str = "sispmctl",
        power_mode: POWER_MODES = POWER_MODES.Impulse,
        **kwargs
    ):

        super(PowerManagerUsbLinux, self).__init__(
            socket,
            path,
            on_args=["-o", "{0}".format(socket)],
            off_args=["-f", "{0}".format(socket)],
            power_mode=power_mode,
            name="USB(Linux)",
        )

    def status(self) -> Optional[bool]:
        self._logger.info('USB PM, trying to connect')
        proc = Popen(
            'sispmctl -g {0}'.format(self._socket),
            stdout=PIPE,
            stderr=PIPE,
            shell=True,
        )
        stdout, _ = proc.communicate()
        stdout = stdout.strip()
        if stdout.endswith(self.ON_TEXT.encode()):
            return True
        elif stdout.endswith(self.OFF_TEXT.encode()):
            return False
        self._logger.warning('USB PM, could not reach or understand PM')
        return None


class PowerManagerUsbWin(PowerManagerUsb):
    """Class for handling USB connected PM:s on windows."""

    def __init__(
        self,
        socket: int,
        path: str = r"C:\Program Files\Gembird\Power Manager\pm.exe",
        power_mode: POWER_MODES = POWER_MODES.Toggle,
        **kwargs,
    ):

        super(PowerManagerUsbWin, self).__init__(
            socket,
            path,
            on_args=["-on", "-PW1", "-Scanner{0}".format(socket)],
            off_args=["-off", "-PW1", "-Scanner{0}".format(socket)],
            power_mode=power_mode,
            name="USB(Windows)",
        )


class PowerManagerLan(PowerManagerNull):
    """Class for handling LAN-connected PM:s.

    host may be None if MAC is supplied.
    If no password is supplied, default password is used."""

    def __init__(
        self,
        socket: int,
        host: Optional[str] = None,
        password: str = "1",
        verify_name: bool = False,
        name: str = "Server 1",
        mac=None,
        power_mode: POWER_MODES = POWER_MODES.Toggle,
        **kwargs,
    ):

        super(PowerManagerLan, self).__init__(
            socket,
            name="LAN",
            power_mode=power_mode,
        )
        self._host = host
        self._mac = mac
        if password is None:
            password = "1"
        self._password = password

        self._pm_server_name = name
        self._pm_server_str = "<h2>{0}".format(name)
        self._verify_name = verify_name

        self._pwd_params = urlencode((("pw", password),))
        self._on_params = urlencode((("cte{0}".format(socket), 1),))
        self._off_params = urlencode((("cte{0}".format(socket), 0),))

        self._set_urls()
        self.test_ip()

        if self._host is None:
            if mac is not None:
                self._logger.info("LAN PM, No valid host known, searching...")
                res = self._find_ip()
                self._logger.info("LAN PM, Found {0}".format(res))
            else:
                self._logger.error(
                    "LAN PM, No known host and no MAC...no way to find PM",
                )
                raise InvalidInit()

    @property
    def host(self) -> Optional[str]:
        return self._host

    def _set_urls(self) -> None:

        host = self._host

        self._login_out_url = "http://{0}/login.html".format(host)
        self._ctrl_panel_url = "http://{0}/".format(host)

    def _find_ip(self) -> Optional[str]:
        """Looks up the MAC-address supplied on the local router"""

        # SEARCHING FOR IP SPECIFIC DEPENDENCIES
        try:
            import nmap
        except ImportError:
            self._logger.error(
                "Can't scan for Power Manager without nmap installed",
            )
            self._host = None
            return self._host

        if not self._mac:
            self._logger.warning(
                "Can not search for the power manager on the LAN without knowing its MAC",  # noqa: E501
            )
            self._host = None
            return self._host

        # PINGSCAN ALL IP:S
        self._logger.info("LAN PM, Scanning hosts (may take a while...)")
        nm = nmap.PortScanner()
        nm_res = nm.scan(hosts="192.168.0.1-255", arguments="-sP")

        # FILTER OUT THOSE RESPONDING
        self._logger.debug("LAN PM, Evaluating all alive hosts")
        up_ips = [
            k for k in nm_res['scan']
            if nm_res['scan'][k]['status']['state'] == 'up'
        ]

        # LET THE OS PING THEM AGAIN SO THEY END UP IN ARP
        self._logger.debug("LAN PM, Scanning pinning alive hosts")
        for ip in up_ips:
            os.system('ping -c 1 {0}'.format(ip))

        # RUN ARP
        self._logger.debug("LAN PM, Searching arp")
        p = Popen(['arp', '-n'], stdout=PIPE)

        # FILTER LIST ON ROWS WITH SOUGHT MAC-ADDRESS
        self._logger.debug("LAN PM, Keeping those with correct MAC-addr")
        res = [
            line for line in p.communicate()[0].split(b"\n")
            if self._mac in line
        ]

        if len(res) > 0:
            # RETURN THE IP

            for r in res:
                self._host = r.split(b" ", 1)[0].decode()
                self._set_urls()
                if self.test_ip() is not None:
                    break
        else:
            # IF IT IS NOT CONNECTED AND UP RETURN NONE
            self._host = None

        self._set_urls()

        return self._host

    def _run_url(
        self,
        *args,
        **kwargs,
    ) -> Any:
        success = False
        connects = 0
        p = None

        while not success and connects < MAX_CONNECTION_TRIES:
            try:
                p = urllib.request.urlopen(*args, **kwargs)
                success = True
            except Exception:
                connects += 1

        if connects == MAX_CONNECTION_TRIES:
            self._logger.error(
                "Failed to reach PM ({0} tries)".format(connects),
            )

        return p

    def _login(self) -> Any:
        if self._host is None or self._host == "":

            self._logger.error("LAN PM, Logging in failed, no host")
            return None

        else:

            self._logger.debug("LAN PM, Logging in")
            return self._run_url(
                self._login_out_url,
                self._pwd_params,
                timeout=URL_TIMEOUT,
            )

    def _logout(self) -> Any:
        if self._host is None or self._host == "":
            self._logger.error("LAN PM, Log out failed, no host")
            return None
        else:
            self._logger.debug("LAN PM, Logging out")
            return self._run_url(self._login_out_url, timeout=URL_TIMEOUT)

    def test_ip(self) -> bool:
        self._logger.debug(
            "LAN PM, Testing current host '{0}'".format(self._host),
        )

        if self._host is not None:
            u = self._logout()
            if u is None:
                self._host = None

            else:
                s = u.read()
                u.close()

                if "EnerGenie" not in s:
                    self._host = None

                if self._pm_server_name not in s:
                    self._host = None

        return self._host is not None

    def _on(self) -> bool:
        u = self._login()
        if u is None:
            return False

        if not self._verify_name or self._pm_server_str in u.read():
            self._logger.info(
                'USB PM, Turning on socket {0}'.format(self._socket),
            )
            if self._run_url(
                self._ctrl_panel_url,
                self._on_params,
                timeout=URL_TIMEOUT
            ) is None:
                return False

            self._logout()
            return True
        else:
            self._logger.error(
                "LAN PM, Failed to turn on socket {0}".format(self._socket),
            )
            return False

    def _off(self) -> bool:
        u = self._login()
        if u is None:
            return False

        if not self._verify_name or self._pm_server_str in u.read():
            self._logger.info(
                'USB PM, Turning off socket {0}'.format(self._socket),
            )

            if self._run_url(
                self._ctrl_panel_url,
                self._off_params,
                timeout=URL_TIMEOUT,
            ) is None:
                return False
            self._logout()
            return True
        else:
            self._logger.error(
                "LAN PM, Failed to turn off socked {0}".format(self._socket),
            )
            return False

    def status(self) -> Optional[bool]:
        u = self._login()
        if u is None:
            self._logger.error('Could not reach LAN-PM')
            return None

        page = u.read()
        if not self._verify_name or self._pm_server_str in page:

            states = re.findall(r'sockstates = ([^;]*)', page)[0].strip()
            try:
                states = eval(states)
                if len(states) >= self._socket:
                    return states[self._socket - 1] == 1
            except Exception:
                pass

        return None
