"""Integration tests demonstrating cache performance improvements for DecisionRetriever.

This module provides performance benchmarks comparing cached vs uncached retrieval
operations, demonstrating the latency improvements from the two-tier cache.
"""

import time
from datetime import UTC, datetime

import pytest

from decision_graph.retrieval import DecisionRetriever
from decision_graph.schema import DecisionNode
from decision_graph.storage import DecisionGraphStorage


@pytest.fixture
def storage_with_decisions():
    """Create in-memory storage with sample decisions."""
    storage = DecisionGraphStorage(":memory:")

    # Add 50 sample decisions
    decisions = []
    for i in range(50):
        decision = DecisionNode(
            id=f"dec{i:03d}",
            question=f"Should we adopt technology {i}?",
            timestamp=datetime.now(UTC),
            participants=["claude", "codex", "droid"],
            convergence_status="converged",
            consensus=f"Technology {i} is recommended for use case {i}",
            winning_option=f"Option {i % 3}",
            transcript_path=f"transcripts/20240101_{i:06d}_technology.md",
        )
        storage.save_decision_node(decision)
        decisions.append(decision)

    return storage


class TestRetrievalCachePerformance:
    """Performance tests for cached vs uncached retrieval."""

    def test_cache_hit_performance_improvement(self, storage_with_decisions):
        """Test cache hit provides significant latency improvement."""
        retriever = DecisionRetriever(storage_with_decisions, enable_cache=True)

        query = "Should we adopt technology 1?"
        threshold = 0.7
        max_results = 5

        # First call - cache miss (slower)
        start = time.perf_counter()
        results1 = retriever.find_relevant_decisions(
            query, threshold=threshold, max_results=max_results
        )
        miss_time = time.perf_counter() - start

        # Second call - cache hit (faster)
        start = time.perf_counter()
        results2 = retriever.find_relevant_decisions(
            query, threshold=threshold, max_results=max_results
        )
        hit_time = time.perf_counter() - start

        # Verify same results
        assert len(results1) == len(results2)
        assert [d.id for d in results1] == [d.id for d in results2]

        # Cache hit should be faster (typically 10-100x faster)
        assert hit_time < miss_time, (
            f"Cache hit ({hit_time:.4f}s) should be faster than "
            f"cache miss ({miss_time:.4f}s)"
        )

        # Log performance metrics
        speedup = miss_time / hit_time if hit_time > 0 else float("inf")
        print("\nCache performance:")
        print(f"  Cache miss: {miss_time*1000:.2f}ms")
        print(f"  Cache hit:  {hit_time*1000:.2f}ms")
        print(f"  Speedup:    {speedup:.1f}x")

        # Verify cache stats
        stats = retriever.get_cache_stats()
        assert stats["l1_query_cache"]["hits"] == 1
        assert stats["l1_query_cache"]["misses"] == 1

    def test_multiple_queries_cache_benefit(self, storage_with_decisions):
        """Test cache benefit across multiple repeated queries."""
        retriever = DecisionRetriever(storage_with_decisions, enable_cache=True)

        query = "Should we adopt technology 5?"
        num_iterations = 10

        # First query - cache miss
        start = time.perf_counter()
        retriever.find_relevant_decisions(query, threshold=0.7, max_results=3)
        first_time = time.perf_counter() - start

        # Subsequent queries - cache hits
        start = time.perf_counter()
        for _ in range(num_iterations - 1):
            retriever.find_relevant_decisions(query, threshold=0.7, max_results=3)
        subsequent_time = time.perf_counter() - start

        avg_hit_time = subsequent_time / (num_iterations - 1)

        # Average cache hit time should be much faster than miss
        assert avg_hit_time < first_time

        print("\nMultiple query performance:")
        print(f"  Initial query (miss): {first_time*1000:.2f}ms")
        print(f"  Avg cached query:     {avg_hit_time*1000:.2f}ms")
        print(f"  Speedup:              {first_time/avg_hit_time:.1f}x")

        # Verify cache stats
        stats = retriever.get_cache_stats()
        assert stats["l1_query_cache"]["hits"] == num_iterations - 1
        assert stats["l1_query_cache"]["misses"] == 1
        assert (
            stats["l1_query_cache"]["hit_rate"] == (num_iterations - 1) / num_iterations
        )

    def test_uncached_retrieval_performance_baseline(self, storage_with_decisions):
        """Baseline test: uncached retrieval always recomputes."""
        retriever = DecisionRetriever(storage_with_decisions, enable_cache=False)

        query = "Should we adopt technology 10?"
        num_iterations = 5

        times = []
        for _ in range(num_iterations):
            start = time.perf_counter()
            retriever.find_relevant_decisions(query, threshold=0.7, max_results=3)
            times.append(time.perf_counter() - start)

        avg_time = sum(times) / len(times)

        print("\nUncached retrieval baseline:")
        print(f"  Average query time: {avg_time*1000:.2f}ms")
        print(f"  Min time:          {min(times)*1000:.2f}ms")
        print(f"  Max time:          {max(times)*1000:.2f}ms")

        # No cache stats should be available
        assert retriever.get_cache_stats() is None

    def test_cache_hit_rate_tracking(self, storage_with_decisions):
        """Test cache hit rate tracking over mixed queries."""
        retriever = DecisionRetriever(storage_with_decisions, enable_cache=True)

        # Query A: 1 miss + 4 hits = 5 requests
        for _ in range(5):
            retriever.find_relevant_decisions("Query A?", threshold=0.7, max_results=3)

        # Query B: 1 miss + 2 hits = 3 requests
        for _ in range(3):
            retriever.find_relevant_decisions("Query B?", threshold=0.7, max_results=3)

        # Query C: 1 miss only = 1 request
        retriever.find_relevant_decisions("Query C?", threshold=0.7, max_results=3)

        # Total: 9 requests, 2 misses (A, B, C first), 6 hits (A×4, B×2)
        # Hit rate: 6/9 = 0.666... but actually we need to track properly

        stats = retriever.get_cache_stats()

        # 3 unique queries = 3 misses
        assert stats["l1_query_cache"]["misses"] == 3

        # 5 + 3 + 1 - 3 = 6 hits
        assert stats["l1_query_cache"]["hits"] == 6

        # Hit rate should be 6/9 = 0.666...
        expected_hit_rate = 6 / 9
        assert abs(stats["l1_query_cache"]["hit_rate"] - expected_hit_rate) < 0.001

        print("\nCache hit rate tracking:")
        print("  Total requests: 9")
        print(f"  Cache hits:     {stats['l1_query_cache']['hits']}")
        print(f"  Cache misses:   {stats['l1_query_cache']['misses']}")
        print(f"  Hit rate:       {stats['l1_query_cache']['hit_rate']:.1%}")

    def test_cache_invalidation_forces_recomputation(self, storage_with_decisions):
        """Test cache invalidation causes performance reset."""
        retriever = DecisionRetriever(storage_with_decisions, enable_cache=True)

        query = "Should we adopt technology 15?"

        # First query - cache miss
        start = time.perf_counter()
        retriever.find_relevant_decisions(query, threshold=0.7, max_results=3)
        first_time = time.perf_counter() - start

        # Second query - cache hit (fast)
        start = time.perf_counter()
        retriever.find_relevant_decisions(query, threshold=0.7, max_results=3)
        cached_time = time.perf_counter() - start

        assert cached_time < first_time

        # Invalidate cache (simulating new decision added)
        retriever.invalidate_cache()

        # Third query - cache miss again (slower)
        start = time.perf_counter()
        retriever.find_relevant_decisions(query, threshold=0.7, max_results=3)
        post_invalidation_time = time.perf_counter() - start

        # Post-invalidation time should be similar to first time (both misses)
        # Allow some variance due to system noise
        assert post_invalidation_time > cached_time

        print("\nCache invalidation performance:")
        print(f"  Initial miss:         {first_time*1000:.2f}ms")
        print(f"  Cached hit:           {cached_time*1000:.2f}ms")
        print(f"  Post-invalidation:    {post_invalidation_time*1000:.2f}ms")

        # Verify cache was invalidated
        stats = retriever.get_cache_stats()
        assert stats["last_invalidation"] is not None

    def test_different_params_no_cache_benefit(self, storage_with_decisions):
        """Test different query parameters don't benefit from each other's cache."""
        retriever = DecisionRetriever(storage_with_decisions, enable_cache=True)

        query = "Should we adopt technology 20?"

        # Query with threshold=0.7
        start = time.perf_counter()
        retriever.find_relevant_decisions(query, threshold=0.7, max_results=3)
        time1 = time.perf_counter() - start

        # Query with threshold=0.8 (different cache key)
        start = time.perf_counter()
        retriever.find_relevant_decisions(query, threshold=0.8, max_results=3)
        time2 = time.perf_counter() - start

        # Both should be cache misses (similar timing)
        stats = retriever.get_cache_stats()
        assert stats["l1_query_cache"]["misses"] == 2
        assert stats["l1_query_cache"]["hits"] == 0

        print("\nDifferent params performance:")
        print(f"  Query (threshold=0.7): {time1*1000:.2f}ms")
        print(f"  Query (threshold=0.8): {time2*1000:.2f}ms")
        print("  Both are cache misses (no cross-benefit)")

    def test_empty_result_caching_performance(self, storage_with_decisions):
        """Test empty results are cached efficiently."""
        retriever = DecisionRetriever(storage_with_decisions, enable_cache=True)

        # Query unlikely to match anything
        query = "XYZABC completely unrelated random query 12345"

        # First query - cache miss
        start = time.perf_counter()
        results1 = retriever.find_relevant_decisions(
            query, threshold=0.9, max_results=3
        )
        miss_time = time.perf_counter() - start

        assert len(results1) == 0  # No matches

        # Second query - cache hit (even for empty result)
        start = time.perf_counter()
        results2 = retriever.find_relevant_decisions(
            query, threshold=0.9, max_results=3
        )
        hit_time = time.perf_counter() - start

        assert len(results2) == 0  # Still no matches
        assert hit_time < miss_time  # But faster due to cache

        print("\nEmpty result caching:")
        print(f"  First query (miss):  {miss_time*1000:.2f}ms")
        print(f"  Second query (hit):  {hit_time*1000:.2f}ms")
        print(f"  Speedup:             {miss_time/hit_time:.1f}x")

        # Verify cache stats
        stats = retriever.get_cache_stats()
        assert stats["l1_query_cache"]["hits"] == 1
        assert stats["l1_query_cache"]["misses"] == 1
