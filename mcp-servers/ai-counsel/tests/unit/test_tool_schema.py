"""Unit tests for tool schema models."""
import pytest
from pydantic import ValidationError
from models.tool_schema import ToolRequest, ToolResult, ToolExecutionRecord


class TestToolRequest:
    """Tests for ToolRequest model."""

    def test_valid_tool_request_parsing(self):
        """Test parsing valid tool request."""
        data = {
            "name": "read_file",
            "arguments": {"path": "/path/to/file.py"}
        }
        request = ToolRequest(**data)
        assert request.name == "read_file"
        assert request.arguments == {"path": "/path/to/file.py"}

    def test_search_code_tool_request(self):
        """Test parsing search_code tool request."""
        data = {
            "name": "search_code",
            "arguments": {"pattern": "def.*test", "path": "."}
        }
        request = ToolRequest(**data)
        assert request.name == "search_code"
        assert request.arguments["pattern"] == "def.*test"

    def test_list_files_tool_request(self):
        """Test parsing list_files tool request."""
        data = {
            "name": "list_files",
            "arguments": {"pattern": "*.py"}
        }
        request = ToolRequest(**data)
        assert request.name == "list_files"

    def test_run_command_tool_request(self):
        """Test parsing run_command tool request."""
        data = {
            "name": "run_command",
            "arguments": {"command": "ls", "args": ["-la"]}
        }
        request = ToolRequest(**data)
        assert request.name == "run_command"
        assert request.arguments["command"] == "ls"

    def test_invalid_tool_name_validation(self):
        """Test that invalid tool names raise ValidationError."""
        data = {
            "name": "invalid_tool_123",
            "arguments": {}
        }
        with pytest.raises(ValidationError) as exc_info:
            ToolRequest(**data)
        assert "name" in str(exc_info.value)

    def test_missing_required_arguments(self):
        """Test validation fails when required fields missing."""
        data = {"name": "read_file"}  # Missing arguments
        with pytest.raises(ValidationError):
            ToolRequest(**data)

    def test_arguments_must_be_dict(self):
        """Test arguments must be a dictionary."""
        data = {
            "name": "read_file",
            "arguments": "not a dict"
        }
        with pytest.raises(ValidationError):
            ToolRequest(**data)


class TestToolResult:
    """Tests for ToolResult model."""

    def test_success_result_creation(self):
        """Test creating successful tool result."""
        result = ToolResult(
            tool_name="read_file",
            success=True,
            output="file contents here",
            error=None
        )
        assert result.success is True
        assert result.output == "file contents here"
        assert result.error is None

    def test_error_result_creation(self):
        """Test creating error tool result."""
        result = ToolResult(
            tool_name="read_file",
            success=False,
            output=None,
            error="File not found: /invalid/path"
        )
        assert result.success is False
        assert result.error is not None
        assert "File not found" in result.error

    def test_result_with_both_output_and_error(self):
        """Test result can have both output and error (for partial success)."""
        result = ToolResult(
            tool_name="search_code",
            success=True,
            output="Some results found",
            error="Warning: Some files skipped"
        )
        assert result.success is True
        assert result.output is not None
        assert result.error is not None

    def test_result_serialization(self):
        """Test result can be serialized to dict."""
        result = ToolResult(
            tool_name="read_file",
            success=True,
            output="content",
            error=None
        )
        data = result.model_dump()
        assert data["tool_name"] == "read_file"
        assert data["success"] is True
        assert data["output"] == "content"


class TestToolExecutionRecord:
    """Tests for ToolExecutionRecord model."""

    def test_record_creation_with_metadata(self):
        """Test creating execution record with full metadata."""
        request = ToolRequest(name="read_file", arguments={"path": "/test.py"})
        result = ToolResult(
            tool_name="read_file",
            success=True,
            output="contents",
            error=None
        )
        record = ToolExecutionRecord(
            request=request,
            result=result,
            round_number=2,
            requested_by="claude-3-5-sonnet@claude"
        )
        assert record.round_number == 2
        assert record.requested_by == "claude-3-5-sonnet@claude"
        assert record.timestamp is not None
        assert record.request.name == "read_file"
        assert record.result.success is True

    def test_timestamp_auto_generation(self):
        """Test timestamp is automatically generated."""
        request = ToolRequest(name="read_file", arguments={"path": "/test.py"})
        result = ToolResult(
            tool_name="read_file",
            success=True,
            output="contents",
            error=None
        )
        record = ToolExecutionRecord(
            request=request,
            result=result,
            round_number=1,
            requested_by="test"
        )
        assert record.timestamp is not None
        # Verify ISO 8601 format
        from datetime import datetime
        datetime.fromisoformat(record.timestamp)  # Should not raise

    def test_record_with_failed_tool_execution(self):
        """Test record with failed tool execution."""
        request = ToolRequest(name="read_file", arguments={"path": "/missing.py"})
        result = ToolResult(
            tool_name="read_file",
            success=False,
            output=None,
            error="File not found"
        )
        record = ToolExecutionRecord(
            request=request,
            result=result,
            round_number=1,
            requested_by="test"
        )
        assert record.result.success is False
        assert record.result.error == "File not found"
