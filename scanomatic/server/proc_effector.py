import os
import socket
import time
from logging import Logger
from subprocess import Popen
from threading import Thread
from typing import Optional

import scanomatic.generics.decorators as decorators
from scanomatic.io.logger import get_logger
import scanomatic.io.rpc_client as rpc_client
import scanomatic.models.rpc_job_models as rpc_job_models
from scanomatic.io import mail
from scanomatic.io.app_config import Config as AppConfig


class _PipeEffector:

    REQUEST_ALLOWED = "__ALLOWED_CALLS__"

    def __init__(self, pipe, loggerName="Pipe effector"):

        self._logger = Logger(loggerName)

        # The actual communications object
        self._pipe = pipe

        # Calls this side accepts
        self._allowedCalls: dict = {}

        # Calls that the other side will accept according to other side
        self._allowedRemoteCalls = None

        # Flag indicating if other side is missing
        self._hasContact = True

        # Sends that faild get stored here
        self._sendBuffer = []

        # Calls that should trigger special reaction if pipe is not working
        # Reaction will depend on if server or client side
        self._failVunerableCalls = []

        self._pid = os.getpid()

    def setFailVunerableCalls(self, *calls):
        self._failVunerableCalls = calls

    def setAllowedCalls(self, allowedCalls: dict):
        """Allowed Calls must be iterable with a get item function
        that understands strings"""
        self._allowedCalls = allowedCalls
        self._sendOwnAllowedKeys()

    def add_allowed_calls(self, additional_calls):
        self._allowedCalls.update(additional_calls)
        self._sendOwnAllowedKeys()

    def _sendOwnAllowedKeys(self):
        self._logger.info("Informing other side of pipe about my allowed calls")
        self.send(
            self.REQUEST_ALLOWED,
            *list(self._allowedCalls.keys()),
        )

    def poll(self):
        while self._hasContact and self._pipe.poll():
            response = None
            try:
                dataRecvd = self._pipe.recv()
            except EOFError:
                self._logger.warning("Lost contact in pipe")
                self._hasContact = False
                return

            self._logger.debug("Pipe recieved {0}".format(dataRecvd))

            try:
                request, args, kwargs = dataRecvd
            except (IndexError, TypeError):
                self._logger.exception(
                    f"Recieved a malformed data package '{dataRecvd}'",
                )

            if request == self.REQUEST_ALLOWED:
                self._logger.info(
                    "Got information about other side's allowed calls '{0}'".format(  # noqa: E501
                        args,
                    )
                )
                if self._allowedRemoteCalls is None:
                    self._sendOwnAllowedKeys()
                    self._allowedRemoteCalls = args
            else:
                if self._allowedCalls is None:
                    self._logger.info("No allowed calls")
                    self._sendOwnAllowedKeys()
                elif request in self._allowedCalls:
                    response = self._allowedCalls[request](*args, **kwargs)
                else:
                    self._logger.warning(
                        f"Request {request} not an allowed call",
                    )
                    self._logger.info(
                        "Allowed calls are '{0}'".format(
                            list(self._allowedCalls.keys()),
                        ),
                    )

            try:
                if response not in (None, True, False):
                    if (isinstance(response, dict) and
                            request == "status"):
                        self.send(request, **response)
                        self._logger.info("Sent status response {0}".format(
                            response,
                        ))
                    else:
                        self.send(response[0], *response[1], **response[2])
                        self._logger.info("Sent response {0}".format(response))

                else:
                    self._logger.debug("No response to request")

            except Exception:
                self._logger.exception(
                    f"Could not send response '{response}'",
                )

    def _failSend(self, callName: str, *args, **kwargs) -> bool:
        """Stores send request in buffer to be sent upon new connection

        If `callName` exists in buffer, it is replaced by the newer send
        request with the same `callName`

        Parameters
        ==========

        callName : str
            Identification string for the type of action or information
            requested or passed through the sent objects

        *args, **kwargs: objects, optional
            Any serializable objects to be passed allong

        Returns
        =======

        bool
            Success status
        """
        for i, (cN, _, __) in enumerate(self._sendBuffer):
            if cN == callName:
                self._sendBuffer[i] = (callName, args, kwargs)
                return True

        self._sendBuffer.append((callName, args, kwargs))
        return True

    def send(self, callName, *args, **kwargs):
        if self._hasContact and self._sendBuffer:
            while self._sendBuffer:
                cN, a, kw = self._sendBuffer.pop()
                if not self._send(cN, *a, **kw) and not self._hasContact:
                    self._failSend(cN, a, kw)
                    break

        success = self._send(callName, *args, **kwargs)
        if not success and not self._hasContact:
            self._failSend(callName, *args, **kwargs)
        return success

    def _send(self, callName, *args, **kwargs) -> bool:
        if (
            self._allowedRemoteCalls is None
            or callName == self.REQUEST_ALLOWED
            or callName in self._allowedRemoteCalls
        ):
            try:
                self._pipe.send((callName, args, kwargs))
            except Exception:
                self._logger.exception(
                    f"Failed to send {(callName, args, kwargs)}",
                )
                self._hasContact = False
                return False
            return True

        else:
            self._logger.warning(
                f"Other side won't accept '{callName}'. "
                f"Known calls are '{self._allowedRemoteCalls}'"
            )
            return False


