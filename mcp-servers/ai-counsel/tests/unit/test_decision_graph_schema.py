"""Unit tests for decision graph schema models."""
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_graph.schema import (DecisionNode, DecisionSimilarity,
                                   ParticipantStance)


class TestDecisionNode:
    """Tests for DecisionNode model."""

    def test_decision_node_creation_valid_data(self):
        """Test creating node with all required fields."""
        node = DecisionNode(
            question="What should we do?",
            timestamp=datetime.now(),
            consensus="We should do X",
            convergence_status="converged",
            participants=["claude", "gpt-4"],
            transcript_path="/path/to/transcript.md",
        )
        assert node.id is not None
        assert len(node.id) > 0
        assert node.question == "What should we do?"
        assert node.consensus == "We should do X"
        assert node.convergence_status == "converged"
        assert node.participants == ["claude", "gpt-4"]
        assert node.transcript_path == "/path/to/transcript.md"

    def test_decision_node_generates_unique_uuid(self):
        """Test that each node gets a unique UUID."""
        node1 = DecisionNode(
            question="Q1",
            timestamp=datetime.now(),
            consensus="C1",
            convergence_status="converged",
            participants=[],
            transcript_path="t1",
        )
        node2 = DecisionNode(
            question="Q2",
            timestamp=datetime.now(),
            consensus="C2",
            convergence_status="refining",
            participants=[],
            transcript_path="t2",
        )
        assert node1.id != node2.id
        assert isinstance(node1.id, str)
        assert isinstance(node2.id, str)

    def test_decision_node_requires_question(self):
        """Test that question field is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionNode(
                timestamp=datetime.now(),
                consensus="C",
                convergence_status="converged",
                participants=[],
                transcript_path="t",
            )
        assert "question" in str(exc_info.value)

    def test_decision_node_question_min_length(self):
        """Test that question must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionNode(
                question="",
                timestamp=datetime.now(),
                consensus="C",
                convergence_status="converged",
                participants=[],
                transcript_path="t",
            )
        assert "question" in str(exc_info.value)

    def test_decision_node_requires_timestamp(self):
        """Test that timestamp field is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionNode(
                question="Q",
                consensus="C",
                convergence_status="converged",
                participants=[],
                transcript_path="t",
            )
        assert "timestamp" in str(exc_info.value)

    def test_decision_node_requires_consensus(self):
        """Test that consensus field is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionNode(
                question="Q",
                timestamp=datetime.now(),
                convergence_status="converged",
                participants=[],
                transcript_path="t",
            )
        assert "consensus" in str(exc_info.value)

    def test_decision_node_requires_convergence_status(self):
        """Test that convergence_status field is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionNode(
                question="Q",
                timestamp=datetime.now(),
                consensus="C",
                participants=[],
                transcript_path="t",
            )
        assert "convergence_status" in str(exc_info.value)

    def test_decision_node_requires_participants(self):
        """Test that participants field is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionNode(
                question="Q",
                timestamp=datetime.now(),
                consensus="C",
                convergence_status="converged",
                transcript_path="t",
            )
        assert "participants" in str(exc_info.value)

    def test_decision_node_requires_transcript_path(self):
        """Test that transcript_path field is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionNode(
                question="Q",
                timestamp=datetime.now(),
                consensus="C",
                convergence_status="converged",
                participants=[],
            )
        assert "transcript_path" in str(exc_info.value)

    def test_decision_node_participants_is_list(self):
        """Test that participants is stored as a list."""
        node = DecisionNode(
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=["model-a", "model-b", "model-c"],
            transcript_path="t",
        )
        assert isinstance(node.participants, list)
        assert len(node.participants) == 3
        assert node.participants[0] == "model-a"

    def test_decision_node_winning_option_optional(self):
        """Test that winning_option is optional."""
        node = DecisionNode(
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="t",
        )
        assert node.winning_option is None

    def test_decision_node_winning_option_can_be_set(self):
        """Test that winning_option can be set when provided."""
        node = DecisionNode(
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            winning_option="Option A",
            convergence_status="converged",
            participants=[],
            transcript_path="t",
        )
        assert node.winning_option == "Option A"

    def test_decision_node_metadata_defaults_to_empty_dict(self):
        """Test that metadata defaults to empty dict."""
        node = DecisionNode(
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="t",
        )
        assert node.metadata == {}
        assert isinstance(node.metadata, dict)

    def test_decision_node_metadata_can_be_set(self):
        """Test that metadata can contain custom fields."""
        metadata = {"custom_field": "value", "round_count": 3}
        node = DecisionNode(
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="t",
            metadata=metadata,
        )
        assert node.metadata == metadata
        assert node.metadata["custom_field"] == "value"
        assert node.metadata["round_count"] == 3

    def test_decision_node_with_complex_data(self):
        """Test node creation with realistic complex data."""
        node = DecisionNode(
            question="Should we migrate to microservices architecture?",
            timestamp=datetime(2024, 10, 20, 14, 30, 0),
            consensus="Yes, but with phased approach starting with user service",
            winning_option="Phased Migration",
            convergence_status="converged",
            participants=["opus@claude", "gpt-4@codex", "gemini-2.5-pro@gemini"],
            transcript_path="transcripts/20241020_143000_microservices.md",
            metadata={
                "deliberation_mode": "conference",
                "rounds_completed": 3,
                "voting_enabled": True,
            },
        )
        assert "microservices" in node.question
        assert node.winning_option == "Phased Migration"
        assert len(node.participants) == 3
        assert node.metadata["rounds_completed"] == 3


class TestParticipantStance:
    """Tests for ParticipantStance model."""

    def test_participant_stance_creation_valid_data(self):
        """Test creating stance with required fields."""
        decision_id = str(uuid4())
        stance = ParticipantStance(
            decision_id=decision_id,
            participant="claude@mcp",
            final_position="I think we should proceed with caution",
        )
        assert stance.decision_id == decision_id
        assert stance.participant == "claude@mcp"
        assert stance.final_position == "I think we should proceed with caution"

    def test_participant_stance_requires_decision_id(self):
        """Test that decision_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ParticipantStance(
                participant="p",
                final_position="pos",
            )
        assert "decision_id" in str(exc_info.value)

    def test_participant_stance_requires_participant(self):
        """Test that participant is required."""
        with pytest.raises(ValidationError) as exc_info:
            ParticipantStance(
                decision_id=str(uuid4()),
                final_position="pos",
            )
        assert "participant" in str(exc_info.value)

    def test_participant_stance_requires_final_position(self):
        """Test that final_position is required."""
        with pytest.raises(ValidationError) as exc_info:
            ParticipantStance(
                decision_id=str(uuid4()),
                participant="p",
            )
        assert "final_position" in str(exc_info.value)

    def test_participant_stance_vote_option_optional(self):
        """Test that vote_option is optional."""
        stance = ParticipantStance(
            decision_id=str(uuid4()),
            participant="model@cli",
            final_position="Position text",
        )
        assert stance.vote_option is None

    def test_participant_stance_confidence_optional(self):
        """Test that confidence is optional."""
        stance = ParticipantStance(
            decision_id=str(uuid4()),
            participant="model@cli",
            final_position="Position text",
        )
        assert stance.confidence is None

    def test_participant_stance_rationale_optional(self):
        """Test that rationale is optional."""
        stance = ParticipantStance(
            decision_id=str(uuid4()),
            participant="model@cli",
            final_position="Position text",
        )
        assert stance.rationale is None

    def test_participant_stance_confidence_valid_range(self):
        """Test that confidence accepts valid 0.0-1.0 values."""
        for confidence in [0.0, 0.25, 0.5, 0.75, 1.0]:
            stance = ParticipantStance(
                decision_id=str(uuid4()),
                participant="p",
                confidence=confidence,
                final_position="pos",
            )
            assert stance.confidence == confidence

    def test_participant_stance_confidence_too_low(self):
        """Test that confidence below 0.0 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ParticipantStance(
                decision_id=str(uuid4()),
                participant="p",
                confidence=-0.1,
                final_position="pos",
            )
        assert "confidence" in str(exc_info.value)

    def test_participant_stance_confidence_too_high(self):
        """Test that confidence above 1.0 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ParticipantStance(
                decision_id=str(uuid4()),
                participant="p",
                confidence=1.5,
                final_position="pos",
            )
        assert "confidence" in str(exc_info.value)

    def test_participant_stance_with_all_vote_fields(self):
        """Test stance with all voting-related fields."""
        stance = ParticipantStance(
            decision_id=str(uuid4()),
            participant="opus@claude",
            vote_option="Option B",
            confidence=0.85,
            rationale="Option B provides better long-term scalability",
            final_position="After considering all factors, I recommend Option B",
        )
        assert stance.vote_option == "Option B"
        assert stance.confidence == 0.85
        assert "scalability" in stance.rationale
        assert "Option B" in stance.final_position

    def test_participant_stance_with_partial_vote_fields(self):
        """Test stance with some but not all vote fields."""
        # vote_option and confidence without rationale
        stance1 = ParticipantStance(
            decision_id=str(uuid4()),
            participant="p",
            vote_option="A",
            confidence=0.9,
            final_position="pos",
        )
        assert stance1.vote_option == "A"
        assert stance1.confidence == 0.9
        assert stance1.rationale is None

        # vote_option without confidence
        stance2 = ParticipantStance(
            decision_id=str(uuid4()),
            participant="p",
            vote_option="B",
            final_position="pos",
        )
        assert stance2.vote_option == "B"
        assert stance2.confidence is None


