from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.database import connect_to_mongo, close_mongo_connection
from app.routes import auth, ai # Import the route modules
from app.utils.config import settings # Import settings if needed for base path etc.
import logging
import uvicorn # Import uvicorn for __main__ block

# Configure logging (optional but recommended)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup...")
    await connect_to_mongo()
    # You could add other startup logic here (e.g., initializing caches)
    yield
    # Shutdown
    logger.info("Application shutdown...")
    await close_mongo_connection()
    # Add other shutdown logic here

# Define the API prefix (optional)
API_PREFIX = "/api/v1"

app = FastAPI(
    lifespan=lifespan,
    title="FastAPI LangChain MongoDB App",
    description="API integrating FastAPI, LangChain, MongoDB, and Google OAuth.",
    version="0.1.0",
    # You can add other FastAPI configurations like docs_url, redoc_url
    # docs_url=f"{API_PREFIX}/docs",
    # redoc_url=f"{API_PREFIX}/redoc",
    # openapi_url=f"{API_PREFIX}/openapi.json"
)

@app.get("/", tags=["Root"])
async def read_root():
    '''Basic health check or welcome endpoint.'''
    return {"message": "Welcome to the FastAPI LangChain MongoDB API"}

# Include the routers
# Ensure the prefix in the router definition itself is compatible if you use app prefix here
app.include_router(auth.router, prefix=API_PREFIX) # Router defined with prefix="/auth" -> becomes /api/v1/auth
app.include_router(ai.router, prefix=API_PREFIX)   # Router defined with prefix="/ai" -> becomes /api/v1/ai

# Add a simple main block to run the app with uvicorn for development
# This allows running `python app/main.py` directly
if __name__ == "__main__":
    logger.info("Starting Uvicorn server...")
    # Note: For production, use a process manager like Gunicorn or systemd
    #       and run uvicorn programmatically or via command line:
    #       uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0", # Listen on all available network interfaces
        port=8000,
        reload=True, # Enable auto-reload for development (requires 'watchfiles')
        log_level="info"
    )
