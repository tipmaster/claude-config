"""Unit tests for BaseHTTPAdapter."""
import asyncio
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest


# Concrete test implementation for testing abstract base
class ConcreteHTTPAdapter:
    """Concrete implementation for testing BaseHTTPAdapter."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 60,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        headers: Optional[dict] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = api_key
        self.default_headers = headers or {}

    def build_request(self, model: str, prompt: str):
        """Test implementation."""
        return (
            "/test",
            {"Authorization": "Bearer test", "Content-Type": "application/json"},
            {"model": model, "prompt": prompt},
        )

    def parse_response(self, response_json: dict) -> str:
        """Test implementation."""
        return response_json.get("response", "")


class TestBaseHTTPAdapter:
    """Tests for BaseHTTPAdapter abstract class behavior."""

    def test_cannot_instantiate_base_adapter(self):
        """Test that BaseHTTPAdapter cannot be instantiated directly."""
        from adapters.base_http import BaseHTTPAdapter

        # Abstract classes should raise TypeError when instantiated
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseHTTPAdapter(base_url="http://test", timeout=60)

    def test_subclass_must_implement_build_request(self):
        """Test that subclass must implement build_request method."""
        from adapters.base_http import BaseHTTPAdapter

        class IncompleteAdapter(BaseHTTPAdapter):
            def parse_response(self, response_json):
                return str(response_json)

        # Should raise TypeError because build_request is not implemented
        with pytest.raises(TypeError, match="abstract"):
            IncompleteAdapter(base_url="http://test", timeout=60)

    def test_subclass_must_implement_parse_response(self):
        """Test that subclass must implement parse_response method."""
        from adapters.base_http import BaseHTTPAdapter

        class IncompleteAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/test", {}, {})

        # Should raise TypeError because parse_response is not implemented
        with pytest.raises(TypeError, match="abstract"):
            IncompleteAdapter(base_url="http://test", timeout=60)

    def test_complete_subclass_can_be_instantiated(self):
        """Test that complete subclass can be instantiated."""
        from adapters.base_http import BaseHTTPAdapter

        class CompleteAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/test", {}, {"model": model, "prompt": prompt})

            def parse_response(self, response_json):
                return response_json.get("text", "")

        # Should work without errors
        adapter = CompleteAdapter(base_url="http://localhost:8080", timeout=60)
        assert adapter.base_url == "http://localhost:8080"
        assert adapter.timeout == 60

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url."""
        from adapters.base_http import BaseHTTPAdapter

        class TestAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/test", {}, {})

            def parse_response(self, response_json):
                return str(response_json)

        adapter = TestAdapter(base_url="http://localhost:8080/", timeout=60)
        assert adapter.base_url == "http://localhost:8080"


class TestHTTPAdapterInvoke:
    """Tests for BaseHTTPAdapter invoke method."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_success(self, mock_client_class):
        """Test successful HTTP request."""
        from adapters.base_http import BaseHTTPAdapter

        class TestAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return (
                    "/api/test",
                    {"Content-Type": "application/json"},
                    {"model": model, "prompt": prompt},
                )

            def parse_response(self, response_json):
                return response_json["response"]

        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test response"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = TestAdapter(base_url="http://test", timeout=60)
        result = await adapter.invoke(prompt="test prompt", model="test-model")

        assert result == "Test response"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_with_context(self, mock_client_class):
        """Test invoke with context prepended to prompt."""
        from adapters.base_http import BaseHTTPAdapter

        class TestAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/api/test", {}, {"model": model, "prompt": prompt})

            def parse_response(self, response_json):
                return response_json["response"]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test response"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = TestAdapter(base_url="http://test", timeout=60)
        await adapter.invoke(
            prompt="test prompt", model="test-model", context="Previous context"
        )

        # Check that post was called with context prepended
        call_args = mock_client.post.call_args
        body = call_args.kwargs["json"]
        assert "Previous context" in body["prompt"]
        assert "test prompt" in body["prompt"]

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_retries_on_503(self, mock_client_class):
        """Test retry logic on 503 Service Unavailable."""
        from adapters.base_http import BaseHTTPAdapter

        class TestAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/api/test", {}, {"prompt": prompt})

            def parse_response(self, response_json):
                return response_json["response"]

        # Setup mock to fail twice with 503, then succeed
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503
        mock_response_fail.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=Mock(url="http://test"),
                response=mock_response_fail,
            )
        )

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"response": "Success after retry"}
        mock_response_success.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[mock_response_fail, mock_response_fail, mock_response_success]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = TestAdapter(base_url="http://test", timeout=60, max_retries=3)
        result = await adapter.invoke(prompt="test", model="test-model")

        assert result == "Success after retry"
        assert mock_client.post.call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_no_retry_on_400(self, mock_client_class):
        """Test that 4xx errors are not retried."""
        from adapters.base_http import BaseHTTPAdapter

        class TestAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/api/test", {}, {"prompt": prompt})

            def parse_response(self, response_json):
                return response_json["response"]

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "400 Bad Request",
                request=Mock(url="http://test"),
                response=mock_response,
            )
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = TestAdapter(base_url="http://test", timeout=60, max_retries=3)

        # Should raise immediately without retries
        with pytest.raises(httpx.HTTPStatusError, match="400"):
            await adapter.invoke(prompt="test", model="test-model")

        # Should only be called once (no retries for 4xx)
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_retries_on_network_error(self, mock_client_class):
        """Test retry logic on network errors."""
        from adapters.base_http import BaseHTTPAdapter

        class TestAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/api/test", {}, {"prompt": prompt})

            def parse_response(self, response_json):
                return response_json["response"]

        # Simulate network error then success
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "response": "Success after network error"
        }
        mock_response_success.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[httpx.ConnectError("Connection failed"), mock_response_success]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = TestAdapter(base_url="http://test", timeout=60, max_retries=3)
        result = await adapter.invoke(prompt="test", model="test-model")

        assert result == "Success after network error"
        assert mock_client.post.call_count == 2  # 1 failure + 1 success

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_invoke_timeout_error(self, mock_client_class):
        """Test that timeout raises TimeoutError."""
        from adapters.base_http import BaseHTTPAdapter

        class TestAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/api/test", {}, {"prompt": prompt})

            def parse_response(self, response_json):
                return response_json["response"]

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        adapter = TestAdapter(base_url="http://test", timeout=1, max_retries=1)

        with pytest.raises(TimeoutError, match="timed out"):
            await adapter.invoke(prompt="test", model="test-model")
