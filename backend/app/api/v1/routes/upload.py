import io
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres import get_db
from app.services.storage import upload_file
from app.services.job_service import create_job
from app.schemas.upload import UploadResponse
from app.models.job import JobStatus
from app.core.logging import get_logger
from workers.pipeline import dispatch_pipeline

router = APIRouter(prefix="/upload", tags=["upload"])
logger = get_logger(__name__)

ALLOWED_TYPES = {"audio/mpeg", "audio/wav", "audio/mp4", "audio/ogg",
                 "video/mp4", "video/webm", "audio/webm", "audio/x-m4a"}
MAX_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB


@router.post("", response_model=UploadResponse, status_code=202)
async def upload_audio(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an audio or video file for async processing.
    Returns a job_id to track progress via /jobs/{job_id}.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {file.content_type}. Allowed: {ALLOWED_TYPES}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max 500MB.")

    file_type = "video" if file.content_type.startswith("video") else "audio"

    # Upload to object storage
    file_url = await upload_file(file_bytes, file.filename, file.content_type)

    # Create DB record
    job = await create_job(db, file_url, file.filename, file_type)
    job.status = JobStatus.PROCESSING
    job.progress = 1
    job.current_stage = "queued"
    # Commit NOW so the job row is visible in Postgres before Celery workers
    # try to look it up. Without this commit, workers that start immediately
    # (within the same transaction window) get a "Job not found" 404.
    await db.commit()

    # Enqueue Celery pipeline
    dispatch_pipeline(str(job.id), file_url)

    logger.info("upload_accepted", job_id=str(job.id), file=file.filename, size=len(file_bytes))
    return UploadResponse(job_id=job.id, status=JobStatus.PENDING, message="Processing started")