class ParentPipeEffector(_PipeEffector):
    def __init__(self, pipe):
        super(ParentPipeEffector, self).__init__(
            pipe,
            loggerName="Parent Pipe Effector",
        )

        self._status = {'pid': self._pid}
        self._allowedCalls['status'] = self._setStatus

    @property
    def status(self) -> dict:
        return self._status

    def _setStatus(self, *args, **kwargs):
        if 'pid' not in kwargs:
            kwargs['pid'] = self._pid
        self._status = kwargs


class ChildPipeEffector(_PipeEffector):
    def __init__(self, pipe, procEffector: Optional["ProcessEffector"] = None):
        super(ChildPipeEffector, self).__init__(
            pipe,
            loggerName="Child Pipe Effector",
        )
        if procEffector is None:
            self._allowedCalls = {}
        self.procEffector: Optional["ProcessEffector"] = procEffector

    @property
    def keepAlive(self) -> bool:
        return (
            True if self._procEffector is None
            else self._procEffector.keep_alive
        )

    def _failSend(self, callName, *args, **kwargs) -> bool:
        # Not loose calls
        super(ChildPipeEffector, self)._failSend(callName, *args, **kwargs)

        if (callName in self._failVunerableCalls):
            rC = rpc_client.get_client(admin=True)

            if not rC.online:
                self._logger.info("Re-booting server process")
                Popen('scan-o-matic_server')
                time.sleep(2)

            if rC.online:
                pipe = rC.reestablishMe(
                    self.procEffector.label,
                    self.procEffector.label,
                    self.procEffector.TYPE,
                    os.getpid(),
                )

                if (pipe is False):
                    self._logger.critical(
                        "Server refused to acknowledge me, "
                        "nothing left to do but die"
                    )
                    self.procEffector.stop()
                    return False

                else:
                    self._pipe = pipe
                    self._hasContact = True

        return True

    @property
    def procEffector(self) -> Optional["ProcessEffector"]:
        return self._procEffector

    @procEffector.setter
    def procEffector(self, procEffector: "ProcessEffector"):
        self._procEffector = procEffector
        self.setAllowedCalls(procEffector.allow_calls)
        self.setFailVunerableCalls(*procEffector.fail_vunerable_calls)
        procEffector.pipe_effector = self

    def sendStatus(self, status):
        self.send('status', **status)


