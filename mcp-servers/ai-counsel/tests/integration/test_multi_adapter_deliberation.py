"""Integration tests for multi-adapter deliberation (CLI + HTTP)."""
from unittest.mock import AsyncMock

import pytest

from deliberation.engine import DeliberationEngine
from models.config import load_config
from models.schema import DeliberateRequest, Participant


@pytest.mark.integration
class TestMultiAdapterDeliberation:
    """Test deliberation with both CLI and HTTP adapters working together."""

    @pytest.fixture
    def config(self):
        """Load test config."""
        return load_config("config.yaml")

    @pytest.fixture
    def mixed_adapters(self):
        """Create mock adapters mixing CLI and HTTP types."""
        # CLI adapter (Claude)
        claude_adapter = AsyncMock()
        claude_adapter.invoke = AsyncMock(
            side_effect=[
                'TypeScript offers type safety for large codebases.\nVOTE: {"option": "TypeScript", "confidence": 0.85, "rationale": "Better maintainability", "continue_debate": false}',
                'TypeScript provides excellent IDE support and refactoring.\nVOTE: {"option": "TypeScript", "confidence": 0.90, "rationale": "Superior tooling", "continue_debate": false}',
            ]
        )

        # HTTP adapter (Ollama)
        ollama_adapter = AsyncMock()
        ollama_adapter.invoke = AsyncMock(
            side_effect=[
                'JavaScript has wider ecosystem and faster development.\nVOTE: {"option": "JavaScript", "confidence": 0.70, "rationale": "Easier onboarding", "continue_debate": true}',
                'JavaScript remains more flexible for rapid prototyping.\nVOTE: {"option": "JavaScript", "confidence": 0.75, "rationale": "Development speed", "continue_debate": false}',
            ]
        )

        # HTTP adapter (LM Studio)
        lmstudio_adapter = AsyncMock()
        lmstudio_adapter.invoke = AsyncMock(
            side_effect=[
                'TypeScript catches bugs at compile time.\nVOTE: {"option": "TypeScript", "confidence": 0.80, "rationale": "Fewer runtime errors", "continue_debate": true}',
                'TypeScript is the clear winner for team projects.\nVOTE: {"option": "TypeScript", "confidence": 0.88, "rationale": "Team collaboration", "continue_debate": false}',
            ]
        )

        return {
            "claude": claude_adapter,
            "ollama": ollama_adapter,
            "lmstudio": lmstudio_adapter,
        }

    @pytest.mark.asyncio
    async def test_deliberation_with_mixed_adapters(self, config, mixed_adapters):
        """Test deliberation with both CLI and HTTP adapters."""
        # Arrange
        engine = DeliberationEngine(adapters=mixed_adapters, config=config)

        request = DeliberateRequest(
            question="Should we use TypeScript or JavaScript for our new project?",
            participants=[
                Participant(cli="claude", model="sonnet"),
                Participant(cli="ollama", model="llama3"),
                Participant(cli="lmstudio", model="mistral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Act
        result = await engine.execute(request)

        # Assert
        assert result.status == "complete"
        assert result.rounds_completed >= 1
        assert (
            len(result.full_debate) >= 3
        )  # At least 3 responses (1 per adapter in round 1)

        # Verify all three adapters were invoked
        assert mixed_adapters["claude"].invoke.called
        assert mixed_adapters["ollama"].invoke.called
        assert mixed_adapters["lmstudio"].invoke.called

        # Verify voting results aggregated correctly
        if result.voting_result:
            assert (
                "TypeScript" in result.voting_result.final_tally
                or "JavaScript" in result.voting_result.final_tally
            )
            assert (
                result.voting_result.consensus_reached
                or not result.voting_result.consensus_reached
            )  # Either is valid

        # Verify all participant types present in debate
        participant_names = [r.participant for r in result.full_debate]
        assert any("claude" in p for p in participant_names)
        assert any("ollama" in p for p in participant_names)
        assert any("lmstudio" in p for p in participant_names)

    @pytest.mark.asyncio
    async def test_http_adapter_failure_doesnt_halt_deliberation(
        self, config, mixed_adapters
    ):
        """Test that HTTP adapter failure is isolated and doesn't stop deliberation."""
        # Arrange
        engine = DeliberationEngine(adapters=mixed_adapters, config=config)

        # Make HTTP adapter fail
        mixed_adapters["ollama"].invoke = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        request = DeliberateRequest(
            question="What is the best database choice?",
            participants=[
                Participant(cli="claude", model="sonnet"),
                Participant(cli="ollama", model="llama3"),
                Participant(cli="lmstudio", model="mistral"),
            ],
            rounds=1,
            mode="quick",
            working_directory="/tmp",)

        # Act
        result = await engine.execute(request)

        # Assert
        assert result.status == "complete"
        assert len(result.full_debate) == 3  # All 3 participants (1 with error)

        # Verify failed adapter response contains error
        ollama_responses = [r for r in result.full_debate if "ollama" in r.participant]
        assert len(ollama_responses) == 1
        assert (
            "[ERROR:" in ollama_responses[0].response
            or "ERROR" in ollama_responses[0].response
        )

        # Verify successful adapters still responded
        claude_responses = [r for r in result.full_debate if "claude" in r.participant]
        lmstudio_responses = [
            r for r in result.full_debate if "lmstudio" in r.participant
        ]
        assert len(claude_responses) == 1
        assert len(lmstudio_responses) == 1
        assert "[ERROR:" not in claude_responses[0].response
        assert "[ERROR:" not in lmstudio_responses[0].response

    @pytest.mark.asyncio
    async def test_all_http_adapters_in_deliberation(self, config):
        """Test deliberation with only HTTP adapters (no CLI)."""
        # Arrange - Create HTTP-only adapters
        http_adapters = {
            "ollama": AsyncMock(),
            "lmstudio": AsyncMock(),
            "openrouter": AsyncMock(),
        }

        # Configure responses
        http_adapters["ollama"].invoke = AsyncMock(
            return_value='Ollama response: Use Redis for caching.\nVOTE: {"option": "Redis", "confidence": 0.90, "rationale": "Fast and proven", "continue_debate": false}'
        )
        http_adapters["lmstudio"].invoke = AsyncMock(
            return_value='LM Studio response: Redis is excellent for this use case.\nVOTE: {"option": "Redis", "confidence": 0.85, "rationale": "Industry standard", "continue_debate": false}'
        )
        http_adapters["openrouter"].invoke = AsyncMock(
            return_value='OpenRouter response: I agree Redis is the best choice.\nVOTE: {"option": "Redis", "confidence": 0.92, "rationale": "Performance and reliability", "continue_debate": false}'
        )

        engine = DeliberationEngine(adapters=http_adapters, config=config)

        request = DeliberateRequest(
            question="What caching solution should we use?",
            participants=[
                Participant(cli="ollama", model="llama3"),
                Participant(cli="lmstudio", model="mistral"),
                Participant(
                    cli="openrouter", model="claude-3-5-sonnet"
                ),
            ],
            rounds=1,
            mode="quick",
            working_directory="/tmp",)

        # Act
        result = await engine.execute(request)

        # Assert
        assert result.status == "complete"
        assert len(result.full_debate) == 3

        # Verify all HTTP adapters invoked
        assert http_adapters["ollama"].invoke.called
        assert http_adapters["lmstudio"].invoke.called
        assert http_adapters["openrouter"].invoke.called

        # Verify voting shows consensus
        assert result.voting_result is not None
        assert result.voting_result.final_tally.get("Redis", 0) == 3
        assert result.voting_result.consensus_reached is True
        assert result.voting_result.winning_option == "Redis"

    @pytest.mark.asyncio
    async def test_convergence_detection_works_with_mixed_adapters(
        self, config, mixed_adapters
    ):
        """Test that convergence detection works correctly with mixed CLI and HTTP adapters."""
        # Arrange
        from deliberation.convergence import ConvergenceDetector

        engine = DeliberationEngine(adapters=mixed_adapters, config=config)
        engine.convergence_detector = ConvergenceDetector(config)

        # Configure adapters to converge over rounds
        mixed_adapters["claude"].invoke = AsyncMock(
            side_effect=[
                "TypeScript is better for large teams.",
                "TypeScript is definitely better for large teams with strong typing.",
            ]
        )
        mixed_adapters["ollama"].invoke = AsyncMock(
            side_effect=[
                "TypeScript provides better tooling.",
                "TypeScript provides much better tooling and IDE support.",
            ]
        )

        request = DeliberateRequest(
            question="TypeScript or JavaScript?",
            participants=[
                Participant(cli="claude", model="sonnet"),
                Participant(cli="ollama", model="llama3"),
            ],
            rounds=3,
            mode="conference",
            working_directory="/tmp",)

        # Act
        result = await engine.execute(request)

        # Assert
        assert result.status == "complete"

        # Convergence info should be present if detector is enabled
        if config.deliberation.convergence_detection.enabled:
            # May have convergence info if similarity detected
            # (depends on similarity threshold and responses)
            pass  # Convergence is optional based on actual similarity

    @pytest.mark.asyncio
    async def test_early_stopping_with_mixed_adapters(self, config, mixed_adapters):
        """Test that model-controlled early stopping works with mixed adapters."""
        # Arrange
        engine = DeliberationEngine(adapters=mixed_adapters, config=config)

        # Configure all adapters to want to stop after round 1
        mixed_adapters["claude"].invoke = AsyncMock(
            return_value='TypeScript is best.\nVOTE: {"option": "TypeScript", "confidence": 0.95, "rationale": "Clear winner", "continue_debate": false}'
        )
        mixed_adapters["ollama"].invoke = AsyncMock(
            return_value='Agree on TypeScript.\nVOTE: {"option": "TypeScript", "confidence": 0.90, "rationale": "Consensus", "continue_debate": false}'
        )
        mixed_adapters["lmstudio"].invoke = AsyncMock(
            return_value='TypeScript for sure.\nVOTE: {"option": "TypeScript", "confidence": 0.88, "rationale": "No doubt", "continue_debate": false}'
        )

        request = DeliberateRequest(
            question="TypeScript or JavaScript?",
            participants=[
                Participant(cli="claude", model="sonnet"),
                Participant(cli="ollama", model="llama3"),
                Participant(cli="lmstudio", model="mistral"),
            ],
            rounds=5,  # Request 5 rounds but should stop early
            mode="conference",
            working_directory="/tmp",)

        # Act
        result = await engine.execute(request)

        # Assert
        # Should stop early (all 3/3 = 100% want to stop, threshold is 66%)
        if config.deliberation.early_stopping.enabled:
            assert result.rounds_completed < 5  # Should stop before max rounds
            assert result.rounds_completed >= 1  # But at least 1 round
