"""Unit tests for Pydantic models."""
import pytest
from pydantic import ValidationError

from models.schema import (DeliberateRequest, DeliberationResult, Participant,
                           RoundResponse, RoundVote, Vote, VotingResult)


class TestParticipant:
    """Tests for Participant model."""

    def test_valid_participant(self):
        """Test creating a valid participant."""
        p = Participant(
            cli="claude", model="claude-3-5-sonnet-20241022"
        )
        assert p.cli == "claude"
        assert p.model == "claude-3-5-sonnet-20241022"

    def test_participant_creation(self):
        """Test participant creation."""
        p = Participant(cli="codex", model="gpt-4")
        assert p.cli == "codex"
        assert p.model == "gpt-4"

    def test_participant_allows_missing_model(self):
        """Participants can defer to defaults when model omitted."""
        p = Participant(cli="claude")
        assert p.model is None

    def test_invalid_cli_raises_error(self):
        """Test that invalid CLI tool raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Participant(cli="invalid-cli", model="gpt-4")
        assert "cli" in str(exc_info.value)



    def test_ollama_participant(self):
        """Test creating an Ollama participant."""
        p = Participant(cli="ollama", model="llama2")
        assert p.cli == "ollama"
        assert p.model == "llama2"

    def test_lmstudio_participant(self):
        """Test creating an LM Studio participant."""
        p = Participant(cli="lmstudio", model="local-model")
        assert p.cli == "lmstudio"
        assert p.model == "local-model"

    def test_llamacpp_participant(self):
        """Test creating a llama.cpp participant."""
        p = Participant(
            cli="llamacpp", model="/path/to/llama-2-7b.Q4_K_M.gguf"
        )
        assert p.cli == "llamacpp"
        assert p.model == "/path/to/llama-2-7b.Q4_K_M.gguf"

    def test_openrouter_participant(self):
        """Test creating an OpenRouter participant."""
        p = Participant(
            cli="openrouter", model="anthropic/claude-3.5-sonnet"
        )
        assert p.cli == "openrouter"
        assert p.model == "anthropic/claude-3.5-sonnet"


class TestDeliberateRequest:
    """Tests for DeliberateRequest model."""

    def test_valid_request_minimal(self):
        """Test valid request with minimal fields."""
        req = DeliberateRequest(
            question="Should we use TypeScript?",
            participants=[
                Participant(cli="claude", model="claude-3-5-sonnet-20241022"),
                Participant(cli="codex", model="gpt-4"),
            ],
            working_directory="/tmp",)
        assert req.question == "Should we use TypeScript?"
        assert len(req.participants) == 2
        assert req.rounds == 2  # Default
        assert req.mode == "quick"  # Default

    def test_request_allows_missing_model(self):
        """Missing model values are permitted and default later."""
        req = DeliberateRequest(
            question="Is Rust suitable for this service?",
            participants=[
                Participant(cli="claude"),
                Participant(cli="codex"),
            ],
            working_directory="/tmp",)
        assert req.participants[0].model is None
        assert req.participants[1].model is None

    def test_valid_request_full(self):
        """Test valid request with all fields."""
        req = DeliberateRequest(
            question="Should we refactor?",
            participants=[
                Participant(
                    cli="claude", model="claude-3-5-sonnet-20241022"
                ),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=3,
            mode="conference",
            context="Legacy codebase, 50K LOC",
            working_directory="/tmp",)
        assert req.rounds == 3
        assert req.mode == "conference"
        assert req.context == "Legacy codebase, 50K LOC"

    def test_requires_at_least_two_participants(self):
        """Test that at least 2 participants are required."""
        with pytest.raises(ValidationError) as exc_info:
            DeliberateRequest(
                question="Test?", participants=[Participant(cli="codex", model="gpt-4")],
            working_directory="/tmp",)
        assert "participants" in str(exc_info.value)

    def test_rounds_must_be_positive(self):
        """Test that rounds must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            DeliberateRequest(
                question="Test?",
                participants=[
                    Participant(cli="claude", model="claude-3-5-sonnet-20241022"),
                    Participant(cli="codex", model="gpt-4"),
                ],
                rounds=0,
            working_directory="/tmp",)
        assert "rounds" in str(exc_info.value)

    def test_rounds_capped_at_five(self):
        """Test that rounds cannot exceed 5."""
        with pytest.raises(ValidationError) as exc_info:
            DeliberateRequest(
                question="Test?",
                participants=[
                    Participant(cli="claude", model="claude-3-5-sonnet-20241022"),
                    Participant(cli="codex", model="gpt-4"),
                ],
                rounds=10,
            working_directory="/tmp",)
        assert "rounds" in str(exc_info.value)


class TestRoundResponse:
    """Tests for RoundResponse model."""

    def test_valid_round_response(self):
        """Test creating a valid round response."""
        resp = RoundResponse(
            round=1,
            participant="claude-3-5-sonnet@claude-code",
            response="I think we should consider...",
            timestamp="2025-10-12T15:30:00Z",
        )
        assert resp.round == 1
        assert "claude-3-5-sonnet" in resp.participant