class ProcessEffector:

    TYPE = rpc_job_models.JOB_TYPE.Unknown

    def __init__(
        self,
        job: rpc_job_models.RPCjobModel,
        logger_name: str = "Process Effector",
        logging_target: Optional[str] = None,
    ):

        self._job = job
        self._job_label = job.id
        self._logger = (
            get_logger(logger_name, logging_target)
            if logging_target is not None
            else Logger(logger_name)
        )
        self._fail_vunerable_calls = tuple()

        self._specific_statuses = {}

        self._allowed_calls = {
            'pause': self.pause,
            'resume': self.resume,
            'setup': self.setup,
            'status': self.status,
            'email': self.email,
            'stop': self.stop
        }

        self._allow_start = False
        self._running = False
        self._started = False
        self._stopping = False
        self._paused = False

        self._log_file_path = None

        self._messages = []

        self._iteration_index = None
        self._pid = os.getpid()
        self._pipe_effector: Optional[ChildPipeEffector] = None
        self._start_time = None
        decorators.register_type_lock(self)

    def email(self, add=None, remove=None) -> bool:
        if add is not None:
            try:
                self._job.content_model.email += (
                    [add] if isinstance(add, str) else add
                )
            except TypeError:
                return False
            return True
        elif remove is not None:
            try:
                self._job.content_model.email.remove(remove)
            except (ValueError, AttributeError, TypeError):
                return False
            return True
        return False

    @property
    def label(self):
        return self._job_label

    @property
    def pipe_effector(self) -> Optional[ChildPipeEffector]:
        if self._pipe_effector is None:
            self._logger.warning(
                "Attempting to get pipe effector that has not been set",
            )

        return self._pipe_effector

    @pipe_effector.setter
    def pipe_effector(self, value: Optional[ChildPipeEffector]):
        if value is None or isinstance(value, ChildPipeEffector):
            self._pipe_effector = value

    @property
    def run_time(self) -> float:
        if self._start_time is None:
            return 0.
        else:
            return time.time() - self._start_time

    @property
    def progress(self) -> float:
        return -1.

    @property
    def fail_vunerable_calls(self):
        return self._fail_vunerable_calls

    @property
    def keep_alive(self):
        return not self._started and not self._stopping or self._running

    def pause(self, *args, **kwargs):
        self._paused = True

    def resume(self, *args, **kwargs):
        self._paused = False

    def setup(self, job):
        self._logger.warning(
            "Setup is not overwritten, job info ({0}) lost.".format(job),
        )

    @property
    def waiting(self) -> bool:
        if self._stopping:
            return False
        if self._paused or not self._running:
            return True
        return False

    def status(self, *args, **kwargs) -> dict:
        return dict(
            [
                ('id', self._job.id),
                ('label', self.label),
                ('log_file', self._log_file_path),
                ('pid', self._pid),
                ('type', self.TYPE.text),
                ('running', self._running),
                ('paused', self._paused),
                ('runTime', self.run_time),
                ('progress', self.progress),
                ('stopping', self._stopping),
                ('messages', self.get_messages())
            ] +
            [
                (k, getattr(self, v)) for k, v in
                list(self._specific_statuses.items())
            ],
        )

    def stop(self, *args, **kwargs):
        self._stopping = True

    @decorators.type_lock
    def get_messages(self):
        msgs = self._messages
        self._messages = []
        return msgs

    @decorators.type_lock
    def add_message(self, msg):
        self._messages.append(msg)

    @property
    def allow_calls(self):
        return self._allowed_calls

    def __iter__(self):
        return self

    def __next__(self) -> bool:
        if not self._stopping and not self._running:
            if self._allow_start:
                self._running = True
                self._logger.info("Setup passed, switching to run-mode")
                return True
            else:
                self._logger.info("Waiting to run...need setup to allow start")
                return True
        elif self._stopping:
            raise StopIteration
        return True

    def _mail(self, title_template, message_template, data_model):

        def _do_mail(title, message, model):

            try:
                if not model.email:
                    self._logger.info(
                        "No mail registered with job, so can't send:\n{0}\n\n{1}".format(  # noqa: E501
                            title, message
                        ))
                    return

                if AppConfig().mail.server:
                    server = mail.get_server(
                        AppConfig().mail.server,
                        smtp_port=AppConfig().mail.port,
                        login=AppConfig().mail.user,
                        password=AppConfig().mail.password,
                    )
                else:
                    server = None

                if not mail.mail(
                    AppConfig().mail.user,
                    model.email,
                    title.format(**model),
                    message.format(**model),
                    server=server,
                ):
                    self._logger.error(
                        "Problem getting access to mail server, mail not sent:\n{0}\n\n{1}".format(  # noqa: E501
                            title.format(**model),
                            message.format(**model),
                        ),
                    )
            except KeyError:
                self._logger.error(
                    "Malformed message template, model is lacking requested keys:\n{1}\n\n{0}".format(  # noqa: E501
                        title,
                        message,
                    ),
                )
            except socket.error:
                self._logger.warning(
                    "Failed to send '{0}' to '{1}'. Probably `sendmail` is not installed. Mail body:\n{2}".format(  # noqa: E501
                        title.format(**model),
                        model.email,
                        message.format(**model),
                    ),
                )
        Thread(
            target=_do_mail,
            args=(title_template, message_template, data_model),
        ).start()
