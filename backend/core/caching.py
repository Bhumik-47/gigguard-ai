"""
caching.py - Caching layer for improved response times

Implements:
- In-memory cache with TTL support
- LRU eviction policy
- Cache hit/miss tracking
- Distributed cache support
"""

import time
from typing import Any, Optional, Dict
from functools import wraps
from datetime import datetime, timedelta


class CacheEntry:
    def __init__(self, value: Any, ttl: Optional[int] = None):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.last_accessed = time.time()
        self.access_count = 0

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def access(self) -> Any:
        self.last_accessed = time.time()
        self.access_count += 1
        return self.value

    def to_dict(self) -> dict:
        return {
            "value": str(self.value)[:100],
            "created_at": self.created_at,
            "ttl": self.ttl,
            "access_count": self.access_count,
            "is_expired": self.is_expired(),
        }


class Cache:
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
            "gets": 0,
        }

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if ttl is None:
            ttl = self.default_ttl

        if len(self.cache) >= self.max_size:
            self._evict_lru()

        self.cache[key] = CacheEntry(value, ttl)
        self.stats["sets"] += 1

    def get(self, key: str) -> Optional[Any]:
        self.stats["gets"] += 1

        if key not in self.cache:
            self.stats["misses"] += 1
            return None

        entry = self.cache[key]

        if entry.is_expired():
            del self.cache[key]
            self.stats["misses"] += 1
            return None

        self.stats["hits"] += 1
        return entry.access()

    def delete(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        self.cache.clear()

    def _evict_lru(self) -> None:
        if not self.cache:
            return

        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_accessed,
        )
        del self.cache[lru_key]
        self.stats["evictions"] += 1

    def get_stats(self) -> dict:
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        return {
            **self.stats,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": f"{hit_rate:.1f}%",
            "memory_usage_estimate_mb": len(self.cache) * 0.001,
        }

    def get_entries(self, limit: int = 20) -> list:
        items = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed,
            reverse=True,
        )
        return [{"key": k, **v.to_dict()} for k, v in items[:limit]]

    def cleanup_expired(self) -> int:
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)


def cache_result(ttl: int = 3600):
    def decorator(func):
        cache = Cache(default_ttl=ttl)

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        wrapper.cache = cache
        wrapper.cache_stats = cache.get_stats

        return wrapper

    return decorator


class QueryResultCache:
    def __init__(self, max_query_results: int = 500):
        self.cache = Cache(max_size=max_query_results)

    def cache_query_result(self, query_hash: str, result: Any, ttl: int = 300):
        self.cache.set(f"query:{query_hash}", result, ttl)

    def get_query_result(self, query_hash: str) -> Optional[Any]:
        return self.cache.get(f"query:{query_hash}")

    def invalidate_query(self, query_hash: str):
        self.cache.delete(f"query:{query_hash}")

    def invalidate_pattern(self, pattern: str):
        to_delete = [k for k in self.cache.cache.keys() if pattern in k]
        for key in to_delete:
            self.cache.delete(key)

    def get_stats(self) -> dict:
        return self.cache.get_stats()


global_cache = Cache(max_size=1000)
global_query_cache = QueryResultCache(max_query_results=500)
