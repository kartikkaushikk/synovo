"""
Topic modeling engine using BERTopic.

Pipeline:
  1. Load transcript chunks for a job.
  2. Fit BERTopic on the chunk texts.
  3. Persist topic labels + representative terms back to DB.
  4. Return summary dict with topics, per-segment labels, and top terms.

BERTopic uses UMAP + HDBSCAN under the hood for clustering.
We use the sentence-transformers embedding model already loaded in
ai.embedding.encoder (passed as embedding_model to avoid double-loading).

Note: for < ~50 segments, BERTopic may return very few or 1 topic — this is normal.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update

from app.db.postgres import worker_session
from app.models.transcript import Transcript
from app.core.logging import get_logger

logger = get_logger(__name__)

MIN_DOCS_FOR_TOPICS = 10


async def extract_topics(job_id: str) -> dict:
    """
    Run BERTopic on a job's transcript chunks.
    Returns topic summary dict.
    """
    async with worker_session() as db:
        rows = (
            await db.execute(
                select(Transcript)
                .where(Transcript.job_id == uuid.UUID(job_id))
                .order_by(Transcript.chunk_index)
            )
        ).scalars().all()

    if len(rows) < MIN_DOCS_FOR_TOPICS:
        logger.warning(
            "topic_too_few_docs",
            job_id=job_id,
            count=len(rows),
            minimum=MIN_DOCS_FOR_TOPICS,
        )
        return {"job_id": job_id, "topics": [], "note": "Not enough segments for topic modeling"}

    texts = [row.text for row in rows]

    import asyncio
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _fit_bertopic, texts)

    # Write topic labels back to transcript rows
    async with worker_session() as db:
        for row, topic_id in zip(rows, result["doc_topics"]):
            await db.execute(
                update(Transcript)
                .where(Transcript.id == row.id)
                .values(topic_id=topic_id)
            )
        await db.commit()

    logger.info(
        "topic_modeling_done",
        job_id=job_id,
        num_topics=len(result["topics"]),
    )
    return {"job_id": job_id, **result}


def _fit_bertopic(texts: list[str]) -> dict:
    """Blocking BERTopic fit — runs in executor."""
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    from umap import UMAP
    from hdbscan import HDBSCAN

    embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    umap_model = UMAP(
        n_neighbors=min(15, len(texts) - 1),
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=max(2, len(texts) // 10),
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )

    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        top_n_words=8,
        verbose=False,
    )

    topics, _ = topic_model.fit_transform(texts)
    topic_info = topic_model.get_topic_info()

    result_topics = []
    for _, row in topic_info.iterrows():
        tid = int(row["Topic"])
        if tid == -1:
            continue   # skip outlier cluster
        terms = topic_model.get_topic(tid) or []
        result_topics.append({
            "topic_id": tid,
            "label": row.get("Name", f"Topic {tid}"),
            "count": int(row["Count"]),
            "top_terms": [{"term": t, "score": round(s, 4)} for t, s in terms[:8]],
        })

    return {
        "topics": result_topics,
        "doc_topics": [int(t) for t in topics],
    }
