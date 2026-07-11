"""
Celery Application Configuration
==================================
Async task queue for VigyanLLM 22-step pipeline execution.
Uses Redis as both broker and result backend.
"""

import os

from celery import Celery

# Redis connection URL from environment, defaulting to localhost
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Create Celery application
celery_app = Celery(
    "primerforge",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["primerforge.engine.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Task tracking
    task_track_started=True,

    # Time limit: 10 minutes max per pipeline task
    task_time_limit=600,

    # Prefetch 1 task at a time (suitable for long-running pipeline tasks)
    worker_prefetch_multiplier=1,

    # Timezone
    timezone="UTC",
    enable_utc=True,
)


def init_celery_with_flask(app):
    """
    Initialize Celery to work within Flask application context.
    This allows tasks to access Flask extensions (DB, config, etc.).
    """

    class FlaskTask(celery_app.Task):
        """Celery task subclass that runs within Flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask
    celery_app.conf.update(app.config)
    return celery_app
