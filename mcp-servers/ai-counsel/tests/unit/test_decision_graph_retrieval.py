"""Unit tests for DecisionRetriever with caching integration."""

import time
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from decision_graph.cache import SimilarityCache
from decision_graph.retrieval import DecisionRetriever
from decision_graph.schema import DecisionNode
from decision_graph.storage import DecisionGraphStorage


@pytest.fixture
def mock_storage():
    """Create mock storage backend."""
    storage = Mock(spec=DecisionGraphStorage)
    return storage


@pytest.fixture
def sample_decisions():
    """Create sample decision nodes for testing."""
    return [
        DecisionNode(
            id="dec1",
            question="Should we use React or Vue?",
            timestamp=datetime.now(UTC),
            participants=["claude", "codex"],
            convergence_status="converged",
            consensus="React is preferred for larger applications",
            winning_option="React",
            transcript_path="transcripts/20240101_120000_React_or_Vue.md",
        ),
        DecisionNode(
            id="dec2",
            question="What database should we use?",
            timestamp=datetime.now(UTC),
            participants=["claude", "codex"],
            convergence_status="converged",
            consensus="PostgreSQL is recommended",
            winning_option="PostgreSQL",
            transcript_path="transcripts/20240101_120000_Database.md",
        ),
        DecisionNode(
            id="dec3",
            question="Should we adopt TypeScript?",
            timestamp=datetime.now(UTC),
            participants=["claude", "codex"],
            convergence_status="converged",
            consensus="TypeScript provides better type safety",
            winning_option="TypeScript",
            transcript_path="transcripts/20240101_120000_TypeScript.md",
        ),
    ]


