from logging import Logger
from time import sleep
from xmlrpc.server import SimpleXMLRPCServer

import scanomatic.generics.decorators as decorators


class Stoppable_RPC_Server(object):

    def __init__(self, *args, **kwargs):
        self.logger = Logger("RPC Server")
        self.logger.info(
            f"Starting server with {args} and {kwargs}",
        )
        self._server = SimpleXMLRPCServer(*args, **kwargs)
        self._keepAlive = True
        self._running = False
        self._started = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self):
        self.serve_forever()

    def stop(self):
        self._keepAlive = False
        while self._running:
            sleep(0.1)

        self._server.server_close()

    def register_introspection_functions(self):
        self._server.register_introspection_functions()

    def register_function(self, function, name):
        self._server.register_function(function, name)

    @decorators.threaded
    def serve_forever(self, poll_interval=0.5):
        if self._started:
            self.logger.warning("Can only start server once")
            return
        elif self._running:
            self.logger.warning(
                "Attempted having two processes handling requests",
            )
            return

        self._started = True
        self._running = True
        self._server.timeout = poll_interval
        while self._keepAlive:
            self._server.handle_request()
        self._running = False
