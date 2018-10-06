"""HitBTC Connector which pre-formats incoming data to the CTS standard."""

import hmac
import hashlib
from collections import defaultdict
from utils import response_types
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory, connectWS
import json
import time
from client import HitBTC


class HitBTCProtocol(WebSocketClientProtocol):
    """Class to process HitBTC data.

    """

    def __init__(self, subs=None, silent=False):
        self.subs = subs
        self.requests = {}
        self.silent = silent
        import io
        from twisted.logger import textFileLogObserver, Logger

        self.log = Logger(observer=textFileLogObserver(io.open("log.txt", "a")))
        self.debug_count = 0
        super().__init__()

    def onMessage(self, payload, isBinary):
        """Handle and pass received data to the appropriate handlers."""
        if isBinary is False:
            decoded_message = json.loads(payload)
            if 'jsonrpc' in decoded_message:
                if 'result' in decoded_message or 'error' in decoded_message:
                    self._handle_response(decoded_message)
                else:
                    try:
                        method = decoded_message['method']
                        symbol = decoded_message['params']['symbol']
                        params = decoded_message['params']
                    except Exception as e:
                        self.log.debug(e)
                        self.log.debug(decoded_message)
                        return
                    self._handle_stream(method, symbol, params)

    def echo(self, msg):
        """Print message to stdout if ``silent`` isn't True."""
        if not self.silent:
            print(msg)

    def _handle_response(self, response):
        """
        Handle JSONRPC response objects.

        Acts as a pre-sorting function and determines whether or not the response is an error
        message, or a response to a succesful request.
        """
        try:
            i_d = response['id']
        except KeyError as e:
            self.log.debug(e)
            self.log.debug("An expected Response ID was not found in %s", response)
            raise

        try:
            request = self.requests.pop(i_d)
        except KeyError as e:
            self.log.debug(e)
            self.log.debug("Could not find Request relating to Response object %s", response)
            raise

        if 'result' in response:
            self._handle_request_response(request, response)
        elif 'error' in response:
            self._handle_error(request, response)

    def _handle_request_response(self, request, response):
        """
        Handle responses to succesful requests.

        Logs messages and prints them to screen.

        """
        method = request['method']

        try:
            msg = response_types[method]
        except KeyError as e:
            self.log.debug(e)
            self.log.debug("Response's method %s is unknown to the client! %s", method, response)
            return
        if method.startswith('subscribe'):
            if 'symbol' in request['params']:
                formatted_msg = msg.format(symbol=request['params']['symbol'])
            else:
                formatted_msg = msg
            self.log.info(formatted_msg)
            self.echo(formatted_msg)
        else:
            text = "Sucessfully processed %s request:\n" % method
            if method.startswith('get'):
                # loop over item in response['result'] for:
                # getSymbols, getTrades, getTradingBalance, getOrders
                for item in response['result']:
                    # Don't print zero balances
                    if method is not 'getTradingBalance' or (float(item['available']) > 0 or float(item['reserved']) > 0):
                        try:
                            text += msg.format(**item)
                        except KeyError as e :
                            print("Formatter for method {} failed on item {} with KeyError {}... item keys {}".format(method, item, e, item.keys()))
                self.log.info(text)
                self.echo(text)
            else:
                # Format messages for these using response['result'] directly
                # (place, cancel, replace, getSymbol, getCurrency)
                try:
                    text += msg.format(**response['result'])
                except TypeError:
                    text += msg.format(response['result'])
                self.log.info(text)
                self.echo(text)
        self.log.debug("Request: {request}, Response: {response}", request=request, response=response)

    def _handle_error(self, request, response):
        """
        Handle Error messages.

        Logs the corresponding requests and the error code and error messages, and prints them to
        the screen.

        """
        err_message = "{code} - {message} - {description}!".format(**response['error'])
        err_message += " Related Request: %r" % request
        self.log.debug(err_message)
        self.echo(err_message)
        self.client.error_callback(request, response)

    def _handle_stream(self, method, symbol, params):
        """Handle streamed data."""

        if method.startswith("snapshot"):
            method = method[8:].lower()
        elif method.startswith("update"):
            method = method[6:].lower()

        getattr(self.client, method + "_callback")(method, symbol, params)

    def onOpen(self):
        print("open")
        self.client = HitBTC(connector=self)
        for i in self.subs:
            for j in self.subs[i]:
                getattr(self.client, i)(**(self.subs[i][j]))
                if i == "subscribe_ticker":
                    self.client.track_tickers(self.subs[i][j]['symbol'])

    def send(self, method, custom_id=None, **params):
        """
        Send the given Payload to the API via the websocket connection.

        :param method: JSONRPC method to call
        :param custom_id: custom ID to identify response messages relating to this request
        :param kwargs: payload parameters as key=value pairs
        """

        payload = {'method': method, 'params': params, 'id': custom_id or int(10000 * time.time())}
        self.requests[payload['id']] = payload
        self.log.debug("Sending: {load}", load=payload)
        self.sendMessage(json.dumps(payload).encode('utf-8'))

    def authenticate(self, key, secret, basic=False, custom_nonce=None):
        """Login to the HitBTC Websocket API using the given public and secret API keys."""
        if basic:
            algo = 'BASIC'
            skey = secret
            payload = {'sKey': skey}
        else:
            algo = 'HS256'
            nonce = custom_nonce or str(round(time.time() * 1000))
            signature = hmac.new(secret.encode('UTF-8'), nonce.encode('UTF-8'), hashlib.sha256).hexdigest()
            payload = {'nonce': nonce, 'signature': signature}

        payload['algo'] = algo
        payload['pKey'] = key
        self.send('login', **payload)


class hitBTCProtocolFactory(WebSocketClientFactory):

    def buildProtocol(self, addr):
        p = self.protocol(self.subs)
        p.factory = self
        return p

    def __init__(self, url=None, key=None, secret=None, q_maxsize=None, books=[], subs=None):

        self.protocol = HitBTCProtocol

        self.subs = subs
        self.url = url or 'wss://api.hitbtc.com/api/2/ws'
        super().__init__(self.url)
        self.books = books or defaultdict(dict)
        self.logged_in = False

        self.key = key
        self.secret = secret

    def clientConnectionLost(self, connector, reason):
        print(reason)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print(reason)
        reactor.stop()


if __name__ == '__main__':
    from twisted.internet import reactor

    subscriptions = {'subscribe_ticker': {0: {'symbol': 'ETHDAI'}, 1: {'symbol': 'BTCDAI'}}, 'subscribe_candles': {0: {'symbol': 'ETHDAI', 'period': 'M30'}}}
    factory = hitBTCProtocolFactory(url='wss://api.hitbtc.com/api/2/ws', subs=subscriptions)
    connectWS(factory)
    reactor.run()
