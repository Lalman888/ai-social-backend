from celery import Celery
from app.utils.config import settings
import logging

logger = logging.getLogger(__name__)

# Ensure Redis URLs are loaded correctly
logger.info(f"Initializing Celery with Broker: {settings.celery_broker_url}")
logger.info(f"Initializing Celery with Backend: {settings.celery_result_backend}")

celery_app = Celery(
    "worker", # Application name
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.automation_tasks"] # List of modules where tasks are defined
)

# Optional Celery configuration settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Allow json content
    result_serializer="json",
    timezone="UTC", # Use UTC timezone
    enable_utc=True,
    # Add other configurations as needed
    # result_expires=3600, # Example: expire results after 1 hour
    # broker_connection_retry_on_startup=True, # Retry connection on startup
)

# Optional: Setup logging for Celery
# from celery.signals import setup_logging
# @setup_logging.connect
# def config_loggers(*args, **kwargs):
#     from logging.config import dictConfig
#     # Load logging configuration from a dict or file
#     # dictConfig(...)
#     logger.info("Celery logging configured.")

# Example Task (can be removed once actual tasks are in automation_tasks.py)
@celery_app.task
def example_task(x, y):
    logger.info(f"Running example task with args: {x}, {y}")
    return x + y

if __name__ == "__main__":
    # This allows running the worker directly for development/debugging
    # Command: python -m app.core.celery_app worker --loglevel=info
    # Or using the celery command directly:
    # celery -A app.core.celery_app worker --loglevel=info
    logger.warning("Running Celery worker directly from celery_app.py is intended for debugging.")
    celery_app.worker_main(["worker", "--loglevel=info"])
