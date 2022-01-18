import os
from multiprocessing import Process
from threading import Thread
from time import sleep

import psutil
import setproctitle  # type: ignore

from abc import ABC, abstractmethod, abstractproperty
from scanomatic.io.logger import get_logger
from scanomatic.server.proc_effector import (
    ChildPipeEffector,
    ParentPipeEffector,
    _PipeEffector
)


class RPCJobInterface(ABC):
    @abstractproperty
    def pipe(self) -> _PipeEffector:
        raise NotImplementedError()

    @abstractproperty
    def abandoned(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def abandon(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def status(self) -> dict:
        raise NotImplementedError()

    @abstractmethod
    def is_alive(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def update_pid(self) -> None:
        raise NotImplementedError()


class Fake(RPCJobInterface):
    def __init__(self, job, parent_pipe):

        self._job = job
        self._parent_pipe = ParentPipeEffector(parent_pipe)
        self._logger = get_logger("Fake Process {0}".format(job.id))
        self._logger.info("Running ({0}) with pid {1}".format(
            self.is_alive(), job.pid))
        self._abandoned = False

    @property
    def abandoned(self) -> bool:
        return self._abandoned

    @property
    def pipe(self) -> _PipeEffector:
        return self._parent_pipe

    @property
    def status(self) -> dict:
        s = self.pipe.status
        if 'id' not in s:
            s['id'] = self._job.id
        if 'label' not in s:
            s['label'] = self._job.id
        if 'running' not in s:
            s['running'] = True
        if 'progress' not in s:
            s['progress'] = -1
        if 'pid' not in s:
            s['pid'] = os.getpid()

        return s

    def abandon(self) -> None:
        self._abandoned = True

    def is_alive(self) -> bool:
        if not self._job.pid:
            return False

        return psutil.pid_exists(self._job.pid)

    def update_pid(self) -> None:
        self._job.pid = self.pipe.status['pid']


class RpcJob(Process, Fake):

    def __init__(self, job, job_effector, parent_pipe, child_pipe):
        super(RpcJob, self).__init__()
        self._job = job
        self._job_effector = job_effector
        self._parent_pipe = ParentPipeEffector(parent_pipe)
        self._childPipe = child_pipe
        self._logger = get_logger("Job {0} Process".format(job.id))
        self._abandoned = False

    def run(self):

        def _communicator():

            while pipe_effector.keepAlive and job_running:
                pipe_effector.poll()
                sleep(0.07)

            _logger.info("Will not recieve any more communications")

        job_running = True
        _logger = get_logger("RPC Job {0} (proc-side)".format(self._job.id))

        pipe_effector = ChildPipeEffector(
            self._childPipe,
            self._job_effector(self._job),
        )
        assert pipe_effector.procEffector is not None

        setproctitle.setproctitle("SoM {0}".format(
            pipe_effector.procEffector.TYPE.name))

        t = Thread(target=_communicator)
        t.start()

        _logger.info("Communications thread started")

        effector_iterator = pipe_effector.procEffector

        _logger.info("Starting main loop")

        while t.is_alive() and job_running:

            if pipe_effector.keepAlive:

                try:

                    next(effector_iterator)

                except StopIteration:

                    _logger.info("Next returned stop iteration, job is done.")
                    job_running = False
                    # pipe_effector.keepAlive = False

                if t.is_alive():
                    pipe_effector.sendStatus(
                        pipe_effector.procEffector.status(),
                    )
                sleep(0.05)

            else:
                _logger.info("Job doesn't want to be kept alive")
                sleep(0.29)

        if t.is_alive():
            pipe_effector.sendStatus(pipe_effector.procEffector.status())
        t.join(timeout=1)
        _logger.info("Job completed")
