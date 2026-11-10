"""
Semantic cache layer backed by Redis.

Strategy:
  - Key = SHA-256(job_id + normalized_query + top_k + speaker_filter)
  - Value = JSON-serialized search results
  - TTL = configurable (default 1 hour)

Usage:
    from ai.cache.semantic_cache import SemanticCache

    cache = SemanticCache()
    cached = await cache.get(job_id, query, top_k, speaker_filter)
    if cached is None:
        results = await do_search(...)
        await cache.set(job_id, query, top_k, speaker_filter, results)
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.db.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TTL = 3600   # 1 hour


class SemanticCache:
    def __init__(self, ttl: int = DEFAULT_TTL) -> None:
        self.ttl = ttl

    def _make_key(
        self,
        job_id: str,
        query: str,
        top_k: int,
        speaker_filter: str | None,
    ) -> str:
        raw = f"{job_id}|{query.strip().lower()}|{top_k}|{speaker_filter or ''}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
        return f"sem_cache:{digest}"

    async def get(
        self,
        job_id: str,
        query: str,
        top_k: int,
        speaker_filter: str | None,
    ) -> list[dict] | None:
        key = self._make_key(job_id, query, top_k, speaker_filter)
        try:
            redis = await get_redis()
            raw = await redis.get(key)
            if raw:
                logger.debug("cache_hit", key=key)
                return json.loads(raw)
        except Exception as exc:
            logger.warning("cache_get_error", error=str(exc))
        return None

    async def set(
        self,
        job_id: str,
        query: str,
        top_k: int,
        speaker_filter: str | None,
        results: list[dict],
    ) -> None:
        key = self._make_key(job_id, query, top_k, speaker_filter)
        try:
            redis = await get_redis()
            await redis.set(key, json.dumps(results), ex=self.ttl)
            logger.debug("cache_set", key=key, ttl=self.ttl)
        except Exception as exc:
            logger.warning("cache_set_error", error=str(exc))

    async def invalidate_job(self, job_id: str) -> int:
        """Delete all cache keys for a given job (best-effort scan)."""
        try:
            redis = await get_redis()
            # SCAN is non-blocking; pattern match on prefix
            cursor = b"0"
            deleted = 0
            while True:
                cursor, keys = await redis.scan(cursor, match="sem_cache:*", count=100)
                if keys:
                    await redis.delete(*keys)
                    deleted += len(keys)
                if cursor == b"0":
                    break
            logger.info("cache_invalidated", job_id=job_id, deleted=deleted)
            return deleted
        except Exception as exc:
            logger.warning("cache_invalidate_error", error=str(exc))
            return 0
