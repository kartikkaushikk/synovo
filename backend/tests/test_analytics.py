"""Unit tests for the behavioral analytics engine."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from ai.analytics.engine import (
    AnalyticsEngine,
    _count_words,
    _count_fillers,
    _compute_wpm,
    FILLER_WORDS,
)


def test_count_words():
    assert _count_words("hello world") == 2
    assert _count_words("") == 0
    assert _count_words("one two three four") == 4


def test_count_fillers():
    assert _count_fillers("um, like, you know, basically") >= 3
    assert _count_fillers("no filler words here at all") == 0
    assert _count_fillers("Actually um I was um thinking") == 3


def test_compute_wpm():
    assert _compute_wpm(150, 60.0) == 150.0
    assert _compute_wpm(0, 60.0) == 0.0
    assert _compute_wpm(100, 0) == 0.0


def test_filler_words_set():
    # Spot-check the filler word set
    for w in ["um", "uh", "like", "basically", "actually"]:
        assert w in FILLER_WORDS


@pytest.mark.asyncio
async def test_analytics_engine_no_chunks():
    """AnalyticsEngine.analyze should return {} when no transcript rows exist."""
    with patch("ai.analytics.engine.AsyncSessionLocal") as MockSession:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
        MockSession.return_value = mock_session

        engine = AnalyticsEngine()
        result = await engine.analyze("00000000-0000-0000-0000-000000000000")
        assert result == {}
