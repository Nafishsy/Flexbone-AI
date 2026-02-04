"""Caching service."""

import hashlib
import logging

from app.config import MAX_CACHE_SIZE

logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}


def get_cache_key(content: bytes) -> str:
    """Generate SHA-256 hash for cache key."""
    return hashlib.sha256(content).hexdigest()


def get_cached(key: str) -> dict | None:
    """Get cached result if exists."""
    if key in _cache:
        logger.info(f"Cache hit for {key[:8]}...")
        return _cache[key]
    logger.info(f"Cache miss for {key[:8]}...")
    return None


def set_cached(key: str, value: dict) -> None:
    """Store result in cache."""
    if len(_cache) >= MAX_CACHE_SIZE:
        oldest_key = next(iter(_cache))
        del _cache[oldest_key]
        logger.debug("Cache eviction performed")
    _cache[key] = value
