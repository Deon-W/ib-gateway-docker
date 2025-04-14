import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from contextlib import contextmanager
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
_mongo_client: Optional[MongoClient] = None

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
else:
    logger.info(f"DATABASE_URL is set and has length: {len(DATABASE_URL)}")

def get_mongo_client() -> MongoClient:
    """Get or create MongoDB client instance (singleton pattern)."""
    global _mongo_client
    
    if _mongo_client is None:
        logger.info("Creating new MongoDB client connection")
        try:
            _mongo_client = MongoClient(DATABASE_URL)
            # Test the connection
            _mongo_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    return _mongo_client

def get_database(db_name: str = 'market_data') -> Database:
    """Get MongoDB database instance.
    Args:
        db_name: Name of the database to connect to. Defaults to 'market_data'.
    Returns:
        Database: MongoDB database instance
    Raises:
        ValueError: If DATABASE_URL is not set
    """
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable is not set")
        raise ValueError("DATABASE_URL environment variable is not set")
    
    client = get_mongo_client()
    return client[db_name]

@contextmanager
def db_connection(db_name: str = 'market_data'):
    """Context manager for database operations.
    
    Use this when you want to ensure proper connection handling:
    
    with db_connection() as db:
        db.collection.find(...)
    """
    try:
        db = get_database(db_name)
        yield db
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        raise
    
def close_connection() -> None:
    """Close the MongoDB connection if it exists.
    Only call this when shutting down the application."""
    global _mongo_client
    if _mongo_client is not None:
        logger.info("Closing MongoDB connection")
        try:
            _mongo_client.close()
            _mongo_client = None
            logger.info("MongoDB connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
def ping_test() -> str:
    """Test the connection to the MongoDB database.
    
    Returns:
        str: Success or error message
    """
    try:
        db = get_database()
        db.client.admin.command('ping')
        return "Pinged your deployment. You successfully connected to MongoDB!"
    except Exception as e:
        return f"Connection failed: {e}"
    finally:
        close_connection()
