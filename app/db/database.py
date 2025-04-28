from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.utils.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_manager = MongoDB()

async def connect_to_mongo():
    '''Connects to MongoDB using the URI from settings.'''
    logger.info("Connecting to MongoDB...")
    try:
        db_manager.client = AsyncIOMotorClient(settings.mongo_uri)
        # Extract database name from URI if present, otherwise default
        # This assumes the DB name might be part of the URI path
        db_name = settings.mongo_uri.split('/')[-1].split('?')[0]
        if not db_name:
            db_name = "mydatabase" # Default database name if not in URI
            logger.warning(f"Database name not found in MONGO_URI, using default: {db_name}")
        db_manager.db = db_manager.client[db_name]
        logger.info(f"Successfully connected to MongoDB, database: '{db_name}'")
        # You might want to ping the server to confirm connection
        await db_manager.client.admin.command('ping')
        logger.info("MongoDB ping successful.")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        # Depending on your strategy, you might want to exit the app or handle reconnection
        raise

async def close_mongo_connection():
    '''Closes the MongoDB connection.'''
    logger.info("Closing MongoDB connection...")
    if db_manager.client:
        db_manager.client.close()
        logger.info("MongoDB connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    '''Returns the database instance.'''
    if db_manager.db is None:
        # This scenario ideally shouldn't happen if connect_to_mongo is called at startup
        logger.error("Database instance is not available. Connection might have failed.")
        raise RuntimeError("Database not initialized. Call connect_to_mongo first.")
    return db_manager.db

# Example of getting a collection (optional, can be done in services)
# async def get_user_collection():
#     db = get_database()
#     return db.get_collection("users")
