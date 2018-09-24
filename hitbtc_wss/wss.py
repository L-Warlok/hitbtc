"""Connector Base class."""

# pylint: disable=too-many-arguments

# Import Built-Ins
import logging
from queue import Queue
from threading import Thread, Timer
import multiprocessing as mp

import json
import time
import ssl

# Import Third-Party
import websocket

# Import home-grown

# Init Logging Facilities
log = logging.getLogger(__name__)


class WebSocketConnector:
    """Websocket Connection Thread.

    Inspired heavily by ekulyk's PythonPusherClient Connection Class
    https://github.com/ekulyk/PythonPusherClient/blob/master/pusherclient/connection.py

    Data received is available by calling WebSocketConnection.recv()
    """

    # pylint: disable=too-many-instance-attributes, too-many-arguments,unused-argument


    def stop(self):
        """Wrap around disconnect()."""
        self.disconnect()



    def recv(self, block=True, timeout=None):
        """Wrap for self.q.get().

        :param block: Whether or not to make the call to this method block
        :param timeout: Value in seconds which determines a timeout for get()
        :return:
        """
        return self.q.get(block, timeout)
