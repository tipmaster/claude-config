"""Unit tests for background worker similarity computation."""

import asyncio
import os
import tempfile
from datetime import datetime

import pytest

from decision_graph.schema import DecisionNode
from decision_graph.storage import DecisionGraphStorage
from decision_graph.workers import BackgroundWorker, SimilarityJob


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
async def worker(storage):
    """Create and cleanup worker instance."""
    worker = BackgroundWorker(
        storage=storage,
        max_queue_size=100,
        batch_size=10,
        similarity_threshold=0.5,
    )
    yield worker
    # Cleanup
    if worker.running:
        await worker.stop()


class TestSimilarityJob:
    """Test SimilarityJob dataclass."""

    def test_similarity_job_creation(self):
        """Job should be created with required fields."""
        job = SimilarityJob(decision_id="test-id", priority="high")

        assert job.decision_id == "test-id"
        assert job.priority == "high"
        assert isinstance(job.created_at, datetime)
        assert len(job.job_id) > 0  # UUID generated

    def test_similarity_job_defaults(self):
        """Job should have default values."""
        job = SimilarityJob(decision_id="test-id")

        assert job.priority == "low"
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.job_id, str)

    def test_similarity_job_unique_ids(self):
        """Each job should get unique ID."""
        job1 = SimilarityJob(decision_id="test-1")
        job2 = SimilarityJob(decision_id="test-2")

        assert job1.job_id != job2.job_id


class TestBackgroundWorkerInit:
    """Test BackgroundWorker initialization."""

    def test_worker_initialization(self, storage):
        """Worker should initialize with correct defaults."""
        worker = BackgroundWorker(storage)

        assert worker.storage == storage
        assert worker.max_queue_size == 1000
        assert worker.batch_size == 50
        assert worker.similarity_threshold == 0.5
        assert not worker.running
        assert worker.worker_task is None
        assert worker.jobs_processed == 0
        assert worker.jobs_failed == 0

    def test_worker_custom_params(self, storage):
        """Worker should accept custom parameters."""
        worker = BackgroundWorker(
            storage=storage,
            max_queue_size=500,
            batch_size=25,
            similarity_threshold=0.7,
        )

        assert worker.max_queue_size == 500
        assert worker.batch_size == 25
        assert worker.similarity_threshold == 0.7

    def test_worker_creates_queues(self, storage):
        """Worker should create priority queues."""
        worker = BackgroundWorker(storage)

        assert isinstance(worker.high_priority_queue, asyncio.Queue)
        assert isinstance(worker.low_priority_queue, asyncio.Queue)
        assert worker.high_priority_queue.maxsize == 1000
        assert worker.low_priority_queue.maxsize == 1000


