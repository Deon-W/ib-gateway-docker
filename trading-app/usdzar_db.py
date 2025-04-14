import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
from mongodb import db_connection

logger = logging.getLogger(__name__)

def insert_usdzar_data(data: Dict[str, Any]) -> bool:
    """
    Insert USDZAR price data into the database.
    
    Args:
        data: Dictionary containing price data with fields:
            - timestamp: datetime
            - ib_bid: float
            - ib_ask: float
            - valr_bid: float
            - valr_ask: float
    
    Returns:
        bool: True if insertion was successful, False otherwise
    """
    try:
        with db_connection() as db:
            collection = db.usdzar
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now(ZoneInfo("Africa/Johannesburg"))
            
            # Create a copy of the data for MongoDB
            mongo_data = data.copy()
            
            # Convert timestamp to UTC for storage
            # MongoDB will store in UTC but maintain the correct instant in time
            if mongo_data['timestamp'].tzinfo:
                mongo_data['timestamp'] = mongo_data['timestamp'].astimezone(timezone.utc)
                
            # Insert the document
            result = collection.insert_one(mongo_data)
            
            # Verify insertion
            inserted_doc = collection.find_one({'_id': result.inserted_id})
            if inserted_doc:
                return True
            else:
                logger.error("Document not found after insertion")
                return False
            
    except Exception as e:
        logger.error(f"Error inserting USDZAR data: {str(e)}")
        return False

def get_latest_usdzar_price() -> Optional[Dict[str, Any]]:
    """
    Get the most recent USDZAR price data.
    
    Returns:
        Optional[Dict]: Latest price data or None if no data exists
    """
    try:
        with db_connection() as db:
            collection = db.usdzar
            
            # Get the most recent document by timestamp
            latest = collection.find_one(
                sort=[('timestamp', -1)]  # -1 for descending order
            )
            
            if latest:
                # Convert UTC timestamp to SA time
                latest['timestamp'] = latest['timestamp'].replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Africa/Johannesburg'))
            
            return latest
            
    except Exception as e:
        logger.error(f"Error retrieving latest USDZAR data: {str(e)}")
        return None

def create_usdzar_indexes():
    """Create necessary indexes for the USDZAR collection."""
    try:
        with db_connection() as db:
            collection = db.usdzar
            
            # Create timestamp index for efficient time-based queries
            collection.create_index([("timestamp", -1)], 
                                   background=True, 
                                   name="timestamp_desc")
            
            # Create compound indexes for commonly queried field combinations
            collection.create_index([
                ("timestamp", -1),
                ("ib_bid", 1),
                ("valr_ask", 1)
            ], background=True, name="price_analysis_bid_ask")
            
            collection.create_index([
                ("timestamp", -1),
                ("valr_bid", 1),
                ("ib_ask", 1)
            ], background=True, name="price_analysis_ask_bid")
            
            # Optional: Add TTL index if you want to automatically remove old data
            # collection.create_index("timestamp", expireAfterSeconds=7*24*60*60)  # 7 days
            
            logger.info("Successfully created indexes for USDZAR collection")
            
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")

def get_price_data_range(start_time: datetime, end_time: datetime, fields: list = None) -> list:
    """Get price data for a specific time range.
    
    Args:
        start_time: Start of the time range
        end_time: End of the time range
        fields: List of fields to return (optimization for partial document reads)
               e.g., ['timestamp', 'ib_bid', 'valr_ask']
    
    Returns:
        list: List of price data documents within the time range
    """
    try:
        with db_connection() as db:
            collection = db.usdzar
            
            # Prepare projection for selective field retrieval
            projection = None
            if fields:
                projection = {field: 1 for field in fields}
                projection['_id'] = 0  # Exclude _id unless specifically requested
            
            # Query using the timestamp index
            query = {
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }
            
            cursor = collection.find(
                query,
                projection=projection
            ).sort("timestamp", -1)
            
            return list(cursor)
            
    except Exception as e:
        logger.error(f"Error retrieving price data range: {str(e)}")
        return []
