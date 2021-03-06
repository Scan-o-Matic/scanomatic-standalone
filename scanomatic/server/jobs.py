from multiprocessing import Pipe
from typing import Union, cast

import scanomatic.io.paths as paths
import scanomatic.models.rpc_job_models as rpc_job_models
import scanomatic.server.analysis_effector as analysis_effector
import scanomatic.server.compile_effector as compile_effector
import scanomatic.server.phenotype_effector as phenotype_effector
import scanomatic.server.rpcjob as rpc_job
import scanomatic.server.scanning_effector as scanning_effector
from scanomatic.generics.singleton import SingeltonOneInit
from scanomatic.io import scanner_manager
from scanomatic.io.jsonizer import dump, dumps, load, purge
from scanomatic.io.logger import get_logger
from scanomatic.models.factories.rpc_job_factory import RPC_Job_Model_Factory


class Jobs(SingeltonOneInit):
    def __one_init__(self):

        self._logger = get_logger("Jobs Handler")
        self._paths = paths.Paths()
        self._scanner_manager = scanner_manager.ScannerPowerManager()
        self._jobs: dict[
            rpc_job_models.RPCjobModel,
            rpc_job.RPCJobInterface
        ] = {}
        self._load_from_file()
        self._forcingStop = False
        self._statuses = []

    def __len__(self) -> int:
        return len(self._jobs)

    def __contains__(
        self,
        key: Union[str, rpc_job_models.RPCjobModel],
    ) -> bool:

        if isinstance(key, str):
            return any(True for j in self._jobs if j.id == key)

        return key in self._jobs

    def __getitem__(self, key):

        if key in self._jobs:
            return self._jobs[key]

        for job in self._jobs:
            if job.id == key:
                return job
            else:
                self._logger.info("{0}!={1}".format(job.id, key))

        self._logger.warning("Unknown job {0} requested".format(key))
        return None

    def __delitem__(self, job: rpc_job_models.RPCjobModel) -> None:
        if job in self._jobs:
            if (
                job.type == rpc_job_models.JOB_TYPE.Scan
                and self._scanner_manager.connected_to_scanners
            ):
                self._scanner_manager.release_scanner(job.id)
            del self._jobs[job]
            self._logger.info("Job '{0}' not active/removed".format(job))
            if not purge(
                job,
                self._paths.rpc_jobs,
                RPC_Job_Model_Factory.is_same_job,
            ):
                self._logger.warning(
                    "Failed to remove references to job in config file",
                )
        else:
            self._logger.warning(
                "Can't delete job {0} as it does not exist, I only know of {1}".format(  # noqa: E501
                    job,
                    list(self._jobs.keys()),
                ),
            )

    @property
    def active_compile_project_jobs(self) -> list[rpc_job_models.RPCjobModel]:
        return [
            job for job in self.active_jobs
            if job.type is rpc_job_models.JOB_TYPE.Compile
        ]

    @property
    def active_jobs(self):
        return list(self._jobs.keys())

    @property
    def status(self):
        return self._statuses

    @property
    def running(self) -> bool:
        for job in self._jobs:
            if self._jobs[job].is_alive() and not self._jobs[job].abandoned:
                return True

        return False

    @property
    def force_stop(self):
        return self._forcingStop

    @force_stop.setter
    def force_stop(self, value):
        if value is True:
            self._forcingStop = True
            for job in self._jobs:
                if self._jobs[job].is_alive():
                    if not self._jobs[job].pipe.send("stop"):
                        self._logger.error(
                            "Can't communicate with job, process will be orphaned",  # noqa: E501
                        )
                        self._jobs[job].abandon()

        self._forcingStop = value

    def _load_from_file(self):
        jobs = load(self._paths.rpc_jobs)
        for job in cast(
            list[rpc_job_models.RPCjobModel],
            [] if jobs is None else jobs
        ):
            if job and job.content_model:
                _, parent_pipe = Pipe()
                self._jobs[job] = rpc_job.Fake(job, parent_pipe)

    def sync(self):
        self._logger.debug("Syncing jobs")
        statuses = []
        jobs = list(self._jobs.keys())
        for job in jobs:
            job_process = self._jobs[job]
            if not self._forcingStop:
                job_process.pipe.poll()
                if not job.pid:
                    job_process.update_pid()
                if not job_process.is_alive():
                    del self[job]
            statuses.append(job_process.status)

        self.handle_scanners()

        self._statuses = statuses

    def handle_scanners(self):

        if not self._scanner_manager.connected_to_scanners:
            return

        self._scanner_manager.update()

        for scanner in self._scanner_manager.non_reported_usbs:
            if scanner.owner in self and scanner.usb:
                self._jobs[scanner.owner].pipe.send(
                    scanning_effector.JOBS_CALL_SET_USB,
                    scanner.usb,
                    scanner.model
                )
                scanner.reported = True
                self._logger.info(
                    "Reported USB {2} for scanner {0} to {1}".format(
                        scanner.socket,
                        scanner.owner.id,
                        scanner.usb,
                    ),
                )
            else:
                if scanner.usb:
                    self._logger.warning(
                        "Unknown scanner claiming process {0}".format(
                            scanner.owner,
                        ),
                    )
                else:
                    self._logger.info(
                        "Waiting for actual USB assignment on request from {0}".format(  # noqa: E501
                            scanner.owner.id,
                        ),
                    )

    def add(self, job: rpc_job_models.RPCjobModel) -> bool:
        """Launches and adds a new jobs."""

        if any(job.id == j.id for j in self._jobs):
            self._logger.error(
                "Job {0} already exists, will drop current request".format(
                    job.id,
                ),
            )
            return True

        job_effector = self._get_job_effector(job)

        if not job_effector:
            self._logger.error(
                "Job {0} can't be executed, will drop request".format(job.id),
            )
            return True

        if (
            not self._scanner_manager.connected_to_scanners
            and job.type == rpc_job_models.JOB_TYPE.Scan
        ):
            self._logger.error("Scanners aren't ready, job request dropped")
            return True

        parent_pipe, child_pipe = Pipe()
        job_process = rpc_job.RpcJob(
            job,
            job_effector,
            parent_pipe,
            child_pipe)

        self._initialize_job_process(job_process, job)
        self._set_initialized_job(job_process, job)
        self._logger.info("Job '{0}' ({1}) started".format(
            job.id, job.type,
        ))
        return True

    def _set_initialized_job(
        self,
        job_process: rpc_job.RpcJob,
        job: rpc_job_models.RPCjobModel,
    ):
        self._jobs[job] = job_process
        job.status = rpc_job_models.JOB_STATUS.Running
        dump([j for j in self._jobs], self._paths.rpc_jobs)

    def _initialize_job_process(
        self,
        job_process: rpc_job.RpcJob,
        job: rpc_job_models.RPCjobModel,
    ) -> None:
        job_process.daemon = True
        job_process.start()
        job.pid = job_process.pid
        if job.type is rpc_job_models.JOB_TYPE.Scan:
            self._add_scanner_operations_to_job(job_process)
            job.content_model.id = job.id

        job_process.pipe.send(
            'setup',
            dumps(job),
        )

    def _add_scanner_operations_to_job(self, job_process: rpc_job.RpcJob):
        job_process.pipe.add_allowed_calls(
            self._scanner_manager.subprocess_operations,
        )

    def _get_job_effector(self, job: rpc_job_models.RPCjobModel):
        """SELECTS EFFECTOR BASED ON TYPE"""
        if job.type is rpc_job_models.JOB_TYPE.Features:
            return phenotype_effector.PhenotypeExtractionEffector
        elif job.type is rpc_job_models.JOB_TYPE.Analysis:
            return analysis_effector.AnalysisEffector
        elif job.type is rpc_job_models.JOB_TYPE.Scan:
            return scanning_effector.ScannerEffector
        elif job.type is rpc_job_models.JOB_TYPE.Compile:
            return compile_effector.CompileProjectEffector
        else:
            self._logger.critical(
                "Job '{0}' ({1}) lost, process not yet implemented".format(
                    job.id,
                    job.type.name,
                ))
            return None
