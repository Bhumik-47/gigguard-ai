"""
cache_service.py
In-memory SHA-256 keyed cache for AI analysis results.

For MVP: uses a Python dict with a 24-hour TTL.
For production: replace the _store dict with Redis calls
(redis.set(key, value, ex=86400) / redis.get(key)).
"""

import hashlib
import json
import time
from typing import Optional, Any

# TTL in seconds (24 hours)
_DEFAULT_TTL = 86400

# In-memory store: { cache_key: {"data": Any, "expires_at": float} }
_store: dict = {}


def _make_key(*parts: str) -> str:
    """
    Hash an arbitrary list of string parts into a single SHA-256 cache key.
    Parts are joined with a pipe separator before hashing.
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_get(key: str) -> Optional[Any]:
    """
    Retrieve a cached value by key.
    Returns None on miss or if the entry has expired (lazy eviction).
    """
    entry = _store.get(key)
    if entry is None:
        return None
    if time.time() > entry["expires_at"]:
        del _store[key]   # lazy eviction
        return None
    return entry["data"]


def cache_set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    """
    Store a value under key with a TTL (seconds).
    Value must be JSON-serialisable.
    """
    _store[key] = {
        "data": value,
        "expires_at": time.time() + ttl,
    }


def cache_invalidate(key: str) -> None:
    """
    Explicitly remove a single cache entry.
    Call this when the contract or client message is updated.
    """
    _store.pop(key, None)


def make_analysis_key(contract_text: str, client_message: str, user_id: str) -> str:
    """
    Convenience function: build the canonical cache key for an AI analysis result.
    """
    return _make_key(contract_text, client_message, user_id)