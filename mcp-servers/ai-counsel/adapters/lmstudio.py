"""LM Studio HTTP adapter."""
from typing import Tuple

from adapters.base_http import BaseHTTPAdapter


class LMStudioAdapter(BaseHTTPAdapter):
    """
    Adapter for LM Studio local API.

    LM Studio provides an OpenAI-compatible API for running local models.
    Uses the OpenAI chat completions format.

    Default endpoint: http://localhost:1234
    API Reference: https://lmstudio.ai/docs/api/rest-api
    """

    def build_request(
        self, model: str, prompt: str
    ) -> Tuple[str, dict[str, str], dict]:
        """
        Build LM Studio API request (OpenAI-compatible format).

        LM Studio uses the OpenAI chat completions API format:
        POST /v1/chat/completions

        Args:
            model: Model name (e.g., "local-model", "llama-2-7b")
            prompt: The prompt to send

        Returns:
            Tuple of (endpoint, headers, body)
        """
        endpoint = "/v1/chat/completions"

        headers = {"Content-Type": "application/json"}

        # Convert prompt to OpenAI chat format
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": False,  # Use non-streaming for simplicity
        }

        return (endpoint, headers, body)

    def parse_response(self, response_json: dict) -> str:
        """
        Parse LM Studio API response (OpenAI format).

        OpenAI chat completions response format:
        {
          "id": "chatcmpl-123",
          "object": "chat.completion",
          "created": 1677652288,
          "model": "gpt-3.5-turbo-0125",
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
            response_json: Parsed JSON response from LM Studio

        Returns:
            Extracted response text from first choice

        Raises:
            KeyError: If response doesn't contain expected fields
            IndexError: If choices array is empty
        """
        if "choices" not in response_json:
            raise KeyError(
                f"LM Studio response missing 'choices' field. "
                f"Received keys: {list(response_json.keys())}"
            )

        if len(response_json["choices"]) == 0:
            raise IndexError("LM Studio response has empty 'choices' array")

        choice = response_json["choices"][0]

        if "message" not in choice:
            raise KeyError(
                f"LM Studio choice missing 'message' field. "
                f"Received keys: {list(choice.keys())}"
            )

        message = choice["message"]

        if "content" not in message:
            raise KeyError(
                f"LM Studio message missing 'content' field. "
                f"Received keys: {list(message.keys())}"
            )

        return message["content"]
