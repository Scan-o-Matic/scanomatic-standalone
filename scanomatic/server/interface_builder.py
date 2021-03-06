import os
import socket
import sys
from functools import wraps
from logging import Logger
from time import sleep
from typing import Optional, Union

import scanomatic.generics.decorators as decorators
import scanomatic.models.rpc_job_models as rpc_job_models
from scanomatic.generics.model import Model
from scanomatic.generics.singleton import SingeltonOneInit
from scanomatic.io.app_config import Config
from scanomatic.io.logger import get_logger
from scanomatic.io.rpc_client import sanitize_communication
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.factories.compile_project_factory import (
    CompileProjectFactory
)
from scanomatic.models.factories.features_factory import FeaturesFactory
from scanomatic.models.factories.scanning_factory import (
    ScannerFactory,
    ScanningModelFactory
)
from scanomatic.models.validators.validate import get_invalid_names, validate
from scanomatic.server.server import Server
from scanomatic.server.stoppable_rpc_server import Stoppable_RPC_Server

_SOM_SERVER: Optional[Server] = None
_RPC_SERVER: Optional[Stoppable_RPC_Server] = None


def _verify_admin(f):

    @wraps(f)
    def _verify_global_admin(interface_builder, user_id, *args, **kwargs):

        global _SOM_SERVER
        global _RPC_SERVER

        if _SOM_SERVER and user_id == _SOM_SERVER.admin:

            return f(interface_builder, user_id, *args, **kwargs)

        elif _RPC_SERVER is not None:

            _RPC_SERVER.logger.warning(
                "User {0} unauthorized attempt at accessing {1}".format(
                    user_id,
                    f,
                ),
            )
        return False

    return _verify_global_admin


def _report_invalid(
    logger: Logger,
    model: Model,
    title,
):
    for param in get_invalid_names(model):
        logger.warning(
            f"{title} got invalid parameter {param} value '{model[param]}'",
        )


