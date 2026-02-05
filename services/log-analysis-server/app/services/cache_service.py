"""
Query Result Cache Service

In-memory cache with TTL and LRU eviction for query results.
"""
from datetime import datetime
from typing import Optional, Dict
import hashlib
import asyncio
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with metadata"""

    def __init__(self, result: dict, timestamp: float):
        self.result = result
        self.timestamp = timestamp
        self.access_count = 0

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry has expired based on TTL"""
        return (datetime.now().timestamp() - self.timestamp) > ttl_seconds


class QueryCache:
    """Query result cache with TTL and LRU eviction"""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        """
        Initialize cache

        Args:
            ttl_seconds: Time-to-live for cache entries (default: 5 minutes)
            max_size: Maximum number of entries to store (default: 100)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._last_log_timestamp: Optional[float] = None
        self._lock = asyncio.Lock()

    def get_cache_key(self, question: str, max_results: int = 100) -> str:
        """
        Generate deterministic cache key from question and parameters

        Args:
            question: User question
            max_results: Maximum results parameter

        Returns:
            SHA256 hash as cache key
        """
        content = f"{question}:{max_results}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def get(self, key: str) -> Optional[dict]:
        """
        Retrieve cached result if valid

        Args:
            key: Cache key

        Returns:
            Cached result dict or None if expired/not found
        """
        try:
            async with self._lock:
                if key in self._cache:
                    entry = self._cache[key]

                    # Check expiration
                    if entry.is_expired(self._ttl):
                        del self._cache[key]
                        return None

                    # Update access count for LRU
                    entry.access_count += 1
                    return entry.result

            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
            return None

    async def set(self, key: str, result: dict):
        """
        Store result in cache with current timestamp

        Args:
            key: Cache key
            result: Result dictionary to cache
        """
        try:
            async with self._lock:
                # Evict least recently used if cache is full
                if len(self._cache) >= self._max_size:
                    self._evict_lru()
                    logger.debug(f"Cache evicted LRU entry")

                self._cache[key] = CacheEntry(result, datetime.now().timestamp())
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")

    async def invalidate_all(self):
        """Invalidate entire cache (called when new logs are inserted)"""
        async with self._lock:
            self._cache.clear()
            self._last_log_timestamp = datetime.now().timestamp()

    def _evict_lru(self):
        """Evict least recently used entry based on access_count"""
        if not self._cache:
            return

        # Find entry with lowest access_count
        lru_key = min(self._cache.items(), key=lambda x: x[1].access_count)[0]
        del self._cache[lru_key]

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache metrics
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "last_invalidation": self._last_log_timestamp
        }


# Singleton instance
_cache_instance: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """
    Get global cache instance (singleton pattern)

    Returns:
        QueryCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = QueryCache(ttl_seconds=300, max_size=100)
    return _cache_instance
