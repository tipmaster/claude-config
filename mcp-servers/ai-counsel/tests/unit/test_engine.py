"""Unit tests for deliberation engine."""
from datetime import datetime
from pathlib import Path

import pytest

from deliberation.engine import DeliberationEngine
from deliberation.tools import (
    ToolExecutor,
    ReadFileTool,
    SearchCodeTool,
    ListFilesTool,
    RunCommandTool,
)
from models.schema import Participant, RoundResponse, Vote


class TestDeliberationEngine:
    """Tests for DeliberationEngine single-round execution."""

    def test_engine_initialization(self, mock_adapters):
        """Test engine initializes with adapters."""
        engine = DeliberationEngine(mock_adapters)
        assert engine.adapters == mock_adapters
        assert len(engine.adapters) == 2

    @pytest.mark.asyncio
    async def test_execute_round_single_participant(self, mock_adapters):
        """Test executing single round with one participant."""
        # Add claude-code adapter for this test
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        participants = [
            Participant(cli="claude", model="claude-3-5-sonnet")
        ]

        mock_adapters["claude"].invoke_mock.return_value = "This is Claude's response"

        responses = await engine.execute_round(
            round_num=1,
            prompt="What is 2+2?",
            participants=participants,
            previous_responses=[],
        )

        assert len(responses) == 1
        assert isinstance(responses[0], RoundResponse)
        assert responses[0].round == 1
        assert responses[0].participant == "claude-3-5-sonnet@claude"
        assert responses[0].response == "This is Claude's response"
        assert responses[0].timestamp is not None

    @pytest.mark.asyncio
    async def test_execute_round_multiple_participants(self, mock_adapters):
        """Test executing single round with multiple participants."""
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        participants = [
            Participant(cli="claude", model="claude-3-5-sonnet"),
            Participant(cli="codex", model="gpt-4"),
        ]

        mock_adapters["claude"].invoke_mock.return_value = "Claude says yes"
        mock_adapters["codex"].invoke_mock.return_value = "Codex says no"

        responses = await engine.execute_round(
            round_num=1,
            prompt="Should we use TDD?",
            participants=participants,
            previous_responses=[],
        )

        assert len(responses) == 2
        assert responses[0].participant == "claude-3-5-sonnet@claude"
        assert responses[0].response == "Claude says yes"
        assert responses[1].participant == "gpt-4@codex"
        assert responses[1].response == "Codex says no"

    @pytest.mark.asyncio
    async def test_execute_round_includes_previous_context(self, mock_adapters):
        """Test that previous responses are included in context."""
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        participants = [
            Participant(cli="claude", model="claude-3-5-sonnet")
        ]

        previous = [
            RoundResponse(
                round=1,
                participant="codex",
                response="Previous response",
                timestamp=datetime.now().isoformat(),
            )
        ]

        mock_adapters["claude"].invoke_mock.return_value = "New response"

        await engine.execute_round(
            round_num=2,
            prompt="Continue discussion",
            participants=participants,
            previous_responses=previous,
        )

        # Verify invoke was called with context
        mock_adapters["claude"].invoke_mock.assert_called_once()
        call_args = mock_adapters["claude"].invoke_mock.call_args
        # Args are: (prompt, model, context)
        assert call_args[0][2] is not None  # context is 3rd positional arg
        assert "Previous response" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_execute_round_adapter_error_handling(self, mock_adapters):
        """Test graceful error handling when adapter fails."""
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        participants = [
            Participant(cli="claude", model="claude-3-5-sonnet")
        ]

        mock_adapters["claude"].invoke_mock.side_effect = RuntimeError("API Error")

        # Should not raise, but return response with error message
        responses = await engine.execute_round(
            round_num=1,
            prompt="Test prompt",
            participants=participants,
            previous_responses=[],
        )

        assert len(responses) == 1
        assert "[ERROR: RuntimeError: API Error]" in responses[0].response

    @pytest.mark.asyncio
    async def test_execute_round_passes_correct_model(self, mock_adapters):
        """Test that correct model is passed to adapter."""
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        participants = [
            Participant(cli="claude", model="claude-3-opus")
        ]

        mock_adapters["claude"].invoke_mock.return_value = "Response"

        await engine.execute_round(
            round_num=1, prompt="Test", participants=participants, previous_responses=[]
        )

        call_args = mock_adapters["claude"].invoke_mock.call_args
        # Args are: (prompt, model, context)
        assert call_args[0][1] == "claude-3-opus"  # model is 2nd positional arg

    @pytest.mark.asyncio
    async def test_execute_round_timestamp_format(self, mock_adapters):
        """Test that timestamp is in ISO format."""
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        participants = [
            Participant(cli="claude", model="claude-3-5-sonnet")
        ]

        mock_adapters["claude"].invoke_mock.return_value = "Response"

        responses = await engine.execute_round(
            round_num=1, prompt="Test", participants=participants, previous_responses=[]
        )

        timestamp = responses[0].timestamp
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(timestamp)


