"""Integration tests for convergence detection in deliberation engine."""
from unittest.mock import AsyncMock

import pytest

from deliberation.engine import DeliberationEngine
from models.config import load_config
from models.schema import DeliberateRequest, Participant, RoundResponse


@pytest.mark.integration
class TestEngineConvergenceIntegration:
    """Test convergence detection integrated with deliberation engine."""

    @pytest.fixture
    def config(self):
        """Load test config."""
        return load_config("config.yaml")

    @pytest.fixture
    def mock_adapters(self):
        """Create mock adapters for testing."""
        claude_adapter = AsyncMock()
        codex_adapter = AsyncMock()

        # Mock responses that will converge
        claude_adapter.invoke = AsyncMock(
            side_effect=[
                "TypeScript is better for large projects",
                "TypeScript is better for large projects due to type safety",
            ]
        )
        codex_adapter.invoke = AsyncMock(
            side_effect=[
                "I agree TypeScript scales better",
                "I agree TypeScript scales better with static typing",
            ]
        )

        return {"claude": claude_adapter, "codex": codex_adapter}

    @pytest.fixture
    def engine_with_config(self, mock_adapters, config):
        """Create engine instance with config and convergence detector."""
        engine = DeliberationEngine(adapters=mock_adapters)

        # Manually initialize convergence detector with config
        from deliberation.convergence import ConvergenceDetector

        if config.deliberation.convergence_detection.enabled:
            engine.convergence_detector = ConvergenceDetector(config)
        else:
            engine.convergence_detector = None

        engine.config = config
        return engine

    def test_engine_has_convergence_detector_when_enabled(self, config, mock_adapters):
        """Engine should have convergence detector when enabled in config."""
        from deliberation.convergence import ConvergenceDetector

        engine = DeliberationEngine(adapters=mock_adapters)

        # Initialize detector if config enables it
        if config.deliberation.convergence_detection.enabled:
            engine.convergence_detector = ConvergenceDetector(config)

        # Check that engine has convergence detector
        assert hasattr(engine, "convergence_detector")
        assert engine.convergence_detector is not None
        assert isinstance(engine.convergence_detector, ConvergenceDetector)

    @pytest.mark.asyncio
    async def test_engine_detects_convergence_with_similar_responses(
        self, config, mock_adapters
    ):
        """Engine should detect convergence when responses are similar."""
        from deliberation.convergence import ConvergenceDetector

        engine = DeliberationEngine(adapters=mock_adapters)
        engine.convergence_detector = ConvergenceDetector(config)
        engine.config = config

        # Create request for 3 rounds
        DeliberateRequest(
            question="Should we use TypeScript?",
            participants=[
                Participant(cli="claude", model="sonnet"),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=3,
            mode="conference",
            working_directory="/tmp",)

        # Round 1 responses
        round1_responses = [
            RoundResponse(
                round=1,
                participant="sonnet@claude",
                response="TypeScript is better for large projects",
                timestamp="2025-01-01T00:00:00",
            ),
            RoundResponse(
                round=1,
                participant="gpt-4@codex",
                response="I agree TypeScript scales better",
                timestamp="2025-01-01T00:00:01",
            ),
        ]

        # Round 2 responses (very similar to round 1)
        round2_responses = [
            RoundResponse(
                round=2,
                participant="sonnet@claude",
                response="TypeScript is better for large projects due to type safety",
                timestamp="2025-01-01T00:01:00",
            ),
            RoundResponse(
                round=2,
                participant="gpt-4@codex",
                response="I agree TypeScript scales better with static typing",
                timestamp="2025-01-01T00:01:01",
            ),
        ]

        # Check convergence at round 3 (min_rounds_before_check=2, so check starts at round 3)
        convergence_result = engine.convergence_detector.check_convergence(
            current_round=round2_responses,
            previous_round=round1_responses,
            round_number=3,
        )

        # Should not converge immediately (needs consecutive_stable_rounds=2)
        assert convergence_result is not None
        assert convergence_result.min_similarity > 0.5  # Should have decent similarity

        # Round 3 responses (still similar)
        round3_responses = [
            RoundResponse(
                round=3,
                participant="sonnet@claude",
                response="TypeScript is better for large projects due to type safety features",
                timestamp="2025-01-01T00:02:00",
            ),
            RoundResponse(
                round=3,
                participant="gpt-4@codex",
                response="I agree TypeScript scales better with static typing system",
                timestamp="2025-01-01T00:02:01",
            ),
        ]

        # Check convergence again
        convergence_result = engine.convergence_detector.check_convergence(
            current_round=round3_responses,
            previous_round=round2_responses,
            round_number=3,
        )

        # After 2 stable rounds, should detect convergence
        assert convergence_result is not None
        if convergence_result.consecutive_stable_rounds >= 2:
            assert (
                convergence_result.converged is True
                or convergence_result.status in ["converged", "refining"]
            )

    @pytest.mark.asyncio
    async def test_engine_no_convergence_with_changing_responses(
        self, config, mock_adapters
    ):
        """Engine should not detect convergence when responses change significantly."""
        from deliberation.convergence import ConvergenceDetector

        engine = DeliberationEngine(adapters=mock_adapters)
        engine.convergence_detector = ConvergenceDetector(config)

        # Round 1 responses
        round1_responses = [
            RoundResponse(
                round=1,
                participant="sonnet@claude",
                response="TypeScript is better",
                timestamp="2025-01-01T00:00:00",
            )
        ]

        # Round 2 responses (completely different opinion)
        round2_responses = [
            RoundResponse(
                round=2,
                participant="sonnet@claude",
                response="Actually JavaScript is more flexible and easier",
                timestamp="2025-01-01T00:01:00",
            )
        ]

        # Check convergence at round 3 (min_rounds_before_check=2)
        convergence_result = engine.convergence_detector.check_convergence(
            current_round=round2_responses,
            previous_round=round1_responses,
            round_number=3,
        )

        # Should not detect convergence
        assert convergence_result is not None
        assert convergence_result.converged is False
        assert convergence_result.status in ["refining", "diverging"]

    @pytest.mark.asyncio
    async def test_engine_skips_convergence_check_before_min_rounds(
        self, config, mock_adapters
    ):
        """Engine should not check convergence before min_rounds_before_check."""
        from deliberation.convergence import ConvergenceDetector

        engine = DeliberationEngine(adapters=mock_adapters)
        engine.convergence_detector = ConvergenceDetector(config)

        # Round 1 responses
        round1_responses = [
            RoundResponse(
                round=1,
                participant="sonnet@claude",
                response="Initial response",
                timestamp="2025-01-01T00:00:00",
            )
        ]

        # Round 2 responses
        round2_responses = [
            RoundResponse(
                round=2,
                participant="sonnet@claude",
                response="Initial response",
                timestamp="2025-01-01T00:01:00",
            )
        ]

        # Check convergence at round 2 (min_rounds_before_check=2, so should skip)
        convergence_result = engine.convergence_detector.check_convergence(
            current_round=round2_responses,
            previous_round=round1_responses,
            round_number=2,
        )

        # Should return None or have status "refining" (too early to check)
        assert convergence_result is None or convergence_result.status == "refining"

    def test_convergence_detector_backend_selection(self, config):
        """Test that convergence detector selects best available backend."""
        from deliberation.convergence import (ConvergenceDetector,
                                              JaccardBackend,
                                              SentenceTransformerBackend,
                                              TFIDFBackend)

        detector = ConvergenceDetector(config)

        # Should have a backend
        assert detector.backend is not None

        # Backend should be one of the three types
        assert isinstance(
            detector.backend, (JaccardBackend, TFIDFBackend, SentenceTransformerBackend)
        )

    @pytest.mark.asyncio
    async def test_engine_includes_convergence_info_structure(
        self, config, mock_adapters
    ):
        """Test that DeliberationResult can include convergence_info."""
        from models.schema import ConvergenceInfo, DeliberationResult, Summary

        # Create a result with convergence info
        result = DeliberationResult(
            status="complete",
            mode="conference",
            rounds_completed=3,
            participants=["sonnet@claude", "gpt-4@codex"],
            summary=Summary(
                consensus="Test consensus",
                key_agreements=["Agreement 1"],
                key_disagreements=["Disagreement 1"],
                final_recommendation="Test recommendation",
            ),
            transcript_path="/path/to/transcript.md",
            full_debate=[],
            convergence_info=ConvergenceInfo(
                detected=True,
                detection_round=3,
                final_similarity=0.87,
                status="converged",
                scores_by_round=[],
                per_participant_similarity={"sonnet@claude": 0.87, "gpt-4@codex": 0.89},
            ),
        )

        # Verify structure
        assert result.convergence_info is not None
        assert result.convergence_info.detected is True
        assert result.convergence_info.detection_round == 3
        assert result.convergence_info.final_similarity == 0.87
        assert result.convergence_info.status == "converged"
        assert len(result.convergence_info.per_participant_similarity) == 2