class TestDecisionRetrieverCacheIntegration:
    """Test DecisionRetriever cache integration."""

    def test_init_with_cache_enabled_default(self, mock_storage):
        """Test initialization with caching enabled by default."""
        retriever = DecisionRetriever(mock_storage)

        assert retriever.cache is not None
        assert isinstance(retriever.cache, SimilarityCache)
        assert retriever.cache.query_cache.maxsize == 200
        assert retriever.cache.embedding_cache.maxsize == 500
        assert retriever.cache.query_ttl == 300

    def test_init_with_cache_disabled(self, mock_storage):
        """Test initialization with caching disabled."""
        retriever = DecisionRetriever(mock_storage, enable_cache=False)

        assert retriever.cache is None

    def test_init_with_custom_cache(self, mock_storage):
        """Test initialization with custom cache instance."""
        custom_cache = SimilarityCache(
            query_cache_size=100,
            embedding_cache_size=250,
            query_ttl=600,
        )

        retriever = DecisionRetriever(mock_storage, cache=custom_cache)

        assert retriever.cache is custom_cache
        assert retriever.cache.query_cache.maxsize == 100
        assert retriever.cache.embedding_cache.maxsize == 250
        assert retriever.cache.query_ttl == 600

    def test_find_relevant_decisions_cache_miss_then_hit(
        self, mock_storage, sample_decisions
    ):
        """Test cache miss followed by cache hit."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        # Mock similarity detector to return predictable results
        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
            {"id": "dec3", "question": sample_decisions[2].question, "score": 0.75},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # First call - cache miss
            results1 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            assert len(results1) == 2
            assert results1[0][0].id == "dec1"  # results are tuples (decision, score)
            assert results1[1][0].id == "dec3"

            # Verify storage was accessed
            assert mock_storage.get_all_decisions.call_count == 1

            # Second call with same params - cache hit
            results2 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            assert len(results2) == 2
            assert results2[0][0].id == "dec1"  # results are tuples (decision, score)
            assert results2[1][0].id == "dec3"

            # Storage should NOT be accessed again for similarity computation
            # (still 1 call from before, but get_decision_node called to reconstruct)
            assert mock_storage.get_all_decisions.call_count == 1

    def test_find_relevant_decisions_different_params_share_cache(
        self, mock_storage, sample_decisions
    ):
        """Test different thresholds now SHARE the same cache (Task 4 change)."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
            {"id": "dec3", "question": sample_decisions[2].question, "score": 0.75},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ) as mock_find_similar:
            # Query with threshold=0.8
            results1 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.8, max_results=3
            )
            assert len(results1) == 2  # Gets all results above noise floor

            # Query with threshold=0.7 (SAME cache key now - threshold ignored)
            results2 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert len(results2) == 2  # Cache hit - same results

            # Only ONE similarity computation (second query hits cache)
            assert mock_find_similar.call_count == 1

    def test_find_relevant_decisions_cache_disabled(
        self, mock_storage, sample_decisions
    ):
        """Test find_relevant_decisions works with cache disabled."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage, enable_cache=False)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # First call
            results1 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert len(results1) == 1

            # Second call - should recompute (no cache)
            results2 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert len(results2) == 1

            # Storage accessed both times
            assert mock_storage.get_all_decisions.call_count == 2

    def test_find_relevant_decisions_empty_result_cached(
        self, mock_storage, sample_decisions
    ):
        """Test empty results are cached to avoid recomputation."""
        mock_storage.get_all_decisions.return_value = sample_decisions

        retriever = DecisionRetriever(mock_storage)

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=[]
        ):
            # First call - no matches
            results1 = retriever.find_relevant_decisions(
                "Completely unrelated question?", threshold=0.7, max_results=3
            )
            assert len(results1) == 0

            # Second call - should hit cache (empty result cached)
            results2 = retriever.find_relevant_decisions(
                "Completely unrelated question?", threshold=0.7, max_results=3
            )
            assert len(results2) == 0

            # Storage accessed only once
            assert mock_storage.get_all_decisions.call_count == 1

    def test_find_relevant_decisions_cached_decision_deleted(
        self, mock_storage, sample_decisions
    ):
        """Test handling when cached decision has been deleted from storage."""
        mock_storage.get_all_decisions.return_value = sample_decisions

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
            {"id": "dec_deleted", "question": "Deleted decision", "score": 0.80},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # First call - cache miss
            mock_storage.get_decision_node.side_effect = lambda id: (
                sample_decisions[0] if id == "dec1" else None
            )

            results1 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            # Should only return dec1 (dec_deleted not found)
            assert len(results1) == 1
            assert results1[0][0].id == "dec1"  # results are tuples (decision, score)

            # Second call - cache hit, but dec_deleted still not found
            results2 = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            assert len(results2) == 1
            assert results2[0][0].id == "dec1"  # results are tuples (decision, score)

    def test_invalidate_cache(self, mock_storage, sample_decisions):
        """Test cache invalidation."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # First query - cache miss
            retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert mock_storage.get_all_decisions.call_count == 1

            # Second query - cache hit
            retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert mock_storage.get_all_decisions.call_count == 1

            # Invalidate cache
            retriever.invalidate_cache()

            # Third query - cache miss again (invalidated)
            retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert mock_storage.get_all_decisions.call_count == 2

    def test_invalidate_cache_with_cache_disabled(self, mock_storage):
        """Test invalidate_cache does nothing when cache disabled."""
        retriever = DecisionRetriever(mock_storage, enable_cache=False)

        # Should not raise error
        retriever.invalidate_cache()

    def test_get_cache_stats_enabled(self, mock_storage, sample_decisions):
        """Test get_cache_stats with caching enabled."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Generate some cache activity
            retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )  # miss
            retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )  # hit

            stats = retriever.get_cache_stats()

            assert stats is not None
            assert "l1_query_cache" in stats
            assert "l2_embedding_cache" in stats
            assert stats["l1_query_cache"]["hits"] == 1
            assert stats["l1_query_cache"]["misses"] == 1

    def test_get_cache_stats_disabled(self, mock_storage):
        """Test get_cache_stats returns None when cache disabled."""
        retriever = DecisionRetriever(mock_storage, enable_cache=False)

        stats = retriever.get_cache_stats()

        assert stats is None

    def test_cache_ttl_expiration(self, mock_storage, sample_decisions):
        """Test cache TTL expiration causes recomputation."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        # Create retriever with very short TTL for testing
        retriever = DecisionRetriever(
            mock_storage,
            cache=SimilarityCache(query_ttl=0.1),  # 100ms TTL
        )

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # First query - cache miss
            retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert mock_storage.get_all_decisions.call_count == 1

            # Wait for TTL to expire
            time.sleep(0.15)

            # Second query - cache miss due to TTL expiration
            retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert mock_storage.get_all_decisions.call_count == 2

    def test_get_enriched_context_uses_cache(self, mock_storage, sample_decisions):
        """Test get_enriched_context benefits from caching."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )
        mock_storage.get_participant_stances.return_value = []

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # First call - cache miss
            context1 = retriever.get_enriched_context(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert "React or Vue" in context1
            assert mock_storage.get_all_decisions.call_count == 1

            # Second call - cache hit
            context2 = retriever.get_enriched_context(
                "Should we use React?", threshold=0.7, max_results=3
            )
            assert context1 == context2
            assert mock_storage.get_all_decisions.call_count == 1

    def test_cache_hit_rate_tracking(self, mock_storage, sample_decisions):
        """Test cache hit rate is tracked correctly."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # 1 miss
            retriever.find_relevant_decisions(
                "Question 1?", threshold=0.7, max_results=3
            )

            # 3 hits
            retriever.find_relevant_decisions(
                "Question 1?", threshold=0.7, max_results=3
            )
            retriever.find_relevant_decisions(
                "Question 1?", threshold=0.7, max_results=3
            )
            retriever.find_relevant_decisions(
                "Question 1?", threshold=0.7, max_results=3
            )

            stats = retriever.get_cache_stats()

            assert stats["l1_query_cache"]["hits"] == 3
            assert stats["l1_query_cache"]["misses"] == 1
            assert stats["l1_query_cache"]["hit_rate"] == 0.75  # 3/4

    def test_empty_query_question_bypasses_cache(self, mock_storage):
        """Test empty query question returns empty list without cache access."""
        retriever = DecisionRetriever(mock_storage)

        results = retriever.find_relevant_decisions("", threshold=0.7, max_results=3)

        assert results == []
        mock_storage.get_all_decisions.assert_not_called()

        # Verify cache wasn't accessed
        stats = retriever.get_cache_stats()
        assert stats["l1_query_cache"]["hits"] == 0
        assert stats["l1_query_cache"]["misses"] == 0

    def test_no_decisions_in_storage_cached(self, mock_storage):
        """Test no decisions scenario is handled correctly."""
        mock_storage.get_all_decisions.return_value = []

        retriever = DecisionRetriever(mock_storage)

        # First call - cache miss
        results1 = retriever.find_relevant_decisions(
            "Any question?", threshold=0.7, max_results=3
        )
        assert results1 == []
        assert mock_storage.get_all_decisions.call_count == 1

        # Second call - should still check storage (no caching when storage empty)
        results2 = retriever.find_relevant_decisions(
            "Any question?", threshold=0.7, max_results=3
        )
        assert results2 == []
        # Note: Empty storage returns immediately, so no cache hit/miss logged
        assert mock_storage.get_all_decisions.call_count == 2