class TestDeliberationResult:
    """Tests for DeliberationResult model."""

    def test_valid_result(self):
        """Test creating a valid deliberation result."""
        result = DeliberationResult(
            status="complete",
            mode="conference",
            rounds_completed=2,
            participants=["claude-3-5-sonnet@claude-code", "gpt-4@codex"],
            summary={
                "consensus": "Strong agreement",
                "key_agreements": ["Point 1", "Point 2"],
                "key_disagreements": ["Detail A"],
                "final_recommendation": "Proceed with approach X",
            },
            transcript_path="/path/to/transcript.md",
            full_debate=[],
        )
        assert result.status == "complete"
        assert result.rounds_completed == 2


class TestVote:
    """Tests for Vote model."""

    def test_valid_vote(self):
        """Test creating a valid vote."""
        vote = Vote(
            option="Option A",
            confidence=0.85,
            rationale="This approach has lower risk and better architectural fit.",
        )
        assert vote.option == "Option A"
        assert vote.confidence == 0.85
        assert "lower risk" in vote.rationale

    def test_vote_confidence_must_be_between_0_and_1(self):
        """Test that confidence must be in range [0.0, 1.0]."""
        # Test confidence > 1.0
        with pytest.raises(ValidationError) as exc_info:
            Vote(option="Yes", confidence=1.5, rationale="Test")
        assert "confidence" in str(exc_info.value)

        # Test confidence < 0.0
        with pytest.raises(ValidationError) as exc_info:
            Vote(option="Yes", confidence=-0.1, rationale="Test")
        assert "confidence" in str(exc_info.value)

    def test_vote_edge_cases_0_and_1(self):
        """Test that confidence can be exactly 0.0 or 1.0."""
        vote_min = Vote(option="No", confidence=0.0, rationale="Completely uncertain")
        assert vote_min.confidence == 0.0

        vote_max = Vote(option="Yes", confidence=1.0, rationale="Absolutely certain")
        assert vote_max.confidence == 1.0

    def test_vote_requires_all_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            Vote(option="Yes")  # Missing confidence and rationale


class TestRoundVote:
    """Tests for RoundVote model."""

    def test_valid_round_vote(self):
        """Test creating a valid round vote."""
        vote = Vote(option="Option B", confidence=0.75, rationale="Better performance")
        round_vote = RoundVote(
            round=2,
            participant="sonnet@claude",
            vote=vote,
            timestamp="2025-10-14T00:00:00Z",
        )
        assert round_vote.round == 2
        assert round_vote.participant == "sonnet@claude"
        assert round_vote.vote.option == "Option B"
        assert round_vote.timestamp == "2025-10-14T00:00:00Z"

    def test_round_vote_requires_all_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            RoundVote(round=1, participant="test@cli")  # Missing vote and timestamp


class TestVotingResult:
    """Tests for VotingResult model."""

    def test_valid_voting_result_with_consensus(self):
        """Test voting result when consensus is reached."""
        vote1 = Vote(option="Option A", confidence=0.9, rationale="Strong reasons")
        vote2 = Vote(
            option="Option A", confidence=0.85, rationale="Agree with analysis"
        )

        round_votes = [
            RoundVote(
                round=1,
                participant="sonnet@claude",
                vote=vote1,
                timestamp="2025-10-14T00:00:00Z",
            ),
            RoundVote(
                round=1,
                participant="codex@codex",
                vote=vote2,
                timestamp="2025-10-14T00:00:01Z",
            ),
        ]

        result = VotingResult(
            final_tally={"Option A": 2, "Option B": 0},
            votes_by_round=round_votes,
            consensus_reached=True,
            winning_option="Option A",
        )
        assert result.consensus_reached is True
        assert result.winning_option == "Option A"
        assert result.final_tally["Option A"] == 2
        assert len(result.votes_by_round) == 2

    def test_valid_voting_result_no_consensus(self):
        """Test voting result when no consensus is reached."""
        vote1 = Vote(option="Option A", confidence=0.7, rationale="Reasons for A")
        vote2 = Vote(option="Option B", confidence=0.8, rationale="Reasons for B")

        round_votes = [
            RoundVote(
                round=2,
                participant="sonnet@claude",
                vote=vote1,
                timestamp="2025-10-14T00:00:00Z",
            ),
            RoundVote(
                round=2,
                participant="codex@codex",
                vote=vote2,
                timestamp="2025-10-14T00:00:01Z",
            ),
        ]

        result = VotingResult(
            final_tally={"Option A": 1, "Option B": 1},
            votes_by_round=round_votes,
            consensus_reached=False,
            winning_option=None,
        )
        assert result.consensus_reached is False
        assert result.winning_option is None
        assert result.final_tally["Option A"] == 1
        assert result.final_tally["Option B"] == 1

    def test_voting_result_requires_all_fields(self):
        """Test that all required fields are present."""
        with pytest.raises(ValidationError):
            VotingResult(final_tally={"A": 1})  # Missing other required fields
