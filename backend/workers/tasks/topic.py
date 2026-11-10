from workers.celery_app import celery_app
from app.core.logging import get_logger
from app.models.job import JobStatus
from workers.status import set_job_status

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.topic.topic_task",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
)
def topic_task(self, job_id: str) -> dict:
    from ai.topic.bertopic_engine import extract_topics
    import asyncio
    logger.info("topic_started", job_id=job_id)
    set_job_status(job_id, JobStatus.PROCESSING, 95, "topic")
    try:
        result = asyncio.run(extract_topics(job_id))
        logger.info("topic_done", job_id=job_id, num_topics=len(result.get("topics", [])))
        set_job_status(job_id, JobStatus.COMPLETED, 100, "completed")
        return result
    except Exception as exc:
        logger.error("topic_failed", job_id=job_id, error=str(exc))
        if self.request.retries >= self.max_retries:
            set_job_status(job_id, JobStatus.FAILED, stage="topic_failed", error_msg=str(exc))
        raise self.retry(exc=exc)
