"""
test_caching.py - Tests for caching functionality
"""

import pytest
from backend.core.caching import Cache, CacheEntry, QueryResultCache


@pytest.mark.unit
@pytest.mark.cache
class TestCacheEntry:
    def test_cache_entry_creation(self):
        entry = CacheEntry("test_value", ttl=100)
        assert entry.value == "test_value"
        assert entry.ttl == 100
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        entry = CacheEntry("test_value", ttl=1)
        import time
        time.sleep(1.1)
        assert entry.is_expired()

    def test_cache_entry_access_tracking(self):
        entry = CacheEntry("test_value")
        val = entry.access()
        assert val == "test_value"
        assert entry.access_count == 1


@pytest.mark.unit
@pytest.mark.cache
class TestCache:
    def test_cache_set_and_get(self, clean_cache):
        clean_cache.set("key1", "value1")
        result = clean_cache.get("key1")

        assert result == "value1"

    def test_cache_miss(self, clean_cache):
        result = clean_cache.get("nonexistent")
        assert result is None

    def test_cache_hit_rate(self, clean_cache):
        clean_cache.set("key1", "value1")
        clean_cache.get("key1")
        clean_cache.get("key1")
        clean_cache.get("nonexistent")

        stats = clean_cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_cache_lru_eviction(self):
        cache = Cache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")

        assert len(cache.cache) == 3
        assert cache.get("key1") is None

    def test_cache_delete(self, clean_cache):
        clean_cache.set("key1", "value1")
        result = clean_cache.delete("key1")

        assert result is True
        assert clean_cache.get("key1") is None

    def test_cache_clear(self, clean_cache):
        clean_cache.set("key1", "value1")
        clean_cache.set("key2", "value2")
        clean_cache.clear()

        assert len(clean_cache.cache) == 0

    def test_get_stats(self, clean_cache):
        clean_cache.set("key1", "value1")
        clean_cache.get("key1")
        clean_cache.get("nonexistent")

        stats = clean_cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats


@pytest.mark.unit
@pytest.mark.cache
class TestQueryResultCache:
    def test_cache_query_result(self):
        cache = QueryResultCache()
        cache.cache_query_result("query_hash_1", {"result": "data"}, ttl=300)

        result = cache.get_query_result("query_hash_1")
        assert result == {"result": "data"}

    def test_invalidate_query(self):
        cache = QueryResultCache()
        cache.cache_query_result("query_hash_1", {"result": "data"})
        cache.invalidate_query("query_hash_1")

        result = cache.get_query_result("query_hash_1")
        assert result is None

    def test_invalidate_pattern(self):
        cache = QueryResultCache()
        cache.cache_query_result("query:users", {"data": "users"})
        cache.cache_query_result("query:posts", {"data": "posts"})
        cache.invalidate_pattern("users")

        assert cache.get_query_result("query:users") is None
        assert cache.get_query_result("query:posts") is not None

    def test_cache_stats(self):
        cache = QueryResultCache()
        cache.cache_query_result("query_1", {"result": 1})
        cache.get_query_result("query_1")

        stats = cache.get_stats()
        assert "hits" in stats or "cache_size" in stats
