"""
Sentence-Transformers embedding encoder + Qdrant ingestion.

Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, fast, good retrieval quality)
Override via EMBEDDING_MODEL env var for larger models (e.g. BAAI/bge-large-en-v1.5).
"""
from __future__ import annotations

import threading
import uuid
import asyncio
from typing import ClassVar

from app.core.config import settings
from app.core.logging import get_logger
from app.db.postgres import worker_session
from app.db.qdrant import get_qdrant_client

logger = get_logger(__name__)

COLLECTION_NAME = "transcript_chunks"
EMBEDDING_DIM = 384  # MiniLM-L6; update if swapping model


class EmbeddingEncoder:
    """Thread-safe singleton for sentence-transformers model."""

    _instance: ClassVar["EmbeddingEncoder | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._model = None

    @classmethod
    def get(cls) -> "EmbeddingEncoder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_model(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        model_name = getattr(settings, "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        logger.info("embedding_loading_model", model=model_name)
        self._model = SentenceTransformer(model_name)
        logger.info("embedding_model_loaded")

    def encode(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Encode a list of texts, return list of float vectors."""
        self._load_model()
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()


async def ingest_job_embeddings(job_id: str) -> int:
    """
    Fetch all transcript chunks for a job, embed them, and upsert into Qdrant.
    Returns number of vectors ingested.
    """
    from sqlalchemy import select
    from app.models.transcript import Transcript
    from qdrant_client.models import PointStruct

    async with worker_session() as db:
        rows = (await db.execute(
            select(Transcript).where(Transcript.job_id == uuid.UUID(job_id))
        )).scalars().all()

    if not rows:
        logger.warning("embedding_no_chunks", job_id=job_id)
        return 0

    texts = [r.text for r in rows]
    encoder = EmbeddingEncoder.get()

    # Run blocking encode in thread executor.
    # Use get_running_loop() — we are inside an async function launched via
    # asyncio.run(), so get_event_loop() can return the *outer* closed loop in
    # Python 3.10+ threads, causing "Future attached to a different loop".
    loop = asyncio.get_running_loop()
    vectors = await loop.run_in_executor(None, encoder.encode, texts)

    points = [
        PointStruct(
            id=str(row.id),
            vector=vec,
            payload={
                "job_id": str(row.job_id),
                "speaker_id": row.speaker_id,
                "text": row.text,
                "start_s": float(row.start_s),
                "end_s": float(row.end_s),
                "chunk_index": int(row.chunk_index),
            },
        )
        for row, vec in zip(rows, vectors)
    ]

    # Always create a fresh client per asyncio.run() invocation so it binds
    # to the current event loop.  Close it in finally to release aiohttp
    # connectors and avoid "Session is closed" warnings on the next call.
    qdrant = get_qdrant_client()
    try:
        # Batch upsert in chunks of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            await qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=points[i : i + batch_size],
            )
    finally:
        await qdrant.close()

    logger.info("embedding_ingested", job_id=job_id, count=len(points))
    return len(points)
