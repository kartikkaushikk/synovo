import tempfile
import os
import subprocess
from workers.celery_app import celery_app
from app.core.logging import get_logger
from app.models.job import JobStatus
from workers.status import set_job_status

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.diarization.diarization_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def diarization_task(self, job_id: str, file_url: str) -> list[dict]:
    """
    Run pyannote speaker diarization on the audio file.
    Returns list of {speaker, start, end} dicts.
    """
    from ai.diarization.pyannote_engine import DiarizationEngine
    from app.core.config import settings
    from app.services.storage import download_file
    import asyncio

    logger.info("diarization_started", job_id=job_id)
    set_job_status(job_id, JobStatus.PROCESSING, 40, "diarization")

    if not settings.HUGGINGFACE_TOKEN or settings.HUGGINGFACE_TOKEN == "hf_your_token_here":
        logger.warning("diarization_skipped_no_token", job_id=job_id)
        set_job_status(job_id, JobStatus.PROCESSING, 50, "diarization_skipped")
        return []
    if settings.WHISPER_DEVICE != "cuda" and not settings.ENABLE_CPU_DIARIZATION:
        logger.warning("diarization_skipped_cpu_disabled", job_id=job_id)
        set_job_status(job_id, JobStatus.PROCESSING, 50, "diarization_skipped_cpu")
        return []

    try:
        file_bytes = asyncio.run(download_file(file_url))
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as f:
            f.write(file_bytes)
            tmp_path = f.name
        wav_path = f"{tmp_path}.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                tmp_path,
                "-ac",
                "1",
                "-ar",
                "16000",
                wav_path,
            ],
            check=True,
        )

        engine = DiarizationEngine.get()
        segments = engine.diarize(wav_path)

        logger.info("diarization_done", job_id=job_id, segments=len(segments))
        set_job_status(job_id, JobStatus.PROCESSING, 55, "diarization_complete")
        return segments

    except Exception as exc:
        logger.error("diarization_failed", job_id=job_id, error=str(exc))
        if self.request.retries >= self.max_retries:
            set_job_status(job_id, JobStatus.FAILED, stage="diarization_failed", error_msg=str(exc))
        raise self.retry(exc=exc)
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if "wav_path" in locals() and os.path.exists(wav_path):
            os.unlink(wav_path)
