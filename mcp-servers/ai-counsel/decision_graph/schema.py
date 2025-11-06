"""Schema models for decision graph memory.

This module defines the core Pydantic models for representing completed
deliberations, participant stances, and similarity relationships in the
decision graph memory system.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class DecisionNode(BaseModel):
    """
    Model representing a completed deliberation in the decision graph.

    DecisionNode stores the essential metadata and outcomes from a completed
    deliberation, enabling retrieval and comparison with future deliberations.
    Each node represents a single deliberation session with its consensus,
    participants, and convergence status.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique decision identifier (UUID)",
    )
    question: str = Field(
        ..., min_length=1, description="The deliberation question or proposal"
    )
    timestamp: datetime = Field(
        ..., description="When the deliberation occurred (ISO 8601 format)"
    )
    consensus: str = Field(
        ..., description="Consensus reached from Summary.consensus field"
    )
    winning_option: Optional[str] = Field(
        None, description="Winning vote option from VotingResult if votes were cast"
    )
    convergence_status: str = Field(
        ...,
        description="Convergence status from ConvergenceInfo (converged, refining, diverging, etc.)",
    )
    participants: List[str] = Field(
        ...,
        description="List of participant model identifiers (e.g., ['opus@claude', 'gpt-4@codex'])",
    )
    transcript_path: str = Field(
        ..., description="Relative or absolute path to the full transcript file"
    )
    metadata: Dict = Field(
        default_factory=dict,
        description="Extensible metadata dictionary for future fields",
    )


class ParticipantStance(BaseModel):
    """
    Model representing a participant's stance in a deliberation.

    ParticipantStance captures how a specific model positioned itself during
    a deliberation, including their vote (if structured voting was used),
    confidence level, rationale, and final position text from their last round.
    """

    decision_id: str = Field(
        ..., description="UUID of the decision this stance belongs to"
    )
    participant: str = Field(
        ...,
        description="Participant identifier in format 'model@cli' (e.g., 'opus@claude')",
    )
    vote_option: Optional[str] = Field(
        None, description="Vote option if structured voting was used (e.g., 'Option A')"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Vote confidence score between 0.0 and 1.0 (None if no vote cast)",
    )
    rationale: Optional[str] = Field(
        None, description="Vote rationale or reasoning provided by the participant"
    )
    final_position: str = Field(
        ...,
        description="Final position text from the participant's last round response (may be truncated)",
    )


class DecisionSimilarity(BaseModel):
    """
    Model representing similarity between two decisions.

    DecisionSimilarity stores pre-computed semantic similarity scores between
    pairs of decisions, enabling fast retrieval of related past deliberations
    when starting a new deliberation. Similarities are computed asynchronously
    after each deliberation is stored.
    """

    source_id: str = Field(
        ..., description="Source decision UUID (the newer or queried decision)"
    )
    target_id: str = Field(
        ..., description="Target decision UUID (the related past decision)"
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Semantic similarity score between questions (0.0 = unrelated, 1.0 = identical)",
    )
    computed_at: datetime = Field(
        default_factory=datetime.now,
        description="When the similarity score was computed (ISO 8601 format)",
    )
