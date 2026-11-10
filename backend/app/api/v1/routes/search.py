import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres import get_db
from app.db.qdrant import get_qdrant_client
from app.db.redis import get_redis
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.core.config import settings
from app.core.logging import get_logger
from qdrant_client.models import Filter, FieldCondition, MatchValue

router = APIRouter(prefix="/search", tags=["search"])
logger = get_logger(__name__)

# Lazy-load embedder to avoid import-time GPU init
_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedder


@router.post("", response_model=SearchResponse)
async def semantic_search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    Natural language semantic search over a job's transcript chunks.
    Results are ranked by cosine similarity. Responses are cached by query hash.
    """
    t0 = time.perf_counter()
    cache_key = f"search:{req.job_id}:{hash(req.query)}:{req.top_k}"
    cached = await redis.get(cache_key)
    if cached:
        import json
        data = json.loads(cached)
        data["cached"] = True
        data["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return SearchResponse(**data)

    embedder = get_embedder()
    q_vec = embedder.encode(req.query, normalize_embeddings=True).tolist()

    # Create a fresh client per request (binds to the current event loop).
    # Always close in finally to release the aiohttp connector; without this
    # the connector leaks accumulate and exhaust the OS socket pool.
    qdrant = get_qdrant_client()
    must_conditions = [FieldCondition(key="job_id", match=MatchValue(value=str(req.job_id)))]
    if req.speaker_filter:
        must_conditions.append(
            FieldCondition(key="speaker_id", match=MatchValue(value=req.speaker_filter))
        )

    try:
        results = await qdrant.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=q_vec,
            query_filter=Filter(must=must_conditions),
            limit=req.top_k,
            with_payload=True,
        )
    finally:
        await qdrant.close()

    search_results = [
        SearchResult(
            chunk_id=str(r.id),
            job_id=r.payload["job_id"],
            chunk_index=r.payload["chunk_index"],
            text=r.payload["text"],
            speaker_id=r.payload.get("speaker_id"),
            start_s=r.payload["start_s"],
            end_s=r.payload["end_s"],
            score=round(r.score, 4),
        )
        for r in results
    ]

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    response = SearchResponse(
        query=req.query,
        results=search_results,
        total=len(search_results),
        cached=False,
        latency_ms=latency_ms,
    )

    import json
    await redis.setex(cache_key, settings.CACHE_TTL_SECONDS, response.model_dump_json())
    logger.info("semantic_search", query=req.query[:60], hits=len(search_results), latency_ms=latency_ms)
    return response
