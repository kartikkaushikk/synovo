"""
Contradiction detection engine.

Uses a zero-shot NLI (Natural Language Inference) model to detect contradictory
statement pairs within a conversation.

Strategy:
  1. Load all transcript chunks for a job.
  2. Group chunks by speaker.
  3. Compute all cross-speaker sentence pairs (within a configurable time window
     to limit quadratic blowup — nearby utterances are more likely to be topically
     related).
  4. Run the NLI model on each pair:
       - "entailment"   → claim B supports claim A
       - "neutral"      → unrelated
       - "contradiction"→ flag as contradiction
  5. Persist flagged pairs to the contradictions table.

Model: cross-encoder/nli-deberta-v3-small (fast, 256-dim)
Upgrade path: facebook/bart-large-mnli for higher accuracy.
"""
from __future__ import annotations

import itertools
import threading
import uuid
from dataclasses import dataclass
from typing import ClassVar

from sqlalchemy import select

from app.db.postgres import worker_session
from app.models.transcript import Transcript
from app.models.analytics import Contradiction
from app.core.logging import get_logger

logger = get_logger(__name__)

# Only compare segments within this time window (seconds) of each other
TIME_WINDOW_S = 300.0
CONTRADICTION_THRESHOLD = 0.65   # NLI contradiction score to flag
NLI_MODEL = "cross-encoder/nli-deberta-v3-small"
MAX_PAIRS = 500   # guard against O(n²) blowup on very long transcripts


class NLIEngine:
    """Thread-safe singleton for the NLI cross-encoder."""

    _instance: ClassVar["NLIEngine | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._model = None

    @classmethod
    def get(cls) -> "NLIEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        if self._model is not None:
            return
        from transformers import pipeline as hf_pipeline

        logger.info("nli_loading_model", model=NLI_MODEL)
        self._model = hf_pipeline(
            "text-classification",
            model=NLI_MODEL,
            top_k=None,
            device=-1,   # CPU; set device=0 for GPU
        )
        logger.info("nli_model_loaded")

    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[dict]:
        """
        Score a list of (premise, hypothesis) pairs.
        Returns list of {label, score} dicts in the same order.
        """
        self._load()
        formatted = [f"{p} [SEP] {h}" for p, h in pairs]
        results = self._model(formatted)

        output = []
        for result_labels in results:
            # result_labels is a list of {label, score}
            label_map = {r["label"].lower(): r["score"] for r in result_labels}
            output.append(label_map)
        return output


async def detect_contradictions(job_id: str) -> list[dict]:
    """
    Main entry — loads transcript, runs NLI, persists contradictions.
    Returns list of flagged contradiction dicts.
    """
    async with worker_session() as db:
        rows = (
            await db.execute(
                select(Transcript)
                .where(Transcript.job_id == uuid.UUID(job_id))
                .order_by(Transcript.start_s)
            )
        ).scalars().all()

    if len(rows) < 2:
        return []

    # Build candidate pairs: cross-speaker, within TIME_WINDOW_S
    candidates: list[tuple[Transcript, Transcript]] = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if b.start_s - a.end_s > TIME_WINDOW_S:
                break
            if a.speaker_id != b.speaker_id:
                candidates.append((a, b))
            if len(candidates) >= MAX_PAIRS:
                break
        if len(candidates) >= MAX_PAIRS:
            break

    if not candidates:
        return []

    pairs = [(c[0].text, c[1].text) for c in candidates]

    import asyncio
    engine = NLIEngine.get()
    # get_running_loop() is safe inside an async coroutine; get_event_loop()
    # can return the outer closed loop when called from asyncio.run() in a
    # Celery worker thread (Python 3.10+).
    loop = asyncio.get_running_loop()
    scores = await loop.run_in_executor(None, engine.score_pairs, pairs)

    contradictions: list[dict] = []
    async with worker_session() as db:
        for (chunk_a, chunk_b), score_map in zip(candidates, scores):
            contra_score = score_map.get("contradiction", 0.0)
            if contra_score >= CONTRADICTION_THRESHOLD:
                entry = {
                    "job_id": job_id,
                    "chunk_a_id": str(chunk_a.id),
                    "speaker_a": chunk_a.speaker_id,
                    "text_a": chunk_a.text,
                    "chunk_b_id": str(chunk_b.id),
                    "speaker_b": chunk_b.speaker_id,
                    "text_b": chunk_b.text,
                    "score": round(contra_score, 4),
                }
                contradictions.append(entry)
                db.add(Contradiction(
                    id=uuid.uuid4(),
                    job_id=uuid.UUID(job_id),
                    chunk_a_id=uuid.UUID(str(chunk_a.id)),
                    chunk_b_id=uuid.UUID(str(chunk_b.id)),
                    score=contra_score,
                    explanation=f"NLI contradiction score: {contra_score:.3f}",
                ))
        await db.commit()

    logger.info(
        "contradiction_detection_done",
        job_id=job_id,
        pairs_checked=len(candidates),
        contradictions_found=len(contradictions),
    )
    return contradictions
