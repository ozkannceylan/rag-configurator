"""Celery application configuration."""

from celery import Celery

from app.core.settings import settings

# Create Celery instance
celery_app = Celery(
    "ingestion_worker",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.tasks.ingestion", "app.tasks.ingestion_task"],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task settings
    task_default_queue=settings.celery_task_default_queue,
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Reject task if worker is lost
    task_track_started=True,  # Track when task starts
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Include task name in result
    # Worker settings
    worker_prefetch_multiplier=1,  # Fetch one task at a time for fair distribution
    worker_concurrency=settings.max_concurrent_tasks,
    # Task execution limits
    task_soft_time_limit=3600,  # Soft limit: 1 hour
    task_time_limit=3900,  # Hard limit: 1 hour 5 minutes
    # Retry settings
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,
    # Event settings for monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Task routes for different queues (optional, for scaling)
celery_app.conf.task_routes = {
    "app.tasks.ingestion.process_ingestion": {"queue": "ingestion"},
    "app.tasks.ingestion.process_document": {"queue": "ingestion"},
    "app.tasks.ingestion.generate_embeddings": {"queue": "embeddings"},
    "app.tasks.ingestion_task.run_ingestion": {"queue": "ingestion"},
    "app.tasks.ingestion_task.cancel_ingestion": {"queue": "ingestion"},
    "app.tasks.ingestion_task.get_ingestion_status": {"queue": "ingestion"},
}


def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app
