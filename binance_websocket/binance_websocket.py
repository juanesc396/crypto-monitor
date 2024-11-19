import websocket
import pandas as pd
import json
from prometheus_client import start_http_server, Gauge
import rel

import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

websocket.enableTrace(False)

open_g = Gauge('stock_open', 'Price open value of stock')
high_g = Gauge('stock_high', 'Price high value of stock')
low_g = Gauge('stock_low', 'Price low value of stock')
close_g = Gauge('stock_close', 'Price close value of stock')
volume_g = Gauge('stock_volume', 'Price volume value of stock')

def on_open(ws):
    logging.info(f'Starting WebSocket Connection with Binance. Requesting: {symbol} - {interval}')

def on_close(ws, close_status_code, close_msg):
    logging.info('Closing Data Streaming.')

def on_error(ws, error):
    logging.error(error)

def on_message(ws, msg):
    """
    Recives the data from websocket and send to Prometheus.
    """
    msg = json.loads(msg)
    event_time = pd.to_datetime(msg['E'], unit = 'ms')
    start_time = pd.to_datetime(msg['k']['t'], unit = 'ms')
    open     = float(msg['k']['o'])
    high     = float(msg['k']['h'])
    low      = float(msg['k']['l'])
    close    = float(msg['k']['c'])
    volume   = float(msg['k']['v'])
    complete = msg['k']['x']

    if complete == True:
        open_g.set(open)
        high_g.set(high)
        low_g.set(low)
        close_g.set(close)
        volume_g.set(volume)

if __name__ == '__main__':
    try:
        start_http_server(8000)
        logging.info('HTTP server started.')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'Error trying to start http server'
        logging.critical(f'{msg}: {exc_type}: {exc_obj} - Line: {exc_tb.tb_lineno}')

    symbol = 'BTCUSDT'
    interval = '5m'
    ws_endpoint = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{interval}"
    ws = websocket.WebSocketApp(ws_endpoint,
                                on_open = on_open,
                                on_message = on_message,
                                on_close = on_close,
                                on_error = on_error)
    ws.run_forever(dispatcher=rel, reconnect=5)
    rel.signal(2, rel.abort)
    rel.dispatch()