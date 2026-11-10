from workers.celery_app import celery_app
from app.core.logging import get_logger
from app.models.job import JobStatus
from workers.status import set_job_status

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.contradiction.contradiction_task",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
)
def contradiction_task(self, job_id: str) -> dict:
    """
    Run NLI-based contradiction detection on all transcript pairs.
    Uses DeBERTa cross-encoder, time-windowed pair generation.
    Persists flagged contradictions to DB.
    """
    from ai.contradiction.detector import detect_contradictions
    import asyncio

    logger.info("contradiction_started", job_id=job_id)
    set_job_status(job_id, JobStatus.PROCESSING, 85, "contradiction")
    try:
        contradictions = asyncio.run(detect_contradictions(job_id))
        stats = {"contradictions_found": len(contradictions)}
        logger.info("contradiction_done", job_id=job_id, **stats)
        set_job_status(job_id, JobStatus.PROCESSING, 90, "contradiction_complete")
        return stats
    except Exception as exc:
        logger.error("contradiction_failed", job_id=job_id, error=str(exc))
        if self.request.retries >= self.max_retries:
            set_job_status(job_id, JobStatus.FAILED, stage="contradiction_failed", error_msg=str(exc))
        raise self.retry(exc=exc)


