import tempfile
import os
from workers.celery_app import celery_app
from app.core.logging import get_logger
from app.models.job import JobStatus
from workers.status import set_job_status

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.transcription.transcription_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def transcription_task(self, job_id: str, file_url: str) -> list[dict]:
    """
    Download audio and transcribe with Faster-Whisper.
    Returns list of segment dicts with text, start, end, words, confidence.
    Updates job progress via Redis.
    """
    from ai.transcription.whisper_engine import WhisperEngine
    from app.services.storage import download_file
    import asyncio

    logger.info("transcription_started", job_id=job_id)
    set_job_status(job_id, JobStatus.PROCESSING, 10, "transcription")

    try:
        # Download file to temp location
        file_bytes = asyncio.run(download_file(file_url))
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
            f.write(file_bytes)
            tmp_path = f.name

        engine = WhisperEngine()
        segments = engine.transcribe(tmp_path)

        set_job_status(job_id, JobStatus.PROCESSING, 35, "transcription_complete")

        logger.info("transcription_done", job_id=job_id, segments=len(segments))
        return segments

    except Exception as exc:
        logger.error("transcription_failed", job_id=job_id, error=str(exc))
        if self.request.retries >= self.max_retries:
            set_job_status(job_id, JobStatus.FAILED, stage="transcription_failed", error_msg=str(exc))
        raise self.retry(exc=exc)
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)