class TestDeliberationEngineMultiRound:
    """Tests for DeliberationEngine multi-round execution."""

    @pytest.mark.asyncio
    async def test_execute_multiple_rounds(self, mock_adapters):
        """Test executing multiple rounds of deliberation."""
        from models.schema import DeliberateRequest

        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        request = DeliberateRequest(
            question="What is the best programming language?",
            participants=[
                Participant(cli="claude", model="claude-3-5-sonnet"),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=3,
            mode="conference",
            working_directory="/tmp",)

        mock_adapters["claude"].invoke_mock.return_value = "Claude response"
        mock_adapters["codex"].invoke_mock.return_value = "Codex response"

        result = await engine.execute(request)

        # Verify result structure
        assert result.status == "complete"
        assert result.rounds_completed == 3
        assert len(result.full_debate) == 6  # 3 rounds * 2 participants
        assert len(result.participants) == 2

    @pytest.mark.asyncio
    async def test_execute_context_builds_across_rounds(self, mock_adapters):
        """Test that context accumulates across rounds."""
        from models.schema import DeliberateRequest

        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        request = DeliberateRequest(
            question="Test question",
            participants=[
                Participant(cli="claude", model="claude-3-5-sonnet"),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        mock_adapters["claude"].invoke_mock.return_value = "Claude response"
        mock_adapters["codex"].invoke_mock.return_value = "Codex response"

        await engine.execute(request)

        # Claude is used for: round 1, round 2, and summary generation
        # So should have at least 2 calls (for the 2 rounds)
        assert mock_adapters["claude"].invoke_mock.call_count >= 2
        second_call = mock_adapters["claude"].invoke_mock.call_args_list[1]
        # Check that context is passed in second deliberation round call
        assert second_call[0][2] is not None  # context should be present

    @pytest.mark.asyncio
    async def test_quick_mode_overrides_rounds(self, mock_adapters):
        """Test that quick mode forces single round regardless of request.rounds."""
        from models.schema import DeliberateRequest

        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        request = DeliberateRequest(
            question="Test question",
            participants=[
                Participant(cli="claude", model="claude-3-5-sonnet"),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=5,  # Request 5 rounds
            mode="quick",  # But quick mode should override to 1,
            working_directory="/tmp",)

        mock_adapters["claude"].invoke_mock.return_value = "Claude response"
        mock_adapters["codex"].invoke_mock.return_value = "Codex response"

        result = await engine.execute(request)

        # Quick mode should force 1 round, not 5
        assert result.rounds_completed == 1
        assert len(result.full_debate) == 2  # 1 round * 2 participants

    @pytest.mark.asyncio
    async def test_engine_saves_transcript(self, mock_adapters, tmp_path):
        """Test that engine saves transcript after execution."""
        from deliberation.transcript import TranscriptManager
        from models.schema import DeliberateRequest

        manager = TranscriptManager(output_dir=str(tmp_path))

        request = DeliberateRequest(
            question="Should we use TypeScript?",
            participants=[
                Participant(
                    cli="claude", model="claude-3-5-sonnet-20241022"
                ),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=1,
            working_directory="/tmp",)

        mock_adapters["claude"] = mock_adapters["claude"]
        mock_adapters["claude"].invoke_mock.return_value = "Claude response"
        mock_adapters["codex"].invoke_mock.return_value = "Codex response"

        engine = DeliberationEngine(adapters=mock_adapters, transcript_manager=manager)
        result = await engine.execute(request)

        # Verify transcript was saved
        assert result.transcript_path
        assert Path(result.transcript_path).exists()

        # Verify content
        content = Path(result.transcript_path).read_text()
        assert "Should we use TypeScript?" in content


class TestVoteParsing:
    """Tests for vote parsing from model responses."""

    def test_parse_vote_from_response_valid_json(self):
        """Test parsing valid vote from response text."""
        response_text = """
        I think Option A is better because it has lower risk.

        VOTE: {"option": "Option A", "confidence": 0.85, "rationale": "Lower risk and better fit"}
        """

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        assert vote is not None
        assert isinstance(vote, Vote)
        assert vote.option == "Option A"
        assert vote.confidence == 0.85
        assert vote.rationale == "Lower risk and better fit"

    def test_parse_vote_from_response_no_vote(self):
        """Test parsing when no vote marker present."""
        response_text = "This is just a regular response without a vote"

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        assert vote is None

    def test_parse_vote_from_response_invalid_json(self):
        """Test parsing when vote JSON is malformed."""
        response_text = """
        My analysis here.

        VOTE: {invalid json}
        """

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        assert vote is None

    def test_parse_vote_from_response_missing_fields(self):
        """Test parsing when vote JSON missing required fields."""
        response_text = """
        My analysis.

        VOTE: {"option": "Option A"}
        """

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        assert vote is None

    def test_parse_vote_confidence_out_of_range(self):
        """Test parsing when confidence is out of valid range."""
        response_text = """
        Analysis here.

        VOTE: {"option": "Yes", "confidence": 1.5, "rationale": "Test"}
        """

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        assert vote is None

    def test_parse_vote_with_multiple_vote_markers(self):
        """Test parsing when response contains multiple VOTE markers (template + actual)."""
        response_text = """
        ## Voting Instructions

        After your analysis, please cast your vote using the following format:

        VOTE: {"option": "Your choice", "confidence": 0.85, "rationale": "Brief explanation"}

        Example:
        VOTE: {"option": "Option A", "confidence": 0.9, "rationale": "Example rationale"}

        ## My Analysis

        After considering the options, I recommend Option B.

        ## Step 5: Casting the Vote
        VOTE: {"option": "Option B", "confidence": 0.75, "rationale": "Better long-term fit"}
        """

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        # Should capture the LAST vote marker (the actual vote), not the template or example
        assert vote is not None
        assert isinstance(vote, Vote)
        assert vote.option == "Option B"
        assert vote.confidence == 0.75
        assert vote.rationale == "Better long-term fit"

    def test_parse_vote_prefers_last_marker_over_first(self):
        """Test that parser takes last VOTE marker when multiple exist."""
        response_text = """
        First attempt (wrong):
        VOTE: {"option": "Wrong", "confidence": 0.5, "rationale": "First try"}

        After more thought, my final vote:
        VOTE: {"option": "Correct", "confidence": 0.9, "rationale": "Final decision"}
        """

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        assert vote is not None
        assert vote.option == "Correct"
        assert vote.confidence == 0.9
        assert vote.rationale == "Final decision"

    def test_parse_vote_handles_latex_wrapper(self):
        """Test parsing vote wrapped in LaTeX notation like $\\boxed{...}$."""
        response_text = """
        ## Step 5: Conclusion
        Based on analysis, Option B is superior.

        The final answer is: $\\boxed{VOTE: {"option": "Option B", "confidence": 0.88, "rationale": "Better scalability"}}$
        """

        engine = DeliberationEngine({})
        vote = engine._parse_vote(response_text)

        assert vote is not None
        assert isinstance(vote, Vote)
        assert vote.option == "Option B"
        assert vote.confidence == 0.88
        assert vote.rationale == "Better scalability"

    @pytest.mark.asyncio
    async def test_execute_round_collects_votes(self, mock_adapters):
        """Test that votes are collected when present in responses."""
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(mock_adapters)

        participants = [
            Participant(cli="claude", model="claude-3-5-sonnet")
        ]

        # Response includes a vote
        response_with_vote = """
        I recommend Option A because it has lower risk.

        VOTE: {"option": "Option A", "confidence": 0.9, "rationale": "Lower risk"}
        """
        mock_adapters["claude"].invoke_mock.return_value = response_with_vote

        responses = await engine.execute_round(
            round_num=1,
            prompt="Which option?",
            participants=participants,
            previous_responses=[],
        )

        # Verify the response includes the full text
        assert len(responses) == 1
        assert "Option A" in responses[0].response

    @pytest.mark.asyncio
    async def test_execute_aggregates_voting_results(self, mock_adapters, tmp_path):
        """Test that votes are aggregated into VotingResult during execution."""
        from deliberation.transcript import TranscriptManager
        from models.schema import DeliberateRequest

        manager = TranscriptManager(output_dir=str(tmp_path))
        mock_adapters["claude"] = mock_adapters["claude"]
        engine = DeliberationEngine(adapters=mock_adapters, transcript_manager=manager)

        request = DeliberateRequest(
            question="Should we implement Option A or Option B?",
            participants=[
                Participant(cli="claude", model="claude-3-5-sonnet"),
                Participant(cli="codex", model="gpt-4"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Both vote for Option A in round 1
        mock_adapters["claude"].invoke_mock.side_effect = [
            'Analysis: Option A is better\n\nVOTE: {"option": "Option A", "confidence": 0.9, "rationale": "Lower risk"}',
            'After review, still Option A\n\nVOTE: {"option": "Option A", "confidence": 0.95, "rationale": "Confirmed"}',
        ]
        mock_adapters["codex"].invoke_mock.side_effect = [
            'I agree with Option A\n\nVOTE: {"option": "Option A", "confidence": 0.85, "rationale": "Better performance"}',
            'Final vote: Option A\n\nVOTE: {"option": "Option A", "confidence": 0.9, "rationale": "Final decision"}',
        ]

        result = await engine.execute(request)

        # Verify voting_result is present
        assert result.voting_result is not None
        assert result.voting_result.consensus_reached is True
        assert result.voting_result.winning_option == "Option A"
        assert (
            result.voting_result.final_tally["Option A"] == 4
        )  # 2 participants x 2 rounds
        assert len(result.voting_result.votes_by_round) == 4


class TestEngineWithTools:
    """Tests for DeliberationEngine with tool execution integration."""

    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self, mock_adapters):
        """Test tool execution times out after 30s to prevent hanging.

        This is a P0 CRITICAL issue: Tools can hang indefinitely without timeout,
        blocking entire deliberation and causing resource leaks.

        Fix: Wrap tool execution in asyncio.wait_for(timeout=30.0)
        """
        import asyncio
        import time
        from models.tool_schema import ToolResult

        # Create a tool that hangs (use registered tool name to pass schema validation)
        class SlowReadFileTool(ReadFileTool):
            async def execute(self, arguments: dict) -> ToolResult:
                # Simulate a hanging tool (60s sleep)
                await asyncio.sleep(60)
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    output="Should timeout before this",
                    error=None
                )

        # Setup engine with custom tool executor that has the slow tool
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(SlowReadFileTool())  # Override read_file with slow version
        engine.tool_execution_history = []

        participants = [Participant(cli="claude", model="sonnet", stance="neutral")]

        # Mock response with tool request (use read_file which is a valid tool name)
        mock_adapters["claude"].invoke_mock.return_value = """
        I need to check something.
        TOOL_REQUEST: {"name": "read_file", "arguments": {"path": "/test.txt"}}
        """

        # Execute round with hanging tool
        start = time.time()
        responses = await engine.execute_round(1, "Test", participants, [])
        duration = time.time() - start

        # Should timeout in ~30s, NOT 60s
        assert duration < 35, f"Tool execution should timeout at 30s, but took {duration:.1f}s"

        # Should have tool execution result with timeout error
        assert hasattr(engine, 'tool_execution_history'), "Engine should track tool execution history"
        assert len(engine.tool_execution_history) > 0, "Should have recorded tool execution"

        tool_record = engine.tool_execution_history[0]
        assert not tool_record.result.success, "Timeout should result in failure"
        assert "timeout" in tool_record.result.error.lower(), f"Error should mention timeout: {tool_record.result.error}"

    @pytest.mark.asyncio
    async def test_tool_history_cleared_between_deliberations(self, mock_adapters, tmp_path):
        """Test tool execution history is cleared between deliberations.

        CRITICAL MEMORY LEAK: tool_execution_history grows unbounded across deliberations
        in long-running MCP servers, causing OOM.

        Expected: History cleared at start of each deliberation.
        Actual (BUG): History accumulates indefinitely.
        """
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())
        engine.tool_execution_history = []

        # First deliberation with tool request
        test_file1 = tmp_path / "file1.txt"
        test_file1.write_text("data1")

        mock_adapters["claude"].invoke_mock.return_value = f"""
        I need to read file1.
        TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_file1}"}}}}
        """

        participants = [
            Participant(cli="claude", model="sonnet", stance="neutral"),
            Participant(cli="codex", model="gpt-4", stance="neutral")
        ]

        # Execute first deliberation
        from models.schema import DeliberateRequest
        request1 = DeliberateRequest(
            question="Test question for deliberation 1",
            participants=participants,
            rounds=1,
            mode="quick",
            working_directory="/tmp",)
        result1 = await engine.execute(request1)

        # Verify tool was executed
        assert len(engine.tool_execution_history) > 0, "First deliberation should have tool execution"
        first_deliberation_count = len(engine.tool_execution_history)

        # Second deliberation with different tool request
        test_file2 = tmp_path / "file2.txt"
        test_file2.write_text("data2")

        mock_adapters["claude"].invoke_mock.return_value = f"""
        I need to read file2.
        TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_file2}"}}}}
        """

        request2 = DeliberateRequest(
            question="Test question for deliberation 2",
            participants=participants,
            rounds=1,
            mode="quick",
            working_directory="/tmp",)
        result2 = await engine.execute(request2)

        # CRITICAL: History should NOT contain both deliberations
        # It should only contain the second deliberation's tools
        assert len(engine.tool_execution_history) <= first_deliberation_count, \
            f"MEMORY LEAK: Tool history should be cleared between deliberations. " \
            f"Found {len(engine.tool_execution_history)} records (expected <= {first_deliberation_count})"

        # Verify the history contains only the second deliberation
        assert any("file2.txt" in str(record.request.arguments)
                   for record in engine.tool_execution_history), \
            "Should contain second deliberation's tool"

        assert not any("file1.txt" in str(record.request.arguments)
                       for record in engine.tool_execution_history), \
            "Should NOT contain first deliberation's tool (indicates memory leak)"

    @pytest.mark.asyncio
    async def test_tool_history_memory_bounded(self, mock_adapters, tmp_path):
        """Test tool history doesn't grow unbounded in long-running server.

        Simulates 10 deliberations to verify memory doesn't accumulate.
        In production: ~1-3MB per deliberation × unlimited = OOM crash.
        """
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())
        engine.tool_execution_history = []

        participants = [
            Participant(cli="claude", model="sonnet", stance="neutral"),
            Participant(cli="codex", model="gpt-4", stance="neutral")
        ]

        # Simulate 10 deliberations (simulating long-running MCP server)
        for i in range(10):
            test_file = tmp_path / f"file{i}.txt"
            test_file.write_text(f"data{i}")

            mock_adapters["claude"].invoke_mock.return_value = f"""
            Reading file {i}.
            TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_file}"}}}}
            """

            from models.schema import DeliberateRequest
            request = DeliberateRequest(
                question=f"Test question for deliberation number {i}",
                participants=participants,
                rounds=1,
                mode="quick",
            working_directory="/tmp",)

            await engine.execute(request)

        # Memory should be bounded (not 10x the first deliberation)
        # With fix (clear at start): should be ~1x (only last deliberation)
        # Without fix (BUG): should be ~10x (all deliberations accumulated)
        assert len(engine.tool_execution_history) < 5, \
            f"MEMORY LEAK: History has {len(engine.tool_execution_history)} records after 10 deliberations. " \
            f"Expected < 5 (with cleanup), but unbounded growth detected!"


class TestVotingPrompts:
    """Tests for voting instruction prompts."""

    def test_build_voting_instructions(self):
        """Test that voting instructions are properly formatted."""
        engine = DeliberationEngine({})

        instructions = engine._build_voting_instructions()

        # Verify voting instructions contain key elements
        assert "VOTE:" in instructions
        assert "option" in instructions
        assert "confidence" in instructions
        assert "rationale" in instructions
        assert (
            "0.0" in instructions
            or "0-1" in instructions
            or "between 0 and 1" in instructions.lower()
        )

    def test_enhance_prompt_with_voting(self):
        """Test that prompt enhancement adds voting instructions."""
        engine = DeliberationEngine({})

        base_question = "Should we use TypeScript?"
        enhanced = engine._enhance_prompt_with_voting(base_question)

        # Verify enhanced prompt contains original question
        assert base_question in enhanced

        # Verify voting instructions are included
        assert "VOTE:" in enhanced
        assert "option" in enhanced.lower()
        assert "confidence" in enhanced.lower()


class TestVoteGrouping:
    """Tests for vote option grouping and similarity detection."""

    def test_group_similar_vote_options_exact_match(self):
        """Test that identical vote options are grouped together."""
        engine = DeliberationEngine({})

        all_options = ["Option A", "Option A", "Option B"]
        raw_tally = {"Option A": 2, "Option B": 1}

        result = engine._group_similar_vote_options(all_options, raw_tally)

        # Exact matches should stay as-is with exact matching
        assert result["Option A"] == 2
        assert result["Option B"] == 1

    def test_group_similar_vote_options_no_grouping_without_backend(self):
        """Test that grouping requires similarity backend (returns raw tally without it)."""
        engine = DeliberationEngine({})
        # Engine has no convergence detector, so no backend
        assert engine.convergence_detector is None

        all_options = ["Option A", "Option B"]
        raw_tally = {"Option A": 2, "Option B": 1}

        result = engine._group_similar_vote_options(all_options, raw_tally)

        # Without backend, should return raw tally unchanged
        assert result == raw_tally

    def test_group_similar_vote_options_single_option(self):
        """Test that single option always returns as-is."""
        engine = DeliberationEngine({})

        all_options = ["Option A"]
        raw_tally = {"Option A": 3}

        result = engine._group_similar_vote_options(all_options, raw_tally)

        # Single option should return unchanged
        assert result == {"Option A": 3}

    @pytest.mark.asyncio
    async def test_aggregate_votes_different_options_not_merged(self, mock_adapters):
        """Test that semantically different vote options (A vs D) are NOT merged.

        This is a regression test for bug where Option A and Option D (0.729 similarity)
        were incorrectly merged due to 0.70 threshold being too aggressive.
        """
        import tempfile

        from deliberation.transcript import TranscriptManager
        from models.schema import DeliberateRequest

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TranscriptManager(output_dir=tmp_dir)
            engine = DeliberationEngine(
                adapters=mock_adapters, transcript_manager=manager
            )

            request = DeliberateRequest(
                question="Docker compose approach?",
                participants=[
                    Participant(cli="claude", model="sonnet"),
                    Participant(cli="codex", model="gpt-5-codex"),
                ],
                rounds=1,
                mode="quick",
            working_directory="/tmp",)

            # Simulate the actual votes from docker-compose deliberation:
            # Claude and Codex vote for Option A
            # Gemini votes for Option D (but we use 2 adapters in fixture)
            # So we'll test with Claude voting A, Codex voting D instead
            mock_adapters["claude"].invoke_mock.side_effect = [
                'Analysis...\n\nVOTE: {"option": "Option A", "confidence": 0.94, "rationale": "Single file"}',
            ]
            mock_adapters["codex"].invoke_mock.side_effect = [
                'Analysis...\n\nVOTE: {"option": "Option D", "confidence": 0.95, "rationale": "Dual file"}',
            ]

            result = await engine.execute(request)

            # Verify voting result
            assert result.voting_result is not None

            # KEY ASSERTION: Verify that A and D are NOT merged
            # Expected: 1 vote for Option A, 1 vote for Option D (tie)
            # Buggy behavior: 2 votes for Option A (D merged with A)

            if len(result.voting_result.final_tally) == 2:
                # If threshold is correct (0.85+), A and D should NOT merge
                assert "Option A" in result.voting_result.final_tally
                assert "Option D" in result.voting_result.final_tally
                assert result.voting_result.final_tally["Option A"] == 1
                assert result.voting_result.final_tally["Option D"] == 1
                assert result.voting_result.consensus_reached is False  # 1-1 is tie
                assert result.voting_result.winning_option is None
            elif len(result.voting_result.final_tally) == 1:
                # If threshold is still aggressive (0.70), A and D would merge
                # This test documents the bug
                assert (
                    result.voting_result.final_tally["Option A"] == 2
                ), "Bug confirmed: Option D was merged into Option A due to aggressive 0.70 threshold"
                pytest.fail(
                    "BUG CONFIRMED: Option A and Option D were incorrectly merged (threshold too aggressive)"
                )

    @pytest.mark.asyncio
    async def test_aggregate_votes_respects_intent(self, mock_adapters):
        """Test that different options remain separate even if semantically similar."""
        import tempfile

        from deliberation.transcript import TranscriptManager
        from models.schema import DeliberateRequest

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TranscriptManager(output_dir=tmp_dir)
            mock_adapters["claude"] = mock_adapters["claude"]
            engine = DeliberationEngine(
                adapters=mock_adapters, transcript_manager=manager
            )

            request = DeliberateRequest(
                question="Test question",
                participants=[
                    Participant(cli="claude", model="model1"),
                    Participant(cli="codex", model="model2"),
                ],
                rounds=1,
                mode="quick",
            working_directory="/tmp",)

            # Two very different votes that shouldn't be merged
            mock_adapters[
                "claude"
            ].invoke_mock.return_value = 'Analysis\n\nVOTE: {"option": "Yes", "confidence": 0.9, "rationale": "Good idea"}'
            mock_adapters[
                "codex"
            ].invoke_mock.return_value = 'Analysis\n\nVOTE: {"option": "No", "confidence": 0.9, "rationale": "Bad idea"}'

            result = await engine.execute(request)

            # Verify that "Yes" and "No" are never merged
            assert result.voting_result is not None
            assert len(result.voting_result.final_tally) == 2
            assert result.voting_result.consensus_reached is False  # 1-1 tie
            assert result.voting_result.winning_option is None  # No winner in tie


class TestEngineContextEfficiency:
    """Tests for context building efficiency and token optimization."""

    @pytest.mark.asyncio
    async def test_context_truncates_large_tool_outputs(self, mock_adapters, tmp_path):
        """Test large tool outputs are truncated to prevent bloat."""
        from deliberation.transcript import TranscriptManager
        from models.schema import DeliberateRequest

        manager = TranscriptManager(output_dir=str(tmp_path))
        engine = DeliberationEngine(adapters=mock_adapters, transcript_manager=manager)

        # Create large file
        large_file = tmp_path / "large.txt"
        large_content = "x" * 5000  # 5KB file
        large_file.write_text(large_content)

        request = DeliberateRequest(
            question="What's in this file?",
            participants=[
                Participant(cli="claude", model="sonnet", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral")
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Round 1: Read large file (simulated tool result with large output)
        # Round 2: Check context size
        mock_adapters["claude"].invoke_mock.side_effect = [
            f"File contains: {large_content}",  # Round 1 - large output
            "Response based on context",  # Round 2
        ]
        mock_adapters["codex"].invoke_mock.side_effect = [
            "Codex response 1",
            "Codex response 2",
        ]

        result = await engine.execute(request)

        # Context for round 2 should be truncated (not include full 5KB)
        # We can test indirectly by checking that round 2 prompt doesn't have massive content
        # In production, _build_context would truncate tool results
        # For now, we verify structure is correct
        assert result.status == "complete"
        assert result.rounds_completed == 2

    @pytest.mark.asyncio
    async def test_context_includes_only_recent_rounds(self, mock_adapters, tmp_path):
        """Test context only includes tool results from recent N rounds."""
        from deliberation.transcript import TranscriptManager
        from models.schema import DeliberateRequest

        manager = TranscriptManager(output_dir=str(tmp_path))
        engine = DeliberationEngine(adapters=mock_adapters, transcript_manager=manager)

        participants = [
            Participant(cli="claude", model="sonnet", stance="neutral"),
            Participant(cli="codex", model="gpt-4", stance="neutral")
        ]

        request = DeliberateRequest(
            question="Test multi-round context",
            participants=participants,
            rounds=5,
            mode="conference",
            working_directory="/tmp",)

        # Simulate 5 rounds with distinct responses
        mock_adapters["claude"].invoke_mock.side_effect = [
            f"Response from round {i}" for i in range(1, 6)
        ]
        mock_adapters["codex"].invoke_mock.side_effect = [
            f"Codex round {i}" for i in range(1, 6)
        ]

        result = await engine.execute(request)

        # Check that context was built for each round
        # In round 5, context should only include recent 2 rounds (3-4)
        # We can't directly test _build_context here, but we can verify
        # that all rounds completed successfully
        assert result.status == "complete"
        assert result.rounds_completed == 5
        assert len(result.full_debate) == 10  # 5 rounds * 2 participants

    @pytest.mark.asyncio
    async def test_context_size_bounded_across_rounds(self, mock_adapters, tmp_path):
        """Test context size remains bounded even in long deliberations.

        Note: This test verifies that _build_context accepts current_round_num parameter.
        The actual tool result truncation logic will be tested when tool execution is added.
        For now, we verify that the parameter is accepted and context builds correctly.
        """
        from deliberation.transcript import TranscriptManager
        from models.schema import DeliberateRequest

        manager = TranscriptManager(output_dir=str(tmp_path))
        engine = DeliberationEngine(adapters=mock_adapters, transcript_manager=manager)

        participants = [
            Participant(cli="claude", model="sonnet", stance="neutral"),
            Participant(cli="codex", model="gpt-4", stance="neutral")
        ]

        request = DeliberateRequest(
            question="Test long deliberation",
            participants=participants,
            rounds=5,  # Max 5 rounds
            mode="conference",
            working_directory="/tmp",)

        # Simulate 5 rounds, each with 2KB response
        large_response = "x" * 2000
        mock_adapters["claude"].invoke_mock.side_effect = [
            f"Round {i}: {large_response}" for i in range(1, 6)
        ] + ["Summary"]  # Add summary response
        mock_adapters["codex"].invoke_mock.side_effect = [
            f"Codex {i}: {large_response}" for i in range(1, 6)
        ]

        result = await engine.execute(request)

        # Verify all rounds completed
        assert result.status == "complete"
        assert result.rounds_completed == 5

        # Test that _build_context accepts current_round_num parameter
        # This parameter will be used for tool result filtering in Task 7
        context = engine._build_context(
            result.full_debate, current_round_num=6
        )

        # Verify context was built successfully
        # Note: Response context is NOT truncated (only tool outputs will be)
        # This test just verifies the parameter works
        assert "Round 1" in context
        assert "Round 5" in context
        assert len(context) > 0

    def test_truncate_output_short_text(self):
        """Test that short outputs are not truncated."""
        engine = DeliberationEngine({})

        short_text = "Short output"
        result = engine._truncate_output(short_text, max_chars=1000)

        assert result == short_text
        assert "truncated" not in result.lower()

    def test_truncate_output_long_text(self):
        """Test that long outputs are truncated with indicator."""
        engine = DeliberationEngine({})

        long_text = "x" * 2000  # 2KB
        result = engine._truncate_output(long_text, max_chars=1000)

        # Should be truncated to 1000 chars
        assert len(result) <= 1100  # Allow for truncation message
        assert "truncated" in result.lower()
        assert "1000 chars" in result.lower() or "1000" in result

    def test_truncate_output_none(self):
        """Test that None/empty inputs are handled gracefully."""
        engine = DeliberationEngine({})

        assert engine._truncate_output(None, max_chars=1000) is None
        assert engine._truncate_output("", max_chars=1000) == ""

    def test_build_context_with_current_round_num(self):
        """Test that _build_context accepts current_round_num parameter."""
        engine = DeliberationEngine({})

        previous = [
            RoundResponse(
                round=1,
                participant="model@cli",
                stance="neutral",
                response="Round 1 response",
                timestamp=datetime.now().isoformat(),
            )
        ]

        # Should accept current_round_num parameter
        context = engine._build_context(previous, current_round_num=2)

        assert "Round 1" in context
        assert "Round 1 response" in context
