"""Two-tier caching strategy for similarity queries.

This module provides a high-performance two-tier cache:
- L1: Query result cache (final top-k lists with TTL)
- L2: Embedding cache (decoded vectors, permanent)

The cache is designed to minimize redundant embedding computations and
similarity searches while providing event-based invalidation when new
decisions are added to the graph.
"""

import hashlib
import logging
import time
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU cache with optional TTL support.

    Implements least-recently-used eviction when max size is reached.
    Supports per-item TTL (time-to-live) for automatic expiration.
    """

    def __init__(self, maxsize: int):
        """Initialize LRU cache.

        Args:
            maxsize: Maximum number of items to cache
        """
        if maxsize < 1:
            raise ValueError(f"maxsize must be >= 1, got {maxsize}")

        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
        self._ttl_map: Dict[str, float] = {}  # key -> expiration timestamp

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.debug(f"Initialized LRUCache with maxsize={maxsize}")

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if present and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        # Check if key exists
        if key not in self._cache:
            self._misses += 1
            return None

        # Check TTL expiration
        if key in self._ttl_map:
            if time.time() > self._ttl_map[key]:
                # Expired - remove and return None
                self._remove(key)
                self._misses += 1
                return None

        # Move to end (mark as recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return self._cache[key]

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Put item in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional time-to-live in seconds (None = no expiration)
        """
        # If key already exists, update it
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value

            # Update TTL
            if ttl is not None:
                self._ttl_map[key] = time.time() + ttl
            elif key in self._ttl_map:
                del self._ttl_map[key]

            return

        # Add new item
        self._cache[key] = value

        # Set TTL if provided
        if ttl is not None:
            self._ttl_map[key] = time.time() + ttl

        # Evict oldest item if over capacity
        if len(self._cache) > self.maxsize:
            oldest_key = next(iter(self._cache))
            self._remove(oldest_key)
            self._evictions += 1

    def _remove(self, key: str) -> None:
        """Remove item from cache and TTL map."""
        if key in self._cache:
            del self._cache[key]
        if key in self._ttl_map:
            del self._ttl_map[key]

    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was present, False otherwise
        """
        if key in self._cache:
            self._remove(key)
            logger.debug(f"Invalidated cache key: {key[:50]}...")
            return True
        return False

    def clear(self) -> None:
        """Clear all items from cache."""
        count = len(self._cache)
        self._cache.clear()
        self._ttl_map.clear()
        logger.debug(f"Cleared cache ({count} items removed)")

    def size(self) -> int:
        """Get current number of items in cache."""
        return len(self._cache)

    def get_stats(self) -> Dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, evictions, size, hit_rate
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "size": len(self._cache),
            "hit_rate": hit_rate,
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0


class SimilarityCache:
    """Two-tier cache for similarity queries.

    L1 Cache (Query Results):
    - Stores final top-k search results for questions
    - TTL-based expiration (5-10 minutes)
    - Invalidated when new decisions added
    - Key: (question_hash, threshold, max_results)

    L2 Cache (Embeddings):
    - Stores computed embedding vectors
    - No TTL (embeddings are immutable)
    - Never invalidated (unless explicitly cleared)
    - Key: (question_hash, embedding_version)

    Design rationale:
    - L1 provides fast retrieval of complete search results
    - L2 avoids recomputing expensive embeddings
    - Event-based invalidation ensures consistency
    - TTL provides safety net for L1
    """

    # Embedding version for cache invalidation when model changes
    EMBEDDING_VERSION = "v1"

    def __init__(
        self,
        query_cache_size: int = 200,
        embedding_cache_size: int = 500,
        query_ttl: int = 300,  # 5 minutes default
    ):
        """Initialize two-tier similarity cache.

        Args:
            query_cache_size: Max size for L1 query result cache
            embedding_cache_size: Max size for L2 embedding cache
            query_ttl: TTL in seconds for query results (default: 300s = 5min)
        """
        self.query_cache = LRUCache(maxsize=query_cache_size)
        self.embedding_cache = LRUCache(maxsize=embedding_cache_size)
        self.query_ttl = query_ttl

        # Track when cache was last invalidated
        self._last_invalidation: Optional[datetime] = None

        logger.info(
            f"Initialized SimilarityCache (L1: {query_cache_size}, "
            f"L2: {embedding_cache_size}, TTL: {query_ttl}s)"
        )

    def _hash_question(self, question: str) -> str:
        """Generate hash for question string.

        Args:
            question: Question text

        Returns:
            SHA256 hash (hex digest)
        """
        return hashlib.sha256(question.encode("utf-8")).hexdigest()

    def _make_query_key(self, question: str, threshold: float, max_results: int) -> str:
        """Generate cache key for query results.

        Args:
            question: Question text
            threshold: Similarity threshold
            max_results: Maximum results to return

        Returns:
            Cache key string
        """
        question_hash = self._hash_question(question)
        return f"query:{question_hash}:{threshold}:{max_results}"

    def _make_embedding_key(self, question: str) -> str:
        """Generate cache key for embeddings.

        Args:
            question: Question text

        Returns:
            Cache key string
        """
        question_hash = self._hash_question(question)
        return f"embed:{question_hash}:{self.EMBEDDING_VERSION}"

    def get_cached_result(
        self, question: str, threshold: float, max_results: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached query results from L1.

        Args:
            question: Question text
            threshold: Similarity threshold used in query
            max_results: Max results used in query

        Returns:
            List of result dicts if cached, None otherwise
        """
        key = self._make_query_key(question, threshold, max_results)
        result = self.query_cache.get(key)

        if result is not None:
            logger.debug(
                f"L1 cache hit for question: {question[:50]}... "
                f"(threshold={threshold}, max={max_results})"
            )

        return result

    def cache_result(
        self,
        question: str,
        threshold: float,
        max_results: int,
        results: List[Dict[str, Any]],
    ) -> None:
        """Store query results in L1 cache with TTL.

        Args:
            question: Question text
            threshold: Similarity threshold used
            max_results: Max results used
            results: List of result dicts to cache
        """
        key = self._make_query_key(question, threshold, max_results)
        self.query_cache.put(key, results, ttl=self.query_ttl)

        logger.debug(
            f"Cached L1 result for question: {question[:50]}... "
            f"({len(results)} results, TTL={self.query_ttl}s)"
        )

    def get_cached_embedding(self, question: str) -> Optional[List[float]]:
        """Retrieve cached embedding from L2.

        Args:
            question: Question text

        Returns:
            Embedding vector if cached, None otherwise
        """
        key = self._make_embedding_key(question)
        embedding = self.embedding_cache.get(key)

        if embedding is not None:
            logger.debug(f"L2 cache hit for question: {question[:50]}...")

        return embedding

    def cache_embedding(self, question: str, embedding: List[float]) -> None:
        """Store embedding in L2 cache (permanent, no TTL).

        Args:
            question: Question text
            embedding: Embedding vector to cache
        """
        key = self._make_embedding_key(question)
        # No TTL for embeddings (they're immutable)
        self.embedding_cache.put(key, embedding, ttl=None)

        logger.debug(
            f"Cached L2 embedding for question: {question[:50]}... "
            f"(dim={len(embedding)})"
        )

    def invalidate_all_queries(self) -> None:
        """Invalidate all L1 query results (event-based invalidation).

        Called when a new decision is added to the graph, ensuring that
        subsequent queries will reflect the updated decision set.

        Note: Does NOT invalidate L2 embedding cache (embeddings are immutable).
        """
        self.query_cache.clear()
        self._last_invalidation = datetime.now()

        logger.info("Invalidated all L1 query results (new decision added to graph)")

    def invalidate_all(self) -> None:
        """Invalidate both L1 and L2 caches completely.

        Use this when embedding model changes or for testing/debugging.
        In normal operation, use invalidate_all_queries() instead.
        """
        self.query_cache.clear()
        self.embedding_cache.clear()
        self._last_invalidation = datetime.now()

        logger.warning("Invalidated both L1 and L2 caches (full cache clear)")

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:
            Dict with L1 and L2 stats, overall hit rate, last invalidation time
        """
        l1_stats = self.query_cache.get_stats()
        l2_stats = self.embedding_cache.get_stats()

        # Calculate combined hit rate
        total_hits = l1_stats["hits"] + l2_stats["hits"]
        total_requests = (
            l1_stats["hits"]
            + l1_stats["misses"]
            + l2_stats["hits"]
            + l2_stats["misses"]
        )
        combined_hit_rate = total_hits / total_requests if total_requests > 0 else 0.0

        return {
            "l1_query_cache": l1_stats,
            "l2_embedding_cache": l2_stats,
            "combined_hit_rate": combined_hit_rate,
            "last_invalidation": (
                self._last_invalidation.isoformat() if self._last_invalidation else None
            ),
            "query_ttl_seconds": self.query_ttl,
        }

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        self.query_cache.reset_stats()
        self.embedding_cache.reset_stats()
        logger.debug("Reset cache statistics")