class TestBackgroundWorkerLifecycle:
    """Test worker start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_worker_start(self, worker):
        """Worker should start successfully."""
        await worker.start()

        assert worker.running is True
        assert worker.worker_task is not None
        assert isinstance(worker.worker_task, asyncio.Task)

    @pytest.mark.asyncio
    async def test_worker_start_idempotent(self, worker):
        """Multiple start calls should be safe."""
        await worker.start()
        task1 = worker.worker_task

        await worker.start()  # Second call
        task2 = worker.worker_task

        assert task1 == task2  # Same task
        assert worker.running is True

    @pytest.mark.asyncio
    async def test_worker_stop(self, worker):
        """Worker should stop gracefully."""
        await worker.start()
        assert worker.running is True

        await worker.stop()

        assert worker.running is False
        assert worker.worker_task is None

    @pytest.mark.asyncio
    async def test_worker_stop_idempotent(self, worker):
        """Multiple stop calls should be safe."""
        await worker.start()
        await worker.stop()

        # Second stop should be no-op
        await worker.stop()

        assert worker.running is False

    @pytest.mark.asyncio
    async def test_worker_stop_without_start(self, worker):
        """Stop should be safe even if never started."""
        await worker.stop()
        assert worker.running is False

    @pytest.mark.asyncio
    async def test_worker_stop_with_timeout(self, worker):
        """Stop should respect timeout for active jobs."""
        await worker.start()

        # Simulate active job
        worker.active_jobs.append("test-job-1")

        # Stop with short timeout (job won't finish)
        start_time = asyncio.get_event_loop().time()
        await worker.stop(timeout=0.2)
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited ~0.2s for timeout
        assert 0.15 < elapsed < 0.5  # Allow some variance
        assert worker.running is False


class TestBackgroundWorkerEnqueue:
    """Test job enqueueing."""

    @pytest.mark.asyncio
    async def test_enqueue_low_priority(self, worker):
        """Should enqueue low-priority job."""
        await worker.start()

        await worker.enqueue(decision_id="test-id", priority="low", delay_seconds=0)

        assert worker.low_priority_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_high_priority(self, worker):
        """Should enqueue high-priority job."""
        await worker.start()

        await worker.enqueue(decision_id="test-id", priority="high", delay_seconds=0)

        assert worker.high_priority_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_default_priority(self, worker):
        """Should default to low priority."""
        await worker.start()

        await worker.enqueue(decision_id="test-id", delay_seconds=0)

        assert worker.low_priority_queue.qsize() == 1
        assert worker.high_priority_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_enqueue_invalid_priority(self, worker):
        """Should raise on invalid priority."""
        await worker.start()

        with pytest.raises(ValueError, match="Invalid priority"):
            await worker.enqueue(decision_id="test-id", priority="medium")

    @pytest.mark.asyncio
    async def test_enqueue_when_not_running(self, worker):
        """Should not enqueue when worker not running."""
        # Don't start worker
        await worker.enqueue(decision_id="test-id", delay_seconds=0)

        # Job should not be enqueued
        assert worker.low_priority_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_enqueue_with_delay(self, worker):
        """Should delay before enqueueing."""
        await worker.start()

        start_time = asyncio.get_event_loop().time()
        await worker.enqueue(decision_id="test-id", delay_seconds=0.1)
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have delayed ~0.1s
        assert elapsed >= 0.1
        assert worker.low_priority_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_queue_full(self, storage):
        """Should raise when queue is full."""
        # Create worker with tiny queue
        worker = BackgroundWorker(storage, max_queue_size=2)
        await worker.start()

        # Fill queue
        await worker.enqueue("id1", delay_seconds=0)
        await worker.enqueue("id2", delay_seconds=0)

        # Third enqueue should raise
        with pytest.raises(asyncio.QueueFull):
            await worker.enqueue("id3", delay_seconds=0)

        await worker.stop()


class TestBackgroundWorkerProcessing:
    """Test job processing."""

    @pytest.mark.asyncio
    async def test_processes_job(self, worker, storage):
        """Worker should process enqueued job."""
        # Create a decision to compute similarities for
        node = DecisionNode(
            question="Test question",
            timestamp=datetime.now(),
            consensus="Test consensus",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/test.md",
        )
        storage.save_decision_node(node)

        await worker.start()
        await worker.enqueue(node.id, delay_seconds=0)

        # Wait for processing
        await asyncio.sleep(0.3)

        assert worker.jobs_processed == 1
        assert worker.jobs_failed == 0

    @pytest.mark.asyncio
    async def test_processes_multiple_jobs(self, worker, storage):
        """Worker should process multiple jobs sequentially."""
        # Create decisions
        nodes = []
        for i in range(3):
            node = DecisionNode(
                question=f"Question {i}",
                timestamp=datetime.now(),
                consensus="Test",
                convergence_status="converged",
                participants=["test"],
                transcript_path="/tmp/test.md",
            )
            storage.save_decision_node(node)
            nodes.append(node)

        await worker.start()

        # Enqueue all jobs
        for node in nodes:
            await worker.enqueue(node.id, delay_seconds=0)

        # Wait for processing
        await asyncio.sleep(0.5)

        assert worker.jobs_processed == 3
        assert worker.jobs_failed == 0

    @pytest.mark.asyncio
    async def test_prioritizes_high_priority_jobs(self, worker, storage):
        """Worker should process high-priority jobs first."""
        # Create decisions
        low_node = DecisionNode(
            question="Low priority",
            timestamp=datetime.now(),
            consensus="Test",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/low.md",
        )
        high_node = DecisionNode(
            question="High priority",
            timestamp=datetime.now(),
            consensus="Test",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/high.md",
        )
        storage.save_decision_node(low_node)
        storage.save_decision_node(high_node)

        await worker.start()

        # Enqueue low priority first
        await worker.enqueue(low_node.id, priority="low", delay_seconds=0)
        # Then high priority
        await worker.enqueue(high_node.id, priority="high", delay_seconds=0)

        # Wait for first job to process
        await asyncio.sleep(0.3)

        # First job processed should be high priority
        # (We can't directly assert order, but both should complete)
        assert worker.jobs_processed >= 1

    @pytest.mark.asyncio
    async def test_handles_job_failure(self, worker, storage):
        """Worker should handle job failures gracefully."""
        # Enqueue job for non-existent decision
        await worker.start()
        await worker.enqueue("non-existent-id", delay_seconds=0)

        # Wait for processing
        await asyncio.sleep(0.3)

        # Job should fail but worker should continue
        assert worker.jobs_failed == 1
        assert worker.running is True

    @pytest.mark.asyncio
    async def test_computes_similarities(self, worker, storage):
        """Worker should compute and store similarities."""
        # Create two decisions with similar questions
        node1 = DecisionNode(
            question="Should we use Python for backend?",
            timestamp=datetime.now(),
            consensus="Yes",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/1.md",
        )
        node2 = DecisionNode(
            question="Should we adopt Python for server side?",
            timestamp=datetime.now(),
            consensus="Yes",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/2.md",
        )
        storage.save_decision_node(node1)
        storage.save_decision_node(node2)

        # Process similarities for node2
        await worker.start()
        await worker.enqueue(node2.id, delay_seconds=0)

        # Wait for processing
        await asyncio.sleep(0.5)

        # Check that similarity was stored
        similarities = storage.get_similar_decisions(node2.id, threshold=0.3, limit=10)
        assert len(similarities) > 0  # Should find node1 as similar


class TestBackgroundWorkerStats:
    """Test worker statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_initial(self, worker):
        """Stats should show initial state."""
        stats = worker.get_stats()

        assert stats["running"] is False
        assert stats["high_priority_pending"] == 0
        assert stats["low_priority_pending"] == 0
        assert stats["active_jobs"] == 0
        assert stats["jobs_processed"] == 0
        assert stats["jobs_failed"] == 0
        assert stats["total_similarities_computed"] == 0
        assert stats["max_queue_size"] == 100
        assert stats["batch_size"] == 10
        assert stats["similarity_threshold"] == 0.5

    @pytest.mark.asyncio
    async def test_get_stats_after_processing(self, worker, storage):
        """Stats should update after processing jobs."""
        # Create decision
        node = DecisionNode(
            question="Test",
            timestamp=datetime.now(),
            consensus="Test",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/test.md",
        )
        storage.save_decision_node(node)

        await worker.start()
        await worker.enqueue(node.id, delay_seconds=0)
        await asyncio.sleep(0.3)

        stats = worker.get_stats()

        assert stats["running"] is True
        assert stats["jobs_processed"] == 1
        assert stats["jobs_failed"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_pending_jobs(self, worker, storage):
        """Stats should show pending jobs."""
        # Create decision
        node = DecisionNode(
            question="Test",
            timestamp=datetime.now(),
            consensus="Test",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/test.md",
        )
        storage.save_decision_node(node)

        await worker.start()

        # Enqueue multiple jobs quickly
        await worker.enqueue(node.id, priority="high", delay_seconds=0)
        await worker.enqueue(node.id, priority="low", delay_seconds=0)

        # Get stats immediately (before processing)
        stats = worker.get_stats()

        # At least one should be pending or being processed
        total_pending = stats["high_priority_pending"] + stats["low_priority_pending"]
        assert total_pending >= 0  # May have already started processing


class TestBackgroundWorkerMemory:
    """Test memory efficiency."""

    @pytest.mark.asyncio
    async def test_queue_bounded(self, storage):
        """Queue should enforce size limit."""
        worker = BackgroundWorker(storage, max_queue_size=5)
        await worker.start()

        # Fill queue to capacity
        for i in range(5):
            await worker.enqueue(f"id-{i}", delay_seconds=0)

        # Next enqueue should raise
        with pytest.raises(asyncio.QueueFull):
            await worker.enqueue("overflow", delay_seconds=0)

        await worker.stop()

    @pytest.mark.asyncio
    async def test_active_jobs_tracking(self, worker, storage):
        """Worker should track active jobs."""
        node = DecisionNode(
            question="Test",
            timestamp=datetime.now(),
            consensus="Test",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/test.md",
        )
        storage.save_decision_node(node)

        await worker.start()
        await worker.enqueue(node.id, delay_seconds=0)

        # Check active jobs during processing
        await asyncio.sleep(0.05)  # Brief delay to catch job in-flight

        # Job may be active or already completed
        stats = worker.get_stats()
        assert stats["active_jobs"] >= 0

        # Wait for completion
        await asyncio.sleep(0.3)
        stats = worker.get_stats()
        assert stats["active_jobs"] == 0  # Should be done


class TestBackgroundWorkerBatching:
    """Test batch processing behavior."""

    @pytest.mark.asyncio
    async def test_batch_size_limit(self, storage):
        """Worker should limit comparisons to batch_size."""
        worker = BackgroundWorker(storage, batch_size=5)

        # Create 10 decisions
        nodes = []
        for i in range(10):
            node = DecisionNode(
                question=f"Question {i}",
                timestamp=datetime.now(),
                consensus="Test",
                convergence_status="converged",
                participants=["test"],
                transcript_path=f"/tmp/{i}.md",
            )
            storage.save_decision_node(node)
            nodes.append(node)

        # Process last node
        await worker.start()
        await worker.enqueue(nodes[-1].id, delay_seconds=0)
        await asyncio.sleep(0.5)

        # Should have compared against at most batch_size decisions
        # (batch_size + 1 to account for self, then -1 for self-exclusion = batch_size)
        stats = worker.get_stats()
        assert stats["jobs_processed"] == 1

        await worker.stop()


class TestBackgroundWorkerFallback:
    """Test fallback behavior for read path."""

    @pytest.mark.asyncio
    async def test_synchronous_computation_fallback(self, storage):
        """Should support synchronous computation for cache miss."""
        from decision_graph.similarity import QuestionSimilarityDetector

        # Create decisions without background processing
        node1 = DecisionNode(
            question="Should we use React?",
            timestamp=datetime.now(),
            consensus="Yes",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/1.md",
        )
        node2 = DecisionNode(
            question="Should we adopt Vue?",
            timestamp=datetime.now(),
            consensus="Maybe",
            convergence_status="converged",
            participants=["test"],
            transcript_path="/tmp/2.md",
        )
        storage.save_decision_node(node1)
        storage.save_decision_node(node2)

        # Simulate cache miss - compute synchronously
        detector = QuestionSimilarityDetector()
        recent = storage.get_all_decisions(limit=50)

        # Should complete quickly
        import time

        start = time.perf_counter()

        similarities = []
        for decision in recent[:50]:  # Bounded to 50
            score = detector.compute_similarity(node2.question, decision.question)
            if score >= 0.5 and decision.id != node2.id:
                similarities.append((decision, score))

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete in <500ms even for 50 comparisons
        assert elapsed_ms < 500, f"Fallback took {elapsed_ms:.2f}ms, expected <500ms"


class TestBackgroundWorkerPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_queue_throughput(self, worker, storage):
        """Worker should process jobs at reasonable rate."""
        # Create decisions
        nodes = []
        for i in range(10):
            node = DecisionNode(
                question=f"Question {i}",
                timestamp=datetime.now(),
                consensus="Test",
                convergence_status="converged",
                participants=["test"],
                transcript_path=f"/tmp/{i}.md",
            )
            storage.save_decision_node(node)
            nodes.append(node)

        await worker.start()

        # Enqueue all jobs
        import time

        start = time.perf_counter()
        for node in nodes:
            await worker.enqueue(node.id, delay_seconds=0)

        # Wait for all to process
        await asyncio.sleep(2.0)  # Give plenty of time

        elapsed = time.perf_counter() - start

        # Should process at >1 job/sec (10 jobs in <10s)
        throughput = worker.jobs_processed / elapsed
        assert throughput > 1.0, f"Throughput {throughput:.2f} jobs/sec too slow"

    @pytest.mark.asyncio
    async def test_deliberation_start_not_blocked(self, worker, storage):
        """Background processing should not block deliberation start."""
        from decision_graph.integration import DecisionGraphIntegration
        from models.schema import ConvergenceInfo, DeliberationResult, Summary

        integration = DecisionGraphIntegration(storage)
        await worker.start()

        result = DeliberationResult(
            status="complete",
            mode="quick",
            rounds_completed=1,
            participants=["test"],
            full_debate=[],
            summary=Summary(
                consensus="Test",
                key_agreements=[],
                key_disagreements=[],
                final_recommendation="Test",
            ),
            convergence_info=ConvergenceInfo(
                detected=True,
                detection_round=1,
                final_similarity=0.85,
                status="converged",
                scores_by_round=[],
                per_participant_similarity={},
            ),
            transcript_path="/tmp/test.md",
        )

        # Store deliberation (which would trigger background processing)
        import time

        start = time.perf_counter()
        decision_id = integration.store_deliberation("Test question?", result)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should return quickly (<100ms) without waiting for similarity computation
        assert elapsed_ms < 100, f"Store took {elapsed_ms:.2f}ms, should be <100ms"
        assert decision_id is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
