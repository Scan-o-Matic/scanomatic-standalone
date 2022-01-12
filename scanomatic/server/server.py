import hashlib
import time
from math import trunc
from typing import Any, Optional, Union

import scanomatic.generics.decorators as decorators
from scanomatic.generics.model import Model
import scanomatic.io.app_config as app_config
import scanomatic.io.scanner_manager as scanner_manager
import scanomatic.models.rpc_job_models as rpc_job_models
import scanomatic.server.jobs as jobs
import scanomatic.server.queue as queue
from scanomatic.io.logger import get_logger
from scanomatic.io.paths import Paths
from scanomatic.io.resource_status import Resource_Status
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory
from scanomatic.models.validators.validate import validate


def get_id() -> str:
    return hashlib.md5(str(time.time()).encode()).hexdigest()


class Server:
    def __init__(self):

        config = app_config.Config()

        self.logger = get_logger(
            "Server",
            Paths().log_server,
        )

        self.admin = config.rpc_server.admin
        self._running = False
        self._started = False
        self._waitForJobsToTerminate = False
        self._server_start_time = None

        self._jobs = jobs.Jobs()
        self._queue = queue.Queue(self._jobs)

        self._scanner_manager = scanner_manager.ScannerPowerManager()

    @property
    def scanner_manager(self) -> scanner_manager.ScannerPowerManager:
        return self._scanner_manager

    @property
    def queue(self) -> queue.Queue:
        return self._queue

    @property
    def jobs(self) -> jobs.Jobs:
        return self._jobs

    @property
    def serving(self) -> bool:
        return self._started

    def shutdown(self) -> bool:
        self._waitForJobsToTerminate = False
        self._running = False
        return True

    def safe_shutdown(self) -> bool:
        self._waitForJobsToTerminate = True
        self._running = False
        return True

    def get_server_status(self) -> dict[str, Any]:

        if self._server_start_time is None:
            run_time = "Not Running"
        else:
            m, s = divmod(time.time() - self._server_start_time, 60)
            h, m = divmod(m, 60)
            run_time = "{0:d}h, {1:d}m, {2:.2f}s".format(
                trunc(h),
                trunc(m),
                s,
            )

        return {
            "ServerUpTime": run_time,
            "QueueLength": len(self._queue),
            "NumberOfJobs": len(self._jobs),
            "ResourceMem": Resource_Status.check_mem(),
            "ResourceCPU": Resource_Status.check_cpu(),
        }

    def start(self):
        if not self._started:
            self._run()
        else:
            self.logger.warning(
                "Attempted to start Scan-o-Matic server that is already running",  # noqa: E501
            )

    def _job_may_be_created(self, job) -> bool:
        """

        Args:
            job: queue item

        Returns: bool

        """
        if job is None:
            return False
        elif job.type == rpc_job_models.JOB_TYPE.Scan:
            return True
        else:
            return (
                Resource_Status.check_resources(consume_checks=True)
                or len(self._jobs) == 0
            )

    def _attempt_job_creation(self):
        next_job = self._queue.get_highest_priority()
        if self._job_may_be_created(next_job):
            if self._jobs.add(next_job):
                self._queue.remove(next_job)

    @decorators.threaded
    def _run(self):

        self._running = True
        self._server_start_time = time.time()
        sleep = 0.07
        i = 0

        while self._running:

            if i == 0 and self._queue:
                self._attempt_job_creation()
            elif i <= 1 and self._scanner_manager.connected_to_scanners:
                self._scanner_manager.update()
            else:
                self._jobs.sync()

            time.sleep(sleep)
            i += 1
            i %= 3

        self._shutdown_cleanup()

    def _shutdown_cleanup(self):
        self.logger.info("Som Server Main process shutting down")
        self._terminate_jobs()

        if self._waitForJobsToTerminate:
            self._wait_on_jobs()

        self._save_state()

        self.logger.info("Scan-o-Matic server shutdown complete")
        self._started = False

    def _save_state(self):
        pass

    def _terminate_jobs(self):

        if self._jobs.running:
            self.logger.info("Asking all jobs to terminate")

            self._jobs.force_stop = True

    def _wait_on_jobs(self):
        i = 0
        max_wait_time = 180
        start_time = time.time()
        while (
            self._jobs.running and time.time() - start_time
            < max_wait_time
        ):
            if i == 0:
                self.logger.info(
                    "Waiting for jobs to terminate ({0:.2f}s waiting left)".format(  # noqa: E501
                        max(0, max_wait_time - (time.time() - start_time)),
                    ),
                )
            i += 1
            i %= 30
            time.sleep(0.1)

        if self._jobs.running:

            self.logger.warning(
                "Jobs will be abandoned, can't wait for ever...",
            )

    def _get_job_id(self) -> str:
        job_id = ""
        bad_name = True

        while bad_name:
            job_id = get_id()
            bad_name = job_id in self._queue or job_id in self._jobs

        return job_id

    def get_job(self, job_id: str) -> rpc_job_models.RPCjobModel:
        """Gets the rpc job model if any corresponding to the id"""
        if job_id in self._queue:
            return self._queue[job_id]
        return self._jobs[job_id]

    def enqueue(
        self,
        model: Model,
        job_type: rpc_job_models.JOB_TYPE,
    ) -> Optional[Union[str, bool]]:

        rpc_job = RPC_Job_Model_Factory.create(
            id=self._get_job_id(),
            pid=None,
            type=job_type,
            status=rpc_job_models.JOB_STATUS.Requested,
            content_model=model,
        )

        if not validate(rpc_job):
            self.logger.error("Failed to create job model")
            return False

        if (
            job_type is rpc_job_models.JOB_TYPE.Scan
            and not self.verify_scanner_claim(rpc_job)
        ):
            return False

        self._queue.add(rpc_job)

        self.logger.info(
            f"Job {rpc_job} with id {rpc_job.id} added to queue",
        )
        return rpc_job.id

    def verify_scanner_claim(self, rpc_job_model):

        if (
            not self.scanner_manager.connected_to_scanners
            or not self.scanner_manager.has_scanners
        ):
            self.logger.error("There are no scanners reachable from server")
            return False

        return self.scanner_manager.request_claim(rpc_job_model)
