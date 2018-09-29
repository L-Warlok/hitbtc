import time
import queue
from hitbtc_wss import HitBTC
c = HitBTC()
c.start()  # start the websocket connection
time.sleep(2)  # Give the socket some time to connect
c.subscribe_ticker(symbol='ETHBTC') # Subscribe to ticker data for the pair ETHBTC

while True:
    try:
        data = c.recv()
    except queue.Empty:
        continue

    # process data from websocket
    ...

c.stop()