class InterfaceBuilder(SingeltonOneInit):

    def __one_init__(self):

        self.logger = get_logger("Server Manager")
        self._start_som_server()
        self._start_rpc_server()

    @staticmethod
    def _start_som_server():

        global _SOM_SERVER
        if _SOM_SERVER is None:
            _SOM_SERVER = Server()
            _SOM_SERVER.start()
            _SOM_SERVER.logger.info('SOM Server started')
        else:
            _SOM_SERVER.logger.warning(
                "Attempt to launch second instance of server",
            )

    def _start_rpc_server(self):

        global _RPC_SERVER
        app_config = Config()
        host = app_config.rpc_server.host
        port = app_config.rpc_server.port

        if _RPC_SERVER is not None and _RPC_SERVER.running:
            _RPC_SERVER.logger.warning(
                "Attempt to launch second instance of server",
            )
            return False

        try:
            _RPC_SERVER = Stoppable_RPC_Server(
                (host, port),
                logRequests=False,
            )
        except socket.error:
            self.logger.critical(
                "Sever is already running or the " +
                "port {0} is in use by other program".format(
                    port))
            self._remove_som_server(False)
            sys.exit(1)

        _RPC_SERVER.register_introspection_functions()

        _RPC_SERVER.logger.info("Server (pid {0}) listens to {1}:{2}".format(
            os.getpid(),
            host,
            port,
        ))

        for m in dir(self):
            if m.startswith("_server_"):
                _RPC_SERVER.register_function(getattr(self, m), m[8:])

        _RPC_SERVER.serve_forever()

    @decorators.threaded
    def _remove_rpc_server(self):

        global _RPC_SERVER
        global _SOM_SERVER

        if _RPC_SERVER:
            _RPC_SERVER.stop()
        else:
            self.logger.warning("Trying to stop a server that is not running")
        _RPC_SERVER = None

        if _SOM_SERVER:
            logger_instance = _SOM_SERVER.logger
        else:
            logger_instance = self.logger

        logger_instance.info("Server no longer accepting requests")

    def _remove_som_server(self, wait_for_jobs_to_stop):
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False
        if wait_for_jobs_to_stop:
            successful_stop = _SOM_SERVER.shutdown()
        else:
            successful_stop = _SOM_SERVER.safe_shutdown()

        return successful_stop

    @_verify_admin
    def _server_shutdown(self, user_id, wait_for_jobs_to_stop=False):
        self._remove_rpc_server()
        val = self._remove_som_server(
            wait_for_jobs_to_stop=wait_for_jobs_to_stop,
        )

        if val:
            self.logger.info("Server is shutting down")
        else:
            self.logger.error("Unknown error shutting down Scan-o-Matic server")

        return sanitize_communication(val)

    @_verify_admin
    def _server_restart(self, user_id, wait_for_jobs_to_stop=False):
        self._remove_rpc_server()
        self._restart_server_thread(wait_for_jobs_to_stop)
        return True

    @decorators.threaded
    def _restart_server_thread(self, wait_for_jobs_to_stop):
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return
        self._remove_som_server(wait_for_jobs_to_stop=wait_for_jobs_to_stop)

        while _SOM_SERVER.serving:
            sleep(0.1)

        del _SOM_SERVER
        _SOM_SERVER = None  # noqa: F841

        self._start_som_server()
        self._start_rpc_server()

    def _server_get_status(self, user_id=None):
        """Gives a dictionary of the servers status

        Kwargs:
            user_id (str):   The ID of the user requesting status
                            The full purpose of userID is to maintain
                            method interface for all exposed RPC methods

        Returns:
            dictionary. Key value pairs for the different aspects of the
                        server status.
        """
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return {}

        return sanitize_communication(_SOM_SERVER.get_server_status())

    def _server_get_scanner_status(self, user_id=None):
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return []
        if not _SOM_SERVER.scanner_manager.connected_to_scanners:
            self.logger.error("Scanner manager not connected to scanner")
            return []
        self.logger.debug(
            f"Scanner manager status: {_SOM_SERVER.scanner_manager.status}"
        )
        return sanitize_communication(sorted(
            [
                ScannerFactory.to_dict(scanner_model)
                for scanner_model in _SOM_SERVER.scanner_manager.status
            ],
            key=lambda x: x['socket'],
        ))

    @_verify_admin
    def _server_get_power_manager_info(self, user_id=None):
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return {}

        pm = _SOM_SERVER.scanner_manager.power_manager
        keys = list(pm.keys())
        if (n_keys := len(keys)) != 1:
            self.logger.error(f"Found {n_keys} power managers, should be 1")
            return {}
        pm = pm[keys[0]]
        host = pm.host

        data = {
            'pm': type(pm),
            'host': host,
            'unasigned_usbs': (
                _SOM_SERVER.scanner_manager.non_reported_usbs
            ),
            'power_status': _SOM_SERVER.scanner_manager.power_statuses,
            'modes': _SOM_SERVER.scanner_manager.pm_types,
        }
        _SOM_SERVER.logger.info(f"PM Status is {data}")

        return sanitize_communication(data)

    def _server_get_queue_status(self, user_id=None):
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return []
        return sanitize_communication(_SOM_SERVER.queue.status)

    def _server_get_job_status(self, user_id=None):
        """Gives a list or statuses.

        First entry is always the status of the server followed by
        an item for each job.

        Kwargs:
            userID (str):   The ID of the user requesting status
                            The full purpose of userID is to maintain
                            method interface for all exposed RPC methods

        Returns:
            list.   Each item in the list is a dictionary.
                    For information about the job dictionaries and
                    their structure, see ``self.getStatus``.
                    The first item of the list will be a dictionary
                    containing general information about the server.::

            ServerUpTime:  (str) Either the message 'Server Not Running'
                           or a string with like "XXh, YYm, ZZ.ZZs"
                           expressing the time that the server has been
                           running.

        """
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return []
        return sanitize_communication(_SOM_SERVER.jobs.status)

    @_verify_admin
    def _server_communicate(
        self,
        user_id,
        job_id: str,
        communication,
        communication_content={},
    ) -> bool:
        """Used to communicate with active jobs.

        Args:
            userID (str):   The ID of the user, this must match the
                            current ID of the server admin or request
                            will be refused.

            jobID (str):    The ID for the job to communicate with.

            title (str):    The name, as understood by the job, for what you
                            want to do. The following are universally
                            understood::

                setup:  Passing settings before the job has been started.
                        This ``title`` is preferrably coupled with ``kwargs``
                        while the other universally used titles have no use
                        for extra parameters.
                email:  Add recipient of notifications to a job
                start:  Starting the job's execution
                pause:  Temporarily pausing the job
                resume: Temporarily resuming the job
                stop:   Stopping the job
                status: Requesting that the job sends back the current status

            kwargs (dict):  Extra parameters to send with the communication.

        Returns:

            bool.   ``True`` if communication was allowed (user was admin and
                    title was accepted imperative) else ``False``
        """
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False

        job: rpc_job_models.RPCjobModel = _SOM_SERVER.get_job(job_id)

        if job is not None:
            if job.status is rpc_job_models.JOB_STATUS.Queued:
                return sanitize_communication(
                    _SOM_SERVER.queue.remove_and_free_potential_scanner_claim(
                        job,
                    )
                )
            else:
                try:
                    ret = _SOM_SERVER.jobs[job].pipe.send(
                        communication,
                        **communication_content,
                    )
                    self.logger.info("The job {0} got message {1}".format(
                        job.id,
                        communication,
                    ))
                    return sanitize_communication(ret)
                except (AttributeError, TypeError):
                    self.logger.error(
                        "The job {0} has no valid call {1} with payload {2}".format(  # noqa: E501
                            job.id,
                            communication,
                            communication_content,
                        ),
                    )
                    return False

        else:
            self.logger.error("The job {0} is not running".format(job_id))
            return False

    @_verify_admin
    def _server_reestablish_process(
        self,
        user_id,
        job_id,
        label,
        job_type,
        process_pid,
    ):
        """Interface for orphaned daemons to re-gain contact with server.

        Parameters
        ==========

        userID : str
            The ID of the user requesting to create a job.
            This must match the current ID of the server admin or
            the request will be refused.
            **NOTE**: If using a rpc_client from scanomatic.io the client
            will typically prepend this parameter

        jobID : str

            The job identifier of the job that wants to regain contact.
            This job must be known to the server

        jobType: int

            The type of job the job is.

        label : str

            User-friendly string with info about the job

        pid : int

            The process id of the orphaned daemon

        Returns
        =======

        multiprocessing.Connection or False
            Returns the part of the pipe used by the child-process if
            re-establishment is allowed, else False

        """
        return False
        # if jobID in self._jobs:
        #
        # return self._jobs.fakeProcess(jobID, label, jobType, pid)
        #
        # else:
        #
        # self._logger.warning(
        # "Unknown job "+
        # "'{0}'({1}, pid {2}) tried to claim it exists".format(
        #             label, jobID, pid))
        #
        #     return False

    @_verify_admin
    def _server_create_scanning_job(self, user_id, scanning_model):

        """Attempts to start a scanning job.

        This is a common interface for all type of scan jobs.

        Parameters
        ==========

        userID : str
            The ID of the user requesting to create a job.
            This must match the current ID of the server admin or
            the request will be refused.
            **NOTE**: If using a rpc_client from scanomatic.io the client
            will typically prepend this parameter

        scanningModel : dict
            Dictionary representation of model for scanning
        """
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False

        _SOM_SERVER.logger.info(
            f"Attempting to create scanning job with {scanning_model}"
        )
        scanning_model = ScanningModelFactory.create(**scanning_model)

        try:
            path_valid = not os.path.isdir(os.path.join(
                scanning_model.directory_containing_project,
                scanning_model.project_name
            ))
            _SOM_SERVER.logger.info(
                "Tested path requested and it is {0}valid".format(
                    "" if path_valid else "in",
                ),
            )
        except Exception:
            path_valid = False
            _SOM_SERVER.logger.warning(
                "Bad data in attempting to check path for scanning job creation",  # noqa: E501
            )

        if (not path_valid or not validate(scanning_model)):
            if not path_valid:
                _SOM_SERVER.logger.error(
                    "Project name duplicate in containing directory",
                )

            if not validate(scanning_model):
                _report_invalid(
                    _SOM_SERVER.logger,
                    scanning_model,
                    "Request scanning job",
                )
            return False

        return sanitize_communication(
            _SOM_SERVER.enqueue(scanning_model, rpc_job_models.JOB_TYPE.Scan),
        )

    @_verify_admin
    def _server_create_compile_project_job(
        self,
        user_id,
        compile_project_model,
    ):
        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False
        compile_project_model = CompileProjectFactory.create(
            **compile_project_model,
        )
        if not validate(compile_project_model):
            _report_invalid(
                _SOM_SERVER.logger,
                compile_project_model,
                "Request compile project",
            )
            return False

        return sanitize_communication(
            _SOM_SERVER.enqueue(
                compile_project_model,
                rpc_job_models.JOB_TYPE.Compile,
            ),
        )

    @_verify_admin
    def _server_remove_from_queue(self, user_id, job_id) -> bool:
        """Removes job from queue

        Parameters
        ==========

        user_id : str
            The ID of the user requesting to create a job.
            This must match the current ID of the server admin or
            the request will be refused.
            **NOTE**: If using a rpc_client from scanomatic.io the client
            will typically prepend this parameter

        jobID : str
            The ID of job to be removed

        Returns
        =======

        bool
            Success status

        See Also
        ========

        flush_queue
            Remove all queued jobs
        """

        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False
        return sanitize_communication(
            _SOM_SERVER.queue.remove_and_free_potential_scanner_claim(job_id),
        )

    @_verify_admin
    def _server_flush_queue(self, user_id) -> bool:
        """Clears the queue

        Parameters
        ==========

        user_id : str
            The ID of the user requesting to create a job.
            This must match the current ID of the server admin or
            the request will be refused.
            **NOTE**: If using a rpc_client from scanomatic.io the client
            will typically prepend this parameter

        Returns
        =======

        bool
            Success status

        See Also
        ========

        remove_from_queue
            Remove individual job from queue
        """

        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False
        queue = _SOM_SERVER.queue

        while queue:
            job = queue.get_highest_priority()
            queue.remove_and_free_potential_scanner_claim(job)

        return True

    @_verify_admin
    def _server_request_scanner_operation(
        self,
        user_id,
        job_id: str,
        scanner: Union[str, int],
        operation: str,
    ):
        """Interface for subprocess to request scanner operations

        Parameters
        ==========

        userID : str
            The ID of the user requesting to create a job.
            This must match the current ID of the server admin or
            the request will be refused.
            **NOTE**: If using a rpc_client from scanomatic.io the client
            will typically prepend this parameter

        jobID : str
            Identifier for the job that owns the scanner to be controlled
            If operation in "CLAIM" set this to None

        scanner: int or string
            Name of the scanner to be controlled

        operation : str
            "ON" Turn power on to scanner / obtain USB
            "OFF" Turn power off
            "RELEASE" Free scanner from claim
        """

        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False

        scanner_manager = _SOM_SERVER.scanner_manager
        operation = operation.upper()

        if not scanner_manager.connected_to_scanners:

            _SOM_SERVER.logger.warning("Scanners not loaded (yet)")
            return False

        if scanner not in scanner_manager:

            _SOM_SERVER.logger.warning("Unknown scanner: {0}".format(scanner))
            return False

        scanner_model = scanner_manager[scanner]

        if not scanner_model.owner or scanner_model.owner.id != job_id:

            _SOM_SERVER.logger.warning(
                "Job '{0}' tried to manipulate someone else's scanners".format(
                    job_id,
                ),
            )

            return False

        if operation == "ON":

            return sanitize_communication(scanner_manager.request_on(job_id))

        elif operation == "OFF":

            return sanitize_communication(scanner_manager.request_off(job_id))

        elif operation == "RELEASE":

            return sanitize_communication(scanner_manager.release_scanner(
                job_id,
            ))

        else:

            return False

    def _server_get_fixtures(self, user_id=None) -> tuple[str, ...]:
        """Gives the names of the fixtures known to the server.

        Returns
        =======

        tuple of strings
            The names known to the server
        """

        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return tuple()
        return sanitize_communication(_SOM_SERVER.scanner_manager.fixtures)

    @_verify_admin
    def _server_create_analysis_job(
        self,
        user_id,
        analysis_model: dict,
    ) -> bool:
        """Enques a new analysis job.

        Parameters
        ==========

        userID : str
            The ID of the user requesting to create a job.
            This must match the current ID of the server admin or
            the request will be refused.
            **NOTE**: If using a rpc_client from scanomatic.io the client
            will typically prepend this parameter

        analysis_model : dict
            A dictionary representation of a
            scanomatic.models.analysis_model.AnalysisModel

        Returns
        =======

        bool
            Success of putting job in queue
        """

        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False
        model = AnalysisModelFactory.create(**analysis_model)
        if not validate(model):
            _report_invalid(
                _SOM_SERVER.logger,
                model,
                "Request analysis",
            )
            return False

        return sanitize_communication(
            _SOM_SERVER.enqueue(
                model,
                rpc_job_models.JOB_TYPE.Analysis,
            ),
        )

    @_verify_admin
    def _server_create_feature_extract_job(
        self,
        user_id,
        feature_extract_model: dict,
    ) -> bool:
        """Enques a new feature extraction job.

        Parameters
        ==========

        userID : str
            The ID of the user requesting to create a job.
            This must match the current ID of the server admin or
            the request will be refused.
            **NOTE**: If using a rpc_client from scanomatic.io the client
            will typically prepend this parameter


        feature_extract_model : dict
            A dictionary representation of
            scanomatic.models.features_model.FeaturesModel

        Returns
        =======
            ``True`` if job request was successfully enqueued, else ``False``
        """

        global _SOM_SERVER
        if _SOM_SERVER is None:
            self.logger.error("Server not fully initialized")
            return False

        model = FeaturesFactory.create(**feature_extract_model)
        if not validate(model):
            _report_invalid(
                _SOM_SERVER.logger,
                model,
                "Request feature extraction",
            )
            return False

        return sanitize_communication(
            _SOM_SERVER.enqueue(
                model,
                rpc_job_models.JOB_TYPE.Features,
            )
        )
