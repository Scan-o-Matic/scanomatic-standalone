import time
from enum import Enum
from threading import Thread
from typing import Any, Optional, Union, cast

import psutil

import scanomatic.generics.decorators as decorators
import scanomatic.io.app_config as app_config
import scanomatic.io.fixtures as fixtures
import scanomatic.io.paths as paths
from scanomatic.generics.singleton import SingeltonOneInit
from scanomatic.io.jsonizer import dump, load
from scanomatic.io.logger import get_logger
from scanomatic.io.power_manager import InvalidInit, PowerManagerNull
from scanomatic.io.sane import get_alive_scanners
from scanomatic.models.factories.scanning_factory import ScannerFactory
from scanomatic.models.rpc_job_models import RPCjobModel
from scanomatic.models.scanning_model import ScannerModel

JOB_CALL_SCANNER_REQUEST_ON = "request_scanner_on"
JOB_CALL_SCANNER_REQUEST_OFF = "request_scanner_off"


class STATE(Enum):
    Unknown = 0
    Reported = 1
    Resolved = 2


class ScannerPowerManager(SingeltonOneInit):
    def __one_init__(self):

        self._logger = get_logger("Scanner Manager")
        self._conf = app_config.Config()
        self._paths = paths.Paths()
        self._fixtures = fixtures.Fixtures()
        self._orphan_usbs = set()

        self._scanners = self._initiate_scanners()
        self._pm = None
        self._scanner_queue = []

        self._reported_sane_missing = STATE.Unknown

        Thread(target=self._load_pm).start()

        decorators.register_type_lock(self)

    def _load_pm(self):

        self._pm = self._get_power_manager(self._scanners)

    def __getitem__(self, item) -> ScannerModel:
        if isinstance(item, int):
            return self._scanners[item]
        return [
            scanner for scanner in list(self._scanners.values())
            if scanner.scanner_name == item
        ][0]

    def __contains__(self, item: Union[int, str]) -> bool:
        if isinstance(item, int):
            return any(scanner_id == item for scanner_id in self._scanners)
        else:
            return any(
                scanner.name == item if scanner else False
                for scanner in self._scanners.values()
            )

    def _initiate_scanners(self) -> dict[int, ScannerModel]:
        scanners: dict[int, ScannerModel] = {}

        # Load saved scanner data
        scanner_configs = load(self._paths.config_scanners)
        if scanner_configs is None:
            scanner_configs = []
        elif not isinstance(scanner_configs, list):
            scanner_configs = [scanner_configs]

        for scanner in cast(list[ScannerModel], scanner_configs):
            if 0 < scanner.socket <= self._conf.number_of_scanners:
                scanners[scanner.socket] = scanner

        # Create free scanners for those missing previous data
        for socket in self._enumerate_scanner_sockets():
            if socket not in scanners:
                scanner = ScannerFactory.create(
                    socket=socket,
                    scanner_name=self._conf.get_scanner_name(socket)
                )
                scanners[scanner.socket] = scanner

        self._logger.info("Scanners initiated: {0}".format(scanners))

        return scanners

    def _enumerate_scanner_sockets(self):

        for power_socket in range(self._conf.number_of_scanners):
            yield power_socket + 1

    def _get_power_manager(
        self,
        scanners: dict[Any, ScannerModel]
    ) -> dict[int, PowerManagerNull]:
        pm = {}
        for scanner in scanners.values():

            try:
                pm[scanner.socket] = self._conf.get_pm(scanner.socket)
            except InvalidInit:
                self._logger.error(
                    "Failed to init socket {0}".format(scanner.socket),
                )
                pm[scanner.socket] = PowerManagerNull(scanner.socket)

            self._logger.info(
                "Power Manager of type {0} initialized for scanner {1}".format(
                    type(pm[scanner.socket]).__name__,
                    scanner.scanner_name,
                ),
            )
        return pm

    def _save(self, scanner_model) -> None:
        dump(
            scanner_model,
            self._paths.config_scanners,
        )

    def _rescue(self, available_usbs, active_usbs) -> None:
        self._orphan_usbs = self._orphan_usbs.union(available_usbs)
        power_statuses = self.power_statuses

        for scanner in list(self._scanners.values()):
            could_have_or_claims_to_have_power = (
                power_statuses[scanner.socket] or scanner.power
            )
            no_or_bad_usb = (
                not scanner.usb or scanner.usb not in active_usbs
            )

            if could_have_or_claims_to_have_power and no_or_bad_usb:
                if self._power_down(scanner):
                    self._save(scanner)

    def _match_scanners(self, alive_scanners) -> bool:
        active_usbs, _ = list(zip(*alive_scanners))
        self._trim_no_longer_active_orphan_usbs(active_usbs)
        available_usbs = self._get_non_orphan_usbs(active_usbs)
        unknown_usbs = self._remove_known_usbs(available_usbs)

        if not unknown_usbs:
            return True

        if not self._can_assign_usb(unknown_usbs):
            self._rescue(unknown_usbs, active_usbs)
            return False

        usb = unknown_usbs.pop()
        scanner_model = tuple(
            name for u, name in alive_scanners if u == usb
        )[0]

        self._assign_usb_to_claim(usb, scanner_model)

        return True

    @property
    def power_manager(self) -> PowerManagerNull:
        return self._pm

    @property
    def _claimer(self) -> Optional[ScannerModel]:
        for scanner in list(self._scanners.values()):
            if scanner.claiming:
                return scanner
        return None

    def _can_assign_usb(self, unknown_usbs) -> bool:
        if len(unknown_usbs) > 1 or not self._claimer:
            self._logger.critical(
                "More than one unclaimed scanner {0}".format(
                    unknown_usbs,
                ),
            )
            return False
        return True

    def _assign_usb_to_claim(self, usb, model_name):
        scanner = self._claimer
        if usb:
            scanner.model = model_name
            scanner.usb = usb
            scanner.claiming = False
            scanner.reported = False
            self._save(scanner)

    def _set_usb_to_scanner_that_could_be_on(self, usb) -> bool:
        if self._claimer:
            return False

        powers = self.power_statuses
        if sum(powers.values()) == 1:

            socket = tuple(
                scanner for scanner in powers if powers[scanner]
            )[0]
            scanner = self._scanners[socket]

            if self._pm[socket].sure_to_have_power():
                scanner.power = True
                scanner.usb = usb
                scanner.reported = False
                self._save(scanner)
                return True
            else:
                self._logger.critical(
                    "There's one scanner on {0}, but can't safely assign it to {1}".format(  # noqa: E501
                        usb,
                        scanner,
                    ),
                )
                return False
        else:
            self._logger.critical(
                f"There's one scanner on {usb}, but none that claims to be",
            )
            return False

    def _remove_known_usbs(self, available_usbs):
        known_usbs = set(
            scanner.usb for scanner in list(self._scanners.values())
            if scanner.usb
        )
        return set(usb for usb in available_usbs if usb not in known_usbs)

    def _trim_no_longer_active_orphan_usbs(self, active_usbs):
        self._orphan_usbs = self._orphan_usbs.intersection(active_usbs)

    def _get_non_orphan_usbs(self, usbs):
        return set(usbs).difference(self._orphan_usbs)

    @property
    def connected_to_scanners(self) -> bool:
        return self._pm is not None

    def request_on(self, job_id) -> Union[str, bool]:
        scanner = self._get_scanner_by_owner_id(job_id)
        if scanner:
            if scanner.usb:
                return scanner.usb
            else:
                self._logger.info(
                    "Requested socket {0} to be turned on (By {1}).".format(
                        scanner.socket,
                        job_id,
                    )
                )
                return self._add_to_claim_queue(scanner)

        else:
            self._logger.warning(f"No scanner has been claimed by {job_id}")
            return False

    @decorators.type_lock
    def _add_to_claim_queue(self, scanner) -> bool:
        if scanner not in self._scanner_queue:
            self._logger.info("Added scanner to queue for on/off action")
            self._scanner_queue.append(scanner)
        return True

    @decorators.type_lock
    def request_off(self, job_id) -> bool:

        scanner = self._get_scanner_by_owner_id(job_id)

        if not scanner:
            self._logger.error(
                f"Can't turn off scanner for unknown job {job_id}",
            )
            return False

        self._logger.info(
            "Requested socket {0} to be turned off (By {1}).".format(
                scanner.socket,
                job_id,
            )
        )
        if self._power_down(scanner):
            self._save(scanner)
            return True
        return False

    def _power_down(self, scanner) -> bool:
        success: bool = self._pm[scanner.socket].powerDownScanner()
        if success:
            scanner.usb = ""
            scanner.power = False
            scanner.claiming = False
            scanner.reported = True
            scanner.last_off = time.time()

        return success

    def request_claim(self, rpc_job_model: RPCjobModel) -> bool:
        scanner = rpc_job_model.content_model.scanner
        scanner_name = self._conf.get_scanner_name(scanner)

        if scanner not in self._scanners:
            self._logger.warning(
                "Unknown scanner referenced ({0})".format(
                    scanner_name,
                ),
            )
            return False

        scanner_model = self._scanners[scanner]

        if scanner_model.owner and scanner_model.owner.id != rpc_job_model.id:
            if psutil.pid_exists(scanner_model.owner.pid):
                self._logger.warning(
                    "Trying to claim {0} when claimed".format(
                        scanner_name,
                    ),
                )
                return False
            else:
                self._logger.info(
                    "Releasing {0} since owner process is dead".format(
                        scanner_name,
                    ),
                )
                self._power_down(scanner_model)

        scanner_model.owner = rpc_job_model
        scanner_model.expected_interval = (
            rpc_job_model.content_model.time_between_scans
        )
        scanner_model.email = rpc_job_model.content_model.email
        self._logger.info(
            "Acquire scanner successful, owner set to {0} (mail {1})".format(
                scanner_model.owner,
                scanner_model.email,
            ),
        )
        self._save(scanner_model)
        return True

    def release_scanner(self, job_id) -> bool:
        scanner = self._get_scanner_by_owner_id(job_id)
        if not scanner:
            return False

        if scanner.power or scanner.usb:
            self._power_down(scanner)

        scanner.owner = {'pid': 0}

        self._logger.info(
            "Removed owner for scanner {0}".format(scanner.scanner_name),
        )
        self._save(scanner)

        return True

    def _get_scanner_by_owner_id(self, job_id):
        scanners = [
            scanner for scanner in list(self._scanners.values())
            if scanner.owner and scanner.owner.id == job_id
        ]
        if scanners:
            return scanners[0]
        self._logger.warning(
            "Job id '{0}' has no registered claim on any scanner. Known claims are {1}".format(  # noqa: E501
                job_id,
                [
                    scanner.owner.id for scanner in
                    list(self._scanners.values()) if scanner.owner
                ],
            )
        )
        return None

    def update(self, synch_from_file=False):
        if synch_from_file:
            self._scanners = self._initiate_scanners()

        self._manage_claimer()
        try:
            alive_scanners = get_alive_scanners()
            if self._reported_sane_missing is STATE.Reported:
                self._logger.info(
                    "SANE is now accessible but need restart to detect scanners",  # noqa: E501
                )
                self._reported_sane_missing = STATE.Resolved

        except OSError:
            self._pm.clear()
            self._scanners.clear()
            if self._reported_sane_missing is not STATE.Reported:
                self._logger.warning(
                    "SANE is not installed, server can't scan",
                )
            self._reported_sane_missing = STATE.Reported
        else:
            if alive_scanners:
                return self._match_scanners(alive_scanners)

    @decorators.type_lock
    def _manage_claimer(self):
        if not self._claimer and self._scanner_queue:
            scanner = self._scanner_queue.pop(0)
            while scanner in self._scanner_queue:
                self._scanner_queue.remove(scanner)
            scanner.claiming = True
            self._save(scanner)

        claimer = self._claimer
        if claimer and not claimer.power:
            claimer.power = self._pm[self._claimer.socket].powerUpScanner()
            claimer.last_on = time.time()
            self._save(claimer)

    def has_fixture(self, fixture_name):
        self._fixtures.update()
        return fixture_name in self._fixtures

    @property
    def status(self):
        if self.has_scanners:
            return list(self._scanners.values())
        else:
            return []

    @property
    def fixtures(self):
        self._fixtures.update()
        return self._fixtures.get_names()

    @property
    def power_statuses(self):
        return {scanner_socket: self._pm[scanner_socket].could_have_power()
                for scanner_socket in self._pm}

    @property
    def pm_types(self):
        return {
            pm.socket: {'mode': pm.power_mode, 'type': type(pm)}
            for pm in self._pm.values()
        }

    @property
    def has_scanners(self):
        reachable_pms = any(
            type(pm) is not PowerManagerNull for pm in list(self._pm.values())
        )
        self._logger.info(
            "Power Manager {0} is reachable? {1}".format(
                self.pm_types,
                reachable_pms,
            ),
        )
        return self._pm and reachable_pms

    @property
    def subprocess_operations(self):

        global JOB_CALL_SCANNER_REQUEST_ON, JOB_CALL_SCANNER_REQUEST_OFF
        return {
            JOB_CALL_SCANNER_REQUEST_ON: self.request_on,
            JOB_CALL_SCANNER_REQUEST_OFF: self.request_off
        }

    @property
    def non_reported_usbs(self):
        return (
            scanner for scanner in self._scanners.values()
            if scanner.owner and scanner.usb and not scanner.reported
        )
