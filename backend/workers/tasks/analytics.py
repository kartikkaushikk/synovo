from workers.celery_app import celery_app
from app.core.logging import get_logger
from app.models.job import JobStatus
from workers.status import set_job_status

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.analytics.analytics_task",
    bind=True,
    max_retries=2,
    default_retry_delay=20,
)
def analytics_task(self, job_id: str) -> dict:
    """
    Compute behavioral analytics: WPM timeline, pause events, filler words,
    speaking balance, confidence trend. Writes results to analytics table.
    """
    from ai.analytics.engine import AnalyticsEngine
    import asyncio

    logger.info("analytics_started", job_id=job_id)
    set_job_status(job_id, JobStatus.PROCESSING, 65, "analytics")
    try:
        engine = AnalyticsEngine()
        result = asyncio.run(engine.analyze(job_id))
        logger.info("analytics_done", job_id=job_id)
        set_job_status(job_id, JobStatus.PROCESSING, 75, "analytics_complete")
        return result
    except Exception as exc:
        logger.error("analytics_failed", job_id=job_id, error=str(exc))
        if self.request.retries >= self.max_retries:
            set_job_status(job_id, JobStatus.FAILED, stage="analytics_failed", error_msg=str(exc))
        raise self.retry(exc=exc)
