#!/usr/bin/env python
"""
Celery worker entry point for cookbook-creator.

This script initializes the Flask app context and starts the Celery worker.

Usage:
    celery -A celery_worker:celery worker --loglevel=info --concurrency=1

Or using uv:
    uv run celery -A celery_worker:celery worker --loglevel=info --concurrency=1
"""
import os
import logging

# Set Flask environment before importing app
# Default to 'development' for local testing; production sets this explicitly
os.environ.setdefault('FLASK_ENV', 'development')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Flask app and create Celery instance
from app import create_app
from app.celery_app import make_celery

# Create Flask app
logger.info("Creating Flask application for Celery worker...")
flask_app = create_app()

# Create Celery instance with Flask app context
logger.info("Initializing Celery with Flask app context...")
celery = make_celery(flask_app)

# Push app context for the worker
# This ensures all tasks have access to Flask's app context
flask_app.app_context().push()

logger.info("Celery worker initialized successfully")

if __name__ == '__main__':
    celery.start()
