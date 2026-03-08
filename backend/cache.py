# -*- coding: utf-8 -*-
"""
Multi-Tier Cache Module for CS Navigator Chatbot
=================================================
Provides L1 (in-memory) + L2 (Redis) caching for optimal performance.

Architecture:
    Request → L1 (In-Memory) → L2 (Redis) → AI
               ~0.001ms         ~1-2ms       ~10sec

L1: Fast, local to each server instance (cachetools TTLCache)
L2: Shared across servers, persistent (Redis Cloud)
"""

import hashlib
import json
import os
import logging
from typing import Optional
from cachetools import TTLCache
from threading import Lock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# L1 (In-Memory) Settings
L1_CACHE_MAX_SIZE = 500  # Smaller since Redis is L2
L1_CACHE_TTL_SECONDS = 3600  # 1 hour for L1 (hot cache)

# L2 (Redis) Settings
L2_CACHE_TTL_SECONDS = 86400  # 24 hours for Redis

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

# Redis Configuration (from environment variables)
REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_HOST = os.getenv("REDIS_HOST", "redis-10159.c8.us-east-1-3.ec2.cloud.redislabs.com")
REDIS_PORT = int(os.getenv("REDIS_PORT", "10159"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "eABZepeDtaNLP4vNd0KQUTC2rBNcMEzH")
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")

# ============================================================================
# L1 CACHE (IN-MEMORY)
# ============================================================================

class L1Cache:
    """
    Level 1 Cache: In-memory LRU + TTL cache.
    Fastest access, local to each server instance.
    """

    def __init__(self, max_size: int = L1_CACHE_MAX_SIZE, ttl: int = L1_CACHE_TTL_SECONDS):
        self._cache = TTLCache(maxsize=max_size, ttl=ttl)
        self._lock = Lock()
        self._stats = {"hits": 0, "misses": 0}

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            value = self._cache.get(key)
            if value is not None:
                self._stats["hits"] += 1
                return value
            self._stats["misses"] += 1
            return None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._cache[key] = value

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0}
            return count

    def get_stats(self) -> dict:
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": f"{hit_rate:.1f}%",
                "size": len(self._cache),
                "max_size": self._cache.maxsize,
            }


# ============================================================================
# L2 CACHE (REDIS)
# ============================================================================

class L2Cache:
    """
    Level 2 Cache: Redis distributed cache.
    Shared across all server instances, persistent.
    """

    def __init__(self, ttl: int = L2_CACHE_TTL_SECONDS):
        self.ttl = ttl
        self._client = None
        self._connected = False
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
        self._connect()

    def _connect(self):
        """Initialize Redis connection."""
        try:
            import redis

            if REDIS_URL:
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
            else:
                self._client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    password=REDIS_PASSWORD,
                    username=REDIS_USERNAME,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                )

            # Test connection
            self._client.ping()
            self._connected = True
            logger.info(f"[REDIS] Connected to {REDIS_HOST}:{REDIS_PORT}")

        except Exception as e:
            self._connected = False
            logger.warning(f"[REDIS] Connection failed: {e}. Running without L2 cache.")

    def is_connected(self) -> bool:
        return self._connected

    def get(self, key: str) -> Optional[str]:
        if not self._connected:
            return None

        try:
            value = self._client.get(f"csnavigator:{key}")
            if value is not None:
                self._stats["hits"] += 1
                return value
            self._stats["misses"] += 1
            return None
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"[REDIS] Get error: {e}")
            return None

    def set(self, key: str, value: str) -> bool:
        if not self._connected:
            return False

        try:
            self._client.setex(f"csnavigator:{key}", self.ttl, value)
            return True
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"[REDIS] Set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self._connected:
            return False

        try:
            return self._client.delete(f"csnavigator:{key}") > 0
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"[REDIS] Delete error: {e}")
            return False

    def clear(self) -> int:
        """Clear all csnavigator keys from Redis."""
        if not self._connected:
            return 0

        try:
            keys = self._client.keys("csnavigator:*")
            if keys:
                count = self._client.delete(*keys)
                self._stats = {"hits": 0, "misses": 0, "errors": 0}
                return count
            return 0
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"[REDIS] Clear error: {e}")
            return 0

    def get_stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        info = {"connected": self._connected}
        if self._connected:
            try:
                db_size = len(self._client.keys("csnavigator:*"))
                info["size"] = db_size
            except:
                info["size"] = "unknown"

        return {
            **info,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "hit_rate": f"{hit_rate:.1f}%",
        }


# ============================================================================
# MULTI-TIER CACHE (L1 + L2)
# ============================================================================

