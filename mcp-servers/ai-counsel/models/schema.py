"""Pydantic models for AI Counsel."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Participant(BaseModel):
    """Model representing a deliberation participant."""

    cli: Literal[
        "claude",
        "codex",
        "droid",
        "gemini",
        "llamacpp",
        "ollama",
        "lmstudio",
        "openrouter",
    ] = Field(
        ...,
        description="Adapter to use for this participant (CLI tools or HTTP services)",
    )
    model: Optional[str] = Field(
        default=None,
        description=(
            "Model identifier (e.g., 'claude-3-5-sonnet-20241022', 'gpt-4'). "
            "If omitted, the server will use the session default or the recommended default for the adapter."
        ),
    )


class DeliberateRequest(BaseModel):
    """Model for deliberation request."""

    question: str = Field(
        ..., min_length=10, description="The question or proposal to deliberate on"
    )
    participants: list[Participant] = Field(
        ..., min_length=2, description="List of participants (minimum 2)"
    )
    rounds: int = Field(
        default=2, ge=1, le=5, description="Number of deliberation rounds (1-5)"
    )
    mode: Literal["quick", "conference"] = Field(
        default="quick", description="Deliberation mode"
    )
    context: Optional[str] = Field(
        default=None, description="Optional additional context"
    )
    working_directory: str = Field(
        ...,
        description="Working directory for tool execution (tools resolve relative paths from here). Required for deliberations using evidence-based tools."
    )


class RoundResponse(BaseModel):
    """Model for a single round response from a participant."""

    round: int = Field(..., description="Round number")
    participant: str = Field(..., description="Participant identifier")
    response: str = Field(..., description="The response text")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class Summary(BaseModel):
    """Model for deliberation summary."""

    consensus: str = Field(..., description="Overall consensus description")
    key_agreements: list[str] = Field(..., description="Points of agreement")
    key_disagreements: list[str] = Field(..., description="Points of disagreement")
    final_recommendation: str = Field(..., description="Final recommendation")


class Vote(BaseModel):
    """Model for an individual vote with confidence and rationale."""

    option: str = Field(
        ..., description="The voting option (e.g., 'Option A', 'Yes', 'Approve')"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence level in this vote (0.0-1.0)"
    )
    rationale: str = Field(..., description="Explanation for this vote")
    continue_debate: bool = Field(
        default=True,
        description="Whether this participant wants to continue deliberating (False = satisfied with outcome)",
    )


class RoundVote(BaseModel):
    """Model for a vote cast in a specific round."""

    round: int = Field(..., description="Round number when vote was cast")
    participant: str = Field(..., description="Participant identifier")
    vote: Vote = Field(..., description="The vote cast by this participant")
    timestamp: str = Field(..., description="ISO 8601 timestamp when vote was cast")


class VotingResult(BaseModel):
    """Model for aggregated voting results across all rounds."""

    final_tally: Dict[str, int] = Field(..., description="Final vote counts by option")
    votes_by_round: List[RoundVote] = Field(
        ..., description="All votes organized by round"
    )
    consensus_reached: bool = Field(..., description="Whether voting reached consensus")
    winning_option: Optional[str] = Field(
        ..., description="The winning option (None if tie or no consensus)"
    )


class ConvergenceInfo(BaseModel):
    """
    Convergence detection metadata for deliberation rounds.

    Tracks similarity metrics between consecutive rounds to determine
    when models have reached consensus or stable disagreement.
    """

    detected: bool = Field(
        ...,
        description="Whether convergence was detected (True if models reached consensus)",
    )
    detection_round: Optional[int] = Field(
        None,
        description="Round number where convergence occurred (None if not detected or max rounds reached)",
    )
    final_similarity: float = Field(
        ...,
        description="Final similarity score (minimum across all participants, range 0.0-1.0)",
    )
    status: Literal[
        "converged",
        "diverging",
        "refining",
        "impasse",
        "max_rounds",
        "unanimous_consensus",
        "majority_decision",
        "tie",
        "unknown",
    ] = Field(
        ...,
        description=(
            "Convergence status: "
            "'converged' (≥85% similarity, consensus reached), "
            "'refining' (40-85%, still making progress), "
            "'diverging' (<40%, significant disagreement), "
            "'impasse' (stable disagreement over multiple rounds), "
            "'max_rounds' (reached round limit), "
            "'unanimous_consensus' (all votes for same option), "
            "'majority_decision' (clear winner from voting), "
            "'tie' (no clear winner from voting), "
            "'unknown' (no convergence data available)"
        ),
    )
    scores_by_round: list[dict] = Field(
        default_factory=list,
        description="Historical similarity scores for each round (for tracking convergence progression)",
    )
    per_participant_similarity: dict[str, float] = Field(
        default_factory=dict,
        description="Latest similarity score for each participant (participant_id -> similarity score 0.0-1.0)",
    )


class DeliberationResult(BaseModel):
    """Model for complete deliberation result."""

    status: Literal["complete", "partial", "failed"] = Field(..., description="Status")
    mode: str = Field(..., description="Mode used")
    rounds_completed: int = Field(..., description="Rounds completed")
    participants: list[str] = Field(..., description="Participant identifiers")
    summary: Summary = Field(..., description="Deliberation summary")
    transcript_path: str = Field(..., description="Path to full transcript")
    full_debate: list[RoundResponse] = Field(..., description="Full debate history")
    convergence_info: Optional[ConvergenceInfo] = Field(
        None,
        description="Convergence detection information (None if detection disabled)",
    )
    voting_result: Optional[VotingResult] = Field(
        None,
        description="Voting results if participants cast votes (None if no votes found)",
    )
    graph_context_summary: Optional[str] = Field(
        None,
        description="Summary of decision graph context used (None if not used)",
    )
    tool_executions: Optional[list] = Field(
        default_factory=list,
        description="List of tool executions during deliberation (evidence-based deliberation)",
    )
