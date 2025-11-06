"""Base HTTP adapter with request/retry management."""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import httpx
from tenacity import (retry, retry_if_exception, stop_after_attempt,
                      wait_exponential)


def is_retryable_http_error(exception):
    """
    Determine if an HTTP error should be retried.

    Retries on:
    - 5xx server errors
    - 429 rate limit errors
    - Network errors (connection, timeout)

    Does NOT retry on:
    - 4xx client errors (bad request, auth, etc.)

    Args:
        exception: The exception to check

    Returns:
        bool: True if the error should be retried
    """
    if isinstance(exception, httpx.HTTPStatusError):
        # Retry on 5xx server errors and 429 rate limit
        return (
            exception.response.status_code >= 500
            or exception.response.status_code == 429
        )

    # Retry on network errors
    return isinstance(
        exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
    )


class BaseHTTPAdapter(ABC):
    """
    Abstract base class for HTTP API adapters.

    Handles HTTP requests, timeout management, retry logic with exponential backoff,
    and error handling. Subclasses must implement build_request() and parse_response()
    for API-specific logic.

    Example:
        class MyAdapter(BaseHTTPAdapter):
            def build_request(self, model, prompt):
                return ("/api/generate", {"Content-Type": "application/json"}, {"prompt": prompt})

            def parse_response(self, response_json):
                return response_json["text"]

        adapter = MyAdapter(base_url="http://localhost:8080", timeout=60)
        result = await adapter.invoke(prompt="Hello", model="my-model")
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 60,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        """
        Initialize HTTP adapter.

        Args:
            base_url: Base URL for API (e.g., "http://localhost:11434")
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts for transient failures (default: 3)
            api_key: Optional API key for authentication
            headers: Optional default headers to include in all requests
        """
        self.base_url = base_url.rstrip("/")  # Remove trailing slash
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = api_key
        self.default_headers = headers or {}

    @abstractmethod
    def build_request(
        self, model: str, prompt: str
    ) -> Tuple[str, dict[str, str], dict]:
        """
        Build API-specific request components.

        Args:
            model: Model identifier
            prompt: The prompt to send

        Returns:
            Tuple of (endpoint, headers, body):
            - endpoint: Full URL path (e.g., "/api/generate")
            - headers: Request headers dict
            - body: Request body dict (will be JSON-encoded)
        """
        pass

    @abstractmethod
    def parse_response(self, response_json: dict) -> str:
        """
        Parse API-specific response to extract model output.

        Args:
            response_json: Parsed JSON response from API

        Returns:
            Extracted model response text
        """
        pass

    async def invoke(
        self,
        prompt: str,
        model: str,
        context: Optional[str] = None,
        is_deliberation: bool = True,
    ) -> str:
        """
        Invoke the HTTP API with the given prompt and model.

        Args:
            prompt: The prompt to send to the model
            model: Model identifier
            context: Optional additional context to prepend to prompt
            is_deliberation: Whether this is part of a deliberation (unused for HTTP,
                           kept for API compatibility with BaseCLIAdapter)

        Returns:
            Parsed response from the model

        Raises:
            TimeoutError: If request exceeds timeout
            httpx.HTTPStatusError: If API returns error status
            RuntimeError: If retries exhausted
        """
        # Build full prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"

        # Get request components from subclass
        endpoint, headers, body = self.build_request(model, full_prompt)

        # Build full URL
        full_url = f"{self.base_url}{endpoint}"

        # Log request details for debugging
        import json
        import logging

        logger = logging.getLogger(__name__)
        body_str = json.dumps(body)
        logger.debug(
            f"HTTP request to {full_url}: "
            f"body_size={len(body_str)} bytes, "
            f"prompt_length={len(full_prompt)} chars"
        )

        # Execute request with retry logic
        try:
            response_json = await self._execute_request_with_retry(
                url=full_url, headers=headers, body=body
            )
            return self.parse_response(response_json)

        except asyncio.TimeoutError:
            raise TimeoutError(f"HTTP request timed out after {self.timeout}s")

    async def _execute_request_with_retry(
        self, url: str, headers: dict[str, str], body: dict
    ) -> dict:
        """
        Execute HTTP POST request with retry logic.

        Uses tenacity for exponential backoff retry on:
        - 5xx server errors
        - 429 rate limit errors
        - Network errors (connection, timeout)

        Does NOT retry on:
        - 4xx client errors (bad request, auth, etc.)

        Args:
            url: Full request URL
            headers: Request headers
            body: Request body (will be JSON-encoded)

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: On HTTP error (after retries exhausted for 5xx)
            httpx.NetworkError: On network error (after retries exhausted)
        """

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception(is_retryable_http_error),
            reraise=True,
        )
        async def _make_request():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=body)

                # Log error response body for 4xx errors (helps debugging)
                if 400 <= response.status_code < 500:
                    import logging

                    logger = logging.getLogger(__name__)
                    try:
                        error_body = response.json()
                        logger.error(
                            f"HTTP {response.status_code} error response: {error_body}"
                        )
                    except Exception:
                        logger.error(
                            f"HTTP {response.status_code} error response body: {response.text}"
                        )

                response.raise_for_status()  # Raise for 4xx/5xx
                return response.json()

        return await _make_request()
