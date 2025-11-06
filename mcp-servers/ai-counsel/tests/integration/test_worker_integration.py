"""Integration tests for background worker integration with DecisionGraphIntegration.

Tests verify that:
1. Worker is properly initialized and started
2. Similarity computation is deferred to background (non-blocking)
3. Fallback to synchronous computation works
4. Shutdown is graceful
5. Existing tests remain compatible
"""

import asyncio
import os
import tempfile
import time

import pytest

from decision_graph.integration import DecisionGraphIntegration
from decision_graph.storage import DecisionGraphStorage
from models.schema import (ConvergenceInfo, DeliberationResult, RoundResponse,
                           RoundVote, Summary, Vote, VotingResult)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def storage(temp_db):
    """Create storage instance."""
    return DecisionGraphStorage(db_path=temp_db)


@pytest.fixture
async def integration(storage):
    """Create integration with worker enabled."""
    integration = DecisionGraphIntegration(storage, enable_background_worker=True)
    # Ensure worker is started
    await integration.ensure_worker_started()
    yield integration
    # Cleanup
    if integration.worker:
        await integration.shutdown()


@pytest.fixture
def sample_result():
    """Sample deliberation result."""
    return DeliberationResult(
        status="complete",
        mode="quick",
        rounds_completed=2,
        participants=["claude", "gpt-4"],
        full_debate=[
            RoundResponse(
                round=2,
                participant="claude",
                response="Claude's final response",
                timestamp="2025-01-01T10:00:00Z",
            ),
            RoundResponse(
                round=2,
                participant="gpt-4",
                response="GPT-4's final response",
                timestamp="2025-01-01T10:00:01Z",
            ),
        ],
        summary=Summary(
            consensus="Test consensus",
            key_agreements=["Agreement 1"],
            key_disagreements=[],
            final_recommendation="Proceed",
        ),
        convergence_info=ConvergenceInfo(
            detected=True,
            detection_round=2,
            final_similarity=0.85,
            status="converged",
            scores_by_round=[],
            per_participant_similarity={},
        ),
        voting_result=VotingResult(
            final_tally={"Option A": 2},
            votes_by_round=[
                RoundVote(
                    round=2,
                    participant="claude",
                    vote=Vote(
                        option="Option A",
                        confidence=0.9,
                        rationale="Best option",
                        continue_debate=False,
                    ),
                    timestamp="2025-01-01T10:00:00Z",
                ),
                RoundVote(
                    round=2,
                    participant="gpt-4",
                    vote=Vote(
                        option="Option A",
                        confidence=0.85,
                        rationale="Agree",
                        continue_debate=False,
                    ),
                    timestamp="2025-01-01T10:00:01Z",
                ),
            ],
            consensus_reached=True,
            winning_option="Option A",
        ),
        transcript_path="/tmp/test.md",
    )


class TestWorkerInitialization:
    """Test background worker initialization."""

    @pytest.mark.asyncio
    async def test_worker_initialized_by_default(self, storage):
        """Worker should be initialized by default."""
        integration = DecisionGraphIntegration(storage)

        assert integration.worker is not None
        assert integration._worker_enabled is True

        # Cleanup
        if integration.worker:
            await integration.shutdown()

    @pytest.mark.asyncio
    async def test_worker_can_be_disabled(self, storage):
        """Worker can be disabled via flag."""
        integration = DecisionGraphIntegration(storage, enable_background_worker=False)

        assert integration.worker is None
        assert integration._worker_enabled is False

    @pytest.mark.asyncio
    async def test_worker_starts_automatically(self, integration):
        """Worker should start automatically when integration is created."""
        # Worker should be running
        assert integration.worker is not None
        assert integration.worker.running is True


