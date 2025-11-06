"""CLI and HTTP adapter factory and exports."""
from typing import Type, Union

from adapters.base import BaseCLIAdapter
from adapters.base_http import BaseHTTPAdapter
from adapters.claude import ClaudeAdapter
from adapters.codex import CodexAdapter
from adapters.droid import DroidAdapter
from adapters.gemini import GeminiAdapter
from adapters.llamacpp import LlamaCppAdapter
from adapters.lmstudio import LMStudioAdapter
from adapters.ollama import OllamaAdapter
from adapters.openrouter import OpenRouterAdapter
from models.config import CLIAdapterConfig, CLIToolConfig, HTTPAdapterConfig


def create_adapter(
    name: str, config: Union[CLIToolConfig, CLIAdapterConfig, HTTPAdapterConfig]
) -> Union[BaseCLIAdapter, BaseHTTPAdapter]:
    """
    Factory function to create appropriate adapter (CLI or HTTP).

    Args:
        name: Adapter name (e.g., 'claude', 'ollama')
        config: Adapter configuration (CLI or HTTP)

    Returns:
        Appropriate adapter instance (CLI or HTTP)

    Raises:
        ValueError: If adapter is not supported
        TypeError: If config type doesn't match adapter type
    """
    # Registry of CLI adapters
    cli_adapters: dict[str, Type[BaseCLIAdapter]] = {
        "claude": ClaudeAdapter,
        "codex": CodexAdapter,
        "droid": DroidAdapter,
        "gemini": GeminiAdapter,
        "llamacpp": LlamaCppAdapter,
    }

    # Registry of HTTP adapters
    http_adapters: dict[str, Type[BaseHTTPAdapter]] = {
        "ollama": OllamaAdapter,
        "lmstudio": LMStudioAdapter,
        "openrouter": OpenRouterAdapter,
    }

    # Handle legacy CLIToolConfig (backward compatibility)
    if isinstance(config, CLIToolConfig):
        if name in cli_adapters:
            return cli_adapters[name](
                command=config.command, args=config.args, timeout=config.timeout
            )
        else:
            raise ValueError(
                f"Unsupported CLI tool: '{name}'. "
                f"Supported tools: {', '.join(cli_adapters.keys())}"
            )

    # Handle new typed configs
    if isinstance(config, CLIAdapterConfig):
        if name not in cli_adapters:
            raise ValueError(
                f"Unknown CLI adapter: '{name}'. "
                f"Supported CLI adapters: {', '.join(cli_adapters.keys())}"
            )

        return cli_adapters[name](
            command=config.command, args=config.args, timeout=config.timeout
        )

    elif isinstance(config, HTTPAdapterConfig):
        if name not in http_adapters:
            raise ValueError(
                f"Unknown HTTP adapter: '{name}'. "
                f"Supported HTTP adapters: {', '.join(http_adapters.keys())} "
                f"(Note: HTTP adapters are being added in phases)"
            )

        return http_adapters[name](
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            api_key=config.api_key,
            headers=config.headers,
        )

    else:
        raise TypeError(
            f"Invalid config type: {type(config)}. "
            f"Expected CLIToolConfig, CLIAdapterConfig, or HTTPAdapterConfig"
        )


__all__ = [
    "BaseCLIAdapter",
    "BaseHTTPAdapter",
    "ClaudeAdapter",
    "CodexAdapter",
    "DroidAdapter",
    "GeminiAdapter",
    "LlamaCppAdapter",
    "LMStudioAdapter",
    "OllamaAdapter",
    "create_adapter",
]
