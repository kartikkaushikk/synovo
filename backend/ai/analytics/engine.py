"""
Behavioral analytics engine.

Computes per-speaker and per-conversation metrics:
  - WPM (words-per-minute) timeline
  - Pause events (gaps > threshold between consecutive segments)
  - Filler word frequency (um, uh, like, you know, basically, right, so)
  - Speaking time balance per speaker
  - Average confidence score trend
  - Interruption detection (overlapping speaker segments)
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from sqlalchemy import select

from app.db.postgres import worker_session
from app.models.transcript import Transcript
from app.models.analytics import Analytics
from app.core.logging import get_logger

logger = get_logger(__name__)

FILLER_WORDS = frozenset([
    "um", "uh", "like", "you know", "basically", "right",
    "so", "actually", "literally", "honestly", "kind of", "sort of",
])
PAUSE_THRESHOLD_S = 1.5   # seconds — gap longer than this is a "pause"
WPM_WINDOW_S = 30.0       # rolling window for WPM calculation


@dataclass
class SpeakerStats:
    speaker_id: str
    total_words: int = 0
    speaking_time_s: float = 0.0
    filler_count: int = 0
    pause_count: int = 0
    avg_confidence: float = 0.0
    wpm_timeline: list[dict] = field(default_factory=list)   # [{t, wpm}]


def _count_words(text: str) -> int:
    return len(text.split())


def _count_fillers(text: str) -> int:
    text_lower = text.lower()
    count = 0
    for fw in FILLER_WORDS:
        count += len(re.findall(r"\b" + re.escape(fw) + r"\b", text_lower))
    return count


def _compute_wpm(words: int, duration_s: float) -> float:
    if duration_s <= 0:
        return 0.0
    return round((words / duration_s) * 60.0, 1)


class AnalyticsEngine:
    async def analyze(self, job_id: str) -> dict:
        """
        Main entry point. Reads transcript chunks, computes analytics,
        persists to analytics table, returns summary dict.
        """
        async with worker_session() as db:
            rows = (
                await db.execute(
                    select(Transcript)
                    .where(Transcript.job_id == uuid.UUID(job_id))
                    .order_by(Transcript.chunk_index)
                )
            ).scalars().all()

        if not rows:
            logger.warning("analytics_no_chunks", job_id=job_id)
            return {}

        speaker_chunks: dict[str, list[Transcript]] = defaultdict(list)
        for row in rows:
            speaker_id = row.speaker_id or "UNKNOWN"
            speaker_chunks[speaker_id].append(row)

        stats_list: list[SpeakerStats] = []
        pause_events: list[dict] = []

        for speaker_id, chunks in speaker_chunks.items():
            stats = SpeakerStats(speaker_id=speaker_id)
            confidences: list[float] = []

            prev_end: float | None = None
            window_words = 0
            window_start = chunks[0].start_s

            for chunk in chunks:
                word_count = _count_words(chunk.text)
                stats.total_words += word_count
                stats.speaking_time_s += chunk.end_s - chunk.start_s
                stats.filler_count += _count_fillers(chunk.text)
                confidences.append(chunk.confidence or 0.0)

                # Pause detection
                if prev_end is not None:
                    gap = chunk.start_s - prev_end
                    if gap > PAUSE_THRESHOLD_S:
                        stats.pause_count += 1
                        pause_events.append({
                            "speaker": speaker_id,
                            "start": prev_end,
                            "end": chunk.start_s,
                            "duration": round(gap, 2),
                        })

                # Rolling WPM
                window_words += word_count
                window_duration = chunk.end_s - window_start
                if window_duration >= WPM_WINDOW_S:
                    stats.wpm_timeline.append({
                        "t": round(chunk.end_s, 1),
                        "wpm": _compute_wpm(window_words, window_duration),
                    })
                    window_words = 0
                    window_start = chunk.end_s

                prev_end = chunk.end_s

            stats.avg_confidence = round(
                sum(confidences) / len(confidences) if confidences else 0.0, 3
            )
            stats_list.append(stats)

        # Interruption detection: find any two different-speaker overlapping segments
        all_sorted = sorted(rows, key=lambda r: r.start_s)
        interruptions: list[dict] = []
        for i in range(len(all_sorted) - 1):
            a, b = all_sorted[i], all_sorted[i + 1]
            if (a.speaker_id != b.speaker_id) and (b.start_s < a.end_s):
                interruptions.append({
                    "interrupter": b.speaker_id,
                    "interrupted": a.speaker_id,
                    "at": round(b.start_s, 2),
                })

        # Build summary
        total_speaking = sum(s.speaking_time_s for s in stats_list)
        summary = {
            "job_id": job_id,
            "total_duration_s": round(rows[-1].end_s, 2) if rows else 0,
            "total_words": sum(s.total_words for s in stats_list),
            "speakers": [
                {
                    "speaker_id": s.speaker_id,
                    "total_words": s.total_words,
                    "speaking_time_s": round(s.speaking_time_s, 2),
                    "speaking_ratio": round(
                        s.speaking_time_s / total_speaking if total_speaking else 0, 3
                    ),
                    "avg_wpm": _compute_wpm(s.total_words, s.speaking_time_s),
                    "filler_count": s.filler_count,
                    "filler_rate": round(
                        s.filler_count / s.total_words if s.total_words else 0, 4
                    ),
                    "pause_count": s.pause_count,
                    "avg_confidence": s.avg_confidence,
                    "wpm_timeline": s.wpm_timeline,
                }
                for s in stats_list
            ],
            "pause_events": pause_events,
            "interruptions": interruptions,
        }

        # Persist to DB
        async with worker_session() as db:
            existing = (
                await db.execute(
                    select(Analytics).where(Analytics.job_id == uuid.UUID(job_id))
                )
            ).scalar_one_or_none()

            if existing:
                existing.metrics = summary
            else:
                db.add(Analytics(
                    id=uuid.uuid4(),
                    job_id=uuid.UUID(job_id),
                    metrics=summary,
                ))
            await db.commit()

        logger.info("analytics_complete", job_id=job_id, speakers=len(stats_list))
        return summary