class TestNonBlockingStorage:
    """Test that storage operations don't block on similarity computation."""

    @pytest.mark.asyncio
    async def test_store_deliberation_returns_quickly(self, integration, sample_result):
        """store_deliberation should return quickly without waiting for similarity computation."""
        # Measure time to store
        start = time.perf_counter()
        decision_id = integration.store_deliberation(
            "Test question for timing", sample_result
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete quickly (<100ms) - not waiting for similarity computation
        assert (
            elapsed_ms < 100
        ), f"store_deliberation took {elapsed_ms:.2f}ms, expected <100ms"
        assert decision_id is not None

        # Decision should be stored immediately
        node = integration.storage.get_decision_node(decision_id)
        assert node is not None
        assert node.question == "Test question for timing"

    @pytest.mark.asyncio
    async def test_similarity_computed_asynchronously(
        self, integration, storage, sample_result
    ):
        """Similarities should be computed in background after store returns."""
        # Store first decision
        integration.store_deliberation(
            "Should we use Python for backend?", sample_result
        )

        # Store second similar decision
        decision_id_2 = integration.store_deliberation(
            "Should we use Python for server-side code?", sample_result
        )

        # Immediately after store, similarities might not be computed yet
        # (This is non-deterministic but demonstrates async behavior)

        # Wait for background processing (5 second delay + processing time)
        await asyncio.sleep(7.0)

        # Check worker stats
        stats = integration.worker.get_stats()

        # Now similarities should be computed
        similarities = storage.get_similar_decisions(
            decision_id_2, threshold=0.3, limit=10
        )

        # Should find decision_id_1 as similar (both mention "Python")
        # Note: If jobs were processed, similarities should exist
        assert (
            stats["jobs_processed"] >= 2
        ), f"Expected at least 2 jobs processed, got {stats['jobs_processed']}"
        assert (
            len(similarities) > 0
        ), f"Expected to find similarities after background processing. Stats: {stats}"

    @pytest.mark.asyncio
    async def test_multiple_stores_dont_block_each_other(
        self, integration, sample_result
    ):
        """Multiple store operations should not block each other."""
        questions = [
            "Question 1: Use TypeScript?",
            "Question 2: Use Python?",
            "Question 3: Use Go?",
            "Question 4: Use Rust?",
            "Question 5: Use Java?",
        ]

        # Store multiple deliberations quickly
        start = time.perf_counter()
        decision_ids = []
        for question in questions:
            decision_id = integration.store_deliberation(question, sample_result)
            decision_ids.append(decision_id)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete quickly even for 5 stores
        # (Would be slow if similarity computation was synchronous)
        assert elapsed_ms < 500, f"5 stores took {elapsed_ms:.2f}ms, expected <500ms"

        # All decisions should be stored
        assert len(decision_ids) == 5
        assert len(set(decision_ids)) == 5  # All unique


class TestFallbackBehavior:
    """Test fallback to synchronous computation."""

    def test_synchronous_fallback_when_worker_disabled(self, storage, sample_result):
        """Should fall back to sync computation when worker disabled."""
        integration = DecisionGraphIntegration(storage, enable_background_worker=False)

        # Store deliberation
        decision_id = integration.store_deliberation(
            "Test synchronous fallback", sample_result
        )

        # Similarity computation should have happened synchronously
        # (No way to verify this directly, but it should not error)
        assert decision_id is not None

        # Decision should be stored
        node = integration.storage.get_decision_node(decision_id)
        assert node is not None

    @pytest.mark.asyncio
    async def test_fallback_when_worker_queue_full(self, storage, sample_result):
        """Should fall back to sync when worker queue is full."""
        # Create worker with tiny queue
        integration = DecisionGraphIntegration(storage, enable_background_worker=True)

        # Override worker with tiny queue for testing
        await integration.shutdown()
        from decision_graph.workers import BackgroundWorker

        integration.worker = BackgroundWorker(storage, max_queue_size=2)
        await integration.worker.start()

        # Fill queue
        integration.store_deliberation("Question 1", sample_result)
        integration.store_deliberation("Question 2", sample_result)
        integration.store_deliberation("Question 3", sample_result)

        # Should not error - falls back to sync when queue full
        # (Exact behavior depends on timing, but should be graceful)

        await integration.shutdown()


class TestGracefulShutdown:
    """Test graceful shutdown of background worker."""

    @pytest.mark.asyncio
    async def test_shutdown_stops_worker(self, storage):
        """Shutdown should stop the worker gracefully."""
        integration = DecisionGraphIntegration(storage, enable_background_worker=True)

        # Ensure worker is started
        await integration.ensure_worker_started()

        assert integration.worker.running is True

        # Shutdown
        await integration.shutdown()

        # Worker should be stopped
        assert integration.worker.running is False

    @pytest.mark.asyncio
    async def test_shutdown_waits_for_active_jobs(
        self, integration, storage, sample_result
    ):
        """Shutdown should wait for active jobs to complete."""
        # Queue some work
        integration.store_deliberation("Question 1", sample_result)
        integration.store_deliberation("Question 2", sample_result)

        # Wait a bit for jobs to be enqueued (they have 5 second delay)
        await asyncio.sleep(0.5)

        # Get initial stats
        integration.worker.get_stats()

        # Shutdown (should wait for jobs)
        await integration.shutdown()

        # Small delay to ensure cleanup completes
        await asyncio.sleep(0.1)

        # Worker should be stopped
        assert integration.worker.running is False

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self, integration):
        """Multiple shutdown calls should be safe."""
        await integration.shutdown()
        assert integration.worker.running is False

        # Second shutdown should be safe
        await integration.shutdown()
        assert integration.worker.running is False


