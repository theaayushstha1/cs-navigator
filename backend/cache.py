# -*- coding: utf-8 -*-
"""
Cache Module for CS Navigator Chatbot
=====================================
Provides caching for frequent queries to reduce AI response times.

Currently uses in-memory LRU cache. Can be swapped to Redis by changing
the CacheBackend implementation.
"""

import hashlib
import time
from typing import Optional, Any
from cachetools import TTLCache
from threading import Lock

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Maximum number of cached responses
CACHE_MAX_SIZE = 1000

# Time-to-live for cached responses (in seconds)
# 1 hour = 3600, 6 hours = 21600, 24 hours = 86400
CACHE_TTL_SECONDS = 86400  # 24 hours

# Minimum query length to cache (avoid caching "hi", "hello", etc.)
MIN_QUERY_LENGTH = 15

# Queries containing these words should NOT be cached (personalized responses)
NO_CACHE_KEYWORDS = [
    "my advisor",
    "my gpa",
    "my credits",
    "my courses",
    "my schedule",
    "my degree",
    "my name",
    "my student",
    "i have",
    "i need",
    "i am",
    "i'm",
    "recommend me",
    "for me",
]

# ============================================================================
# CACHE IMPLEMENTATION
# ============================================================================

class QueryCache:
    """
    LRU Cache with TTL for chatbot query responses.

    Features:
    - Thread-safe operations
    - Automatic expiration (TTL)
    - Query normalization for better hit rates
    - Skips personalized queries
    - Cache statistics tracking
    """

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: int = CACHE_TTL_SECONDS):
        self._cache = TTLCache(maxsize=max_size, ttl=ttl)
        self._lock = Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "skipped": 0,  # Queries that shouldn't be cached
        }

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for better cache hit rates.
        - Lowercase
        - Strip whitespace
        - Remove extra spaces
        """
        return " ".join(query.lower().strip().split())

    def _generate_key(self, query: str, context_hash: str = "") -> str:
        """
        Generate a cache key from query and optional context.
        Uses MD5 hash for compact, consistent keys.
        """
        normalized = self._normalize_query(query)
        key_source = f"{normalized}:{context_hash}"
        return hashlib.md5(key_source.encode()).hexdigest()

    def _should_cache(self, query: str) -> bool:
        """
        Determine if a query should be cached.
        Returns False for personalized or too-short queries.
        """
        if len(query) < MIN_QUERY_LENGTH:
            return False

        query_lower = query.lower()
        for keyword in NO_CACHE_KEYWORDS:
            if keyword in query_lower:
                return False

        return True

    def get(self, query: str, context_hash: str = "") -> Optional[str]:
        """
        Get cached response for a query.

        Args:
            query: The user's question
            context_hash: Hash of user context (to differentiate users)

        Returns:
            Cached response string, or None if not found
        """
        if not self._should_cache(query):
            self._stats["skipped"] += 1
            return None

        key = self._generate_key(query, context_hash)

        with self._lock:
            response = self._cache.get(key)
            if response is not None:
                self._stats["hits"] += 1
                return response
            else:
                self._stats["misses"] += 1
                return None

    def set(self, query: str, response: str, context_hash: str = "") -> bool:
        """
        Cache a response for a query.

        Args:
            query: The user's question
            response: The AI response to cache
            context_hash: Hash of user context

        Returns:
            True if cached, False if skipped
        """
        if not self._should_cache(query):
            return False

        # Don't cache error responses
        if "error" in response.lower()[:50] or "unavailable" in response.lower()[:50]:
            return False

        key = self._generate_key(query, context_hash)

        with self._lock:
            self._cache[key] = response
            return True

    def invalidate(self, query: str, context_hash: str = "") -> bool:
        """Remove a specific query from cache."""
        key = self._generate_key(query, context_hash)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """Clear all cached entries. Returns count of cleared items."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "skipped": self._stats["skipped"],
                "hit_rate": f"{hit_rate:.1f}%",
                "cached_items": len(self._cache),
                "max_size": self._cache.maxsize,
                "ttl_seconds": self._cache.ttl,
            }

    def get_size(self) -> int:
        """Get current number of cached items."""
        with self._lock:
            return len(self._cache)


# ============================================================================
# GLOBAL CACHE INSTANCE
# ============================================================================

# Single global cache instance for the application
query_cache = QueryCache()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_context_hash(user_id: int = None, has_degreeworks: bool = False) -> str:
    """
    Generate a context hash for cache key differentiation.

    For general queries (no personalization needed), returns empty string
    to maximize cache hits across users.

    For users with DegreeWorks data, includes user_id to prevent
    cross-user cache pollution.
    """
    if has_degreeworks and user_id:
        return hashlib.md5(f"user:{user_id}".encode()).hexdigest()[:8]
    return ""  # General queries share cache


def log_cache_stats():
    """Print cache statistics to console."""
    stats = query_cache.get_stats()
    print(f"[CACHE] Stats: {stats['hits']} hits, {stats['misses']} misses, "
          f"{stats['hit_rate']} hit rate, {stats['cached_items']}/{stats['max_size']} items")
