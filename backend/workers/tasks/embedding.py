from workers.celery_app import celery_app
from app.core.logging import get_logger
from app.models.job import JobStatus
from workers.status import set_job_status

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.embedding.embedding_task",
    bind=True,
    max_retries=2,
    default_retry_delay=20,
)
def embedding_task(self, job_id: str) -> dict:
    """
    Load merged transcript chunks from DB, generate embeddings,
    and upsert to Qdrant vector store.
    """
    from ai.embedding.encoder import ingest_job_embeddings
    import asyncio

    logger.info("embedding_started", job_id=job_id)
    set_job_status(job_id, JobStatus.PROCESSING, 65, "embedding")

    try:
        count = asyncio.run(ingest_job_embeddings(job_id))
        stats = {"vectors_ingested": count}
        logger.info("embedding_done", job_id=job_id, **stats)
        set_job_status(job_id, JobStatus.PROCESSING, 75, "embedding_complete")
        return stats

    except Exception as exc:
        logger.error("embedding_failed", job_id=job_id, error=str(exc))
        if self.request.retries >= self.max_retries:
            set_job_status(job_id, JobStatus.FAILED, stage="embedding_failed", error_msg=str(exc))
        raise self.retry(exc=exc)