class MultiTierCache:
    """
    Multi-tier cache combining L1 (in-memory) and L2 (Redis).

    Flow:
    GET: L1 → L2 → Miss
    SET: L1 + L2 (write to both)

    Benefits:
    - L1 provides ultra-fast access for hot data
    - L2 provides persistence and cross-server sharing
    - Graceful degradation if Redis is down
    """

    def __init__(self):
        self.l1 = L1Cache()
        self.l2 = L2Cache()
        self._skipped = 0

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent cache keys."""
        return " ".join(query.lower().strip().split())

    def _generate_key(self, query: str, context_hash: str = "") -> str:
        """Generate cache key from query."""
        normalized = self._normalize_query(query)
        key_source = f"{normalized}:{context_hash}"
        return hashlib.md5(key_source.encode()).hexdigest()

    def _should_cache(self, query: str) -> bool:
        """Determine if query should be cached."""
        if len(query) < MIN_QUERY_LENGTH:
            return False

        query_lower = query.lower()
        for keyword in NO_CACHE_KEYWORDS:
            if keyword in query_lower:
                return False

        return True

    def get(self, query: str, context_hash: str = "") -> Optional[str]:
        """
        Get cached response using multi-tier lookup.

        Returns:
            Tuple of (response, cache_level) where cache_level is 'L1', 'L2', or None
        """
        if not self._should_cache(query):
            self._skipped += 1
            return None

        key = self._generate_key(query, context_hash)

        # Try L1 first (fastest)
        response = self.l1.get(key)
        if response is not None:
            logger.info(f"[CACHE] L1 HIT for: {query[:50]}...")
            return response

        # Try L2 (Redis)
        response = self.l2.get(key)
        if response is not None:
            logger.info(f"[CACHE] L2 HIT for: {query[:50]}...")
            # Promote to L1 for faster future access
            self.l1.set(key, response)
            return response

        logger.info(f"[CACHE] MISS for: {query[:50]}...")
        return None

    def set(self, query: str, response: str, context_hash: str = "") -> bool:
        """Store response in both cache tiers."""
        if not self._should_cache(query):
            return False

        # Don't cache error responses
        if "error" in response.lower()[:50] or "unavailable" in response.lower()[:50]:
            return False

        key = self._generate_key(query, context_hash)

        # Write to both tiers
        self.l1.set(key, response)
        self.l2.set(key, response)

        logger.info(f"[CACHE] Stored in L1+L2: {query[:50]}...")
        return True

    def invalidate(self, query: str, context_hash: str = "") -> bool:
        """Remove query from all cache tiers."""
        key = self._generate_key(query, context_hash)
        l1_deleted = self.l1.delete(key)
        l2_deleted = self.l2.delete(key)
        return l1_deleted or l2_deleted

    def clear(self) -> dict:
        """Clear all caches."""
        l1_count = self.l1.clear()
        l2_count = self.l2.clear()
        return {"l1_cleared": l1_count, "l2_cleared": l2_count}

    def get_stats(self) -> dict:
        """Get combined cache statistics."""
        l1_stats = self.l1.get_stats()
        l2_stats = self.l2.get_stats()

        total_hits = l1_stats["hits"] + l2_stats["hits"]
        total_misses = l1_stats["misses"]  # L1 misses = total misses
        total = total_hits + total_misses
        overall_hit_rate = (total_hits / total * 100) if total > 0 else 0

        return {
            "overall": {
                "total_hits": total_hits,
                "total_misses": total_misses,
                "hit_rate": f"{overall_hit_rate:.1f}%",
                "skipped": self._skipped,
            },
            "l1_inmemory": l1_stats,
            "l2_redis": l2_stats,
        }


# ============================================================================
# GLOBAL CACHE INSTANCE
# ============================================================================

# Single global multi-tier cache instance
query_cache = MultiTierCache()


# ============================================================================
# HELPER FUNCTIONS (Backwards Compatible)
# ============================================================================

def get_context_hash(user_id: int = None, has_degreeworks: bool = False) -> str:
    """
    Generate a context hash for cache key differentiation.
    """
    if has_degreeworks and user_id:
        return hashlib.md5(f"user:{user_id}".encode()).hexdigest()[:8]
    return ""


def log_cache_stats():
    """Print cache statistics to console."""
    stats = query_cache.get_stats()
    print(f"\n{'='*60}")
    print("CACHE STATISTICS")
    print(f"{'='*60}")
    print(f"Overall Hit Rate: {stats['overall']['hit_rate']}")
    print(f"Total Hits: {stats['overall']['total_hits']}")
    print(f"Total Misses: {stats['overall']['total_misses']}")
    print(f"Skipped (personalized): {stats['overall']['skipped']}")
    print(f"\nL1 (In-Memory): {stats['l1_inmemory']['size']}/{stats['l1_inmemory']['max_size']} items")
    print(f"L2 (Redis): Connected={stats['l2_redis']['connected']}, Items={stats['l2_redis'].get('size', 'N/A')}")
    print(f"{'='*60}\n")
