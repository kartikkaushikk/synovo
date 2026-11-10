import uuid
from sqlalchemy import String, Float, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.postgres import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    speaker_id: Mapped[str | None] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_s: Mapped[float] = mapped_column(Float, nullable=False)
    end_s: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)   # BERTopic cluster id
    words: Mapped[list | None] = mapped_column(JSONB, nullable=True)       # word-level timestamps

    job: Mapped["Job"] = relationship(back_populates="transcripts")


class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(32))        # SPEAKER_00, etc.
    total_s: Mapped[float | None] = mapped_column(Float)
    wpm: Mapped[float | None] = mapped_column(Float)
    filler_rate: Mapped[float | None] = mapped_column(Float)
    avg_pause_s: Mapped[float | None] = mapped_column(Float)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped["Job"] = relationship(back_populates="speakers")
