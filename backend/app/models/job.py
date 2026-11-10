import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.postgres import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.PENDING, index=True)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(512))
    file_type: Mapped[str | None] = mapped_column(String(16))  # audio | video
    duration_s: Mapped[float | None] = mapped_column(Float)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    current_stage: Mapped[str | None] = mapped_column(String(64))
    error_msg: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transcripts: Mapped[list["Transcript"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    speakers: Mapped[list["Speaker"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    analytics: Mapped["Analytics | None"] = relationship(back_populates="job", cascade="all, delete-orphan", uselist=False)
    contradictions: Mapped[list["Contradiction"]] = relationship(back_populates="job", cascade="all, delete-orphan")
