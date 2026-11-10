"""
Merges Faster-Whisper word-level segments with diarization output.
Uses interval overlap to assign speaker labels to each Whisper segment.
Falls back to silence-based chunk labeling when diarization is unavailable.
"""
from __future__ import annotations
import uuid
import asyncio
from app.db.postgres import worker_session
from app.models import analytics as _analytics  # noqa: F401
from app.models.transcript import Transcript
from app.core.logging import get_logger

logger = get_logger(__name__)


def _find_speaker(start: float, end: float, diarization: list[dict]) -> str | None:
    """
    Assign speaker by maximum overlap between a whisper segment and
    diarization intervals. O(n) scan — acceptable for typical conversation lengths.
    For very long recordings, upgrade to interval tree (sortedcontainers).
    """
    best_speaker = None
    best_overlap = 0.0

    for seg in diarization:
        overlap_start = max(start, seg["start"])
        overlap_end = min(end, seg["end"])
        overlap = max(0.0, overlap_end - overlap_start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = seg["speaker"]

    return best_speaker


def _fallback_speakers(whisper_segments: list[dict], gap_s: float = 1.5) -> list[str]:
    """
    Assign alternating speaker labels using silence gaps between segments.
    This is a lightweight VAD-style fallback when diarization is skipped.
    """
    labels: list[str] = []
    speaker_idx = 0
    last_end: float | None = None

    for seg in whisper_segments:
        if last_end is not None:
            gap = max(0.0, seg["start"] - last_end)
            if gap >= gap_s:
                speaker_idx = (speaker_idx + 1) % 2
        labels.append(f"SPEAKER_{speaker_idx:02d}")
        last_end = seg["end"]

    return labels


def merge_transcript_diarization(
    job_id: str,
    whisper_segments: list[dict],
    diarization_segments: list[dict],
) -> None:
    """
    Synchronously merge and persist speaker-labeled transcript chunks.
    Called from a Celery chord callback (sync context).
    """
    asyncio.run(_persist_merged(job_id, whisper_segments, diarization_segments))


async def _persist_merged(
    job_id: str,
    whisper_segments: list[dict],
    diarization_segments: list[dict],
) -> None:
    async with worker_session() as db:
        fallback_labels = None
        if not diarization_segments:
            fallback_labels = _fallback_speakers(whisper_segments)
            logger.info("diarization_fallback_used", job_id=job_id, segments=len(fallback_labels))

        chunks = []
        for idx, seg in enumerate(whisper_segments):
            speaker = None
            if diarization_segments:
                speaker = _find_speaker(seg["start"], seg["end"], diarization_segments)
            if speaker is None and fallback_labels is not None:
                speaker = fallback_labels[idx]
            confidence = 1.0 + seg.get("avg_logprob", -1.0)  # logprob → rough 0-1 confidence
            confidence = max(0.0, min(1.0, confidence))

            chunk = Transcript(
                id=uuid.uuid4(),
                job_id=uuid.UUID(job_id),
                speaker_id=speaker,
                text=seg["text"],
                start_s=seg["start"],
                end_s=seg["end"],
                confidence=round(confidence, 3),
                chunk_index=idx,
            )
            chunks.append(chunk)

        db.add_all(chunks)
        await db.commit()
        logger.info("transcript_merged", job_id=job_id, chunks=len(chunks))
