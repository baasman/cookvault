"""
Celery application configuration for cookbook-creator.

This module creates and configures the Celery instance with Flask app context integration.
"""
import os
from celery import Celery


def make_celery(app=None):
    """
    Create a Celery instance configured for Flask app context.

    This function can be called:
    1. With app=None: Creates a standalone Celery instance for workers
    2. With app: Integrates with an existing Flask app

    Args:
        app: Optional Flask application instance

    Returns:
        Configured Celery instance
    """
    # Get Redis URL from environment or use default
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    celery = Celery(
        'cookbook_creator',
        broker=redis_url,
        backend=redis_url,
        include=['app.tasks.recipe_tasks']
    )

    # Default Celery configuration
    celery.conf.update(
        # Task serialization
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='UTC',
        enable_utc=True,

        # Worker settings - CRITICAL: concurrency=1 for sequential processing
        worker_concurrency=1,
        worker_prefetch_multiplier=1,  # Fetch only 1 task at a time

        # Task time limits (match Gunicorn timeout)
        task_soft_time_limit=170,  # Soft limit: 170 seconds
        task_time_limit=180,       # Hard limit: 180 seconds

        # Result backend settings
        result_expires=3600,  # Results expire after 1 hour

        # Task acknowledgment - ensures task is re-queued if worker dies
        task_acks_late=True,
        task_reject_on_worker_lost=True,

        # Retry settings
        task_default_retry_delay=30,
        task_max_retries=2,

        # Broker transport options
        broker_transport_options={
            'visibility_timeout': 3600,  # 1 hour
        },
    )

    if app:
        # Update config from Flask app
        celery.conf.update(
            broker_url=app.config.get('REDIS_URL', redis_url),
            result_backend=app.config.get('REDIS_URL', redis_url),
        )

        # Make tasks run within Flask app context
        class ContextTask(celery.Task):
            """Custom task class that runs within Flask app context."""

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Create a default celery instance for workers to import
celery = make_celery()
