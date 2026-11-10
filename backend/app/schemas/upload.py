from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.job import JobStatus


class UploadResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: UUID = Field(alias="id")
    status: JobStatus
    progress: int
    current_stage: str | None
    file_name: str | None
    duration_s: float | None
    created_at: datetime
    completed_at: datetime | None
    error_msg: str | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class TranscriptChunk(BaseModel):
    id: UUID
    speaker_id: str | None
    text: str
    start_s: float
    end_s: float
    confidence: float | None
    chunk_index: int

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    job_id: UUID
    chunks: list[TranscriptChunk]
    total_chunks: int


class SpeakerResponse(BaseModel):
    id: UUID
    label: str
    total_s: float | None
    wpm: float | None
    filler_rate: float | None
    avg_pause_s: float | None
    turn_count: int

    model_config = {"from_attributes": True}
