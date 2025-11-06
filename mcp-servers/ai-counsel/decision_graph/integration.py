"""Integration layer connecting decision graph memory to deliberation engine.

This module provides the DecisionGraphIntegration class, which acts as a facade
for all decision graph operations. It handles storing completed deliberations,
computing similarities between decisions, and retrieving enriched context for
new deliberations.
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from decision_graph.maintenance import DecisionGraphMaintenance
from decision_graph.retrieval import DecisionRetriever
from decision_graph.schema import (DecisionNode, DecisionSimilarity,
                                   ParticipantStance)
from decision_graph.similarity import QuestionSimilarityDetector
from decision_graph.storage import DecisionGraphStorage
from decision_graph.workers import BackgroundWorker
from models.schema import DeliberationResult

if TYPE_CHECKING:
    from models.config import Config

logger = logging.getLogger(__name__)


class DecisionGraphIntegration:
    """Integration layer connecting decision graph memory to deliberation engine.

    This class provides a high-level API for:
    - Storing completed deliberations in the decision graph
    - Computing semantic similarities between decisions
    - Retrieving enriched context for new deliberations

    It acts as a facade, coordinating between storage, retrieval, and similarity
    detection components while providing graceful error handling to ensure that
    decision graph issues never break deliberation execution.

    Example:
        >>> storage = DecisionGraphStorage("decisions.db")
        >>> integration = DecisionGraphIntegration(storage)
        >>>
        >>> # After deliberation completes
        >>> decision_id = integration.store_deliberation(question, result)
        >>>
        >>> # Before starting new deliberation
        >>> context = integration.get_context_for_deliberation(new_question)
        >>> # Use context to enrich prompts
    """

    def __init__(
        self,
        storage: DecisionGraphStorage,
        enable_background_worker: bool = True,
        config: Optional["Config"] = None,
    ):
        """Initialize integration with storage backend.

        Args:
            storage: DecisionGraphStorage instance for persistence
            enable_background_worker: Enable async background processing for similarities
            config: Optional Config instance for budget-aware context injection
        """
        self.storage = storage
        self.config = config

        # Extract decision_graph config from root config
        dg_config = config.decision_graph if config else None

        # Initialize retriever with decision_graph config
        self.retriever = DecisionRetriever(storage, config=dg_config)

        self.worker: Optional[BackgroundWorker] = None
        self._worker_enabled = enable_background_worker
        self.maintenance = DecisionGraphMaintenance(storage)
        self._decision_count = 0

        # Initialize background worker if enabled
        if enable_background_worker:
            self.worker = BackgroundWorker(
                storage=storage,
                max_queue_size=1000,
                batch_size=100,
                similarity_threshold=0.5,
                config=dg_config,
            )
            # Note: Worker start is deferred - call ensure_worker_started() or
            # let it auto-start on first enqueue

        logger.info("Initialized DecisionGraphIntegration with config-aware components")

    async def ensure_worker_started(self) -> None:
        """Ensure background worker is started.

        This method is called automatically when needed, but can be called
        explicitly to start the worker early.
        """
        if self.worker and not self.worker.running:
            await self.worker.start()
            logger.info("Started background worker for similarity computation")

    def store_deliberation(self, question: str, result: DeliberationResult) -> str:
        """Store completed deliberation in decision graph.

        Extracts data from DeliberationResult and saves:
        - Decision node with metadata, consensus, and convergence status
        - Participant stances with votes, confidence, and rationale
        - Similarity relationships to past decisions (async computation)

        Args:
            question: The deliberation question
            result: DeliberationResult from deliberation engine

        Returns:
            The decision node ID (UUID)

        Raises:
            Exception: Re-raises storage errors after logging (caller should handle)

        Example:
            >>> integration = DecisionGraphIntegration(storage)
            >>> result = await engine.execute(request)
            >>> decision_id = integration.store_deliberation(
            ...     request.question,
            ...     result
            ... )
            >>> print(f"Stored decision: {decision_id}")
        """
        try:
            # Extract winning option from voting result
            winning_option = None
            if result.voting_result and result.voting_result.winning_option:
                winning_option = result.voting_result.winning_option

            # Extract consensus from summary
            consensus = ""
            if result.summary and result.summary.consensus:
                consensus = result.summary.consensus

            # Extract convergence status
            convergence_status = "unknown"
            if result.convergence_info and result.convergence_info.status:
                convergence_status = result.convergence_info.status

            # Create decision node
            node = DecisionNode(
                id=str(uuid4()),
                question=question,
                timestamp=datetime.now(),
                consensus=consensus,
                winning_option=winning_option,
                convergence_status=convergence_status,
                participants=result.participants,
                transcript_path=result.transcript_path or "",
            )

            # Save decision node
            decision_id = self.storage.save_decision_node(node)
            logger.info(
                f"Stored decision {decision_id} for question: {question[:50]}..."
            )

            # Extract and save participant stances from final round
            stances_saved = 0
            if result.rounds_completed > 0 and result.full_debate:
                # Get final round responses (last N responses where N = number of participants)
                num_participants = len(result.participants)
                final_round_responses = result.full_debate[-num_participants:]

                # Build map of participant -> final response
                final_responses = {}
                for resp in final_round_responses:
                    final_responses[resp.participant] = resp.response

                # Extract votes from voting result if available
                vote_map = {}
                if result.voting_result and result.voting_result.votes_by_round:
                    # Get votes from final round
                    final_round_num = result.rounds_completed
                    for round_vote in result.voting_result.votes_by_round:
                        if round_vote.round == final_round_num:
                            vote_map[round_vote.participant] = round_vote.vote

                # Save stance for each participant
                for participant in result.participants:
                    # Get vote info
                    vote = vote_map.get(participant)

                    # Get final position (truncate to 500 chars)
                    final_position = final_responses.get(participant, "")[:500]

                    # Create and save stance
                    stance = ParticipantStance(
                        decision_id=decision_id,
                        participant=participant,
                        vote_option=vote.option if vote else None,
                        confidence=vote.confidence if vote else None,
                        rationale=vote.rationale if vote else None,
                        final_position=final_position,
                    )
                    self.storage.save_participant_stance(stance)
                    stances_saved += 1

            logger.info(
                f"Saved {stances_saved} participant stances for decision {decision_id}"
            )

            # Increment decision count and perform periodic health checks
            self._decision_count += 1
            if self._decision_count % 100 == 0:
                try:
                    stats = self.maintenance.get_database_stats()
                    logger.info(
                        f"Decision graph stats (at {self._decision_count} stored): "
                        f"{stats['total_decisions']} decisions, "
                        f"{stats['total_stances']} stances, "
                        f"{stats['total_similarities']} similarities, "
                        f"{stats['db_size_mb']} MB"
                    )

                    # Warn if approaching archival threshold
                    total_decisions = stats.get("total_decisions", 0)
                    if total_decisions >= 4500:
                        logger.warning(
                            f"Decision graph approaching archival threshold: "
                            f"{total_decisions} decisions (threshold: 5000)"
                        )

                    # Get growth analysis periodically (every 500 decisions)
                    if self._decision_count % 500 == 0:
                        growth = self.maintenance.analyze_growth(days=30)
                        logger.info(
                            f"Growth analysis: {growth['decisions_in_period']} decisions in "
                            f"{growth['analysis_period_days']} days, "
                            f"avg {growth['avg_decisions_per_day']}/day, "
                            f"projected {growth['projected_decisions_30d']} in next 30 days"
                        )
                except Exception as e:
                    logger.error(
                        f"Error collecting maintenance stats: {e}", exc_info=True
                    )

            # Queue similarity computation to background worker (non-blocking)
            if self.worker and self._worker_enabled:
                try:
                    # Get event loop and queue job
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Ensure worker is started and enqueue
                            async def enqueue_job():
                                await self.ensure_worker_started()
                                await self.worker.enqueue(
                                    decision_id=decision_id,
                                    priority="low",
                                    delay_seconds=5,
                                )

                            asyncio.create_task(enqueue_job())
                            logger.info(
                                f"Queued similarity computation for decision {decision_id}"
                            )
                        else:
                            # No running loop, fall back to synchronous
                            logger.debug(
                                "No running event loop, falling back to synchronous similarity computation"
                            )
                            self._compute_similarities(node)
                    except RuntimeError:
                        # No event loop available, fall back to synchronous
                        logger.debug(
                            "Event loop not available, falling back to synchronous similarity computation"
                        )
                        self._compute_similarities(node)
                except Exception as e:
                    # Log error but don't fail - fall back to sync computation
                    logger.warning(
                        f"Error queueing background similarity job for {decision_id}: {e}, "
                        "falling back to synchronous computation"
                    )
                    try:
                        self._compute_similarities(node)
                    except Exception as sync_error:
                        logger.error(
                            f"Error in fallback similarity computation: {sync_error}",
                            exc_info=True,
                        )
            else:
                # Background worker disabled, compute synchronously
                try:
                    self._compute_similarities(node)
                except Exception as e:
                    # Log but don't fail if similarity computation fails
                    logger.error(
                        f"Error computing similarities for decision {decision_id}: {e}",
                        exc_info=True,
                    )

            # Invalidate retriever cache so next query reflects this new decision
            # This ensures that subsequent get_context_for_deliberation() calls
            # will find context from this newly stored decision
            try:
                self.retriever.invalidate_cache()
            except Exception as e:
                logger.warning(
                    f"Error invalidating retriever cache after storing decision {decision_id}: {e}"
                )

            return decision_id

        except Exception as e:
            logger.error(
                f"Error storing deliberation in decision graph: {e}", exc_info=True
            )
            raise  # Re-raise to let caller handle

    def _compute_similarities(self, new_node: DecisionNode) -> None:
        """Compute similarities between new decision and existing decisions.

        Compares the new decision against all existing decisions in the database
        and stores similarity relationships above a threshold. This enables fast
        retrieval of related past deliberations.

        Args:
            new_node: The newly created DecisionNode

        Note:
            - Limits comparison to 100 most recent decisions to avoid O(n^2) growth
            - Stores similarities >= 0.5 for potential future use
            - Logs errors but does not raise to avoid breaking deliberation flow
        """
        try:
            # Get recent decisions (limit to avoid O(n^2) growth)
            all_decisions = self.storage.get_all_decisions(limit=100)

            if not all_decisions:
                logger.debug("No existing decisions to compare against")
                return

            # Initialize similarity detector
            detector = QuestionSimilarityDetector()

            similarities_stored = 0
            for existing in all_decisions:
                # Skip self-comparison
                if existing.id == new_node.id:
                    continue

                # Compute similarity score
                try:
                    score = detector.compute_similarity(
                        new_node.question, existing.question
                    )

                    # Store similarity if above threshold (0.5 = moderate similarity)
                    if score >= 0.5:
                        similarity = DecisionSimilarity(
                            source_id=new_node.id,
                            target_id=existing.id,
                            similarity_score=score,
                            computed_at=datetime.now(),
                        )
                        self.storage.save_similarity(similarity)
                        similarities_stored += 1
                        logger.debug(
                            f"Stored similarity: {new_node.id} -> {existing.id} "
                            f"(score={score:.3f})"
                        )
                except Exception as e:
                    logger.error(
                        f"Error computing similarity with decision {existing.id}: {e}",
                        exc_info=True,
                    )
                    continue

            logger.info(
                f"Computed and stored {similarities_stored} similarities "
                f"for decision {new_node.id}"
            )

        except Exception as e:
            logger.error(f"Error in similarity computation: {e}", exc_info=True)
            # Don't raise - this is a non-critical operation

    def _log_context_metrics(
        self,
        question: str,
        scored_count: int,
        tier_dist: dict,
        tokens_used: int,
        token_budget: int,
        db_size: int,
    ) -> None:
        """Log structured measurement metrics for Phase 1.5 calibration.

        This method logs metrics in a structured format that can be parsed
        for empirical analysis of context injection effectiveness:
        - Which tiers (strong/moderate/brief) help convergence?
        - Should tier boundaries move based on usage patterns?
        - Is the token budget appropriately sized?

        Args:
            question: The deliberation question (truncated for logging)
            scored_count: Number of scored decisions retrieved
            tier_dist: Dictionary with strong/moderate/brief counts
            tokens_used: Tokens used in formatted context
            token_budget: Token budget from config
            db_size: Current database size (decision count)

        Example log output:
            MEASUREMENT: question='Should we use TypeScript?...', scored_results=3,
            tier_distribution={'strong': 1, 'moderate': 1, 'brief': 1},
            tokens=450/1500, db_size=250
        """
        # Truncate question for logging (max 30 chars)
        truncated_question = question[:30] + "..." if len(question) > 30 else question

        # Format tier distribution for readability
        tier_str = (
            f"strong:{tier_dist.get('strong', 0)}, "
            f"moderate:{tier_dist.get('moderate', 0)}, "
            f"brief:{tier_dist.get('brief', 0)}"
        )

        # Log in structured format
        logger.info(
            f"MEASUREMENT: question='{truncated_question}', "
            f"scored_results={scored_count}, "
            f"tier_distribution=({tier_str}), "
            f"tokens={tokens_used}/{token_budget}, "
            f"db_size={db_size}"
        )

    def get_context_for_deliberation(
        self,
        question: str,
        threshold: float = 0.7,
        max_context_decisions: int = 3,
    ) -> str:
        """Get enriched context for a new deliberation.

        Finds past deliberations that are semantically similar to the new question
        and formats them as markdown context. This context can be prepended to
        deliberation prompts to provide historical perspective.

        NEW (Task 5): Uses budget-aware tiered formatting if config is available.
        Falls back to legacy formatting if config is None.

        Args:
            question: The deliberation question
            threshold: DEPRECATED - Kept for backward compatibility. Use config.tier_boundaries instead.
            max_context_decisions: DEPRECATED - Kept for backward compatibility. Adaptive k is used instead.

        Returns:
            Markdown-formatted context string. Empty string if no similar decisions
            found or if any error occurs (graceful degradation).

        Example:
            >>> integration = DecisionGraphIntegration(storage, config=config)
            >>> context = integration.get_context_for_deliberation(
            ...     "Should we adopt TypeScript?"
            ... )
            >>> if context:
            ...     print("Found relevant context:")
            ...     print(context)
            ... else:
            ...     print("No relevant context found")
        """
        try:
            # Validate parameters
            if not question or not question.strip():
                logger.warning(
                    "Empty question provided to get_context_for_deliberation"
                )
                return ""

            if not (0.0 <= threshold <= 1.0):
                logger.warning(f"Invalid threshold {threshold}, clamping to [0.0, 1.0]")
                threshold = max(0.0, min(1.0, threshold))

            if max_context_decisions < 1:
                logger.warning(
                    f"Invalid max_context_decisions {max_context_decisions}, using 1"
                )
                max_context_decisions = 1

            # Log deprecation warning if non-default parameters used
            if threshold != 0.7 or max_context_decisions != 3:
                logger.warning(
                    f"Parameters threshold={threshold} and max_context_decisions={max_context_decisions} "
                    f"are deprecated. Use config.decision_graph.tier_boundaries and adaptive k instead."
                )

            # Branch: Use budget-aware tiered formatting if config available
            if self.config and self.config.decision_graph:
                logger.debug("Using budget-aware tiered formatting from config")

                # Get configuration values
                token_budget = self.config.decision_graph.context_token_budget
                tier_boundaries = self.config.decision_graph.tier_boundaries

                # Get database size for logging
                db_stats = self.storage.get_all_decisions(limit=1)
                db_size = len(self.storage.get_all_decisions(limit=10000))
                logger.debug(f"Database size: {db_size} decisions")

                # Find relevant decisions (returns tuples of (DecisionNode, score))
                scored_decisions = self.retriever.find_relevant_decisions(
                    question, threshold=threshold, max_results=max_context_decisions
                )

                if not scored_decisions:
                    logger.info(f"No relevant decisions found for question: {question[:50]}...")
                    return ""

                # Format using tiered approach
                result = self.retriever.format_context_tiered(
                    scored_decisions=scored_decisions,
                    tier_boundaries=tier_boundaries,
                    token_budget=token_budget,
                )

                # Log metrics for Phase 1.5 calibration using structured format
                tier_dist = result["tier_distribution"]
                tokens_used = result["tokens_used"]

                # Use dedicated measurement logging method
                self._log_context_metrics(
                    question=question,
                    scored_count=len(scored_decisions),
                    tier_dist=tier_dist,
                    tokens_used=tokens_used,
                    token_budget=token_budget,
                    db_size=db_size,
                )

                return result["formatted"]

            # Legacy path: Use old retriever.get_enriched_context
            else:
                logger.debug("Using legacy formatting (no config available)")
                context = self.retriever.get_enriched_context(
                    question, threshold=threshold, max_results=max_context_decisions
                )

                if context:
                    logger.info(
                        f"Retrieved enriched context for question: {question[:50]}... "
                        f"(threshold={threshold}, max_results={max_context_decisions})"
                    )
                else:
                    logger.debug(
                        f"No relevant context found for question: {question[:50]}... "
                        f"(threshold={threshold})"
                    )

                return context

        except Exception as e:
            # Log error but return empty string for graceful degradation
            logger.error(
                f"Error retrieving context for deliberation: {e}", exc_info=True
            )
            return ""  # Never break deliberation due to context retrieval failure

    def get_graph_stats(self) -> dict:
        """Get current decision graph statistics for monitoring.

        Returns comprehensive statistics about the decision graph including:
        - Total counts (decisions, stances, similarities)
        - Database size (bytes and MB)

        This method is safe to call frequently for monitoring dashboards
        or health checks. It gracefully handles errors and returns empty
        dict on failure.

        Returns:
            Dictionary with statistics. Empty dict on error.

        Example:
            >>> integration = DecisionGraphIntegration(storage)
            >>> stats = integration.get_graph_stats()
            >>> print(f"Database has {stats['total_decisions']} decisions")
            >>> print(f"Database size: {stats['db_size_mb']} MB")
        """
        try:
            return self.maintenance.get_database_stats()
        except Exception as e:
            logger.error(f"Error retrieving graph stats: {e}", exc_info=True)
            return {}

    def get_graph_metrics(self) -> dict:
        """Get detailed graph metrics for Phase 1.5 calibration analysis.

        Returns metrics useful for empirical calibration including:
        - total_decisions: Total number of decisions in database
        - recent_100_count: Number of decisions in last 100 entries (query window)
        - recent_1000_count: Number of decisions in last 1000 entries (extended window)

        These metrics help answer:
        - How many decisions are typically considered for context?
        - Is the query window appropriately sized?
        - What is the database growth rate?

        Returns:
            Dictionary with detailed metrics. Returns zeros on error.

        Example:
            >>> integration = DecisionGraphIntegration(storage)
            >>> metrics = integration.get_graph_metrics()
            >>> print(f"Query window coverage: {metrics['recent_100_count']}/100")
            >>> print(f"Extended window: {metrics['recent_1000_count']}/1000")
        """
        try:
            # Get all decisions to compute counts
            all_decisions = self.storage.get_all_decisions(limit=10000)
            total_count = len(all_decisions)

            # Compute recent counts (simulating query windows)
            recent_100 = min(100, total_count)
            recent_1000 = min(1000, total_count)

            return {
                "total_decisions": total_count,
                "recent_100_count": recent_100,
                "recent_1000_count": recent_1000,
            }
        except Exception as e:
            logger.error(f"Error retrieving graph metrics: {e}", exc_info=True)
            return {
                "total_decisions": 0,
                "recent_100_count": 0,
                "recent_1000_count": 0,
            }

    def health_check(self) -> dict:
        """Perform comprehensive health check on decision graph.

        Validates database integrity including:
        - Checking for orphaned stances and similarities
        - Validating timestamps (no future dates)
        - Verifying required fields are populated
        - Checking similarity scores are in valid range [0.0, 1.0]

        Returns:
            Dictionary with health check results:
                - healthy: bool (True if all checks pass)
                - checks_passed: int (number of successful checks)
                - checks_failed: int (number of failed checks)
                - issues: List[str] (descriptions of issues found)
                - details: dict (detailed results per check)

        Example:
            >>> integration = DecisionGraphIntegration(storage)
            >>> health = integration.health_check()
            >>> if health['healthy']:
            ...     print("Database is healthy")
            ... else:
            ...     print(f"Found {health['checks_failed']} issues:")
            ...     for issue in health['issues']:
            ...         print(f"  - {issue}")
        """
        try:
            return self.maintenance.health_check()
        except Exception as e:
            logger.error(f"Error performing health check: {e}", exc_info=True)
            return {
                "healthy": False,
                "checks_passed": 0,
                "checks_failed": 1,
                "issues": [f"Health check error: {str(e)}"],
                "details": {},
            }

    async def shutdown(self) -> None:
        """Gracefully shutdown background worker.

        This method should be called when the integration is no longer needed
        to ensure background jobs complete and resources are released.

        Example:
            >>> integration = DecisionGraphIntegration(storage)
            >>> # ... use integration ...
            >>> await integration.shutdown()
        """
        if self.worker:
            logger.info("Shutting down background worker...")
            try:
                await self.worker.stop(timeout=30.0)
                logger.info("Background worker shutdown complete")
            except Exception as e:
                logger.error(
                    f"Error shutting down background worker: {e}", exc_info=True
                )

    def __del__(self):
        """Cleanup on destruction - attempt graceful shutdown if event loop available."""
        if self.worker and self.worker.running:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.shutdown())
                else:
                    # Try to run shutdown synchronously
                    loop.run_until_complete(self.shutdown())
            except Exception as e:
                logger.warning(
                    f"Could not gracefully shutdown worker in destructor: {e}"
                )
