"""Tests for the semantic cache layer."""
import pytest
import json
from unittest.mock import AsyncMock, patch

from ai.cache.semantic_cache import SemanticCache


@pytest.mark.asyncio
@patch("ai.cache.semantic_cache.get_redis")
async def test_cache_miss(mock_get_redis):
    """Cache get returns None when no entry exists."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_get_redis.return_value = mock_redis

    cache = SemanticCache()
    result = await cache.get("job-1", "hello query", 5, None)
    assert result is None


@pytest.mark.asyncio
@patch("ai.cache.semantic_cache.get_redis")
async def test_cache_hit(mock_get_redis):
    """Cache get returns deserialized results when entry exists."""
    mock_redis = AsyncMock()
    stored = [{"chunk_id": "abc", "text": "hello", "score": 0.95}]
    mock_redis.get.return_value = json.dumps(stored).encode()
    mock_get_redis.return_value = mock_redis

    cache = SemanticCache()
    result = await cache.get("job-1", "hello query", 5, None)
    assert result == stored


@pytest.mark.asyncio
async def test_cache_key_determinism():
    """Same inputs always produce same key."""
    cache = SemanticCache()
    k1 = cache._make_key("job-1", "  Hello Query  ", 5, None)
    k2 = cache._make_key("job-1", "hello query", 5, None)
    assert k1 == k2   # query normalization (strip + lower)


@pytest.mark.asyncio
async def test_cache_key_speaker_sensitivity():
    """Keys differ when speaker_filter differs."""
    cache = SemanticCache()
    k1 = cache._make_key("job-1", "query", 5, None)
    k2 = cache._make_key("job-1", "query", 5, "SPEAKER_00")
    assert k1 != k2
