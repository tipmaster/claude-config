"""Pytest fixtures for all test modules."""
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from adapters.base import BaseCLIAdapter


class MockAdapter(BaseCLIAdapter):
    """Mock adapter for testing."""

    def __init__(self, name: str, timeout: int = 60):
        """Initialize mock adapter."""
        super().__init__(command=f"mock-{name}", args=[], timeout=timeout)
        self.name = name
        self.invoke_mock = AsyncMock()
        self.response_counter = 0
        # Set a default return value
        self._set_default_responses()

    def _set_default_responses(self):
        """Set sensible default responses for mock deliberations."""
        # Default response when no specific mock is configured
        # Use return_value instead of side_effect so tests can override easily
        default_response = "After careful analysis, I believe the proposed approach has merit. It addresses the core concerns while maintaining practical feasibility. The implementation timeline seems reasonable."
        self.invoke_mock.return_value = default_response
        self.response_counter = 0

    async def invoke(
        self, prompt: str, model: str, context: Optional[str] = None, is_deliberation: bool = True, working_directory: Optional[str] = None
    ) -> str:
        """Mock invoke method."""
        result = await self.invoke_mock(prompt, model, context, is_deliberation)
        self.response_counter += 1
        return result

    def parse_output(self, raw_output: str) -> str:
        """Mock parse_output method."""
        return raw_output.strip()


@pytest.fixture
def mock_adapters():
    """
    Create mock adapters for testing deliberation engine.

    Returns:
        dict: Dictionary of mock adapters by name
    """
    claude = MockAdapter("claude")
    codex = MockAdapter("codex")

    # Set default return values
    claude.invoke_mock.return_value = "Claude response"
    codex.invoke_mock.return_value = "Codex response"

    return {
        "claude": claude,
        "codex": codex,
    }


@pytest.fixture
def sample_config():
    """
    Sample configuration for testing.

    Returns:
        dict: Sample configuration dict
    """
    return {
        "defaults": {
            "mode": "quick",
            "rounds": 2,
            "max_rounds": 5,
            "timeout_per_round": 60,
        },
        "storage": {
            "transcripts_dir": "transcripts",
            "format": "markdown",
            "auto_export": True,
        },
        "deliberation": {
            "convergence_threshold": 0.8,
            "enable_convergence_detection": True,
        },
    }
