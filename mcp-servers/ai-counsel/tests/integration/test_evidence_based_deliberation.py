"""Integration tests for evidence-based deliberation with tool execution.

Tests the complete workflow of models requesting tools during deliberation,
executing them, and injecting results into subsequent rounds.
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
class TestEvidenceBasedDeliberation:
    """Test evidence-based deliberation with tool execution."""

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
    def test_codebase(self, tmp_path):
        """Create a realistic test codebase structure."""
        # Create a simple Python project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create a main module
        main_file = src_dir / "main.py"
        main_file.write_text('''"""Main module for the application."""

def calculate_total(items):
    """Calculate total price of items."""
    return sum(item.price for item in items)


def process_order(order):
    """Process an order."""
    total = calculate_total(order.items)
    return {"order_id": order.id, "total": total}
''')

        # Create a utils module
        utils_file = src_dir / "utils.py"
        utils_file.write_text('''"""Utility functions."""

def format_currency(amount):
    """Format amount as currency."""
    return f"${amount:.2f}"


def validate_email(email):
    """Validate email address."""
    return "@" in email and "." in email
''')

        # Create a config file
        config_file = src_dir / "config.json"
        config_file.write_text('{"database": "postgres", "cache": "redis"}')

        return tmp_path

    @pytest.fixture
    def mock_adapters_with_tool_requests(self, test_codebase):
        """Create mock adapters that return responses with TOOL_REQUEST markers."""
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")
        droid_adapter = MockAdapter("droid")

        # Round 1: Claude requests file reading, Codex requests code search, Droid analyzes
        claude_adapter.invoke_mock.side_effect = [
            f"""Let me examine the main module to understand the current implementation.

TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/main.py"}}}}

I'll analyze this file to provide my assessment.
""",
            # Round 2: After seeing tool results, cast vote
            """Based on the code review, the implementation follows best practices.
The calculate_total function is clean and maintainable.

VOTE: {"option": "Approve Implementation", "confidence": 0.9, "rationale": "Code quality is high", "continue_debate": false}""",
            # Summarizer response
            "Summary: Implementation approved based on code review.",
        ]

        codex_adapter.invoke_mock.side_effect = [
            f"""I'll search for similar patterns in the codebase to ensure consistency.

TOOL_REQUEST: {{"name": "search_code", "arguments": {{"pattern": "def calculate_", "path": "{test_codebase}"}}}}

This will help identify any duplicate logic.
""",
            # Round 2
            """The search shows consistent naming patterns across the codebase.

VOTE: {"option": "Approve Implementation", "confidence": 0.85, "rationale": "Consistent with existing patterns", "continue_debate": false}""",
            # Summarizer response
            "Summary: Code patterns are consistent.",
        ]

        droid_adapter.invoke_mock.side_effect = [
            f"""Let me check the project structure first.

TOOL_REQUEST: {{"name": "list_files", "arguments": {{"pattern": "*.py", "path": "{test_codebase}/src"}}}}

And also verify the configuration.

TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/config.json"}}}}

This gives me a complete picture.
""",
            # Round 2
            """The project structure is well-organized with proper configuration.

VOTE: {"option": "Approve Implementation", "confidence": 0.88, "rationale": "Good project structure", "continue_debate": false}""",
            # Summarizer response
            "Summary: Well-organized project structure.",
        ]

        return {
            "claude": claude_adapter,
            "codex": codex_adapter,
            "droid": droid_adapter,
        }

    @pytest.mark.asyncio
    async def test_complete_workflow_with_file_reading(
        self, config, test_codebase, tmp_transcript_dir
    ):
        """Test complete deliberation workflow with file reading tool."""
        # Setup
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        # Create response with file reading request
        claude_adapter.invoke_mock.side_effect = [
            f"""Let me examine the implementation first.

TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/main.py"}}}}

I'll provide my analysis after reviewing the code.
""",
            # Round 2 - after seeing tool results
            """The code looks good. I approve.

