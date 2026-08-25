"""
Unit tests for cache_service.
No external dependencies — runs entirely in memory.
"""
import time
import pytest
from services.cache_service import (
    cache_get,
    cache_set,
    cache_invalidate,
    make_analysis_key,
    _store,
)


def setup_function():
    """Clear the cache before every test."""
    _store.clear()


def test_cache_miss_returns_none():
    result = cache_get("nonexistent_key")
    assert result is None


def test_cache_set_and_get():
    cache_set("test_key", {"score": 0.87}, ttl=60)
    result = cache_get("test_key")
    assert result == {"score": 0.87}


def test_cache_hit_after_set():
    key = make_analysis_key("contract text", "client msg", "user123")
    cache_set(key, {"analysis": "ok"})
    assert cache_get(key) == {"analysis": "ok"}


def test_cache_expires():
    cache_set("short_key", {"data": "temp"}, ttl=1)
    time.sleep(1.1)
    assert cache_get("short_key") is None


def test_cache_invalidate():
    cache_set("inv_key", {"data": "value"})
    cache_invalidate("inv_key")
    assert cache_get("inv_key") is None


def test_cache_invalidate_nonexistent_is_safe():
    # Should not raise
    cache_invalidate("key_that_never_existed")


def test_make_analysis_key_is_deterministic():
    key1 = make_analysis_key("contract", "message", "user1")
    key2 = make_analysis_key("contract", "message", "user1")
    assert key1 == key2


def test_make_analysis_key_differs_on_input_change():
    key1 = make_analysis_key("contract A", "message", "user1")
    key2 = make_analysis_key("contract B", "message", "user1")
    assert key1 != key2