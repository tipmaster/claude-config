"""Tests for LM Studio adapter."""
import pytest

from adapters.lmstudio import LMStudioAdapter


class TestLMStudioAdapter:
    """Tests for LMStudioAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes correctly."""
        adapter = LMStudioAdapter(base_url="http://localhost:1234", timeout=60)
        assert adapter.base_url == "http://localhost:1234"
        assert adapter.timeout == 60

    def test_build_request_structure(self):
        """Test build_request returns correct OpenAI-compatible structure."""
        adapter = LMStudioAdapter(base_url="http://localhost:1234")

        endpoint, headers, body = adapter.build_request(
            model="local-model", prompt="What is 2+2?"
        )

        assert endpoint == "/v1/chat/completions"
        assert headers["Content-Type"] == "application/json"
        assert body["model"] == "local-model"
        assert body["messages"] == [{"role": "user", "content": "What is 2+2?"}]
        assert body["stream"] is False
        assert body["temperature"] == 0.7

    def test_build_request_with_long_prompt(self):
        """Test build_request handles long prompts."""
        adapter = LMStudioAdapter(base_url="http://localhost:1234")

        long_prompt = "A" * 1000
        endpoint, headers, body = adapter.build_request(
            model="test-model", prompt=long_prompt
        )

        assert body["messages"][0]["content"] == long_prompt

    def test_parse_response_extracts_content(self):
        """Test parse_response extracts message content."""
        adapter = LMStudioAdapter(base_url="http://localhost:1234")

        response_json = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "local-model",
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
        adapter = LMStudioAdapter(base_url="http://localhost:1234")

        response_json = {"id": "chatcmpl-123", "object": "chat.completion"}

        with pytest.raises(KeyError) as exc_info:
            adapter.parse_response(response_json)

        assert "choices" in str(exc_info.value).lower()

    def test_parse_response_handles_empty_choices(self):
        """Test parse_response raises error if choices is empty."""
        adapter = LMStudioAdapter(base_url="http://localhost:1234")

        response_json = {"choices": []}

        with pytest.raises(IndexError):
            adapter.parse_response(response_json)

    def test_parse_response_handles_missing_message(self):
        """Test parse_response raises error if message missing."""
        adapter = LMStudioAdapter(base_url="http://localhost:1234")

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
            "choices": [{"message": {"content": "Test response from LM Studio"}}]
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = LMStudioAdapter(base_url="http://localhost:1234", timeout=60)
            result = await adapter.invoke(prompt="Say hello", model="local-model")

            assert result == "Test response from LM Studio"
            mock_client.post.assert_called_once()

            # Verify the request was built correctly
            call_args = mock_client.post.call_args
            assert "/v1/chat/completions" in call_args[0][0]
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
            adapter = LMStudioAdapter(base_url="http://localhost:1234")
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
