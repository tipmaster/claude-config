"""Asynchronous background processing for similarity computation.

This module provides background workers for computing decision similarities
asynchronously after deliberations complete. This keeps deliberation start
times fast by deferring expensive similarity computation to background tasks.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from decision_graph.schema import DecisionSimilarity
from decision_graph.similarity import QuestionSimilarityDetector
from decision_graph.storage import DecisionGraphStorage

if TYPE_CHECKING:
    from models.config import DecisionGraphConfig

logger = logging.getLogger(__name__)


@dataclass
class SimilarityJob:
    """Background job for similarity computation.

    Attributes:
        decision_id: UUID of decision to compute similarities for
        priority: Job priority ("high" or "low")
        created_at: Timestamp when job was created
        job_id: Unique job identifier
    """

    decision_id: str
    priority: str = "low"  # "high" or "low"
    created_at: datetime = field(default_factory=datetime.now)
    job_id: str = field(default_factory=lambda: str(uuid4()))


class BackgroundWorker:
    """Manages async background tasks for similarity computation.

    BackgroundWorker provides:
    - Priority queue for similarity computation jobs
    - Async worker loop for processing jobs
    - Graceful shutdown with pending job handling
    - Batch processing to reduce overhead
    - Memory-bounded queue to prevent runaway growth

    Example:
        >>> storage = DecisionGraphStorage("decisions.db")
        >>> worker = BackgroundWorker(storage, max_queue_size=1000)
        >>> await worker.start()
        >>>
        >>> # After deliberation completes
        >>> await worker.enqueue(decision_id="abc-123", priority="low")
        >>>
        >>> # Later when shutting down
        >>> await worker.stop()
    """

    def __init__(
        self,
        storage: DecisionGraphStorage,
        max_queue_size: int = 1000,
        batch_size: int = 50,
        similarity_threshold: float = 0.5,
        config: Optional["DecisionGraphConfig"] = None,
    ):
        """Initialize background worker.

        Args:
            storage: DecisionGraphStorage instance for database access
            max_queue_size: Maximum number of pending jobs (prevents memory bloat)
            batch_size: Number of recent decisions to compare against per job
            similarity_threshold: Minimum similarity score to store (0.0-1.0)
            config: Optional DecisionGraphConfig to override defaults
        """
        self.storage = storage
        self.config = config

        # Use config values if provided, otherwise use constructor parameters
        if config:
            # Note: Config doesn't have max_queue_size, batch_size, or similarity_threshold yet
            # These remain as constructor parameters for now
            self.max_queue_size = max_queue_size
            self.batch_size = batch_size
            self.similarity_threshold = similarity_threshold
            logger.info(
                f"BackgroundWorker initialized with config-aware setup "
                f"(using constructor params for now)"
            )
        else:
            self.max_queue_size = max_queue_size
            self.batch_size = batch_size
            self.similarity_threshold = similarity_threshold

        # Priority queues
        self.high_priority_queue: asyncio.Queue[SimilarityJob] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self.low_priority_queue: asyncio.Queue[SimilarityJob] = asyncio.Queue(
            maxsize=max_queue_size
        )

        # Worker state
        self.worker_task: Optional[asyncio.Task] = None
        self.running = False
        self.active_jobs: List[str] = []  # Track active job IDs

        # Statistics
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.total_similarities_computed = 0

        # Similarity detector
        self.similarity_detector = QuestionSimilarityDetector()

        logger.info(
            f"Initialized BackgroundWorker (max_queue_size={max_queue_size}, "
            f"batch_size={batch_size}, threshold={similarity_threshold})"
        )

    async def start(self) -> None:
        """Start background worker processing.

        Spawns an async task that processes jobs from the queue until stopped.
        Safe to call multiple times - no-op if already running.
        """
        if self.running:
            logger.warning("BackgroundWorker already running, ignoring start() call")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._process_queue())
        logger.info("BackgroundWorker started")

    async def stop(self, timeout: float = 30.0) -> None:
        """Gracefully shutdown worker.

        Stops accepting new jobs, waits for active jobs to complete,
        and cancels the worker task.

        Args:
            timeout: Maximum time to wait for active jobs to complete (seconds)
        """
        if not self.running:
            logger.warning("BackgroundWorker not running, ignoring stop() call")
            return

        logger.info("Stopping BackgroundWorker...")
        self.running = False

        # Wait for active jobs with timeout
        if self.active_jobs:
            logger.info(
                f"Waiting for {len(self.active_jobs)} active jobs to complete..."
            )
            start_time = asyncio.get_event_loop().time()
            while (
                self.active_jobs
                and (asyncio.get_event_loop().time() - start_time) < timeout
            ):
                await asyncio.sleep(0.1)

            if self.active_jobs:
                logger.warning(
                    f"Timeout reached, {len(self.active_jobs)} jobs still active"
                )

        # Cancel worker task
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None

        # Report pending jobs
        high_pending = self.high_priority_queue.qsize()
        low_pending = self.low_priority_queue.qsize()
        if high_pending + low_pending > 0:
            logger.warning(
                f"BackgroundWorker stopped with {high_pending} high-priority "
                f"and {low_pending} low-priority jobs pending"
            )

        logger.info(
            f"BackgroundWorker stopped (processed={self.jobs_processed}, "
            f"failed={self.jobs_failed})"
        )

    async def enqueue(
        self,
        decision_id: str,
        priority: str = "low",
        delay_seconds: int = 5,
    ) -> None:
        """Queue a similarity computation job.

        Args:
            decision_id: UUID of decision to compute similarities for
            priority: Job priority ("high" or "low")
            delay_seconds: Delay before processing (allows batching)

        Raises:
            asyncio.QueueFull: If queue is at max capacity
            ValueError: If priority is not "high" or "low"
        """
        if priority not in ("high", "low"):
            raise ValueError(f"Invalid priority '{priority}', must be 'high' or 'low'")

        if not self.running:
            logger.warning(
                f"Attempted to enqueue job for {decision_id} but worker not running"
            )
            return

        job = SimilarityJob(
            decision_id=decision_id,
            priority=priority,
            created_at=datetime.now(),
        )

        # Select queue based on priority
        queue = (
            self.high_priority_queue if priority == "high" else self.low_priority_queue
        )

        try:
            # Apply delay to allow batching
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            # Enqueue job (will raise QueueFull if at capacity)
            queue.put_nowait(job)
            logger.debug(
                f"Enqueued {priority}-priority job {job.job_id} for decision {decision_id}"
            )
        except asyncio.QueueFull:
            logger.error(
                f"Queue full ({self.max_queue_size}), cannot enqueue job for {decision_id}"
            )
            raise

    async def _process_queue(self) -> None:
        """Main worker loop - processes queued jobs.

        Continuously processes jobs from priority queues until stopped.
        High-priority jobs are processed before low-priority jobs.
        """
        logger.info("Worker loop started")

        while self.running:
            try:
                # Try high-priority queue first (non-blocking)
                job = None
                try:
                    job = self.high_priority_queue.get_nowait()
                    logger.debug(f"Processing high-priority job {job.job_id}")
                except asyncio.QueueEmpty:
                    pass

                # If no high-priority job, try low-priority
                if job is None:
                    try:
                        job = self.low_priority_queue.get_nowait()
                        logger.debug(f"Processing low-priority job {job.job_id}")
                    except asyncio.QueueEmpty:
                        pass

                # If still no job, sleep briefly and continue
                if job is None:
                    await asyncio.sleep(0.1)
                    continue

                # Process job
                self.active_jobs.append(job.job_id)
                try:
                    await self._compute_similarities(
                        decision_id=job.decision_id,
                        batch_size=self.batch_size,
                    )
                    self.jobs_processed += 1
                    logger.debug(
                        f"Completed job {job.job_id} for decision {job.decision_id}"
                    )
                except Exception as e:
                    self.jobs_failed += 1
                    logger.error(
                        f"Job {job.job_id} failed for decision {job.decision_id}: {e}",
                        exc_info=True,
                    )
                finally:
                    self.active_jobs.remove(job.job_id)

            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Back off on errors

    async def _compute_similarities(
        self,
        decision_id: str,
        batch_size: int = 50,
    ) -> None:
        """Compute similarities for a decision.

        Compares the decision against recent decisions and stores
        similarity relationships above the threshold.

        Args:
            decision_id: UUID of decision to compute similarities for
            batch_size: Number of recent decisions to compare against
        """
        try:
            # Get the decision node
            decision = self.storage.get_decision_node(decision_id)
            if not decision:
                logger.error(f"Decision {decision_id} not found in storage")
                raise ValueError(f"Decision {decision_id} not found in storage")

            # Get recent decisions to compare against
            recent_decisions = self.storage.get_all_decisions(
                limit=batch_size + 1  # +1 to account for self
            )

            if not recent_decisions:
                logger.debug(f"No decisions to compare against for {decision_id}")
                return

            # Compute similarities
            similarities_stored = 0
            for existing in recent_decisions:
                # Skip self-comparison
                if existing.id == decision_id:
                    continue

                try:
                    # Compute similarity score
                    score = self.similarity_detector.compute_similarity(
                        decision.question,
                        existing.question,
                    )

                    # Store if above threshold (clamp score to [0, 1] to handle floating point precision)
                    if score >= self.similarity_threshold:
                        # Clamp score to [0, 1] to prevent validation errors from floating point overflow
                        clamped_score = max(0.0, min(1.0, score))
                        similarity = DecisionSimilarity(
                            source_id=decision_id,
                            target_id=existing.id,
                            similarity_score=clamped_score,
                            computed_at=datetime.now(),
                        )
                        self.storage.save_similarity(similarity)
                        similarities_stored += 1
                        self.total_similarities_computed += 1

                        logger.debug(
                            f"Stored similarity: {decision_id[:8]}... -> "
                            f"{existing.id[:8]}... (score={score:.3f})"
                        )

                except Exception as e:
                    logger.error(
                        f"Error computing similarity with {existing.id}: {e}",
                        exc_info=True,
                    )
                    continue

            logger.info(
                f"Computed {similarities_stored} similarities for decision {decision_id} "
                f"(compared against {len(recent_decisions) - 1} decisions)"
            )

        except Exception as e:
            logger.error(
                f"Error in _compute_similarities for {decision_id}: {e}",
                exc_info=True,
            )
            raise

    def get_stats(self) -> dict:
        """Return queue statistics.

        Returns:
            Dictionary with queue state and performance metrics
        """
        return {
            "running": self.running,
            "high_priority_pending": self.high_priority_queue.qsize(),
            "low_priority_pending": self.low_priority_queue.qsize(),
            "active_jobs": len(self.active_jobs),
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "total_similarities_computed": self.total_similarities_computed,
            "max_queue_size": self.max_queue_size,
            "batch_size": self.batch_size,
            "similarity_threshold": self.similarity_threshold,
        }
