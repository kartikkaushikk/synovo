import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job import Job, JobStatus
from app.core.exceptions import JobNotFound
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_job(
    db: AsyncSession,
    file_url: str,
    file_name: str,
    file_type: str,
    user_id: str | None = None,
) -> Job:
    job = Job(
        id=uuid.uuid4(),
        user_id=user_id,
        file_url=file_url,
        file_name=file_name,
        file_type=file_type,
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    logger.info("job_created", job_id=str(job.id))
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job:
    result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise JobNotFound(job_id)
    return job


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: JobStatus,
    progress: int | None = None,
    stage: str | None = None,
    error_msg: str | None = None,
) -> None:
    job = await get_job(db, job_id)
    job.status = status
    if progress is not None:
        job.progress = progress
    if stage is not None:
        job.current_stage = stage
    if error_msg is not None:
        job.error_msg = error_msg
    if status in (JobStatus.COMPLETED, JobStatus.FAILED):
        job.completed_at = datetime.utcnow()
    logger.info("job_status_updated", job_id=job_id, status=status, progress=progress)
