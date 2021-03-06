from time import sleep
from xmlrpc.server import SimpleXMLRPCServer

import scanomatic.generics.decorators as decorators
from scanomatic.io.logger import get_logger


class Stoppable_RPC_Server:

    def __init__(self, *args, **kwargs):
        self.logger = get_logger("RPC Server")
        self.logger.info(
            f"Starting server with {args} and {kwargs}",
        )
        self._server = SimpleXMLRPCServer(*args, **kwargs)
        self._keep_alive = True
        self._running = False
        self._started = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self):
        self.serve_forever()

    def stop(self):
        self._keep_alive = False
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
        self.logger.info("Ready to recieve messages")
        while self._keep_alive:
            self._server.handle_request()
        self._running = False
        self.logger.info("Stopped")
