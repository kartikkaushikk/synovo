from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.postgres import get_db
from app.models.job import Job
from app.models.transcript import Transcript, Speaker
from app.models.analytics import Analytics, Contradiction
from app.services.job_service import get_job
from app.schemas.upload import (
    JobStatusResponse, TranscriptResponse, TranscriptChunk, SpeakerResponse
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """List recent processing jobs for the dashboard."""
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()
    return [
        {
            "id": str(job.id),
            "status": job.status,
            "file_name": job.file_name,
            "file_size_bytes": (job.metadata_ or {}).get("file_size_bytes"),
            "duration_s": job.duration_s,
            "created_at": job.created_at,
            "updated_at": job.completed_at or job.created_at,
            "error_message": job.error_msg,
        }
        for job in jobs
    ]


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Poll job status and processing progress."""
    job = await get_job(db, job_id)
    return JobStatusResponse.model_validate(job)


@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Fetch full speaker-labeled transcript for a completed job."""
    await get_job(db, job_id)
    result = await db.execute(
        select(Transcript)
        .where(Transcript.job_id == job_id)
        .order_by(Transcript.chunk_index)
    )
    chunks = result.scalars().all()
    return TranscriptResponse(
        job_id=job_id,
        chunks=[TranscriptChunk.model_validate(c) for c in chunks],
        total_chunks=len(chunks),
    )


@router.get("/{job_id}/speakers", response_model=list[SpeakerResponse])
async def get_speakers(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Speaker-level analytics breakdown."""
    await get_job(db, job_id)
    result = await db.execute(
        select(Speaker).where(Speaker.job_id == job_id)
    )
    return [SpeakerResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/{job_id}/analytics")
async def get_analytics(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Full behavioral analytics: WPM timeline, pauses, filler words, topics."""
    await get_job(db, job_id)
    result = await db.execute(select(Analytics).where(Analytics.job_id == job_id))
    analytics = result.scalar_one_or_none()
    if not analytics or not analytics.metrics:
        return {"job_id": job_id, "message": "Analytics not yet computed"}
    return analytics.metrics



@router.get("/{job_id}/contradictions")
async def get_contradictions(
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Contradiction pairs detected across the conversation."""
    await get_job(db, job_id)
    result = await db.execute(
        select(Contradiction).where(Contradiction.job_id == job_id)
        .order_by(Contradiction.score.desc())
    )
    contradictions = result.scalars().all()
    return {
        "job_id": job_id,
        "total": len(contradictions),
        "contradictions": [
            {
                "id": str(c.id),
                "score": c.score,
                "label": c.label,
                "explanation": c.explanation,
                "chunk_a_id": str(c.chunk_a_id),
                "chunk_b_id": str(c.chunk_b_id),
            }
            for c in contradictions
        ],
    }
