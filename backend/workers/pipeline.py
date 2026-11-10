from celery import chain, group, chord
from workers.celery_app import celery_app
from workers.tasks.transcription import transcription_task
from workers.tasks.diarization import diarization_task
from workers.tasks.embedding import embedding_task
from workers.tasks.analytics import analytics_task
from workers.tasks.contradiction import contradiction_task
from workers.tasks.topic import topic_task
from app.core.logging import get_logger
from app.models.job import JobStatus
from workers.status import set_job_status

logger = get_logger(__name__)


def dispatch_pipeline(job_id: str, file_url: str) -> str:
    """
    Orchestrates the full AI processing pipeline using Celery Canvas.

    Execution graph:
        transcription_task + diarization_task (parallel)
                    ↓ (merge)
        group(embedding_task, analytics_task)   ← parallel fan-out
                    ↓ (chord callback)
        contradiction_task
                    ↓
        topic_task
    """
    pipeline = chain(
        # Stage 1: Transcription + Diarization in parallel, then merge
        chord(
            group(
                transcription_task.s(job_id, file_url),
                diarization_task.s(job_id, file_url),
            ),
            _merge_transcript_diarization.s(job_id),
        ),
        # Stage 2: Embedding + Analytics in parallel on merged transcript
        chord(
            group(
                embedding_task.si(job_id),
                analytics_task.si(job_id),
            ),
            _parallel_done.s(job_id),
        ).set(immutable=True),
        # Stage 3: Contradiction detection (needs embeddings from Stage 2)
        contradiction_task.si(job_id),
        # Stage 4: Topic modeling
        topic_task.si(job_id),
    )

    result = pipeline.apply_async()
    logger.info("pipeline_dispatched", job_id=job_id, task_id=result.id)
    return result.id


@celery_app.task(name="workers.pipeline._merge_transcript_diarization")
def _merge_transcript_diarization(results: list, job_id: str) -> str:
    """Chord callback: merges whisper segments with diarization timeline."""
    from ai.transcription.merger import merge_transcript_diarization
    whisper_segments, diarization_segments = results
    merge_transcript_diarization(job_id, whisper_segments, diarization_segments)
    set_job_status(job_id, JobStatus.PROCESSING, 60, "transcript_merged")
    return job_id


@celery_app.task(name="workers.pipeline._parallel_done")
def _parallel_done(results: list, job_id: str) -> str:
    """Chord callback: signals embedding + analytics both complete."""
    set_job_status(job_id, JobStatus.PROCESSING, 80, "intelligence_complete")
    return job_id
