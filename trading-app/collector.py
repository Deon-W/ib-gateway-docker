import asyncio
import logging
import os
import signal
import sys
import subprocess
import time
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
import nest_asyncio
import threading
from ib_insync import *
from valr_ws import ValrWebSocket
from usdzar_db import insert_usdzar_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Allow nested event loops
nest_asyncio.apply()

class PriceCollector:
    def __init__(self):
        # Initialize IB connection
        self.ib = IB()
        self.connected_to_ib = False
        
        # Store latest prices
        self.ib_bid = None
        self.ib_ask = None
        self.valr_bid = None
        self.valr_ask = None
        self.last_timestamp = None

        # Define callback before creating ValrWebSocket
        def _on_valr_price_update(bid: float, ask: float):
            self.valr_bid = bid
            self.valr_ask = ask
            # logging.info(f"VALR Price Update - Bid: {bid}, Ask: {ask}")

        self.valr_ws = ValrWebSocket(on_price_update=_on_valr_price_update)
        self.valr_ws_thread = None

        # Setup signal handlers
        

    async def connect_to_ib(self, max_retries=5):
        """Connect to IB Gateway with retries and data farm verification"""
        await asyncio.sleep(60)  # Initial delay to ensure IB Gateway is ready
        retry_delay = 5  # Initial delay in seconds

        while True:  # Keep trying to connect indefinitely
            for attempt in range(max_retries):
                try:
                    if hasattr(self, 'ib') and self.ib.isConnected():
                        self.ib.disconnect()

                    self.ib = IB()
                    host = os.environ.get('IB_HOST', '127.0.0.1')
                    port = int(os.environ.get('IB_PORT', '4002'))
                    logging.info(f"Attempting to connect to IB Gateway (attempt {attempt + 1}/{max_retries})")
                    
                    await self.ib.connectAsync(host, port, clientId=1)
                    await asyncio.sleep(2)  # Wait for connection to stabilize
                    
                    if not self.ib.isConnected():
                        raise ConnectionError("Failed to connect to IB Gateway")
                    
                    # Check data farm connections
                    account = self.ib.managedAccounts()[0]
                    self.ib.reqMarketDataType(3)  # Request delayed market data
                    
                    logging.info("Successfully connected to IB Gateway")
                    self.connected_to_ib = True
                    return True
                    
                except Exception as e:
                    logging.error(f"Failed to connect to IB Gateway (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)  # Double delay up to 60 seconds
                    else:
                        logging.error("Failed all immediate retries, waiting 60 seconds before starting over")
                        await asyncio.sleep(60)
                        retry_delay = 5  # Reset delay
                        break  # Break inner loop to start fresh retry sequence
                    
            # If we get here, all retries in this round failed
            logging.error("All connection attempts failed, waiting 60 seconds before next round")
            await asyncio.sleep(60)
            retry_delay = 5  # Reset delay

    def start_valr_websocket(self):
        """Start VALR websocket connection in a separate thread"""
        if self.valr_ws_thread is None or not self.valr_ws_thread.is_alive():
            self.valr_ws_thread = threading.Thread(target=self.valr_ws.connect)
            self.valr_ws_thread.daemon = True
            self.valr_ws_thread.start()
            logging.info("VALR websocket connection started")
            
    def get_valr_prices(self):
        """Get VALR USDTZAR prices from websocket with retry mechanism"""
        # Check if we need to restart the websocket
        if self.valr_ws_thread is None or not self.valr_ws_thread.is_alive():
            self.start_valr_websocket()
            time.sleep(2)  # Give websocket time to connect
        
        # Check if we have valid prices
        if self.valr_bid is None or self.valr_ask is None:
            error_msg = "No valid VALR prices available"
            raise ValueError(error_msg)
            
        # Check for stale prices (no updates in last 30 seconds)
        if hasattr(self, 'last_valr_update') and time.time() - self.last_valr_update > 30:
            error_msg = "VALR prices are stale"
            # Force websocket restart
            if self.valr_ws and self.valr_ws.ws:
                self.valr_ws.unsubscribe_from_orderbook()
            self.valr_ws_thread = None
            raise ValueError(error_msg)
            
        return self.valr_bid, self.valr_ask

    async def collect_prices(self):
        """Collect and print prices from both sources"""
        while True:
            try:
                # Check connection status
                if not self.ib.isConnected():
                    logging.warning("IB connection lost, attempting to reconnect...")
                    connected = await self.connect_to_ib()
                    if not connected:
                        logging.error("Failed to reconnect to IB")
                        await asyncio.sleep(20)
                        continue

                # Set up IB contract
                usdzar = Forex('USDZAR')
                self.ib.qualifyContracts(usdzar)
                ticker = self.ib.reqMktData(usdzar)
                
                # Wait for initial market data
                data_received = False
                for _ in range(10):  # Try for up to 10 seconds
                    if not self.ib.isConnected():
                        break
                    await asyncio.sleep(0.5)
                    if ticker.bid and ticker.ask:
                        data_received = True
                        break
                
                if not data_received:
                    logging.warning("No market data received, retrying...")
                    await asyncio.sleep(20)
                    continue

                # Get VALR prices with retry mechanism
                self.valr_bid, self.valr_ask = self.get_valr_prices()
                
                # Get IB prices with validation
                if ticker.bid is not None and ticker.ask is not None:
                    bid = abs(ticker.bid) if ticker.bid < 0 else ticker.bid  # Convert negative to positive
                    ask = abs(ticker.ask) if ticker.ask < 0 else ticker.ask  # Convert negative to positive
                    
                    # Validate prices are above minimum threshold
                    if bid >= 2 and ask >= 2:
                        self.ib_bid = bid
                        self.ib_ask = ask
                        # Clear any previous errors and mark as running when prices are valid

                    else:
                        self.ib_bid = None
                        self.ib_ask = None
                        error_msg = f"Invalid IB prices detected: bid={bid}, ask={ask} (values below 2)"
                        logging.info(error_msg)
                        # logging.info(f"IB   USD/ZAR | Bid: {self.ib_bid:.4f} | Ask: {self.ib_ask:.4f}")
                        logging.info(f"VALR USDTZAR | Bid: {self.valr_bid:.4f} | Ask: {self.valr_ask:.4f}")
                        logging.info("Not storing data...")

                        await asyncio.sleep(20)
                        continue
                
                # Helper function to check if price is valid
                def is_valid_price(p):
                    return p is not None and not (isinstance(p, float) and (p != p))  # Check for None and NaN
                    
                # Store data in MongoDB if all prices are available and valid
                if all(is_valid_price(x) for x in [self.ib_bid, self.ib_ask, self.valr_bid, self.valr_ask]):
                    # Record timestamp right before storing
                    current_time = datetime.now(ZoneInfo("Africa/Johannesburg"))
                    
                    # Log the valid prices
                    logging.info(f"\nPrices at {current_time.strftime('%H:%M:%S')}:")
                    logging.info(f"IB   USD/ZAR | Bid: {self.ib_bid:.4f} | Ask: {self.ib_ask:.4f}")
                    logging.info(f"VALR USDTZAR | Bid: {self.valr_bid:.4f} | Ask: {self.valr_ask:.4f}")
                    
                    price_data = {
                        'timestamp': current_time,
                        'ib_bid': self.ib_bid,
                        'ib_ask': self.ib_ask,
                        'valr_bid': self.valr_bid,
                        'valr_ask': self.valr_ask
                    }
                    
                    try:
                        if insert_usdzar_data(price_data):
                            logging.info(f"Data stored successfully at {current_time.strftime('%H:%M:%S')} - IB: {self.ib_bid:.4f}/{self.ib_ask:.4f}, VALR: {self.valr_bid:.4f}/{self.valr_ask:.4f}")
                        else:
                            error_msg = "Failed to store price data in MongoDB"
                            self.health_monitor.record_error(error_msg)
                            logging.error(error_msg)
                            self.telegram.telegram(f"⚠️ MongoDB Error: {error_msg}")
                            await asyncio.sleep(20)
                            continue
                    except Exception as e:
                        error_msg = f"Database error: {str(e)}"

                        logging.error(error_msg)
                        await asyncio.sleep(20)
                        continue
                else:
                    missing = []
                    if not is_valid_price(self.ib_bid) or not is_valid_price(self.ib_ask):
                        missing.append("IB prices")
                    if not is_valid_price(self.valr_bid) or not is_valid_price(self.valr_ask):
                        missing.append("VALR prices")
                    error_msg = f"Missing valid prices for: {', '.join(missing)}"
                    logging.warning(error_msg)
                    await asyncio.sleep(20)
                    continue

            except Exception as e:
                error_msg = f"Unexpected error in price collection: {str(e)}"

                logging.error(error_msg)
 
                await asyncio.sleep(20)
                continue
            
            # Wait for next update if everything was successful
            await asyncio.sleep(15)



    async def run(self):
        """Main run function"""
        try:
            logging.info("Starting USD/ZAR price streaming service...")
            logging.info("Waiting 60 seconds for IB Gateway to be fully ready...")
            await asyncio.sleep(60)  # Initial delay to ensure IB Gateway is ready
            
            retry_count = 0
            stable_connection_time = 0
            
            while True:
                try:
                    # Start VALR websocket
                    self.start_valr_websocket()
                    
                    # Connect to IB
                    if not await self.connect_to_ib():
                        retry_count += 1
                        wait_time = min(30 * retry_count, 300)  # Exponential backoff, max 5 minutes
                        logging.error(f"Connection failed. Retrying in {wait_time} seconds... (Attempt {retry_count})")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Reset retry count if we've been connected for more than 5 minutes
                    current_time = time.time()
                    if current_time - stable_connection_time > 300:
                        retry_count = 0
                        stable_connection_time = current_time
                    
                    logging.info("Starting price collection...")
                    await self.collect_prices()
                    
                except Exception as e:
                    logging.error(f"Error occurred: {e}")
                    retry_count += 1
                    wait_time = min(30 * retry_count, 300)  # Exponential backoff, max 5 minutes
                    logging.error(f"Reconnecting in {wait_time} seconds... (Attempt {retry_count})")
                    if self.ib and self.ib.isConnected():
                        self.ib.disconnect()
                    await asyncio.sleep(wait_time)
                    
        except Exception as e:
            error_msg = f"Fatal error in price collector: {str(e)}"
            logging.error(error_msg)
            raise

if __name__ == "__main__":
    collector = PriceCollector()
    try:
        asyncio.run(collector.run())

    except Exception as e:
        error_msg = f"❌ Fatal error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        sys.exit(1)