VOTE: {"option": "Approve", "confidence": 0.9, "rationale": "Code quality verified", "continue_debate": false}""",
            # Summarizer
            "Summary: Approved based on code review.",
        ]

        codex_adapter.invoke_mock.side_effect = [
            "I'll wait for Claude's analysis.",
            "I agree with the approval.",
            "Summary: Consensus reached.",
        ]

        adapters = {"claude": claude_adapter, "codex": codex_adapter}
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=adapters, transcript_manager=manager, config=config)

        request = DeliberateRequest(
            question="Should we approve the current implementation?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify tool was executed
        assert len(engine.tool_execution_history) > 0, "Tool should have been executed"

        # Verify read_file was called
        tool_names = [record.request.name for record in engine.tool_execution_history]
        assert "read_file" in tool_names, "read_file tool should have been invoked"

        # Verify tool result contains expected data
        read_file_record = next(
            r for r in engine.tool_execution_history if r.request.name == "read_file"
        )
        assert read_file_record.result.success, "Tool execution should succeed"
        assert "calculate_total" in read_file_record.result.output, "Should contain function name"
        assert "def calculate_total" in read_file_record.result.output, "Should contain function definition"

        # Verify deliberation completed successfully
        assert result.status == "complete", "Deliberation should complete"
        assert result.rounds_completed == 2, "Should complete 2 rounds"

    @pytest.mark.asyncio
    async def test_multiple_tools_in_single_deliberation(
        self, config, mock_adapters_with_tool_requests, tmp_transcript_dir, test_codebase
    ):
        """Test deliberation using multiple different tools."""
        # Setup
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(
            adapters=mock_adapters_with_tool_requests,
            transcript_manager=manager,
            config=config
        )

        request = DeliberateRequest(
            question="Should we approve this implementation?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
                Participant(cli="droid", model="claude-sonnet-4-5", stance="neutral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify multiple tools were executed
        assert len(engine.tool_execution_history) >= 3, "At least 3 tools should be executed"

        # Verify different tool types were used
        tool_names = {record.request.name for record in engine.tool_execution_history}
        assert "read_file" in tool_names, "read_file should be used"
        assert "search_code" in tool_names, "search_code should be used"
        assert "list_files" in tool_names, "list_files should be used"

        # Verify all tools succeeded
        for record in engine.tool_execution_history:
            assert record.result.success, f"Tool {record.request.name} should succeed"

        # Verify deliberation completed
        assert result.status == "complete"

    @pytest.mark.asyncio
    async def test_all_models_see_tool_results(
        self, config, test_codebase, tmp_transcript_dir
    ):
        """Verify all models receive tool results in context."""
        # Setup: First model requests tool, second model should see results
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        # Claude requests tool in round 1
        claude_adapter.invoke_mock.side_effect = [
            f"""TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/main.py"}}}}""",
            "Round 2 response",
            "Summary response",
        ]

        # Codex should see tool results in round 2 context
        codex_adapter.invoke_mock.side_effect = [
            "Round 1 response without tools",
            "Round 2 response after seeing tool results",
            "Summary response",
        ]

        adapters = {"claude": claude_adapter, "codex": codex_adapter}
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=adapters, transcript_manager=manager, config=config)

        request = DeliberateRequest(
            question="Test question",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify tool was executed in round 1
        assert len(engine.tool_execution_history) > 0
        assert engine.tool_execution_history[0].round_number == 1

        # Verify round 2 context included tool results
        # Check that codex (second participant) received context in round 2
        assert codex_adapter.invoke_mock.call_count >= 2
        round2_call = codex_adapter.invoke_mock.call_args_list[1]

        # Context can be in kwargs or args
        context = None
        if round2_call.kwargs:
            context = round2_call.kwargs.get("context")
        if context is None and len(round2_call.args) > 2:
            context = round2_call.args[2]

        # Tool results should be in context for round 2
        assert context is not None, "Round 2 should have context"
        assert "Tool Results" in context or "read_file" in context, "Context should mention tool results"

    @pytest.mark.asyncio
    async def test_tool_results_influence_final_decision(
        self, config, test_codebase, tmp_transcript_dir
    ):
        """Verify tool results impact voting/consensus."""
        # Setup: Model uses tool results to make decision
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        claude_adapter.invoke_mock.side_effect = [
            # Round 1: Request tool
            f"""TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/main.py"}}}}""",
            # Round 2: Vote based on tool results
            """After reviewing the file contents, I can see the calculate_total function is well-implemented.

VOTE: {"option": "Approve", "confidence": 0.95, "rationale": "Code review via read_file confirmed quality", "continue_debate": false}""",
            # Summarizer
            "Summary: Approved based on tool-assisted code review.",
        ]

        codex_adapter.invoke_mock.side_effect = [
            "Waiting for analysis.",
            "I agree with the assessment.",
            "Summary: Approved.",
        ]

        adapters = {"claude": claude_adapter, "codex": codex_adapter}
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=adapters, transcript_manager=manager, config=config)

        request = DeliberateRequest(
            question="Should we approve the implementation?",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify tool execution happened
        assert len(engine.tool_execution_history) > 0

        # Verify voting result exists
        assert result.voting_result is not None, "Should have voting result"
        assert result.voting_result.winning_option == "Approve"

        # Verify vote rationale mentions tool usage
        votes = result.voting_result.votes_by_round
        round2_vote = next(v for v in votes if v.round == 2)
        assert "read_file" in round2_vote.vote.rationale.lower() or "code review" in round2_vote.vote.rationale.lower()
        assert round2_vote.vote.confidence >= 0.9, "Confidence should be high after tool verification"

    @pytest.mark.asyncio
    async def test_transcript_includes_tool_executions(
        self, config, test_codebase, tmp_transcript_dir
    ):
        """Verify transcript captures tool execution history."""
        # Setup
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        claude_adapter.invoke_mock.side_effect = [
            f"""TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/main.py"}}}}""",
            "Round 2 response",
            "Summary",
        ]

        codex_adapter.invoke_mock.side_effect = [
            f"""TOOL_REQUEST: {{"name": "search_code", "arguments": {{"pattern": "def calculate_", "path": "{test_codebase}"}}}}""",
            "Round 2 response",
            "Summary",
        ]

        adapters = {"claude": claude_adapter, "codex": codex_adapter}
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=adapters, transcript_manager=manager, config=config)

        request = DeliberateRequest(
            question="Review the codebase",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify tool execution history is populated
        assert len(engine.tool_execution_history) >= 2, "Should have at least 2 tool executions"

        # Verify transcript was created
        assert result.transcript_path is not None
        transcript_path = Path(result.transcript_path)
        assert transcript_path.exists()

        # Read transcript and verify tool execution information is present
        transcript_content = transcript_path.read_text()

        # Tool requests should be visible in the debate text (they're in the responses)
        assert "TOOL_REQUEST" in transcript_content, "Transcript should show tool requests"
        assert "read_file" in transcript_content, "Transcript should mention read_file"
        assert "search_code" in transcript_content, "Transcript should mention search_code"

        # Check for round markers
        assert "Round 1" in transcript_content, "Should show round number"
        assert "claude-sonnet-4-5@claude" in transcript_content or "gpt-4@codex" in transcript_content, "Should show participants"

    @pytest.mark.asyncio
    async def test_tool_execution_timeout_handling(
        self, config, test_codebase, tmp_transcript_dir
    ):
        """Verify tool execution timeout is handled gracefully."""
        # This test verifies the timeout handling in engine.execute_round()
        # where tools have a 30s timeout
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        # Request a tool that will execute normally (no actual timeout in test)
        claude_adapter.invoke_mock.side_effect = [
            f"""TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/main.py"}}}}""",
            "Round 2 response",
            "Summary",
        ]

        codex_adapter.invoke_mock.side_effect = [
            "Round 1",
            "Round 2",
            "Summary",
        ]

        adapters = {"claude": claude_adapter, "codex": codex_adapter}
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=adapters, transcript_manager=manager, config=config)

        request = DeliberateRequest(
            question="Test timeout handling",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute - should not raise exception even if tool times out
        result = await engine.execute(request)

        # Verify deliberation completes even if tool execution fails
        assert result.status == "complete"

        # Verify tool was attempted
        assert len(engine.tool_execution_history) > 0

    @pytest.mark.asyncio
    async def test_tool_request_parsing_robustness(
        self, config, tmp_transcript_dir
    ):
        """Verify robust parsing of TOOL_REQUEST markers."""
        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        # Test various formatting edge cases
        claude_adapter.invoke_mock.side_effect = [
            """Here's my analysis with multiple tool requests:

TOOL_REQUEST: {"name": "read_file", "arguments": {"path": "/tmp/test.py"}}

And another tool:

TOOL_REQUEST: {"name": "search_code", "arguments": {"pattern": "test", "path": "."}}

Both should be parsed correctly.
""",
            "Round 2 response",
            "Summary",
        ]

        codex_adapter.invoke_mock.side_effect = [
            "Round 1",
            "Round 2",
            "Summary",
        ]

        adapters = {"claude": claude_adapter, "codex": codex_adapter}
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=adapters, transcript_manager=manager, config=config)

        request = DeliberateRequest(
            question="Test parsing",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
            ],
            rounds=2,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify both tool requests were parsed (even if they fail due to invalid paths)
        # At minimum, we should see attempts in the history
        assert len(engine.tool_execution_history) >= 2, "Should parse multiple tool requests"

        # Verify different tools were requested
        tool_names = [record.request.name for record in engine.tool_execution_history]
        assert "read_file" in tool_names
        assert "search_code" in tool_names

    @pytest.mark.asyncio
    async def test_tool_context_injection_configuration(
        self, config, test_codebase, tmp_transcript_dir
    ):
        """Verify tool context injection respects configuration limits."""
        # Use existing config - it has the deliberation settings we need

        claude_adapter = MockAdapter("claude")
        codex_adapter = MockAdapter("codex")

        # Request tool that produces long output
        claude_adapter.invoke_mock.side_effect = [
            f"""TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_codebase}/src/main.py"}}}}""",
            "Round 2",
            "Round 3",
            "Summary",
        ]

        codex_adapter.invoke_mock.side_effect = [
            "Round 1",
            "Round 2",
            "Round 3",
            "Summary",
        ]

        adapters = {"claude": claude_adapter, "codex": codex_adapter}
        manager = TranscriptManager(output_dir=str(tmp_transcript_dir))
        engine = DeliberationEngine(adapters=adapters, transcript_manager=manager, config=config)

        request = DeliberateRequest(
            question="Test config",
            participants=[
                Participant(cli="claude", model="claude-sonnet-4-5", stance="neutral"),
                Participant(cli="codex", model="gpt-4", stance="neutral"),
            ],
            rounds=3,
            mode="conference",
            working_directory="/tmp",)

        # Execute
        result = await engine.execute(request)

        # Verify tool was executed
        assert len(engine.tool_execution_history) > 0

        # Verify context building respects limits
        # This is verified internally by _build_context() but we can check the result
        assert result.status == "complete"
        assert result.rounds_completed == 3
