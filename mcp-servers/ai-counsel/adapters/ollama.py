"""Ollama HTTP adapter."""
from typing import Tuple

from adapters.base_http import BaseHTTPAdapter


class OllamaAdapter(BaseHTTPAdapter):
    """
    Adapter for Ollama local API.

    Ollama is a local LLM runtime that provides an OpenAI-compatible API.
    API reference: https://github.com/ollama/ollama/blob/main/docs/api.md

    Default endpoint: http://localhost:11434

    Example:
        adapter = OllamaAdapter(base_url="http://localhost:11434", timeout=120)
        result = await adapter.invoke(prompt="What is 2+2?", model="llama2")
    """

    def build_request(
        self, model: str, prompt: str
    ) -> Tuple[str, dict[str, str], dict]:
        """
        Build Ollama API request.

        Args:
            model: Ollama model name (e.g., "llama2", "mistral", "codellama")
                  Run 'ollama list' to see available models
            prompt: The prompt to send

        Returns:
            Tuple of (endpoint, headers, body):
            - endpoint: "/api/generate"
            - headers: Content-Type header
            - body: Request body with model, prompt, and stream=false
        """
        endpoint = "/api/generate"

        headers = {"Content-Type": "application/json"}

        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # Use non-streaming mode for simplicity
        }

        return (endpoint, headers, body)

    def parse_response(self, response_json: dict) -> str:
        """
        Parse Ollama API response.

        Ollama response format (non-streaming):
        {
          "model": "llama2",
          "created_at": "2023-08-01T00:00:00Z",
          "response": "The model's response text",
          "done": true,
          "context": [...],
          "total_duration": 5000000000,
          "load_duration": 3000000,
          "prompt_eval_count": 26,
          "eval_count": 298,
          "eval_duration": 4900000000
        }

        Args:
            response_json: Parsed JSON response from Ollama

        Returns:
            Extracted response text

        Raises:
            KeyError: If response doesn't contain 'response' field
        """
        if "response" not in response_json:
            raise KeyError(
                f"Ollama response missing 'response' field. "
                f"Received keys: {list(response_json.keys())}"
            )

        return response_json["response"]