class TestDecisionSimilarity:
    """Tests for DecisionSimilarity model."""

    def test_decision_similarity_creation(self):
        """Test creating similarity relationship."""
        source = str(uuid4())
        target = str(uuid4())
        sim = DecisionSimilarity(
            source_id=source,
            target_id=target,
            similarity_score=0.75,
        )
        assert sim.source_id == source
        assert sim.target_id == target
        assert sim.similarity_score == 0.75

    def test_decision_similarity_requires_source_id(self):
        """Test that source_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionSimilarity(
                target_id=str(uuid4()),
                similarity_score=0.5,
            )
        assert "source_id" in str(exc_info.value)

    def test_decision_similarity_requires_target_id(self):
        """Test that target_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionSimilarity(
                source_id=str(uuid4()),
                similarity_score=0.5,
            )
        assert "target_id" in str(exc_info.value)

    def test_decision_similarity_requires_score(self):
        """Test that similarity_score is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionSimilarity(
                source_id=str(uuid4()),
                target_id=str(uuid4()),
            )
        assert "similarity_score" in str(exc_info.value)

    def test_decision_similarity_score_valid_range(self):
        """Test that score accepts valid 0.0-1.0 values."""
        for score in [0.0, 0.1, 0.5, 0.9, 1.0]:
            sim = DecisionSimilarity(
                source_id=str(uuid4()),
                target_id=str(uuid4()),
                similarity_score=score,
            )
            assert sim.similarity_score == score

    def test_decision_similarity_score_too_low(self):
        """Test that score below 0.0 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionSimilarity(
                source_id=str(uuid4()),
                target_id=str(uuid4()),
                similarity_score=-0.1,
            )
        assert "similarity_score" in str(exc_info.value)

    def test_decision_similarity_score_too_high(self):
        """Test that score above 1.0 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionSimilarity(
                source_id=str(uuid4()),
                target_id=str(uuid4()),
                similarity_score=1.5,
            )
        assert "similarity_score" in str(exc_info.value)

    def test_decision_similarity_computed_at_defaults(self):
        """Test that computed_at gets default value."""
        sim = DecisionSimilarity(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            similarity_score=0.8,
        )
        assert sim.computed_at is not None
        assert isinstance(sim.computed_at, datetime)
        # Should be very recent (within last second)
        now = datetime.now()
        time_diff = abs((now - sim.computed_at).total_seconds())
        assert time_diff < 1.0

    def test_decision_similarity_computed_at_can_be_set(self):
        """Test that computed_at can be explicitly set."""
        custom_time = datetime(2024, 10, 15, 10, 30, 0)
        sim = DecisionSimilarity(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            similarity_score=0.9,
            computed_at=custom_time,
        )
        assert sim.computed_at == custom_time

    def test_decision_similarity_with_identical_ids(self):
        """Test similarity with same source and target (self-similarity)."""
        same_id = str(uuid4())
        sim = DecisionSimilarity(
            source_id=same_id,
            target_id=same_id,
            similarity_score=1.0,
        )
        assert sim.source_id == sim.target_id
        assert sim.similarity_score == 1.0

    def test_decision_similarity_edge_cases(self):
        """Test similarity with edge case values."""
        # Perfect match
        sim1 = DecisionSimilarity(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            similarity_score=1.0,
        )
        assert sim1.similarity_score == 1.0

        # No similarity
        sim2 = DecisionSimilarity(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            similarity_score=0.0,
        )
        assert sim2.similarity_score == 0.0

        # Barely similar
        sim3 = DecisionSimilarity(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            similarity_score=0.01,
        )
        assert sim3.similarity_score == 0.01

        # Highly similar
        sim4 = DecisionSimilarity(
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            similarity_score=0.99,
        )
        assert sim4.similarity_score == 0.99
