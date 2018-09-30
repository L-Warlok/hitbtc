"""HitBTC Connector which pre-formats incoming data to the CTS standard."""

import hmac
import hashlib
from collections import defaultdict
from hitbtc_wss.utils import response_types
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory, connectWS
import json
import time
from client import HitBTC

from queue import Queue


class HitBTCProtocol(WebSocketClientProtocol):
    """Class to pre-process HitBTC data, before putting it on the internal queue.

    Data on the queue is available as a 3-item-tuple by default.
    
    Response items on the queue are formatted as:
        ('Response', 'Success' or 'Failure', (request, response))
    
    'Success' indicates a successful response and 'Failure' a failed one. 
    ``request`` is the original payload sent by the
    client and ``response`` the related response object from the server.
    
    Stream items on the queue are formatted as:
        (method, symbol, params)
    """

    def __init__(self, subs=None):
        self.subs = subs
        super().__init__()

    def onMessage(self, payload, isBinary):
        """Handle and pass received data to the appropriate handlers."""
        if isBinary is False:
            decoded_message = json.loads(payload)
            print(decoded_message)
            if 'jsonrpc' in decoded_message:
                if 'result' in decoded_message or 'error' in decoded_message:
                    self._handle_response(decoded_message)
                else:
                    try:
                        method = decoded_message['method']
                        symbol = decoded_message['params']['symbol']
                        params = decoded_message['params']
                    except Exception as e:
                        self.log.exception(e)
                        self.log.error(decoded_message)
                        return
                    self._handle_stream(method, symbol, params)

    def _handle_response(self, response):
        """
        Handle JSONRPC response objects.

        Acts as a pre-sorting function and determines whether or not the response is an error
        message, or a response to a succesful request.
        """
        try:
            i_d = response['id']
        except KeyError as e:
            self.log.exception(e)
            self.log.error("An expected Response ID was not found in %s", response)
            raise

        try:
            request = self.requests.pop(i_d)
        except KeyError as e:
            log.exception(e)
            log.error("Could not find Request relating to Response object %s", response)
            raise

        if 'result' in response:
            self._handle_request_response(request, response)
        elif 'error' in response:
            self._handle_error(request, response)

    def _handle_request_response(self, request, response):
        """
        Handle responses to succesful requests.

        Logs messages and prints them to screen.

        Finally, we'll put the response and its corresponding request on the internal queue for
        retrieval by the client.
        """
        method = request['method']

        try:
            msg = response_types[method]
        except KeyError as e:
            log.exception(e)
            log.error("Response's method %s is unknown to the client! %s", method, response)
            return
        print(request)
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
        self.log.debug("Request: %r, Response: %r", request, response)
        self.put(('Response', 'Success', (request, response)))

    def _handle_error(self, request, response):
        """
        Handle Error messages.

        Logs the corresponding requests and the error code and error messages, and prints them to
        the screen.

        Finally, we'll put the response and its corresponding request on the internal queue for
        retrieval by the client.
        """
        err_message = "{code} - {message} - {description}!".format(**response['error'])
        err_message += " Related Request: %r" % request
        self.log.error(err_message)
        self.echo(err_message)
        self.put(('Response', 'Failure', (request, response)))

    def onOpen(self):
        print("open")
        self.client = HitBTC(connector=self)
        for i in self.subs:
            for j in self.subs[i]['params']:
                for k in self.subs[i]['params'][j]:
                    getattr(self.client, i)(**{j:k})

    def send(self, method, custom_id=None, **params):
        """
        Send the given Payload to the API via the websocket connection.

        :param method: JSONRPC method to call
        :param custom_id: custom ID to identify response messages relating to this request
        :param kwargs: payload parameters as key=value pairs
        """

        payload = {'method': method, 'params': params, 'id': custom_id or int(10000 * time.time())}
        self.log.debug("Sending: %s", payload)
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

    def __init__(self, url=None, key=None, secret=None, q_maxsize=None, symbols=None, books=[], subs=None):
        import sys

        from twisted.python import log
        log.startLogging(sys.stdout)

        self.protocol = HitBTCProtocol

        self.subs = subs
        self.url = url or 'wss://api.hitbtc.com/api/2/ws'
        super().__init__(self.url)
        self.books = books or defaultdict(dict)
        self.logged_in = False

        self.key = key
        self.secret = secret

        self.q = Queue(maxsize=q_maxsize or 100)

    def clientConnectionLost(self, connector, reason):
        print(reason)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print(reason)
        reactor.stop()


if __name__ == '__main__':
    from twisted.internet import reactor

    subscriptions = {'subscribe_ticker': {'params': {'symbol': ['ETHDAI', 'ETHBTC']}}, 'subscribe_book': {'params': {'symbol': ['ETHDAI', 'ETHBTC']}}}
    factory = hitBTCProtocolFactory(url='wss://api.hitbtc.com/api/2/ws', subs=subscriptions)
    connectWS(factory)
    reactor.run()
