"""Unit tests for tool result injection into context (Task 7).

This test file verifies the CRITICAL bug fix: tool results must be injected
into subsequent round contexts so all models can see the evidence.
"""
import pytest
from datetime import datetime
from pathlib import Path

from deliberation.engine import DeliberationEngine
from deliberation.tools import (
    ToolExecutor,
    ReadFileTool,
    SearchCodeTool,
    ListFilesTool,
    RunCommandTool,
)
from models.schema import Participant, RoundResponse
from models.tool_schema import ToolRequest, ToolResult, ToolExecutionRecord


class TestToolResultContextInjection:
    """Tests that verify tool results are actually injected into context."""

    @pytest.mark.asyncio
    async def test_tool_results_injected_into_context(self, mock_adapters, tmp_path):
        """Test tool results are actually injected into subsequent round contexts."""
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())
        engine.tool_execution_history = []

        # Create test file
        test_file = tmp_path / "config.yaml"
        test_file.write_text("database: postgresql\nport: 5432")

        participants = [Participant(cli="claude", model="sonnet", stance="neutral")]

        # Round 1: Model requests tool
        mock_adapters["claude"].invoke_mock.return_value = f"""
I'll check the config file.
TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_file}"}}}}
"""

        round1 = await engine.execute_round(1, "What database?", participants, [])

        # Verify tool was executed and stored in history
        assert hasattr(engine, 'tool_execution_history'), "Engine should have tool_execution_history"
        assert len(engine.tool_execution_history) > 0, "Should have executed tool"

        # Round 2: Build context and verify tool result is included
        # CRITICAL: This is testing the ACTUAL context string passed to models
        context = engine._build_context(round1, current_round_num=2)

        # Verify tool results are in context
        assert "Recent Tool Results" in context, "Context should have tool results section"
        assert "read_file" in context, "Context should mention the tool name"
        assert "postgresql" in context, "Context should contain the file contents"
        assert "port: 5432" in context, "Context should contain the full tool output"

        # Verify it's formatted properly
        assert "Round 1" in context, "Should indicate which round the tool was used"
        assert "```" in context, "Should use code blocks for output"

    @pytest.mark.asyncio
    async def test_tool_results_visible_to_all_participants_in_next_round(self, mock_adapters, tmp_path):
        """Test all participants see tool results in their prompts."""
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())
        engine.tool_execution_history = []

        test_file = tmp_path / "data.txt"
        test_file.write_text("important evidence")

        participants = [
            Participant(cli="claude", model="sonnet", stance="neutral"),
            Participant(cli="codex", model="gpt-4", stance="neutral")
        ]

        # Round 1: One model uses tool
        mock_adapters["claude"].invoke_mock.return_value = f"""
Let me check the data.
TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_file}"}}}}
"""
        mock_adapters["codex"].invoke_mock.return_value = "I'll wait for data."

        round1 = await engine.execute_round(1, "Review data", participants, [])

        # Reset mocks to track round 2 calls
        mock_adapters["claude"].invoke_mock.reset_mock()
        mock_adapters["codex"].invoke_mock.reset_mock()

        # Round 2: Both models should receive context with tool results
        mock_adapters["claude"].invoke_mock.return_value = "I see the evidence."
        mock_adapters["codex"].invoke_mock.return_value = "I also see it."

        round2 = await engine.execute_round(2, "Review data", participants, round1)

        # Check that BOTH adapters received context with tool results
        # This verifies the actual integration, not just the helper method

        # Get the actual calls made in round 2
        claude_calls = mock_adapters["claude"].invoke_mock.call_args_list
        codex_calls = mock_adapters["codex"].invoke_mock.call_args_list

        # Both should have been called in round 2
        assert len(claude_calls) == 1, "Claude should be called once in round 2"
        assert len(codex_calls) == 1, "Codex should be called once in round 2"

        # Extract context from the calls (can be positional arg 3 or kwarg 'context')
        def get_context_from_call(call):
            if 'context' in call.kwargs:
                return call.kwargs['context']
            elif len(call.args) > 2:
                return call.args[2]
            return None

        claude_context = get_context_from_call(claude_calls[0])
        codex_context = get_context_from_call(codex_calls[0])

        # Both should have received context with tool results
        assert claude_context is not None, "Claude should receive context parameter"
        assert codex_context is not None, "Codex should receive context parameter"

        # Verify both contexts contain the tool output
        assert "important evidence" in claude_context, \
            "Claude should receive context with tool output"
        assert "important evidence" in codex_context, \
            "Codex should receive context with tool output"
        assert "read_file" in claude_context, \
            "Claude should see which tool was used"
        assert "read_file" in codex_context, \
            "Codex should see which tool was used"

    @pytest.mark.asyncio
    async def test_truncation_actually_applied(self, mock_adapters, tmp_path):
        """Test that large tool outputs are actually truncated in context."""
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())
        engine.tool_execution_history = []

        # Create large file (5KB)
        large_file = tmp_path / "large.txt"
        large_content = "x" * 5000
        large_file.write_text(large_content)

        participants = [Participant(cli="claude", model="sonnet", stance="neutral")]

        # Round 1: Read large file
        mock_adapters["claude"].invoke_mock.return_value = f"""
Reading the file.
TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{large_file}"}}}}
"""

        round1 = await engine.execute_round(1, "Test", participants, [])

        # Verify tool was executed
        assert len(engine.tool_execution_history) > 0, "Should have executed tool"

        # Round 2: Check context is truncated
        context = engine._build_context(round1, current_round_num=2)

        # Should be truncated to ~1000 chars, not 5000
        # Context includes formatting, so allow some overhead but not full 5KB
        assert len(context) < 3000, \
            f"Context should be truncated (got {len(context)} chars, expected <3000)"
        assert "truncated" in context.lower(), \
            "Context should indicate truncation"

    @pytest.mark.asyncio
    async def test_round_filtering_actually_applied(self, mock_adapters, tmp_path):
        """Test that old tool results are actually filtered out."""
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())
        engine.tool_execution_history = []

        participants = [Participant(cli="claude", model="sonnet", stance="neutral")]

        all_responses = []

        # Execute 5 rounds with tools
        for i in range(1, 6):
            test_file = tmp_path / f"file{i}.txt"
            test_file.write_text(f"data from round {i}")

            mock_adapters["claude"].invoke_mock.return_value = f"""
Checking round {i}.
TOOL_REQUEST: {{"name": "read_file", "arguments": {{"path": "{test_file}"}}}}
"""

            responses = await engine.execute_round(i, "Test", participants, all_responses)
            all_responses.extend(responses)

        # Verify we have 5 tool executions
        assert len(engine.tool_execution_history) == 5, "Should have 5 tool executions"

        # Build context for round 6 (should only include rounds 4-5 with default max_rounds=2)
        context = engine._build_context(all_responses, current_round_num=6)

        # Should NOT include old rounds in tool results
        assert "data from round 1" not in context, "Round 1 tool result should be filtered out"
        assert "data from round 2" not in context, "Round 2 tool result should be filtered out"
        assert "data from round 3" not in context, "Round 3 tool result should be filtered out"

        # SHOULD include recent rounds in tool results
        assert "data from round 4" in context, "Round 4 tool result should be included"
        assert "data from round 5" in context, "Round 5 tool result should be included"

    @pytest.mark.asyncio
    async def test_tool_errors_shown_in_context(self, mock_adapters):
        """Test that tool errors are shown in context (not just success)."""
        engine = DeliberationEngine(mock_adapters)
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())
        engine.tool_execution_history = []

        participants = [Participant(cli="claude", model="sonnet", stance="neutral")]

        # Round 1: Tool fails (invalid path)
        mock_adapters["claude"].invoke_mock.return_value = """
Checking file.
TOOL_REQUEST: {"name": "read_file", "arguments": {"path": "/nonexistent/file.txt"}}
"""

        round1 = await engine.execute_round(1, "Test", participants, [])

        # Verify tool execution failed
        assert len(engine.tool_execution_history) > 0
        assert not engine.tool_execution_history[0].result.success, "Tool should have failed"

        # Round 2: Build context and verify error is shown
        context = engine._build_context(round1, current_round_num=2)

        # Should show the error
        assert "Error" in context or "error" in context, "Context should show error indicator"
        assert "read_file" in context, "Should still show which tool was attempted"

    def test_truncate_output_method_exists_and_works(self):
        """Test that _truncate_output helper method works correctly."""
        engine = DeliberationEngine({})

        # Test short text (no truncation)
        short = "short text"
        assert engine._truncate_output(short, 1000) == short

        # Test long text (should truncate)
        long_text = "x" * 2000
        truncated = engine._truncate_output(long_text, 1000)
        assert len(truncated) < 1100  # 1000 + truncation message
        assert "truncated" in truncated.lower()

        # Test None
        assert engine._truncate_output(None, 1000) is None

    def test_build_context_without_tools(self):
        """Test that context building still works when no tools were used."""
        engine = DeliberationEngine({})

        # No tool execution history
        assert not hasattr(engine, 'tool_execution_history') or len(engine.tool_execution_history) == 0

        previous = [
            RoundResponse(
                round=1,
                participant="model@cli",
                stance="neutral",
                response="Response without tools",
                timestamp=datetime.now().isoformat(),
            )
        ]

        # Should work fine without tools
        context = engine._build_context(previous, current_round_num=2)

        assert "Response without tools" in context
        assert "Recent Tool Results" not in context  # No tools section

    def test_build_context_with_no_current_round_num(self):
        """Test that context building works when current_round_num is None."""
        engine = DeliberationEngine({})
        engine.tool_executor = ToolExecutor()
        engine.tool_executor.register_tool(ReadFileTool())
        engine.tool_executor.register_tool(SearchCodeTool())
        engine.tool_executor.register_tool(ListFilesTool())
        engine.tool_executor.register_tool(RunCommandTool())

        # Add fake tool execution history
        if not hasattr(engine, 'tool_execution_history'):
            engine.tool_execution_history = []

        engine.tool_execution_history.append(
            ToolExecutionRecord(
                round_number=1,
                request=ToolRequest(name="read_file", arguments={"path": "/test.txt"}),
                result=ToolResult(
                    tool_name="read_file",
                    success=True,
                    output="test output",
                    error=None
                ),
                requested_by="test@cli"
            )
        )

        previous = [
            RoundResponse(
                round=1,
                participant="model@cli",
                stance="neutral",
                response="Response",
                timestamp=datetime.now().isoformat(),
            )
        ]

        # Call without current_round_num (should not crash, just skip tool results)
        context = engine._build_context(previous, current_round_num=None)

        # Should have basic context but no tool results (since current_round_num is None)
        assert "Response" in context
        # Tool results are only added when current_round_num is provided
        # So this should NOT include tool results
