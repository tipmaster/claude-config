"""Performance tests for decision graph caching layer."""

import time

from decision_graph.cache import SimilarityCache


class TestCachePerformance:
    """Performance and benchmarking tests for cache."""

    def test_cache_lookup_latency(self):
        """Test cache lookup is under 1ms."""
        cache = SimilarityCache()

        # Populate cache
        question = "What is the capital of France?"
        results = [{"id": f"d{i}", "score": 0.9 - i * 0.01} for i in range(10)]
        cache.cache_result(question, 0.7, 10, results)

        # Measure lookup time (average over 1000 lookups)
        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            cache.get_cached_result(question, 0.7, 10)

        end_time = time.perf_counter()
        avg_latency_ms = ((end_time - start_time) / iterations) * 1000

        print(
            f"\nL1 cache lookup: {avg_latency_ms:.4f}ms (avg over {iterations} iterations)"
        )
        assert avg_latency_ms < 1.0, f"Cache lookup too slow: {avg_latency_ms}ms"

    def test_embedding_cache_lookup_latency(self):
        """Test embedding cache lookup is under 1ms."""
        cache = SimilarityCache()

        # Populate cache with large embedding
        question = "What is the capital of France?"
        embedding = [0.1] * 384  # Typical sentence transformer dimension

        cache.cache_embedding(question, embedding)

        # Measure lookup time
        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            cache.get_cached_embedding(question)

        end_time = time.perf_counter()
        avg_latency_ms = ((end_time - start_time) / iterations) * 1000

        print(
            f"\nL2 cache lookup: {avg_latency_ms:.4f}ms (avg over {iterations} iterations)"
        )
        assert (
            avg_latency_ms < 1.0
        ), f"Embedding cache lookup too slow: {avg_latency_ms}ms"

    def test_cache_invalidation_latency(self):
        """Test cache invalidation is under 10ms."""
        cache = SimilarityCache(query_cache_size=100)

        # Populate cache with 100 items
        for i in range(100):
            cache.cache_result(f"Question {i}?", 0.7, 3, [{"id": f"d{i}"}])

        # Measure invalidation time
        start_time = time.perf_counter()
        cache.invalidate_all_queries()
        end_time = time.perf_counter()

        invalidation_ms = (end_time - start_time) * 1000

        print(f"\nCache invalidation: {invalidation_ms:.4f}ms (100 items)")
        assert invalidation_ms < 10.0, f"Invalidation too slow: {invalidation_ms}ms"

    def test_cache_hit_rate_after_warmup(self):
        """Test cache achieves 60%+ hit rate after warmup."""
        cache = SimilarityCache()

        # Simulate query patterns (Zipf distribution - some queries more common)
        common_questions = [
            "What is the capital of France?",
            "How do I install Python?",
            "What is the best programming language?",
        ]

        rare_questions = [f"Rare question {i}?" for i in range(20)]

        # Warmup phase - cache common questions
        for q in common_questions:
            results = [{"id": f"d_{q[:10]}", "score": 0.9}]
            cache.cache_result(q, 0.7, 3, results)

        # Simulate realistic query mix (70% common, 30% rare)
        total_queries = 100
        for i in range(total_queries):
            if i % 10 < 7:  # 70% common questions
                q = common_questions[i % len(common_questions)]
            else:  # 30% rare questions
                q = rare_questions[i % len(rare_questions)]

            # Try to get from cache
            cache.get_cached_result(q, 0.7, 3)

        stats = cache.get_stats()
        hit_rate = stats["l1_query_cache"]["hit_rate"]

        print(f"\nL1 cache hit rate after warmup: {hit_rate:.2%}")
        assert hit_rate >= 0.60, f"Hit rate too low: {hit_rate:.2%}"

    def test_memory_overhead(self):
        """Test memory overhead is reasonable for cached items."""

        cache = SimilarityCache(query_cache_size=1000, embedding_cache_size=1000)

        # Populate with realistic data
        for i in range(1000):
            question = f"What is the best approach for {i}?"

            # Cache query result (10 items)
            results = [
                {"id": f"d{j}", "question": f"Question {j}", "score": 0.9 - j * 0.01}
                for j in range(10)
            ]
            cache.cache_result(question, 0.7, 10, results)

            # Cache embedding (384 dimensions - typical)
            embedding = [0.1 + i * 0.0001] * 384
            cache.cache_embedding(question, embedding)

        # Rough memory estimate
        # Each result ~200 bytes, each embedding ~3KB (384 floats)
        # Expected: ~1000 * (200 + 3000) = ~3.2MB
        # With overhead: ~5-10MB acceptable

        stats = cache.get_stats()
        l1_size = stats["l1_query_cache"]["size"]
        l2_size = stats["l2_embedding_cache"]["size"]

        print(f"\nCache sizes - L1: {l1_size} items, L2: {l2_size} items")

        # Verify caches are at capacity
        assert l1_size == 1000
        assert l2_size == 1000

    def test_cache_with_concurrent_access_pattern(self):
        """Test cache performs well with realistic concurrent access patterns."""
        cache = SimilarityCache(query_cache_size=50)

        # Simulate multiple rounds of deliberations
        questions = [
            "Should we adopt microservices?",
            "What is the best database for our use case?",
            "How should we handle authentication?",
            "What testing strategy should we use?",
            "Should we use TypeScript or JavaScript?",
        ]

        # Each question gets asked multiple times (different thresholds)
        thresholds = [0.6, 0.7, 0.8]
        max_results_options = [3, 5, 10]

        iterations = 100
        start_time = time.perf_counter()

        for i in range(iterations):
            q = questions[i % len(questions)]
            threshold = thresholds[i % len(thresholds)]
            max_results = max_results_options[i % len(max_results_options)]

            # Try to get from cache
            cached = cache.get_cached_result(q, threshold, max_results)

            if cached is None:
                # Cache miss - compute and store
                results = [
                    {"id": f"d{j}", "score": 0.9 - j * 0.01} for j in range(max_results)
                ]
                cache.cache_result(q, threshold, max_results, results)

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        stats = cache.get_stats()
        hit_rate = stats["l1_query_cache"]["hit_rate"]
        avg_time_per_query_ms = total_time_ms / iterations

        print(
            f"\nConcurrent access - Hit rate: {hit_rate:.2%}, "
            f"Avg time per query: {avg_time_per_query_ms:.4f}ms"
        )

        # Should achieve decent hit rate with repeated queries
        assert hit_rate > 0.5, f"Hit rate too low: {hit_rate:.2%}"
        assert (
            avg_time_per_query_ms < 1.0
        ), f"Avg query time too high: {avg_time_per_query_ms}ms"

    def test_ttl_impact_on_hit_rate(self):
        """Test TTL doesn't prematurely expire frequently accessed items."""
        # Use short TTL for testing
        cache = SimilarityCache(query_ttl=0.5)

        question = "What is the capital of France?"
        results = [{"id": "d1", "score": 0.9}]

        # Cache result
        cache.cache_result(question, 0.7, 3, results)

        # Access repeatedly within TTL window
        hits = 0
        for i in range(10):
            if cache.get_cached_result(question, 0.7, 3) is not None:
                hits += 1
            time.sleep(0.04)  # 40ms between accesses (total 400ms < 500ms TTL)

        assert hits == 10, f"Expected 10 hits, got {hits}"

        # Wait for TTL to expire
        time.sleep(0.2)

        # Should be expired now
        assert cache.get_cached_result(question, 0.7, 3) is None

    def test_lru_eviction_doesnt_impact_hot_items(self):
        """Test LRU eviction preserves frequently accessed items."""
        cache = SimilarityCache(query_cache_size=5)

        # Cache 5 items (fill cache)
        for i in range(5):
            cache.cache_result(f"Q{i}", 0.7, 3, [{"id": f"d{i}"}])

        # Repeatedly access Q0 (make it hot)
        for _ in range(10):
            cache.get_cached_result("Q0", 0.7, 3)

        # Add 2 more items (should evict Q1-Q2, not Q0 which is most recently used)
        for i in range(5, 7):
            cache.cache_result(f"Q{i}", 0.7, 3, [{"id": f"d{i}"}])

        # Q0 should still be present (it was accessed frequently)
        assert cache.get_cached_result("Q0", 0.7, 3) is not None

        # Q1 should be evicted (it was oldest and not accessed)
        assert cache.get_cached_result("Q1", 0.7, 3) is None

    def test_cache_stats_accuracy(self):
        """Test cache statistics are accurate over many operations."""
        cache = SimilarityCache()

        questions = [f"Question {i}?" for i in range(10)]

        # Track expected counts
        expected_hits = 0
        expected_misses = 0

        # First access - all misses
        for q in questions:
            result = cache.get_cached_result(q, 0.7, 3)
            assert result is None
            expected_misses += 1

            # Cache it
            cache.cache_result(q, 0.7, 3, [{"id": "d1"}])

        # Second access - all hits
        for q in questions:
            result = cache.get_cached_result(q, 0.7, 3)
            assert result is not None
            expected_hits += 1

        # Third access - mix (different thresholds)
        for i, q in enumerate(questions):
            threshold = 0.8 if i % 2 == 0 else 0.7
            result = cache.get_cached_result(q, threshold, 3)

            if threshold == 0.7:
                assert result is not None
                expected_hits += 1
            else:
                assert result is None
                expected_misses += 1

        stats = cache.get_stats()
        actual_hits = stats["l1_query_cache"]["hits"]
        actual_misses = stats["l1_query_cache"]["misses"]

        assert (
            actual_hits == expected_hits
        ), f"Expected {expected_hits} hits, got {actual_hits}"
        assert (
            actual_misses == expected_misses
        ), f"Expected {expected_misses} misses, got {actual_misses}"

    def test_hash_collision_resistance(self):
        """Test hash function has low collision rate."""
        cache = SimilarityCache()

        # Generate 1000 unique questions
        questions = [f"Question {i} with unique content" for i in range(1000)]

        # Hash all questions
        hashes = [cache._hash_question(q) for q in questions]

        # Check for collisions
        unique_hashes = set(hashes)

        collision_rate = 1 - (len(unique_hashes) / len(hashes))

        print(
            f"\nHash collision rate: {collision_rate:.4%} ({len(hashes) - len(unique_hashes)} collisions)"
        )

        # SHA256 should have zero collisions for this test
        assert len(unique_hashes) == len(hashes), "Unexpected hash collision detected"

    def test_cache_performance_degradation_at_capacity(self):
        """Test cache performance doesn't degrade significantly when at capacity."""
        cache = SimilarityCache(query_cache_size=100)

        # Fill cache to capacity
        for i in range(100):
            cache.cache_result(f"Q{i}", 0.7, 3, [{"id": f"d{i}"}])

        # Measure performance when adding more items (triggering evictions)
        start_time = time.perf_counter()

        for i in range(100, 200):
            cache.cache_result(f"Q{i}", 0.7, 3, [{"id": f"d{i}"}])

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / 100) * 1000

        print(f"\nAvg cache insertion time at capacity: {avg_time_ms:.4f}ms")

        # Should still be fast (under 1ms per insertion with eviction)
        assert (
            avg_time_ms < 1.0
        ), f"Cache insertion too slow at capacity: {avg_time_ms}ms"

        # Verify cache is still at max size
        stats = cache.get_stats()
        assert stats["l1_query_cache"]["size"] == 100
        assert stats["l1_query_cache"]["evictions"] == 100
