"""Shared query engine for decision graph analysis.

This module provides the QueryEngine class, which serves as a unified interface
for querying and analyzing the decision graph memory. It's used by both MCP tools
and CLI commands to provide consistent functionality.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from decision_graph.retrieval import DecisionRetriever
from decision_graph.schema import DecisionNode, ParticipantStance
from decision_graph.similarity import QuestionSimilarityDetector
from decision_graph.storage import DecisionGraphStorage

if TYPE_CHECKING:
    from models.config import DecisionGraphConfig

logger = logging.getLogger(__name__)


@dataclass
class SimilarResult:
    """Result from similar decision search."""

    decision: DecisionNode
    score: float


@dataclass
class Contradiction:
    """Detected contradiction between decisions."""

    decision_id_1: str
    decision_id_2: str
    question_1: str
    question_2: str
    conflict_type: str  # e.g., "conflicting_consensus", "contradicting_votes"
    severity: float  # 0.0-1.0
    description: str


@dataclass
class TimelineEntry:
    """Single entry in decision evolution timeline."""

    round_num: int
    timestamp: str
    consensus: str
    confidence: float
    participant_positions: List[dict] = field(default_factory=list)


@dataclass
class Timeline:
    """Complete evolution of a decision across rounds."""

    decision_id: str
    question: str
    consensus: str
    status: str
    participants: List[str]
    rounds: List[TimelineEntry] = field(default_factory=list)
    related_decisions: List[dict] = field(default_factory=list)




class QueryEngine:
    """Unified query interface for decision graph memory.

    Provides methods for:
    - Similar decision search
    - Contradiction detection
    - Decision evolution tracing

    Used by both MCP tools and CLI commands.
    """

    def __init__(
        self,
        storage: Optional[DecisionGraphStorage] = None,
        config: Optional["DecisionGraphConfig"] = None,
    ):
        """Initialize query engine.

        Args:
            storage: DecisionGraphStorage instance. If None, creates default.
            config: Optional DecisionGraphConfig for threshold configuration.
        """
        self.storage = storage or DecisionGraphStorage()
        self.config = config
        self.retriever = DecisionRetriever(self.storage, config=config)
        self.similarity_detector = QuestionSimilarityDetector()

        # Extract noise_floor from config or use default
        self.default_threshold = config.noise_floor if config else 0.4

        logger.info(f"Initialized QueryEngine with threshold={self.default_threshold}")

    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        threshold: Optional[float] = None,
    ) -> List[SimilarResult]:
        """Find similar past deliberations by semantic meaning.

        Args:
            query: Query question/text
            limit: Maximum results to return
            threshold: Minimum similarity score (0.0-1.0). If None, uses config's noise_floor.

        Returns:
            List of SimilarResult objects sorted by score descending
        """
        # Use config's noise_floor if no threshold provided
        if threshold is None:
            threshold = self.default_threshold
        try:
            # Don't use run_in_executor - SQLite connection is thread-bound
            results = self._search_similar_sync(query, limit, threshold)
            return results
        except Exception as e:
            logger.error(f"Error in search_similar: {e}", exc_info=True)
            return []

    def _search_similar_sync(
        self, query: str, limit: int, threshold: float
    ) -> List[SimilarResult]:
        """Synchronous implementation of similar search."""
        try:
            # Get all decisions from storage
            decisions = self.storage.get_all_decisions()

            if not decisions:
                return []

            # Compute similarity scores
            results = []
            for decision in decisions:
                score = self.similarity_detector.compute_similarity(
                    query, decision.question
                )
                if score >= threshold:
                    results.append(SimilarResult(decision=decision, score=score))

            # Sort by score descending
            results.sort(key=lambda x: x.score, reverse=True)

            # Return top N results
            return results[:limit]
        except Exception as e:
            logger.error(f"Error in _search_similar_sync: {e}", exc_info=True)
            return []

    async def find_contradictions(
        self,
        scope: Optional[str] = None,
        threshold: float = 0.5,
    ) -> List[Contradiction]:
        """Identify conflicting decisions across deliberations.

        Args:
            scope: Optional scope/topic to filter by
            threshold: Similarity threshold for detecting contradictions

        Returns:
            List of Contradiction objects
        """
        try:
            contradictions = self._find_contradictions_sync(scope, threshold)
            return contradictions
        except Exception as e:
            logger.error(f"Error in find_contradictions: {e}", exc_info=True)
            return []

    def _find_contradictions_sync(
        self, scope: Optional[str], threshold: float
    ) -> List[Contradiction]:
        """Synchronous implementation of contradiction detection."""
        try:
            decisions = self.storage.get_all_decisions()
            contradictions = []

            # Compare all pairs of decisions
            for i, dec1 in enumerate(decisions):
                for dec2 in decisions[i + 1 :]:
                    # Check if questions are similar (potential contradiction)
                    similarity = self.similarity_detector.compute_similarity(
                        dec1.question, dec2.question
                    )

                    if similarity >= threshold:
                        # Check if consensus differs significantly
                        if self._consensus_differs(dec1, dec2):
                            severity = (
                                similarity  # Similar questions, different outcomes
                            )

                            contradictions.append(
                                Contradiction(
                                    decision_id_1=dec1.id,
                                    decision_id_2=dec2.id,
                                    question_1=dec1.question,
                                    question_2=dec2.question,
                                    conflict_type="conflicting_consensus",
                                    severity=severity,
                                    description=f"Different consensus on similar topic: '{dec1.consensus}' vs '{dec2.consensus}'",
                                )
                            )

            return contradictions
        except Exception as e:
            logger.error(f"Error in _find_contradictions_sync: {e}", exc_info=True)
            return []

    def _consensus_differs(self, dec1: DecisionNode, dec2: DecisionNode) -> bool:
        """Check if two decisions have significantly different consensus."""
        # Simple heuristic: check if winning options differ
        if (
            dec1.winning_option
            and dec2.winning_option
            and dec1.winning_option != dec2.winning_option
        ):
            return True

        # Check if convergence status differs
        if dec1.convergence_status != dec2.convergence_status:
            return True

        return False

    async def trace_evolution(
        self, decision_id: str, include_related: bool = False
    ) -> Timeline:
        """Show how a decision evolved across rounds.

        Args:
            decision_id: ID of decision to trace
            include_related: Whether to include related decisions

        Returns:
            Timeline object with evolution details

        Raises:
            ValueError: If decision not found
        """
        try:
            timeline = self._trace_evolution_sync(decision_id, include_related)
            return timeline
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error in trace_evolution: {e}", exc_info=True)
            raise ValueError(f"Could not trace evolution for {decision_id}") from e

    def _trace_evolution_sync(
        self, decision_id: str, include_related: bool
    ) -> Timeline:
        """Synchronous implementation of evolution tracing."""
        # Get decision
        decision = self.storage.get_decision_node(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        # Get participant stances
        stances = self.storage.get_participant_stances(decision_id)

        # Build timeline entries (simplified: single entry for now)
        # In a full implementation, would track across rounds
        rounds = [
            TimelineEntry(
                round_num=1,
                timestamp=decision.timestamp.isoformat(),
                consensus=decision.consensus,
                confidence=0.8,  # Placeholder
                participant_positions=[
                    {
                        "participant": s.participant,
                        "option": s.vote_option,
                        "confidence": s.confidence,
                    }
                    for s in stances
                ],
            )
        ]

        # Find related decisions
        related = []
        if include_related:
            related = self._find_related_decisions(decision)

        return Timeline(
            decision_id=decision_id,
            question=decision.question,
            consensus=decision.consensus,
            status=decision.convergence_status,
            participants=decision.participants,
            rounds=rounds,
            related_decisions=related,
        )

    def _find_related_decisions(self, decision: DecisionNode) -> List[dict]:
        """Find decisions related to the given decision."""
        try:
            decisions = self.storage.get_all_decisions()
            related = []

            for other in decisions:
                if other.id != decision.id:
                    similarity = self.similarity_detector.compute_similarity(
                        decision.question, other.question
                    )
                    if similarity > 0.5:
                        related.append(
                            {
                                "id": other.id,
                                "question": other.question,
                                "similarity": similarity,
                                "consensus": other.consensus,
                            }
                        )

            related.sort(key=lambda x: x["similarity"], reverse=True)
            return related[:5]  # Top 5 related
        except Exception as e:
            logger.error(f"Error finding related decisions: {e}")
            return []