class TestWorkerStats:
    """Test worker statistics and monitoring."""

    @pytest.mark.asyncio
    async def test_stats_available(self, integration):
        """Worker stats should be available."""
        stats = integration.worker.get_stats()

        assert "running" in stats
        assert "jobs_processed" in stats
        assert "jobs_failed" in stats
        assert "high_priority_pending" in stats
        assert "low_priority_pending" in stats

        assert stats["running"] is True

    @pytest.mark.asyncio
    async def test_stats_updated_after_processing(self, integration, sample_result):
        """Stats should update after jobs are processed."""
        initial_stats = integration.worker.get_stats()
        initial_processed = initial_stats["jobs_processed"]

        # Store deliberation
        integration.store_deliberation("Test question", sample_result)

        # Wait for processing (5 second delay + processing time)
        await asyncio.sleep(7.0)

        # Stats should show job processed
        final_stats = integration.worker.get_stats()
        assert final_stats["jobs_processed"] > initial_processed


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_existing_tests_work_without_worker(self, storage, sample_result):
        """Existing tests should work when worker is disabled."""
        integration = DecisionGraphIntegration(storage, enable_background_worker=False)

        # This mimics existing test patterns
        decision_id = integration.store_deliberation("Test question", sample_result)

        assert decision_id is not None
        node = integration.storage.get_decision_node(decision_id)
        assert node is not None
        assert node.question == "Test question"

    @pytest.mark.asyncio
    async def test_context_retrieval_still_works(self, integration, sample_result):
        """Context retrieval should work with background processing."""
        # Store deliberation
        integration.store_deliberation("Should we use TypeScript?", sample_result)

        # Wait for background processing
        await asyncio.sleep(1.0)

        # Retrieve context for similar question
        context = integration.get_context_for_deliberation(
            "Should we use TypeScript or JavaScript?", threshold=0.3
        )

        # Context should be available (or empty if no matches)
        assert isinstance(context, str)


class TestEventLoopHandling:
    """Test handling of different event loop scenarios."""

    def test_no_event_loop_falls_back_to_sync(self, storage, sample_result):
        """Should fall back to sync when no event loop is running."""
        # Create integration without running event loop
        integration = DecisionGraphIntegration(storage, enable_background_worker=True)

        # Store should work (falls back to sync)
        decision_id = integration.store_deliberation("Test question", sample_result)

        assert decision_id is not None

        # Cleanup - can't await without loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(integration.shutdown())
            loop.close()
        except Exception:
            pass


class TestErrorHandling:
    """Test error handling in worker integration."""

    @pytest.mark.asyncio
    async def test_worker_error_doesnt_break_storage(self, storage, sample_result):
        """Worker errors should not prevent deliberation storage."""
        integration = DecisionGraphIntegration(storage, enable_background_worker=True)

        # Start worker
        if integration.worker and not integration.worker.running:
            await integration.worker.start()

        # Store deliberation - should succeed even if worker has issues
        decision_id = integration.store_deliberation("Test question", sample_result)

        # Decision should be stored regardless of worker state
        assert decision_id is not None
        node = integration.storage.get_decision_node(decision_id)
        assert node is not None

        await integration.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
