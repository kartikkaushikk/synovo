from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "cip",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_RESULT_BACKEND,
    include=[
        "workers.tasks.transcription",
        "workers.tasks.diarization",
        "workers.tasks.embedding",
        "workers.tasks.analytics",
        "workers.tasks.contradiction",
        "workers.tasks.topic",
        "workers.pipeline",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_LIMIT,
    task_time_limit=settings.CELERY_TASK_SOFT_LIMIT + 60,
    worker_prefetch_multiplier=1,          # fair dispatch — critical for long GPU tasks
    task_acks_late=True,                   # ack only after success (safer retry)
    task_reject_on_worker_lost=True,
    result_expires=86400,                  # 24h result TTL
    task_routes={
        "workers.tasks.transcription.*": {"queue": "transcription"},
        "workers.tasks.diarization.*":   {"queue": "diarization"},
        "workers.tasks.embedding.*":     {"queue": "embedding"},
        "workers.tasks.analytics.*":     {"queue": "analytics"},
        "workers.tasks.contradiction.*": {"queue": "contradiction"},
        "workers.tasks.topic.*":         {"queue": "topic"},
    },
    task_default_queue="default",
)
