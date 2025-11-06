"""Tests for OpenRouter adapter."""
import os

import pytest

from adapters.openrouter import OpenRouterAdapter


class TestOpenRouterAdapter:
    """Tests for OpenRouterAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes correctly."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key="sk-test-123", timeout=90
        )
        assert adapter.base_url == "https://openrouter.ai/api/v1"
        assert adapter.api_key == "sk-test-123"
        assert adapter.timeout == 90

    def test_adapter_initialization_without_api_key(self):
        """Test adapter can be initialized without API key (will fail on request)."""
        adapter = OpenRouterAdapter(base_url="https://openrouter.ai/api/v1", timeout=60)
        assert adapter.base_url == "https://openrouter.ai/api/v1"
        assert adapter.api_key is None

    def test_build_request_structure(self):
        """Test build_request returns correct OpenAI-compatible structure with auth."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key="sk-test-key-123"
        )

        endpoint, headers, body = adapter.build_request(
            model="anthropic/claude-3.5-sonnet", prompt="What is 2+2?"
        )

        assert endpoint == "/chat/completions"
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer sk-test-key-123"
        assert body["model"] == "anthropic/claude-3.5-sonnet"
        assert body["messages"] == [{"role": "user", "content": "What is 2+2?"}]
        assert body["stream"] is False

    def test_build_request_without_api_key_still_includes_header(self):
        """Test build_request includes Authorization header even if api_key is None."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key=None
        )

        endpoint, headers, body = adapter.build_request(
            model="test-model", prompt="test"
        )

        # Should include header with "Bearer None" - will fail at API level
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer None"

    def test_build_request_with_long_prompt(self):
        """Test build_request handles long prompts."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key="sk-test"
        )

        long_prompt = "A" * 5000
        endpoint, headers, body = adapter.build_request(
            model="test-model", prompt=long_prompt
        )

        assert body["messages"][0]["content"] == long_prompt

    def test_parse_response_extracts_content(self):
        """Test parse_response extracts message content from OpenAI format."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key="sk-test"
        )

        response_json = {
            "id": "gen-123",
            "model": "anthropic/claude-3.5-sonnet",
            "created": 1234567890,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "The answer is 4."},
                    "finish_reason": "stop",
                }
            ],
        }

        result = adapter.parse_response(response_json)
        assert result == "The answer is 4."

    def test_parse_response_handles_missing_choices(self):
        """Test parse_response raises error if choices missing."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key="sk-test"
        )

        response_json = {"id": "gen-123", "model": "test-model"}

        with pytest.raises(KeyError) as exc_info:
            adapter.parse_response(response_json)

        assert "choices" in str(exc_info.value).lower()

    def test_parse_response_handles_empty_choices(self):
        """Test parse_response raises error if choices is empty."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key="sk-test"
        )

        response_json = {"choices": []}

        with pytest.raises(IndexError):
            adapter.parse_response(response_json)

    def test_parse_response_handles_missing_message(self):
        """Test parse_response raises error if message missing."""
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1", api_key="sk-test"
        )

        response_json = {"choices": [{"index": 0, "finish_reason": "stop"}]}

        with pytest.raises(KeyError) as exc_info:
            adapter.parse_response(response_json)

        assert "message" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invoke_success(self):
        """Test successful invocation with mocked HTTP client."""
        from unittest.mock import AsyncMock, Mock, patch

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response from OpenRouter"}}]
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterAdapter(
                base_url="https://openrouter.ai/api/v1",
                api_key="sk-test-key",
                timeout=60,
            )
            result = await adapter.invoke(
                prompt="Say hello", model="anthropic/claude-3.5-sonnet"
            )

            assert result == "Test response from OpenRouter"
            mock_client.post.assert_called_once()

            # Verify the request was built correctly
            call_args = mock_client.post.call_args
            assert "/chat/completions" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer sk-test-key"
            assert call_args[1]["json"]["messages"][0]["content"] == "Say hello"

    @pytest.mark.asyncio
    async def test_invoke_with_context(self):
        """Test invocation with context prepends context to prompt."""
        from unittest.mock import AsyncMock, Mock, patch

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response with context"}}]
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterAdapter(
                base_url="https://openrouter.ai/api/v1", api_key="sk-test"
            )
            await adapter.invoke(
                prompt="Current question",
                model="test-model",
                context="Previous context",
            )

            # Verify context was prepended
            call_args = mock_client.post.call_args
            message_content = call_args[1]["json"]["messages"][0]["content"]
            assert "Previous context" in message_content
            assert "Current question" in message_content

    def test_environment_variable_in_api_key(self):
        """Test that environment variables can be used for API keys."""
        # This test verifies the pattern - actual env var substitution
        # happens in HTTPAdapterConfig validator
        test_key = "sk-or-test-env-123"
        os.environ["TEST_OPENROUTER_KEY"] = test_key

        # Simulating what would happen after config loading
        adapter = OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1",
            api_key=test_key,  # In real usage, this would be resolved from ${TEST_OPENROUTER_KEY}
            timeout=60,
        )

        assert adapter.api_key == test_key

        # Cleanup
        del os.environ["TEST_OPENROUTER_KEY"]