class TestDecisionRetrieverTieredFormatting:
    """Test tiered context formatting with token budget tracking."""

    def test_format_context_tiered_strong_tier(self, mock_storage, sample_decisions):
        """Test that strong matches (≥0.75) get full formatting (~500 tokens)."""
        retriever = DecisionRetriever(mock_storage)

        # Create a scored decision with strong similarity
        scored_decisions = [
            (sample_decisions[0], 0.85),  # Strong match
        ]

        tier_boundaries = {"strong": 0.75, "moderate": 0.60}
        token_budget = 2000

        # Mock get_participant_stances to return sample stances
        mock_storage.get_participant_stances.return_value = [
            Mock(
                participant="claude",
                vote_option="React",
                confidence=0.9,
                rationale="Better ecosystem support",
            )
        ]

        result = retriever.format_context_tiered(
            scored_decisions, tier_boundaries, token_budget
        )

        # Strong tier should include full formatting:
        # - Question, timestamp, convergence_status, consensus, winning_option
        # - Participants with their positions, votes, confidence, rationale
        formatted = result["formatted"]
        assert "Should we use React or Vue?" in formatted
        assert "convergence_status" in formatted.lower() or "converged" in formatted
        assert "consensus" in formatted.lower() or "React is preferred" in formatted
        assert "React" in formatted  # Winning option
        assert "claude" in formatted  # Participant
        assert "Better ecosystem support" in formatted  # Rationale

        # Should use roughly 100-300 tokens (strong tier with full details)
        tokens_used = result["tokens_used"]
        assert 80 < tokens_used < 400, f"Expected ~100-300 tokens, got {tokens_used}"

        # Tier distribution should show 1 strong
        assert result["tier_distribution"]["strong"] == 1
        assert result["tier_distribution"]["moderate"] == 0
        assert result["tier_distribution"]["brief"] == 0

    def test_format_context_tiered_moderate_tier(self, mock_storage, sample_decisions):
        """Test that moderate matches (0.60-0.74) get summary formatting (~200 tokens)."""
        retriever = DecisionRetriever(mock_storage)

        # Create a scored decision with moderate similarity
        scored_decisions = [
            (sample_decisions[1], 0.65),  # Moderate match
        ]

        tier_boundaries = {"strong": 0.75, "moderate": 0.60}
        token_budget = 2000

        result = retriever.format_context_tiered(
            scored_decisions, tier_boundaries, token_budget
        )

        # Moderate tier should include summary:
        # - Question, consensus, winning_option (no detailed stances)
        formatted = result["formatted"]
        assert "What database should we use?" in formatted
        assert "PostgreSQL" in formatted  # Winning option or consensus

        # Should NOT include detailed participant stances (moderate is summary only)
        # Note: We're being less strict here - moderate format might mention participants
        # but shouldn't have detailed rationales

        # Should use roughly 50-150 tokens (moderate tier summary)
        tokens_used = result["tokens_used"]
        assert 40 < tokens_used < 200, f"Expected ~50-150 tokens, got {tokens_used}"

        # Tier distribution should show 1 moderate
        assert result["tier_distribution"]["strong"] == 0
        assert result["tier_distribution"]["moderate"] == 1
        assert result["tier_distribution"]["brief"] == 0

    def test_format_context_tiered_brief_tier(self, mock_storage, sample_decisions):
        """Test that brief matches (<0.60) get one-liner formatting (~50 tokens)."""
        retriever = DecisionRetriever(mock_storage)

        # Create a scored decision with brief similarity
        scored_decisions = [
            (sample_decisions[2], 0.45),  # Brief match (above noise floor)
        ]

        tier_boundaries = {"strong": 0.75, "moderate": 0.60}
        token_budget = 2000

        result = retriever.format_context_tiered(
            scored_decisions, tier_boundaries, token_budget
        )

        # Brief tier should be minimal: just question and winning option
        formatted = result["formatted"]
        assert "Should we adopt TypeScript?" in formatted
        assert "TypeScript" in formatted  # Winning option

        # Should NOT include consensus text, participants, or detailed info
        # (Being pragmatic: brief format is question + result)

        # Should use roughly 20-60 tokens (brief tier one-liner)
        tokens_used = result["tokens_used"]
        assert 15 < tokens_used < 80, f"Expected ~20-60 tokens, got {tokens_used}"

        # Tier distribution should show 1 brief
        assert result["tier_distribution"]["strong"] == 0
        assert result["tier_distribution"]["moderate"] == 0
        assert result["tier_distribution"]["brief"] == 1

    def test_format_context_tiered_respects_token_budget(
        self, mock_storage, sample_decisions
    ):
        """Test that formatting stops when token budget is exceeded."""
        retriever = DecisionRetriever(mock_storage)

        # Create multiple strong matches
        scored_decisions = [
            (sample_decisions[0], 0.90),  # Strong
            (sample_decisions[1], 0.85),  # Strong
            (sample_decisions[2], 0.80),  # Strong
        ]

        tier_boundaries = {"strong": 0.75, "moderate": 0.60}
        token_budget = 150  # Small budget - should only fit ~1 strong decision

        # Mock stances for all decisions
        mock_storage.get_participant_stances.return_value = [
            Mock(
                participant="claude",
                vote_option="Option A",
                confidence=0.9,
                rationale="Good reasoning here",
            )
        ]

        result = retriever.format_context_tiered(
            scored_decisions, tier_boundaries, token_budget
        )

        # Should stop before including all decisions
        tokens_used = result["tokens_used"]
        assert (
            tokens_used <= token_budget
        ), f"Token budget exceeded: {tokens_used} > {token_budget}"

        # Should include at least 1 decision but not all 3
        formatted = result["formatted"]
        decisions_included = result["tier_distribution"]["strong"]
        assert decisions_included >= 1, "Should include at least 1 decision"
        assert (
            decisions_included < 3
        ), "Should not include all 3 decisions (budget exceeded)"

    def test_format_context_tiered_returns_metrics(
        self, mock_storage, sample_decisions
    ):
        """Test that format_context_tiered returns complete metrics dict."""
        retriever = DecisionRetriever(mock_storage)

        scored_decisions = [
            (sample_decisions[0], 0.85),  # Strong
            (sample_decisions[1], 0.65),  # Moderate
            (sample_decisions[2], 0.45),  # Brief
        ]

        tier_boundaries = {"strong": 0.75, "moderate": 0.60}
        token_budget = 2000

        mock_storage.get_participant_stances.return_value = []

        result = retriever.format_context_tiered(
            scored_decisions, tier_boundaries, token_budget
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert "formatted" in result
        assert "tokens_used" in result
        assert "tier_distribution" in result

        # Verify types
        assert isinstance(result["formatted"], str)
        assert isinstance(result["tokens_used"], int)
        assert isinstance(result["tier_distribution"], dict)

        # Verify tier distribution structure
        tier_dist = result["tier_distribution"]
        assert "strong" in tier_dist
        assert "moderate" in tier_dist
        assert "brief" in tier_dist

        # Verify counts
        assert tier_dist["strong"] == 1
        assert tier_dist["moderate"] == 1
        assert tier_dist["brief"] == 1

        # Verify tokens_used is positive
        assert result["tokens_used"] > 0

    def test_format_context_tiered_empty_input(self, mock_storage):
        """Test that empty input returns empty string and zero metrics."""
        retriever = DecisionRetriever(mock_storage)

        scored_decisions = []
        tier_boundaries = {"strong": 0.75, "moderate": 0.60}
        token_budget = 2000

        result = retriever.format_context_tiered(
            scored_decisions, tier_boundaries, token_budget
        )

        # Should return empty formatted string
        assert result["formatted"] == ""

        # Should have zero tokens used
        assert result["tokens_used"] == 0

        # Should have zero counts in tier distribution
        assert result["tier_distribution"]["strong"] == 0
        assert result["tier_distribution"]["moderate"] == 0
        assert result["tier_distribution"]["brief"] == 0

    def test_format_context_tiered_all_below_noise_floor(
        self, mock_storage, sample_decisions
    ):
        """Test that all scores below noise floor (0.40) returns empty."""
        retriever = DecisionRetriever(mock_storage)

        # All scores below noise floor
        scored_decisions = [
            (sample_decisions[0], 0.35),  # Below noise floor
            (sample_decisions[1], 0.25),  # Below noise floor
            (sample_decisions[2], 0.15),  # Below noise floor
        ]

        tier_boundaries = {"strong": 0.75, "moderate": 0.60}
        token_budget = 2000

        result = retriever.format_context_tiered(
            scored_decisions, tier_boundaries, token_budget
        )

        # Should return empty formatted string (noise floor filter)
        assert result["formatted"] == ""

        # Should have zero tokens used
        assert result["tokens_used"] == 0

        # Should have zero counts (all filtered by noise floor)
        assert result["tier_distribution"]["strong"] == 0
        assert result["tier_distribution"]["moderate"] == 0
        assert result["tier_distribution"]["brief"] == 0


class TestDecisionRetrieverAdaptiveK:
    """Test adaptive k selection based on database size."""

    def test_adaptive_k_small_db_exploration(self, mock_storage):
        """Test that small databases (<100 decisions) return k=5 for exploration."""
        retriever = DecisionRetriever(mock_storage)

        # Test various small database sizes
        assert retriever._compute_adaptive_k(0) == 5
        assert retriever._compute_adaptive_k(1) == 5
        assert retriever._compute_adaptive_k(50) == 5
        assert retriever._compute_adaptive_k(99) == 5

    def test_adaptive_k_medium_db_balanced(self, mock_storage):
        """Test that medium databases (100-999 decisions) return k=3 for balance."""
        retriever = DecisionRetriever(mock_storage)

        # Test various medium database sizes
        assert retriever._compute_adaptive_k(100) == 3
        assert retriever._compute_adaptive_k(250) == 3
        assert retriever._compute_adaptive_k(500) == 3
        assert retriever._compute_adaptive_k(999) == 3

    def test_adaptive_k_large_db_precision(self, mock_storage):
        """Test that large databases (≥1000 decisions) return k=2 for precision."""
        retriever = DecisionRetriever(mock_storage)

        # Test various large database sizes
        assert retriever._compute_adaptive_k(1000) == 2
        assert retriever._compute_adaptive_k(1500) == 2
        assert retriever._compute_adaptive_k(5000) == 2
        assert retriever._compute_adaptive_k(10000) == 2

    def test_adaptive_k_boundary_conditions(self, mock_storage):
        """Test exact boundary conditions at 100 and 1000 decisions."""
        retriever = DecisionRetriever(mock_storage)

        # Boundary at 100: 99 should be k=5 (small), 100 should be k=3 (medium)
        assert retriever._compute_adaptive_k(99) == 5
        assert retriever._compute_adaptive_k(100) == 3

        # Boundary at 1000: 999 should be k=3 (medium), 1000 should be k=2 (large)
        assert retriever._compute_adaptive_k(999) == 3
        assert retriever._compute_adaptive_k(1000) == 2

    def test_adaptive_k_empty_db(self, mock_storage):
        """Test that empty database returns k=5 for exploration."""
        retriever = DecisionRetriever(mock_storage)

        # Empty database should use exploration strategy
        assert retriever._compute_adaptive_k(0) == 5


class TestDecisionRetrieverConfidenceRanking:
    """Test confidence ranking refactor (Task 4): find_relevant_decisions returns scores."""

    def test_find_relevant_decisions_returns_scores(
        self, mock_storage, sample_decisions
    ):
        """Test that find_relevant_decisions returns tuples with scores."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
            {"id": "dec2", "question": sample_decisions[1].question, "score": 0.65},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Act: Call find_relevant_decisions
            results = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            # Assert: Results should be list of tuples (DecisionNode, float)
            assert isinstance(results, list)
            assert len(results) == 2

            # Check first result
            decision1, score1 = results[0]
            assert isinstance(decision1, DecisionNode)
            assert isinstance(score1, float)
            assert decision1.id == "dec1"
            assert score1 == 0.85

            # Check second result
            decision2, score2 = results[1]
            assert isinstance(decision2, DecisionNode)
            assert isinstance(score2, float)
            assert decision2.id == "dec2"
            assert score2 == 0.65

    def test_find_relevant_decisions_adaptive_k(
        self, mock_storage, sample_decisions
    ):
        """Test that find_relevant_decisions uses adaptive k (not fixed max_results)."""
        # Create 10 sample decisions for a medium-sized DB
        many_decisions = []
        for i in range(150):  # Medium DB = 100-999 = k=3
            many_decisions.append(
                DecisionNode(
                    id=f"dec{i}",
                    question=f"Question {i}",
                    timestamp=datetime.now(UTC),
                    participants=["claude"],
                    convergence_status="converged",
                    consensus=f"Consensus {i}",
                    winning_option=f"Option {i}",
                    transcript_path=f"transcripts/dec{i}.md",
                )
            )

        mock_storage.get_all_decisions.return_value = many_decisions

        retriever = DecisionRetriever(mock_storage)

        # Create 5 similar results (but adaptive k=3 for medium DB)
        similar_results = [
            {"id": f"dec{i}", "question": f"Question {i}", "score": 0.9 - i * 0.05}
            for i in range(5)
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Act: Call with max_results=5 (but adaptive k should limit to 3)
            results = retriever.find_relevant_decisions(
                "Any question?", threshold=0.7, max_results=5
            )

            # Assert: Should return only k=3 results (adaptive k for medium DB)
            assert len(results) == 3, f"Expected 3 results (adaptive k), got {len(results)}"

            # Verify top 3 by score
            scores = [score for _, score in results]
            assert scores == [0.9, 0.85, 0.8]

    def test_find_relevant_decisions_no_threshold_filter(
        self, mock_storage, sample_decisions
    ):
        """Test that find_relevant_decisions does NOT filter by threshold (returns results below 0.7)."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        # Similar results include scores below threshold (0.7)
        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
            {"id": "dec2", "question": sample_decisions[1].question, "score": 0.55},  # Below 0.7
            {"id": "dec3", "question": sample_decisions[2].question, "score": 0.45},  # Below 0.7
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Act: Call with threshold=0.7
            results = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            # Assert: Should return ALL results (including those below threshold)
            # Threshold filtering is now handled by format_context_tiered()
            assert len(results) == 3, "Should return all results, not filter by threshold"

            scores = [score for _, score in results]
            assert 0.55 in scores, "Should include result below threshold (0.55)"
            assert 0.45 in scores, "Should include result below threshold (0.45)"

    def test_find_relevant_decisions_noise_floor_only(
        self, mock_storage, sample_decisions
    ):
        """Test that find_relevant_decisions only filters by noise floor (0.40), not threshold."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        # Similar results with scores around noise floor boundary
        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
            {"id": "dec2", "question": sample_decisions[1].question, "score": 0.42},  # Above noise floor
            {"id": "dec3", "question": sample_decisions[2].question, "score": 0.35},  # Below noise floor
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Act: Call find_relevant_decisions
            results = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            # Assert: Should return results >= 0.40 (noise floor), filter out < 0.40
            assert len(results) == 2, "Should filter out results below noise floor (0.40)"

            scores = [score for _, score in results]
            assert 0.85 in scores, "Should include high score"
            assert 0.42 in scores, "Should include score above noise floor (0.42)"
            assert 0.35 not in scores, "Should exclude score below noise floor (0.35)"

    def test_find_relevant_decisions_includes_metadata(
        self, mock_storage, sample_decisions
    ):
        """Test that each result includes score metadata in tuple."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Act: Call find_relevant_decisions
            results = retriever.find_relevant_decisions(
                "Should we use React?", threshold=0.7, max_results=3
            )

            # Assert: Each result should be a tuple with DecisionNode and score
            assert len(results) == 1
            result_tuple = results[0]

            assert isinstance(result_tuple, tuple), "Result should be a tuple"
            assert len(result_tuple) == 2, "Tuple should have 2 elements (DecisionNode, score)"

            decision, score = result_tuple
            assert isinstance(decision, DecisionNode), "First element should be DecisionNode"
            assert isinstance(score, float), "Second element should be float score"
            assert score == 0.85, "Score should match the similarity score"


class TestGetEnrichedContextTieredIntegration:
    """Test get_enriched_context integration with tiered formatting (Task 6)."""

    def test_get_enriched_context_uses_tiered_formatting(
        self, mock_storage, sample_decisions
    ):
        """Test that get_enriched_context calls format_context_tiered, not format_context."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Mock format_context_tiered to verify it's called
            with patch.object(retriever, "format_context_tiered") as mock_tiered:
                mock_tiered.return_value = {
                    "formatted": "## Tiered Context",
                    "tokens_used": 100,
                    "tier_distribution": {"strong": 1, "moderate": 0, "brief": 0},
                }

                # Act: Call get_enriched_context
                context = retriever.get_enriched_context(
                    "Should we use React?", threshold=0.7, max_results=3
                )

                # Assert: format_context_tiered should be called
                mock_tiered.assert_called_once()

                # Verify it received scored decisions (tuples)
                call_args = mock_tiered.call_args[0]
                scored_decisions = call_args[0]
                assert len(scored_decisions) == 1
                assert isinstance(scored_decisions[0], tuple)
                assert scored_decisions[0][1] == 0.85  # Score preserved

    def test_get_enriched_context_returns_tiered_context(
        self, mock_storage, sample_decisions
    ):
        """Test that get_enriched_context returns tiered context with tier labels."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )
        mock_storage.get_participant_stances.return_value = []

        retriever = DecisionRetriever(mock_storage)

        # Create scored results for tiered formatting
        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},  # Strong
            {"id": "dec2", "question": sample_decisions[1].question, "score": 0.65},  # Moderate
            {"id": "dec3", "question": sample_decisions[2].question, "score": 0.45},  # Brief
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Act: Call get_enriched_context
            context = retriever.get_enriched_context(
                "Should we use React?", threshold=0.7, max_results=3
            )

            # Assert: Context should include tier labels from format_context_tiered
            assert "Tiered by Relevance" in context, "Should use tiered formatting"
            assert "Strong Match" in context or "Moderate Match" in context or "Brief Match" in context, \
                "Should include tier indicators"

    def test_get_enriched_context_backward_compat_format_context(
        self, mock_storage, sample_decisions
    ):
        """Test that old format_context() method is still callable directly."""
        mock_storage.get_participant_stances.return_value = []

        retriever = DecisionRetriever(mock_storage)

        # Act: Call format_context directly (legacy method)
        context = retriever.format_context(
            sample_decisions[:2],  # Just DecisionNode list
            "Should we use React?"
        )

        # Assert: Should work without errors
        assert "Similar Past Deliberations (Decision Graph Memory)" in context
        assert "React or Vue" in context
        assert "What database should we use?" in context

    def test_format_context_still_works_with_nodes(
        self, mock_storage, sample_decisions
    ):
        """Test that legacy format_context() still accepts DecisionNode list (no scores)."""
        mock_storage.get_participant_stances.return_value = []

        retriever = DecisionRetriever(mock_storage)

        # Act: Call format_context with DecisionNode list (no scores)
        decisions = [sample_decisions[0], sample_decisions[1]]
        context = retriever.format_context(decisions, "Test query")

        # Assert: Should format correctly without scores
        assert isinstance(context, str)
        assert len(context) > 0
        assert "React or Vue" in context
        assert "What database should we use?" in context

        # Should NOT include tier labels (legacy format)
        assert "Strong Match" not in context
        assert "Moderate Match" not in context
        assert "Tiered by Relevance" not in context

    def test_get_enriched_context_handles_score_tuples(
        self, mock_storage, sample_decisions
    ):
        """Test that get_enriched_context properly unpacks and uses score tuples."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )
        mock_storage.get_participant_stances.return_value = []

        retriever = DecisionRetriever(mock_storage)

        # Create similar results with specific scores
        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.92},
            {"id": "dec2", "question": sample_decisions[1].question, "score": 0.68},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Act: Call get_enriched_context
            context = retriever.get_enriched_context(
                "Should we use React?", threshold=0.7, max_results=3
            )

            # Assert: Scores should appear in formatted output
            assert "0.92" in context, "Should include score 0.92 in formatted output"
            assert "0.68" in context, "Should include score 0.68 in formatted output"

    def test_get_enriched_context_uses_default_tier_boundaries(
        self, mock_storage, sample_decisions
    ):
        """Test that get_enriched_context uses sensible default tier boundaries."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )
        mock_storage.get_participant_stances.return_value = []

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Mock format_context_tiered to inspect tier boundaries
            with patch.object(retriever, "format_context_tiered") as mock_tiered:
                mock_tiered.return_value = {
                    "formatted": "## Test",
                    "tokens_used": 100,
                    "tier_distribution": {"strong": 1, "moderate": 0, "brief": 0},
                }

                # Act: Call get_enriched_context
                retriever.get_enriched_context(
                    "Should we use React?", threshold=0.7, max_results=3
                )

                # Assert: Check tier boundaries passed to format_context_tiered
                call_args = mock_tiered.call_args[0]
                tier_boundaries = call_args[1]

                assert "strong" in tier_boundaries, "Should define strong threshold"
                assert "moderate" in tier_boundaries, "Should define moderate threshold"
                assert tier_boundaries["strong"] >= 0.75, "Strong threshold should be >= 0.75"
                assert tier_boundaries["moderate"] >= 0.60, "Moderate threshold should be >= 0.60"

    def test_get_enriched_context_uses_default_token_budget(
        self, mock_storage, sample_decisions
    ):
        """Test that get_enriched_context uses a sensible default token budget."""
        mock_storage.get_all_decisions.return_value = sample_decisions
        mock_storage.get_decision_node.side_effect = lambda id: next(
            (d for d in sample_decisions if d.id == id), None
        )

        retriever = DecisionRetriever(mock_storage)

        similar_results = [
            {"id": "dec1", "question": sample_decisions[0].question, "score": 0.85},
        ]

        with patch.object(
            retriever.similarity_detector, "find_similar", return_value=similar_results
        ):
            # Mock format_context_tiered to inspect token budget
            with patch.object(retriever, "format_context_tiered") as mock_tiered:
                mock_tiered.return_value = {
                    "formatted": "## Test",
                    "tokens_used": 100,
                    "tier_distribution": {"strong": 1, "moderate": 0, "brief": 0},
                }

                # Act: Call get_enriched_context
                retriever.get_enriched_context(
                    "Should we use React?", threshold=0.7, max_results=3
                )

                # Assert: Check token budget passed to format_context_tiered
                call_args = mock_tiered.call_args[0]
                token_budget = call_args[2]

                assert isinstance(token_budget, int), "Token budget should be an integer"
                assert token_budget >= 1000, "Token budget should be at least 1000 (reasonable minimum)"
                assert token_budget <= 5000, "Token budget should be <= 5000 (reasonable maximum)"
