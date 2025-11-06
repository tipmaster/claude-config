"""Unit tests for Ollama adapter."""
from unittest.mock import AsyncMock, Mock, patch

import pytest

from adapters.ollama import OllamaAdapter


class TestOllamaAdapter:
    """Tests for Ollama HTTP adapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct base_url and defaults."""
        adapter = OllamaAdapter(base_url="http://localhost:11434", timeout=60)
        assert adapter.base_url == "http://localhost:11434"
        assert adapter.timeout == 60
        assert adapter.max_retries == 3

    def test_adapter_strips_trailing_slash(self):
        """Test adapter removes trailing slash from base_url."""
        adapter = OllamaAdapter(base_url="http://localhost:11434/", timeout=60)
        assert adapter.base_url == "http://localhost:11434"

    def test_build_request_structure(self):
        """Test build_request returns correct endpoint, headers, body."""
        adapter = OllamaAdapter(base_url="http://localhost:11434")

        endpoint, headers, body = adapter.build_request(
            model="llama2", prompt="What is 2+2?"
        )

        assert endpoint == "/api/generate"
        assert headers["Content-Type"] == "application/json"
        assert body["model"] == "llama2"
        assert body["prompt"] == "What is 2+2?"
        assert body["stream"] is False

    def test_build_request_with_context(self):
        """Test build_request includes prompt (context handled by invoke)."""
        adapter = OllamaAdapter(base_url="http://localhost:11434")

        # Note: context is handled by invoke(), not build_request()
        # This test verifies build_request handles any prompt correctly
        long_prompt = "Context from previous rounds\n\nWhat is 2+2?"
        endpoint, headers, body = adapter.build_request(
            model="mistral", prompt=long_prompt
        )

        assert body["prompt"] == long_prompt
        assert body["model"] == "mistral"

    def test_parse_response_extracts_content(self):
        """Test parse_response extracts 'response' field from JSON."""
        adapter = OllamaAdapter(base_url="http://localhost:11434")

        response_json = {
            "model": "llama2",
            "created_at": "2023-08-01T00:00:00Z",
            "response": "The answer is 4.",
            "done": True,
        }

        result = adapter.parse_response(response_json)
        assert result == "The answer is 4."

    def test_parse_response_missing_field_raises_error(self):
        """Test parse_response raises error if 'response' field missing."""
        adapter = OllamaAdapter(base_url="http://localhost:11434")

        response_json = {
            "model": "llama2",
            "created_at": "2023-08-01T00:00:00Z",
            "done": True
            # Missing 'response' field
        }

        with pytest.raises(KeyError) as exc_info:
            adapter.parse_response(response_json)

        assert "response" in str(exc_info.value).lower()
        assert "missing" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_success(self, mock_client_class):
        """Test successful HTTP request returns parsed response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "llama2",
            "response": "Hello! How can I help you today?",
            "done": True,
        }
        mock_response.raise_for_status = Mock()

        # Setup mock client
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = OllamaAdapter(base_url="http://localhost:11434", timeout=60)
        result = await adapter.invoke(prompt="Say hello", model="llama2")

        assert result == "Hello! How can I help you today?"
        mock_client.post.assert_called_once()

        # Verify request structure
        call_args = mock_client.post.call_args
        assert "http://localhost:11434/api/generate" in str(call_args)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_with_context(self, mock_client_class):
        """Test invoke properly prepends context to prompt."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "llama2",
            "response": "Based on previous context, the answer is 4.",
            "done": True,
        }
        mock_response.raise_for_status = Mock()

        # Setup mock client
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = OllamaAdapter(base_url="http://localhost:11434")
        result = await adapter.invoke(
            prompt="What is the answer?",
            model="llama2",
            context="Previous round: Someone said 2+2",
        )

        assert result == "Based on previous context, the answer is 4."

        # Verify context was prepended to prompt
        call_args = mock_client.post.call_args
        sent_body = call_args.kwargs.get("json")
        assert "Previous round: Someone said 2+2" in sent_body["prompt"]
        assert "What is the answer?" in sent_body["prompt"]
