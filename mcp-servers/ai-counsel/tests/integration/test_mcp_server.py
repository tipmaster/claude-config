"""Integration tests for MCP server.

These tests validate the MCP protocol endpoints (list_tools, call_tool)
and ensure proper parameter validation and error handling.
"""
import json

import pytest
from mcp.types import TextContent


@pytest.mark.integration
class TestMCPEndpoints:
    """Comprehensive tests for MCP protocol endpoints."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_deliberate_tool(self):
        """Test list_tools returns deliberate tool."""
        from server import list_tools

        tools = await list_tools()

        assert len(tools) >= 1, "Should have at least deliberate tool"

        tool_names = [t.name for t in tools]
        assert "deliberate" in tool_names, "Should include deliberate tool"

    @pytest.mark.asyncio
    async def test_list_tools_with_decision_graph_disabled(self):
        """Test list_tools returns only deliberate when decision graph disabled."""
        from server import config, list_tools

        # Decision graph should be disabled by default
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            tools = await list_tools()
            tool_names = [t.name for t in tools]

            assert "deliberate" in tool_names
            assert "query_decisions" not in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_returns_valid_schemas(self):
        """Test tool schemas are valid and complete."""
        from server import list_tools

        tools = await list_tools()

        for tool in tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")
            assert len(tool.description) > 100, "Description should be substantial"

            # Validate schema structure
            schema = tool.inputSchema
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema

    @pytest.mark.asyncio
    async def test_deliberate_tool_schema_has_required_fields(self):
        """Test deliberate tool schema has all required fields."""
        from server import list_tools

        tools = await list_tools()
        deliberate_tool = next(t for t in tools if t.name == "deliberate")

        schema = deliberate_tool.inputSchema
        assert "required" in schema
        assert "question" in schema["required"]
        assert "participants" in schema["required"]

        # Check properties
        props = schema["properties"]
        assert "question" in props
        assert "participants" in props
        assert "rounds" in props
        assert "mode" in props
        assert "context" in props

    @pytest.mark.asyncio
    async def test_call_tool_deliberate_missing_question(self):
        """Test deliberate tool fails with missing required question parameter."""
        from server import call_tool

        # Missing 'question'
        arguments = {"participants": [{"cli": "claude", "model": "sonnet"}]}

        result = await call_tool("deliberate", arguments)

        # Should return error response
        assert len(result) > 0
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "error" in data or "status" in data
        if "error" in data:
            assert (
                "question" in data["error"].lower()
                or "required" in data["error"].lower()
            )

    @pytest.mark.asyncio
    async def test_call_tool_deliberate_missing_participants(self):
        """Test deliberate tool fails with missing participants parameter."""
        from server import call_tool

        arguments = {"question": "Should we use PostgreSQL or SQLite?"}

        result = await call_tool("deliberate", arguments)

        # Should return error response
        assert len(result) > 0
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "error" in data or "status" in data
        if "error" in data:
            assert (
                "participants" in data["error"].lower()
                or "required" in data["error"].lower()
            )

    @pytest.mark.asyncio
    async def test_call_tool_deliberate_invalid_cli(self):
        """Test deliberate with invalid CLI name fails with validation error."""
        from server import call_tool

        arguments = {
            "question": "Test question that is long enough to pass validation?",
            "participants": [{"cli": "invalid_cli_name", "model": "some_model"}],
        }

        result = await call_tool("deliberate", arguments)

        # Should return error response with validation error
        assert len(result) > 0
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "error" in data
        # Pydantic validation error should mention invalid enum value
        assert "cli" in data["error"].lower() or "invalid" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_call_tool_deliberate_too_few_participants(self):
        """Test deliberate with only 1 participant fails validation."""
        from server import call_tool

        arguments = {
            "question": "Test question that is long enough to pass validation?",
            "participants": [{"cli": "claude", "model": "sonnet"}],
        }

        result = await call_tool("deliberate", arguments)

        # Should return error response
        assert len(result) > 0
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "error" in data
        # Should mention minimum participants requirement
        assert (
            "participants" in data["error"].lower() or "2" in data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_call_tool_deliberate_question_too_short(self):
        """Test deliberate with question < 10 chars fails validation."""
        from server import call_tool

        arguments = {
            "question": "short",  # Only 5 characters
            "participants": [
                {"cli": "claude", "model": "sonnet"},
                {"cli": "codex", "model": "gpt-5-codex"},
            ],
        }

        result = await call_tool("deliberate", arguments)

        # Should return error response
        assert len(result) > 0
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "error" in data
        # Should mention length requirement
        assert (
            "question" in data["error"].lower() or "length" in data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_call_tool_deliberate_invalid_rounds(self):
        """Test deliberate with rounds outside 1-5 range fails."""
        from server import call_tool

        arguments = {
            "question": "Test question that is long enough to pass validation?",
            "participants": [
                {"cli": "claude", "model": "sonnet"},
                {"cli": "codex", "model": "gpt-5-codex"},
            ],
            "rounds": 10,  # Exceeds maximum of 5
        }

        result = await call_tool("deliberate", arguments)

        # Should return error response
        assert len(result) > 0
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "error" in data
        # Should mention rounds constraint
        assert "rounds" in data["error"].lower() or "5" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_call_tool_deliberate_invalid_mode(self):
        """Test deliberate with invalid mode fails validation."""
        from server import call_tool

        arguments = {
            "question": "Test question that is long enough to pass validation?",
            "participants": [
                {"cli": "claude", "model": "sonnet"},
                {"cli": "codex", "model": "gpt-5-codex"},
            ],
            "mode": "invalid_mode",
        }

        result = await call_tool("deliberate", arguments)

        # Should return error response
        assert len(result) > 0
        assert isinstance(result[0], TextContent)

        data = json.loads(result[0].text)
        assert "error" in data
        # Should mention mode validation error
        assert "mode" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool_fails(self):
        """Test calling unknown tool raises appropriate error."""
        from server import call_tool

        with pytest.raises(ValueError) as exc_info:
            await call_tool("unknown_tool_name", {})

        assert "unknown" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_call_tool_query_decisions_without_decision_graph(self):
        """Test query_decisions tool returns error when decision graph disabled."""
        from server import call_tool, config

        # Only test if decision graph is disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            # query_decisions should raise error since it's not available
            with pytest.raises(ValueError) as exc_info:
                await call_tool("query_decisions", {"query_text": "test"})

            assert "unknown" in str(exc_info.value).lower()


@pytest.mark.integration
class TestMCPToolSchema:
    """Tests for MCP tool schema documentation."""

    @pytest.mark.asyncio
    async def test_deliberate_tool_description_includes_tool_usage(self):
        """Test deliberate tool description documents tool invocation."""
        from server import list_tools

        tools = await list_tools()
        deliberate_tool = next(t for t in tools if t.name == "deliberate")

        description = deliberate_tool.description

        # Check for tool documentation
        assert "TOOL_REQUEST" in description
        assert "read_file" in description
        assert "search_code" in description
        assert "evidence" in description.lower() or "query" in description.lower()

    @pytest.mark.asyncio
    async def test_tool_list_includes_supported_tools(self):
        """Test tool description lists all supported tools."""
        from server import list_tools

        tools = await list_tools()
        deliberate_tool = next(t for t in tools if t.name == "deliberate")

        description = deliberate_tool.description

        # All Phase 1 tools should be mentioned
        assert "read_file" in description
        assert "search_code" in description
        assert "list_files" in description
        assert "run_command" in description

    @pytest.mark.asyncio
    async def test_deliberate_tool_description_clarifies_internal_vs_mcp_tools(self):
        """Test description clarifies which tools are MCP-exposed vs internal."""
        from server import list_tools

        tools = await list_tools()
        deliberate_tool = next(t for t in tools if t.name == "deliberate")

        description = deliberate_tool.description

        # Should clarify that internal tools use TOOL_REQUEST markers
        assert "TOOL_REQUEST" in description
        # Should list the internal tools
        assert "read_file" in description
        assert "search_code" in description
        assert "list_files" in description
        assert "run_command" in description


@pytest.mark.integration
class TestMCPParameterValidation:
    """Tests for query_decisions parameter validation gaps (Task 8)."""

    @pytest.mark.asyncio
    async def test_query_decisions_format_parameter_used_summary(self):
        """Test format='summary' returns basic fields only."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        args = {"query_text": "database choice", "format": "summary"}

        result = await call_tool("query_decisions", args)
        data = json.loads(result[0].text)

        # Summary format should have minimal fields
        if data.get("results") and len(data["results"]) > 0:
            result_keys = set(data["results"][0].keys())
            # Summary should NOT include timestamp or stances
            assert "timestamp" not in result_keys, "Summary should not include timestamp"
            assert "stances" not in result_keys, "Summary should not include stances"

    @pytest.mark.asyncio
    async def test_query_decisions_format_parameter_used_detailed(self):
        """Test format='detailed' returns extended fields."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        args = {"query_text": "database choice", "format": "detailed"}

        result = await call_tool("query_decisions", args)
        data = json.loads(result[0].text)

        # Detailed format should have extended fields
        if data.get("results") and len(data["results"]) > 0:
            result_keys = set(data["results"][0].keys())
            # Detailed should include timestamp and stances
            assert "timestamp" in result_keys, "Detailed should include timestamp"
            assert "stances" in result_keys, "Detailed should include stances"

    @pytest.mark.asyncio
    async def test_query_decisions_format_affects_all_query_types(self):
        """Test format parameter works for all query types (search, contradictions, evolution)."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        # Test format with query_text
        args_search = {"query_text": "test", "format": "detailed"}
        result_search = await call_tool("query_decisions", args_search)
        data_search = json.loads(result_search[0].text)

        # Should not crash
        assert "type" in data_search or "error" in data_search

        # Test format with find_contradictions
        args_contra = {"find_contradictions": True, "format": "detailed"}
        result_contra = await call_tool("query_decisions", args_contra)
        data_contra = json.loads(result_contra[0].text)

        # Should not crash
        assert "type" in data_contra or "error" in data_contra

    @pytest.mark.asyncio
    async def test_query_decisions_mutual_exclusivity_enforced(self):
        """Test providing multiple query params raises error."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        # Provide both query_text and find_contradictions
        args = {"query_text": "database", "find_contradictions": True}

        result = await call_tool("query_decisions", args)
        data = json.loads(result[0].text)

        # Should return error
        assert "error" in data, "Should return error when multiple params provided"
        assert data.get("status") == "failed", "Status should be 'failed'"
        assert (
            "only one" in data.get("error", "").lower()
            or "mutual" in data.get("error", "").lower()
        ), "Error should mention mutual exclusivity"

    @pytest.mark.asyncio
    async def test_query_decisions_mutual_exclusivity_all_combinations(self):
        """Test all combinations of mutual exclusivity violations."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        # Test query_text + decision_id
        args1 = {"query_text": "test", "decision_id": "123"}
        result1 = await call_tool("query_decisions", args1)
        data1 = json.loads(result1[0].text)
        assert "error" in data1, "Should error on query_text + decision_id"

        # Test find_contradictions + decision_id
        args2 = {"find_contradictions": True, "decision_id": "123"}
        result2 = await call_tool("query_decisions", args2)
        data2 = json.loads(result2[0].text)
        assert "error" in data2, "Should error on find_contradictions + decision_id"

        # Test all three
        args3 = {
            "query_text": "test",
            "find_contradictions": True,
            "decision_id": "123",
        }
        result3 = await call_tool("query_decisions", args3)
        data3 = json.loads(result3[0].text)
        assert "error" in data3, "Should error on all three params"

    @pytest.mark.asyncio
    async def test_query_decisions_requires_at_least_one_param(self):
        """Test providing no query params raises error."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        # Provide no query parameters (only optional ones)
        args = {"limit": 10, "format": "summary"}

        result = await call_tool("query_decisions", args)
        data = json.loads(result[0].text)

        # Should return error
        assert "error" in data, "Should return error when no query param provided"
        assert (
            "must provide" in data.get("error", "").lower()
            or "required" in data.get("error", "").lower()
        ), "Error should indicate a param is required"

    @pytest.mark.asyncio
    async def test_query_decisions_format_invalid_value_handled(self):
        """Test invalid format value is handled gracefully."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        args = {"query_text": "test", "format": "invalid_format"}

        # Should either:
        # 1. Default to "summary" (graceful)
        # 2. Return error (strict)
        result = await call_tool("query_decisions", args)
        data = json.loads(result[0].text)

        # Should not crash (either returns results or error)
        assert (
            "type" in data or "error" in data
        ), "Should handle invalid format gracefully"

    @pytest.mark.asyncio
    async def test_query_decisions_error_provides_helpful_context(self):
        """Test validation errors include context about what was provided."""
        from server import call_tool, config

        # Skip if decision graph disabled
        if not (
            hasattr(config, "decision_graph")
            and config.decision_graph
            and config.decision_graph.enabled
        ):
            pytest.skip("Decision graph disabled")

        # Multiple params provided
        args = {
            "query_text": "test",
            "find_contradictions": True,
            "decision_id": "123",
        }

        result = await call_tool("query_decisions", args)
        data = json.loads(result[0].text)

        # Should include which params were provided
        if "error" in data:
            # Could include field names or "provided" context
            error_text = data.get("error", "")
            # At minimum, should be descriptive
            assert len(error_text) > 20, "Error message should be descriptive"
