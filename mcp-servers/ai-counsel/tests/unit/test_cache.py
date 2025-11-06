"""Unit tests for decision graph caching layer."""

import time
from datetime import datetime

import pytest

from decision_graph.cache import LRUCache, SimilarityCache


class TestLRUCache:
    """Test cases for LRU cache implementation."""

    def test_init_valid_maxsize(self):
        """Test cache initialization with valid maxsize."""
        cache = LRUCache(maxsize=10)
        assert cache.maxsize == 10
        assert cache.size() == 0

    def test_init_invalid_maxsize(self):
        """Test cache initialization with invalid maxsize."""
        with pytest.raises(ValueError, match="maxsize must be >= 1"):
            LRUCache(maxsize=0)

        with pytest.raises(ValueError, match="maxsize must be >= 1"):
            LRUCache(maxsize=-5)

    def test_put_and_get(self):
        """Test basic put and get operations."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.size() == 2

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = LRUCache(maxsize=5)
        assert cache.get("nonexistent") is None

    def test_put_update_existing_key(self):
        """Test updating an existing key."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        cache.put("key1", "value2")
        assert cache.get("key1") == "value2"
        assert cache.size() == 1  # Still only 1 item

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache(maxsize=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.size() == 3

        # Adding 4th item should evict key1 (oldest)
        cache.put("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_ordering_with_get(self):
        """Test that get() updates LRU ordering."""
        cache = LRUCache(maxsize=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4 - should evict key2 (now oldest)
        cache.put("key4", "value4")
        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LRUCache(maxsize=5)

        # Put with 0.1 second TTL
        cache.put("key1", "value1", ttl=0.1)
        cache.put("key2", "value2")  # No TTL

        # Immediately should be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # Wait for TTL to expire
        time.sleep(0.15)

        # key1 should be expired and removed
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"  # Still present

    def test_ttl_update_on_put(self):
        """Test TTL update when putting existing key."""
        cache = LRUCache(maxsize=5)

        # Put with short TTL
        cache.put("key1", "value1", ttl=0.1)

        # Wait a bit
        time.sleep(0.06)

        # Update with longer TTL
        cache.put("key1", "value2", ttl=0.2)

        # Wait for original TTL to expire
        time.sleep(0.06)

        # Should still be present (new TTL hasn't expired)
        assert cache.get("key1") == "value2"

    def test_ttl_removal_on_update_to_no_ttl(self):
        """Test TTL removal when updating key without TTL."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1", ttl=0.1)
        cache.put("key1", "value2")  # No TTL

        time.sleep(0.15)

        # Should still be present (no TTL anymore)
        assert cache.get("key1") == "value2"

    def test_invalidate_existing_key(self):
        """Test invalidating a specific key."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.size() == 1

    def test_invalidate_nonexistent_key(self):
        """Test invalidating a key that doesn't exist."""
        cache = LRUCache(maxsize=5)
        assert cache.invalidate("nonexistent") is False

    def test_clear(self):
        """Test clearing the entire cache."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1")
        cache.put("key2", "value2", ttl=10)
        cache.put("key3", "value3")

        assert cache.size() == 3

        cache.clear()

        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_statistics_hits_and_misses(self):
        """Test statistics tracking for hits and misses."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1")

        # 2 hits
        cache.get("key1")
        cache.get("key1")

        # 3 misses
        cache.get("key2")
        cache.get("key3")
        cache.get("key4")

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 3
        assert stats["hit_rate"] == 2 / 5

    def test_statistics_evictions(self):
        """Test statistics tracking for evictions."""
        cache = LRUCache(maxsize=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Evicts key1
        cache.put("key4", "value4")  # Evicts key2

        stats = cache.get_stats()
        assert stats["evictions"] == 2

    def test_statistics_size(self):
        """Test statistics size tracking."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        stats = cache.get_stats()
        assert stats["size"] == 2

    def test_statistics_hit_rate_zero_requests(self):
        """Test hit rate calculation with zero requests."""
        cache = LRUCache(maxsize=5)
        stats = cache.get_stats()
        assert stats["hit_rate"] == 0.0

    def test_reset_stats(self):
        """Test resetting statistics."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        cache.reset_stats()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0

    def test_expired_item_counts_as_miss(self):
        """Test that accessing expired item counts as miss."""
        cache = LRUCache(maxsize=5)

        cache.put("key1", "value1", ttl=0.1)
        time.sleep(0.15)

        # Should be miss (expired)
        assert cache.get("key1") is None

        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0


class TestSimilarityCache:
    """Test cases for two-tier similarity cache."""

    def test_init_defaults(self):
        """Test initialization with default parameters."""
        cache = SimilarityCache()

        assert cache.query_cache.maxsize == 200
        assert cache.embedding_cache.maxsize == 500
        assert cache.query_ttl == 300

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        cache = SimilarityCache(
            query_cache_size=100,
            embedding_cache_size=250,
            query_ttl=600,
        )

        assert cache.query_cache.maxsize == 100
        assert cache.embedding_cache.maxsize == 250
        assert cache.query_ttl == 600

    def test_hash_question_consistency(self):
        """Test question hashing is consistent."""
        cache = SimilarityCache()

        hash1 = cache._hash_question("What is the capital of France?")
        hash2 = cache._hash_question("What is the capital of France?")

        assert hash1 == hash2

    def test_hash_question_uniqueness(self):
        """Test different questions produce different hashes."""
        cache = SimilarityCache()

        hash1 = cache._hash_question("Question A")
        hash2 = cache._hash_question("Question B")

        assert hash1 != hash2

    def test_query_cache_miss(self):
        """Test L1 cache miss."""
        cache = SimilarityCache()

        result = cache.get_cached_result("Test question?", threshold=0.7, max_results=3)

        assert result is None

    def test_query_cache_hit(self):
        """Test L1 cache hit."""
        cache = SimilarityCache()

        question = "What is the capital of France?"
        results = [
            {"id": "d1", "score": 0.9},
            {"id": "d2", "score": 0.8},
        ]

        # Cache results
        cache.cache_result(question, 0.7, 3, results)

        # Retrieve from cache
        cached = cache.get_cached_result(question, 0.7, 3)

        assert cached == results

    def test_query_cache_different_params_different_keys(self):
        """Test different query params create different cache keys."""
        cache = SimilarityCache()

        question = "Test question?"
        results1 = [{"id": "d1", "score": 0.9}]
        results2 = [{"id": "d2", "score": 0.85}]

        # Cache with different thresholds
        cache.cache_result(question, 0.7, 3, results1)
        cache.cache_result(question, 0.8, 3, results2)

        # Should get different results
        cached1 = cache.get_cached_result(question, 0.7, 3)
        cached2 = cache.get_cached_result(question, 0.8, 3)

        assert cached1 == results1
        assert cached2 == results2

    def test_query_cache_ttl_expiration(self):
        """Test L1 cache TTL expiration."""
        cache = SimilarityCache(query_ttl=0.1)

        question = "Test question?"
        results = [{"id": "d1", "score": 0.9}]

        cache.cache_result(question, 0.7, 3, results)

        # Immediately should be present
        assert cache.get_cached_result(question, 0.7, 3) == results

        # Wait for TTL to expire
        time.sleep(0.15)

        # Should be expired
        assert cache.get_cached_result(question, 0.7, 3) is None

    def test_embedding_cache_miss(self):
        """Test L2 cache miss."""
        cache = SimilarityCache()

        embedding = cache.get_cached_embedding("Test question?")

        assert embedding is None

    def test_embedding_cache_hit(self):
        """Test L2 cache hit."""
        cache = SimilarityCache()

        question = "What is the capital of France?"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Cache embedding
        cache.cache_embedding(question, embedding)

        # Retrieve from cache
        cached = cache.get_cached_embedding(question)

        assert cached == embedding

    def test_embedding_cache_no_ttl(self):
        """Test L2 cache has no TTL (permanent)."""
        cache = SimilarityCache(query_ttl=0.1)

        question = "Test question?"
        embedding = [0.1, 0.2, 0.3]

        cache.cache_embedding(question, embedding)

        # Wait longer than query TTL
        time.sleep(0.15)

        # Embedding should still be present (no TTL)
        cached = cache.get_cached_embedding(question)
        assert cached == embedding

    def test_invalidate_all_queries(self):
        """Test event-based L1 invalidation."""
        cache = SimilarityCache()

        # Cache some query results
        cache.cache_result("Question 1?", 0.7, 3, [{"id": "d1"}])
        cache.cache_result("Question 2?", 0.7, 3, [{"id": "d2"}])

        # Cache some embeddings
        cache.cache_embedding("Question 1?", [0.1, 0.2])
        cache.cache_embedding("Question 2?", [0.3, 0.4])

        # Invalidate L1 only
        cache.invalidate_all_queries()

        # Query results should be gone
        assert cache.get_cached_result("Question 1?", 0.7, 3) is None
        assert cache.get_cached_result("Question 2?", 0.7, 3) is None

        # Embeddings should still be present
        assert cache.get_cached_embedding("Question 1?") == [0.1, 0.2]
        assert cache.get_cached_embedding("Question 2?") == [0.3, 0.4]

    def test_invalidate_all_queries_sets_timestamp(self):
        """Test invalidation sets last_invalidation timestamp."""
        cache = SimilarityCache()

        assert cache._last_invalidation is None

        cache.invalidate_all_queries()

        assert cache._last_invalidation is not None
        assert isinstance(cache._last_invalidation, datetime)

    def test_invalidate_all(self):
        """Test full cache invalidation (L1 + L2)."""
        cache = SimilarityCache()

        # Cache some data
        cache.cache_result("Question 1?", 0.7, 3, [{"id": "d1"}])
        cache.cache_embedding("Question 1?", [0.1, 0.2])

        # Invalidate everything
        cache.invalidate_all()

        # Both should be gone
        assert cache.get_cached_result("Question 1?", 0.7, 3) is None
        assert cache.get_cached_embedding("Question 1?") is None

    def test_get_stats_empty_cache(self):
        """Test statistics for empty cache."""
        cache = SimilarityCache()

        stats = cache.get_stats()

        assert stats["l1_query_cache"]["size"] == 0
        assert stats["l2_embedding_cache"]["size"] == 0
        assert stats["combined_hit_rate"] == 0.0
        assert stats["last_invalidation"] is None
        assert stats["query_ttl_seconds"] == 300

    def test_get_stats_with_data(self):
        """Test statistics with cached data."""
        cache = SimilarityCache(query_ttl=600)

        # Add some data and access patterns
        cache.cache_result("Q1", 0.7, 3, [{"id": "d1"}])
        cache.cache_embedding("Q1", [0.1, 0.2])

        # Generate hits and misses
        cache.get_cached_result("Q1", 0.7, 3)  # L1 hit
        cache.get_cached_result("Q2", 0.7, 3)  # L1 miss
        cache.get_cached_embedding("Q1")  # L2 hit
        cache.get_cached_embedding("Q2")  # L2 miss

        stats = cache.get_stats()

        # Check L1 stats
        assert stats["l1_query_cache"]["hits"] == 1
        assert stats["l1_query_cache"]["misses"] == 1
        assert stats["l1_query_cache"]["size"] == 1

        # Check L2 stats
        assert stats["l2_embedding_cache"]["hits"] == 1
        assert stats["l2_embedding_cache"]["misses"] == 1
        assert stats["l2_embedding_cache"]["size"] == 1

        # Check combined hit rate (2 hits / 4 requests = 0.5)
        assert stats["combined_hit_rate"] == 0.5

        assert stats["query_ttl_seconds"] == 600

    def test_get_stats_after_invalidation(self):
        """Test statistics include invalidation timestamp."""
        cache = SimilarityCache()

        cache.invalidate_all_queries()

        stats = cache.get_stats()

        assert stats["last_invalidation"] is not None
        # Should be ISO format string
        datetime.fromisoformat(stats["last_invalidation"])

    def test_reset_stats(self):
        """Test resetting statistics."""
        cache = SimilarityCache()

        # Generate some activity
        cache.cache_result("Q1", 0.7, 3, [{"id": "d1"}])
        cache.get_cached_result("Q1", 0.7, 3)  # hit
        cache.get_cached_result("Q2", 0.7, 3)  # miss

        cache.cache_embedding("Q1", [0.1, 0.2])
        cache.get_cached_embedding("Q1")  # hit

        # Reset stats
        cache.reset_stats()

        stats = cache.get_stats()

        assert stats["l1_query_cache"]["hits"] == 0
        assert stats["l1_query_cache"]["misses"] == 0
        assert stats["l2_embedding_cache"]["hits"] == 0
        assert stats["l2_embedding_cache"]["misses"] == 0

        # But data should still be present
        assert cache.get_cached_result("Q1", 0.7, 3) == [{"id": "d1"}]
        assert cache.get_cached_embedding("Q1") == [0.1, 0.2]

    def test_embedding_version_in_key(self):
        """Test embedding version is part of cache key."""
        cache = SimilarityCache()

        question = "Test question?"
        embedding = [0.1, 0.2, 0.3]

        cache.cache_embedding(question, embedding)

        # Check key includes version
        key = cache._make_embedding_key(question)
        assert cache.EMBEDDING_VERSION in key

    def test_large_result_caching(self):
        """Test caching large result sets."""
        cache = SimilarityCache()

        question = "Test question?"
        results = [{"id": f"d{i}", "score": 0.9 - i * 0.01} for i in range(100)]

        cache.cache_result(question, 0.7, 100, results)

        cached = cache.get_cached_result(question, 0.7, 100)
        assert cached == results
        assert len(cached) == 100

    def test_lru_eviction_in_query_cache(self):
        """Test LRU eviction works in L1 query cache."""
        cache = SimilarityCache(query_cache_size=2)

        # Fill cache
        cache.cache_result("Q1", 0.7, 3, [{"id": "d1"}])
        cache.cache_result("Q2", 0.7, 3, [{"id": "d2"}])

        # Add third item - should evict Q1
        cache.cache_result("Q3", 0.7, 3, [{"id": "d3"}])

        assert cache.get_cached_result("Q1", 0.7, 3) is None  # Evicted
        assert cache.get_cached_result("Q2", 0.7, 3) == [{"id": "d2"}]
        assert cache.get_cached_result("Q3", 0.7, 3) == [{"id": "d3"}]

    def test_lru_eviction_in_embedding_cache(self):
        """Test LRU eviction works in L2 embedding cache."""
        cache = SimilarityCache(embedding_cache_size=2)

        # Fill cache
        cache.cache_embedding("Q1", [0.1])
        cache.cache_embedding("Q2", [0.2])

        # Add third item - should evict Q1
        cache.cache_embedding("Q3", [0.3])

        assert cache.get_cached_embedding("Q1") is None  # Evicted
        assert cache.get_cached_embedding("Q2") == [0.2]
        assert cache.get_cached_embedding("Q3") == [0.3]

    def test_cache_with_special_characters_in_question(self):
        """Test caching questions with special characters."""
        cache = SimilarityCache()

        question = "What's the best approach? (2024) #performance $100k+"
        results = [{"id": "d1", "score": 0.9}]
        embedding = [0.1, 0.2, 0.3]

        cache.cache_result(question, 0.7, 3, results)
        cache.cache_embedding(question, embedding)

        assert cache.get_cached_result(question, 0.7, 3) == results
        assert cache.get_cached_embedding(question) == embedding

    def test_cache_with_unicode_question(self):
        """Test caching questions with Unicode characters."""
        cache = SimilarityCache()

        question = "Comment améliorer la performance? 中文测试 🚀"
        results = [{"id": "d1", "score": 0.9}]

        cache.cache_result(question, 0.7, 3, results)
        assert cache.get_cached_result(question, 0.7, 3) == results
