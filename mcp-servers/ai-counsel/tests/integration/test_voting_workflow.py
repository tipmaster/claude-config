"""Integration tests for end-to-end voting workflow.

Tests the complete voting pipeline from vote parsing through aggregation,
convergence detection, and transcript generation.
"""
from pathlib import Path

import pytest

from deliberation.convergence import ConvergenceDetector
from deliberation.engine import DeliberationEngine
from deliberation.transcript import TranscriptManager
from models.config import load_config
from models.schema import DeliberateRequest, Participant
from tests.conftest import MockAdapter


@pytest.mark.integration
class TestVotingWorkflowIntegration:
    """Test complete voting workflow from parsing to transcript."""

    @pytest.fixture
    def config(self):
        """Load test config."""
        return load_config("config.yaml")

    @pytest.fixture
    def tmp_transcript_dir(self, tmp_path):
        """Create temporary directory for transcripts."""
        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()
        return transcript_dir

    @pytest.fixture
    def mock_adapters_with_votes(self):
        """Create mock adapters that return responses with votes."""
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")
        droid_adapter = MockAdapter("droid")

        # Round 1: All vote for Option A with high confidence
        claude_adapter.invoke_mock.side_effect = [
            """After careful analysis, Option A provides better long-term value.

VOTE: {"option": "Option A", "confidence": 0.9, "rationale": "Superior scalability and maintainability", "continue_debate": true}""",
            # Round 2: Maintain vote with even higher confidence
            """I've reviewed the discussion and remain convinced Option A is best.

VOTE: {"option": "Option A", "confidence": 0.95, "rationale": "All counterarguments addressed", "continue_debate": false}""",
            # Third response for summarizer
            "Summary: Unanimous consensus on Option A with high confidence.",
        ]

        codex_adapter.invoke_mock.side_effect = [
            """I agree with the analysis favoring Option A.

VOTE: {"option": "Option A", "confidence": 0.85, "rationale": "Better performance metrics", "continue_debate": true}""",
            """After deliberation, I'm confident in Option A.

VOTE: {"option": "Option A", "confidence": 0.92, "rationale": "Consensus on key benefits", "continue_debate": false}""",
            # Third response for summarizer
            "Summary: Strong agreement on Option A based on performance data.",
        ]

        droid_adapter.invoke_mock.side_effect = [
            """Option A shows clear advantages in testing.

VOTE: {"option": "Option A", "confidence": 0.88, "rationale": "Empirical evidence supports it", "continue_debate": true}""",
            """Final assessment confirms Option A.

VOTE: {"option": "Option A", "confidence": 0.93, "rationale": "Unanimous agreement reached", "continue_debate": false}""",
            # Third response for summarizer
            "Summary: Testing evidence confirms Option A superiority.",
        ]

        return {
            "claude": claude_adapter,
            "codex": codex_adapter,
            "droid": droid_adapter,
        }

    @pytest.fixture
    def mock_adapters_split_vote(self):
        """Create mock adapters with split voting (2-1 decision)."""
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")
        droid_adapter = MockAdapter("droid")

        # Round 1: 2 vote Safety First, 1 votes Speed First
        # Using distinct option names to avoid semantic similarity grouping
        claude_adapter.invoke_mock.side_effect = [
            'Safety First is better.\n\nVOTE: {"option": "Safety First", "confidence": 0.8, "rationale": "Lower risk", "continue_debate": true}',
            'Still prefer Safety First.\n\nVOTE: {"option": "Safety First", "confidence": 0.85, "rationale": "Risk management priority", "continue_debate": false}',
            # Third response for summarizer
            "Summary: Safety First approach won with 2-1 majority decision.",
        ]

        codex_adapter.invoke_mock.side_effect = [
            'I favor Speed First.\n\nVOTE: {"option": "Speed First", "confidence": 0.75, "rationale": "Faster implementation", "continue_debate": true}',
            'Speed First remains best.\n\nVOTE: {"option": "Speed First", "confidence": 0.8, "rationale": "Time to market critical", "continue_debate": false}',
            # Third response for summarizer
            "Summary: Split decision with Speed First being minority view.",
        ]

        droid_adapter.invoke_mock.side_effect = [
            'Safety First aligns better.\n\nVOTE: {"option": "Safety First", "confidence": 0.82, "rationale": "Strategic fit", "continue_debate": true}',
            'Confirmed: Safety First.\n\nVOTE: {"option": "Safety First", "confidence": 0.87, "rationale": "Long-term strategy wins", "continue_debate": false}',
            # Third response for summarizer
            "Summary: Safety First won with solid rationale.",
        ]

        return {
            "claude": claude_adapter,
            "codex": codex_adapter,
            "droid": droid_adapter,
        }

    @pytest.mark.asyncio
    async def test_unanimous_vote_workflow(
        self, config, mock_adapters_with_votes, tmp_transcript_dir
    ):
        """Test complete workflow with unanimous voting."""
        # Setup
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(
            adapters=mock_adapters_with_votes, transcript_manager=manager
        )
        engine.convergence_detector = ConvergenceDetector(config)
        engine.config = config

        request = DeliberateRequest(
            question="Should we implement Option A or Option B?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5"),
                Participant(cli="codex", model="gpt-4"),
                Participant(cli="droid", model="claude-sonnet-4-5"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify voting results
        assert result.voting_result is not None, "Voting result should be present"
        assert result.voting_result.consensus_reached is True, "Should reach consensus"
        assert result.voting_result.winning_option == "Option A", "Option A should win"
        assert (
            result.voting_result.final_tally["Option A"] == 6
        ), "Should have 6 votes (3 participants x 2 rounds)"
        assert (
            len(result.voting_result.votes_by_round) == 6
        ), "Should have 6 vote records"

        # Verify convergence status reflects voting outcome
        if result.convergence_info:
            assert result.convergence_info.status in [
                "unanimous_consensus",
                "converged",
            ], "Status should indicate unanimous consensus"

        # Verify transcript was created
        assert result.transcript_path is not None
        transcript_path = Path(result.transcript_path)
        assert transcript_path.exists(), "Transcript file should exist"

        # Verify transcript contains voting information
        transcript_content = transcript_path.read_text()
        assert (
            "## Voting Results" in transcript_content
        ), "Transcript should have voting section"
        assert "### Final Tally" in transcript_content, "Transcript should show tally"
        assert (
            "Option A" in transcript_content
        ), "Transcript should mention winning option"
        assert (
            "6 vote(s)" in transcript_content or "6" in transcript_content
        ), "Transcript should show vote count"

    @pytest.mark.asyncio
    async def test_majority_vote_workflow(
        self, config, mock_adapters_split_vote, tmp_transcript_dir
    ):
        """Test workflow with split vote (2-1 majority decision)."""
        # Setup
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(
            adapters=mock_adapters_split_vote, transcript_manager=manager
        )
        engine.convergence_detector = ConvergenceDetector(config)
        engine.config = config

        request = DeliberateRequest(
            question="Should we prioritize safety or speed?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5"),
                Participant(cli="codex", model="gpt-4"),
                Participant(cli="droid", model="claude-sonnet-4-5"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify voting results
        assert result.voting_result is not None, "Voting result should be present"
        assert (
            result.voting_result.winning_option == "Safety First"
        ), "Safety First should win with majority"
        assert (
            result.voting_result.final_tally["Safety First"] == 4
        ), "Safety First should have 4 votes"
        assert (
            result.voting_result.final_tally["Speed First"] == 2
        ), "Speed First should have 2 votes"

        # Verify convergence status reflects majority decision
        if result.convergence_info:
            assert result.convergence_info.status in [
                "majority_decision",
                "converged",
                "refining",
            ], "Status should reflect voting outcome"

        # Verify transcript shows split vote
        transcript_path = Path(result.transcript_path)
        transcript_content = transcript_path.read_text()
        assert (
            "Safety First" in transcript_content and "Speed First" in transcript_content
        )
        assert "4 vote(s)" in transcript_content or "4" in transcript_content
        assert "2 vote(s)" in transcript_content or "2" in transcript_content

    @pytest.mark.asyncio
    async def test_continue_debate_flag_tracking(
        self, config, mock_adapters_with_votes, tmp_transcript_dir
    ):
        """Test that continue_debate flags are tracked correctly in votes."""
        # Setup
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(
            adapters=mock_adapters_with_votes, transcript_manager=manager
        )
        engine.convergence_detector = ConvergenceDetector(config)
        engine.config = config

        request = DeliberateRequest(
            question="Should we implement Option A or Option B?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5"),
                Participant(cli="codex", model="gpt-4"),
                Participant(cli="droid", model="claude-sonnet-4-5"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify continue_debate flags are tracked
        assert result.voting_result is not None

        # Round 1: all should have continue_debate=true
        round1_votes = [v for v in result.voting_result.votes_by_round if v.round == 1]
        assert len(round1_votes) == 3, "Should have 3 votes in round 1"
        for vote in round1_votes:
            assert (
                vote.vote.continue_debate is True
            ), f"{vote.participant} should want to continue in round 1"

        # Round 2: all should have continue_debate=false
        round2_votes = [v for v in result.voting_result.votes_by_round if v.round == 2]
        assert len(round2_votes) == 3, "Should have 3 votes in round 2"
        for vote in round2_votes:
            assert (
                vote.vote.continue_debate is False
            ), f"{vote.participant} should want to stop in round 2"

    @pytest.mark.asyncio
    async def test_vote_confidence_tracking(
        self, config, mock_adapters_with_votes, tmp_transcript_dir
    ):
        """Test that vote confidence levels are tracked correctly."""
        # Setup
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(
            adapters=mock_adapters_with_votes, transcript_manager=manager
        )
        engine.config = config

        request = DeliberateRequest(
            question="Should we implement Option A or Option B?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5"),
                Participant(cli="codex", model="gpt-4"),
                Participant(cli="droid", model="claude-sonnet-4-5"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify confidence values are present and valid
        assert result.voting_result is not None
        for round_vote in result.voting_result.votes_by_round:
            assert (
                0.0 <= round_vote.vote.confidence <= 1.0
            ), "Confidence should be between 0 and 1"
            assert round_vote.vote.rationale, "Each vote should have a rationale"
            assert isinstance(
                round_vote.vote.continue_debate, bool
            ), "continue_debate should be boolean"

        # Verify confidence increases in round 2 (as designed in mock)
        round1_votes = [v for v in result.voting_result.votes_by_round if v.round == 1]
        round2_votes = [v for v in result.voting_result.votes_by_round if v.round == 2]

        assert len(round1_votes) == 3, "Should have 3 votes in round 1"
        assert len(round2_votes) == 3, "Should have 3 votes in round 2"

        # Check that confidence generally increases (models become more certain)
        for participant in [
            "claude-sonnet-4-5@claude",
            "gpt-4@codex",
            "claude-sonnet-4-5@droid",
        ]:
            r1_vote = next(v for v in round1_votes if v.participant == participant)
            r2_vote = next(v for v in round2_votes if v.participant == participant)
            assert (
                r2_vote.vote.confidence >= r1_vote.vote.confidence
            ), f"{participant} confidence should not decrease"

    @pytest.mark.asyncio
    async def test_transcript_voting_section_format(
        self, config, mock_adapters_with_votes, tmp_transcript_dir
    ):
        """Test that transcript voting section is properly formatted."""
        # Setup
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(
            adapters=mock_adapters_with_votes, transcript_manager=manager
        )
        engine.config = config

        request = DeliberateRequest(
            question="Should we implement Option A or Option B?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5"),
                Participant(cli="codex", model="gpt-4"),
                Participant(cli="droid", model="claude-sonnet-4-5"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Read and verify transcript format
        transcript_path = Path(result.transcript_path)
        transcript_content = transcript_path.read_text()

        # Check voting section structure
        assert (
            "## Voting Results" in transcript_content
        ), "Should have voting results header"
        assert "### Final Tally" in transcript_content, "Should have tally section"
        assert (
            "### Votes by Round" in transcript_content
        ), "Should have votes by round section"

        # Check for winning indicator
        assert (
            "✓" in transcript_content or "winning" in transcript_content.lower()
        ), "Should indicate winning option"

        # Check for consensus status
        assert (
            "Consensus Reached:" in transcript_content
        ), "Should show consensus status"
        assert "Winning Option:" in transcript_content, "Should show winning option"

        # Check round headers
        assert "#### Round 1" in transcript_content, "Should have round 1 header"
        assert "#### Round 2" in transcript_content, "Should have round 2 header"

        # Check vote details are present
        assert "Confidence:" in transcript_content, "Should show confidence values"
        assert "Rationale:" in transcript_content, "Should show rationales"
        assert (
            "Continue Debate:" in transcript_content
        ), "Should show continue_debate flag"

    @pytest.mark.asyncio
    async def test_no_votes_workflow(self, config, tmp_transcript_dir):
        """Test workflow when no votes are cast (backward compatibility)."""
        # Setup adapters without votes
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        claude_adapter.invoke_mock.side_effect = [
            "Option A seems better based on analysis.",
            "After review, I still favor Option A.",
            # Third response for summarizer
            "Summary: Discussion favored Option A.",
        ]

        codex_adapter.invoke_mock.side_effect = [
            "I agree with the analysis.",
            "Option A is the right choice.",
            # Third response for summarizer
            "Summary: Agreement on Option A.",
        ]

        mock_adapters = {"claude": claude_adapter, "codex": codex_adapter}

        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=mock_adapters, transcript_manager=manager)
        engine.config = config

        request = DeliberateRequest(
            question="Should we implement Option A?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5"),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify no voting result when no votes present
        assert (
            result.voting_result is None
        ), "Should have no voting result when no votes cast"

        # Verify transcript doesn't have voting section
        transcript_path = Path(result.transcript_path)
        transcript_content = transcript_path.read_text()
        assert (
            "## Voting Results" not in transcript_content
        ), "Transcript should not have voting section when no votes"
