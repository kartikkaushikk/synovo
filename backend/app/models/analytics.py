import uuid
from sqlalchemy import Float, Integer, Text, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.postgres import Base


class Analytics(Base):
    """
    Single JSONB `metrics` blob storing the full analytics summary dict
    produced by AnalyticsEngine.analyze(). Easier to evolve than many columns.
    """
    __tablename__ = "analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Full analytics payload from AnalyticsEngine — includes speakers, wpm_timeline,
    # pause_events, interruptions, filler_count, speaking_ratio, etc.
    metrics: Mapped[dict | None] = mapped_column(JSONB)

    job: Mapped["Job"] = relationship(back_populates="analytics")


class Contradiction(Base):
    __tablename__ = "contradictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    chunk_a_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("transcripts.id"))
    chunk_b_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("transcripts.id"))
    score: Mapped[float] = mapped_column(Float)
    label: Mapped[str | None] = mapped_column(String(32))   # contradiction | neutral | entailment
    explanation: Mapped[str | None] = mapped_column(Text)

    job: Mapped["Job"] = relationship(back_populates="contradictions")
