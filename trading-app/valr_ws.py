import websocket
import json
import hmac
import hashlib
import time
import os
import logging
from dotenv import load_dotenv
from typing import Optional, Tuple, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ValrWebSocket:
    def __init__(self, on_price_update: Optional[Callable[[float, float], None]] = None):
        load_dotenv()
        self.api_key = os.getenv('VALR_API_KEY')
        self.api_secret = os.getenv('VALR_API_SECRET')
        self.ws_url = "wss://api.valr.com/ws/trade"
        self.ws = None
        self.on_price_update = on_price_update
        self.last_bid: Optional[float] = None
        self.last_ask: Optional[float] = None

    def _generate_signature(self, timestamp: int) -> str:
        path = "/ws/trade"
        verb = "GET"
        body = ""
        
        message = str(timestamp) + verb + path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        return signature

    def on_message(self, ws, message):
        data = json.loads(message)
        if data.get('type') == 'AUTHENTICATED':
            self.subscribe_to_orderbook()
        elif data.get('type') == 'AGGREGATED_ORDERBOOK_UPDATE':
            orderbook = data.get('data', {})
            bids = orderbook.get('Bids', [])
            asks = orderbook.get('Asks', [])
            
            if bids and asks:
                try:
                    bid = float(bids[0]['price'])
                    ask = float(asks[0]['price'])
                    self.last_bid = bid
                    self.last_ask = ask
                    if self.on_price_update:
                        self.on_price_update(bid, ask)
                except (IndexError, KeyError, ValueError) as e:
                    print(f"Error parsing prices: {e}")

    def on_error(self, ws, error):
        logging.error(f"VALR WebSocket error: {error}")
        self._reconnect()

    def on_close(self, ws, close_status_code, close_msg):
        logging.warning(f"VALR WebSocket closed. Code: {close_status_code}, Message: {close_msg}")
        self._reconnect()

    def on_open(self, ws):
        logging.info("VALR WebSocket connected")

    def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        max_retries = 5
        retry_delay = 5  # Initial delay in seconds

        for attempt in range(max_retries):
            try:
                time.sleep(retry_delay)
                logging.info(f"Attempting to reconnect to VALR (attempt {attempt + 1}/{max_retries})")
                self.connect()
                return
            except Exception as e:
                logging.error(f"Reconnection attempt {attempt + 1} failed: {e}")
                retry_delay = min(retry_delay * 2, 60)  # Double delay up to 60 seconds

        logging.error("Failed to reconnect to VALR after maximum retries")

    def get_current_prices(self) -> Tuple[Optional[float], Optional[float]]:
        """Get the most recent bid and ask prices"""
        return self.last_bid, self.last_ask

    def connect(self):
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(timestamp)

        headers = {
            'X-VALR-API-KEY': self.api_key,
            'X-VALR-SIGNATURE': signature,
            'X-VALR-TIMESTAMP': str(timestamp)
        }

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=[": ".join([k, v]) for k, v in headers.items()],
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        self.ws.run_forever()

    def subscribe_to_orderbook(self):
        if self.ws:
            subscribe_message = {
                "type": "SUBSCRIBE",
                "subscriptions": [
                    {
                        "event": "AGGREGATED_ORDERBOOK_UPDATE",
                        "pairs": ["USDTZAR"]
                    }
                ]
            }
            self.ws.send(json.dumps(subscribe_message))

    def unsubscribe_from_orderbook(self):
        if self.ws:
            unsubscribe_message = {
                "type": "SUBSCRIBE",
                "subscriptions": [
                    {
                        "event": "AGGREGATED_ORDERBOOK_UPDATE",
                        "pairs": []
                    }
                ]
            }
            self.ws.send(json.dumps(unsubscribe_message))
