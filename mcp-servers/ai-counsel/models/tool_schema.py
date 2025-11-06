"""Tool execution schema models for evidence-based deliberation."""
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ToolRequest(BaseModel):
    """Model for a tool invocation request."""

    name: Literal[
        "read_file", "search_code", "list_files", "run_command", "get_file_tree"
    ] = Field(..., description="Tool name to invoke")

    arguments: Dict[str, Any] = Field(
        ..., description="Arguments for the tool (structure varies by tool)"
    )


class ToolResult(BaseModel):
    """Model for a tool execution result."""

    tool_name: str = Field(..., description="Name of the tool that was executed")
    success: bool = Field(..., description="Whether execution succeeded")
    output: Optional[str] = Field(None, description="Tool output (if successful)")
    error: Optional[str] = Field(None, description="Error message (if failed)")


class ToolExecutionRecord(BaseModel):
    """Model for complete tool execution record with metadata."""

    request: ToolRequest = Field(..., description="The original tool request")
    result: ToolResult = Field(..., description="The execution result")
    round_number: int = Field(
        ..., description="Deliberation round when tool was invoked"
    )
    requested_by: str = Field(..., description="Participant ID who requested the tool")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO 8601 timestamp of execution",
    )
