"""Initial schema — jobs, transcripts, speakers, analytics, contradictions.

Revision ID: 0001
Revises:
Create Date: 2026-05-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="jobstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # transcripts
    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("speaker_id", sa.String(64), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_s", sa.Float(), nullable=False),
        sa.Column("end_s", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("words", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_transcripts_job_id", "transcripts", ["job_id"])
    op.create_index("ix_transcripts_speaker_id", "transcripts", ["speaker_id"])

    # speakers
    op.create_table(
        "speakers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("speaking_time_s", sa.Float(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
    )
    op.create_index("ix_speakers_job_id", "speakers", ["job_id"])

    # analytics
    op.create_table(
        "analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
    )

    # contradictions
    op.create_table(
        "contradictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_a_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcripts.id"), nullable=False),
        sa.Column("chunk_b_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcripts.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
    )
    op.create_index("ix_contradictions_job_id", "contradictions", ["job_id"])


def downgrade() -> None:
    op.drop_table("contradictions")
    op.drop_table("analytics")
    op.drop_table("speakers")
    op.drop_table("transcripts")
    op.drop_table("jobs")
    op.execute("DROP TYPE IF EXISTS jobstatus")
