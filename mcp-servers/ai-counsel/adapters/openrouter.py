"""OpenRouter HTTP adapter."""
from typing import Tuple

from adapters.base_http import BaseHTTPAdapter


class OpenRouterAdapter(BaseHTTPAdapter):
    """
    Adapter for OpenRouter API.

    OpenRouter provides access to multiple LLM providers through a unified
    OpenAI-compatible API with authentication.

    API Reference: https://openrouter.ai/docs
    Default endpoint: https://openrouter.ai/api/v1
    """

    def build_request(
        self, model: str, prompt: str
    ) -> Tuple[str, dict[str, str], dict]:
        """
        Build OpenRouter API request (OpenAI-compatible format with auth).

        OpenRouter uses the OpenAI chat completions API format with Bearer token auth:
        POST /chat/completions
        Authorization: Bearer <api_key>

        Args:
            model: Model identifier (e.g., "anthropic/claude-3.5-sonnet", "openai/gpt-4")
            prompt: The prompt to send

        Returns:
            Tuple of (endpoint, headers, body)
        """
        endpoint = "/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # Convert prompt to OpenAI chat format
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,  # Use non-streaming for simplicity
        }

        return (endpoint, headers, body)

    def parse_response(self, response_json: dict) -> str:
        """
        Parse OpenRouter API response (OpenAI format).

        OpenRouter returns OpenAI-compatible chat completions format:
        {
          "id": "gen-abc123",
          "model": "anthropic/claude-3.5-sonnet",
          "created": 1234567890,
          "choices": [{
            "index": 0,
            "message": {
              "role": "assistant",
              "content": "The model's response"
            },
            "finish_reason": "stop"
          }]
        }

        Args:
            response_json: Parsed JSON response from OpenRouter

        Returns:
            Extracted response text from first choice

        Raises:
            KeyError: If response doesn't contain expected fields
            IndexError: If choices array is empty
        """
        if "choices" not in response_json:
            raise KeyError(
                f"OpenRouter response missing 'choices' field. "
                f"Received keys: {list(response_json.keys())}"
            )

        if len(response_json["choices"]) == 0:
            raise IndexError("OpenRouter response has empty 'choices' array")

        choice = response_json["choices"][0]

        if "message" not in choice:
            raise KeyError(
                f"OpenRouter choice missing 'message' field. "
                f"Received keys: {list(choice.keys())}"
            )

        message = choice["message"]

        if "content" not in message:
            raise KeyError(
                f"OpenRouter message missing 'content' field. "
                f"Received keys: {list(message.keys())}"
            )

        return message["content"]
