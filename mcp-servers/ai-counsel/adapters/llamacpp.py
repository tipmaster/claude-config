"""llama.cpp CLI adapter.

llama.cpp is a fast, lightweight LLM inference engine for running models locally.
It outputs verbose metadata along with the actual model response, requiring
custom parsing logic to extract just the response text.

Typical output format:
    llama_model_loader: loaded meta data with N key-value pairs
    llm_load_print_meta: model type = 7B
    llama_new_context_with_model: n_ctx = 512
    sampling: repeat_last_n = 64, repeat_penalty = 1.100

    [Actual model response here]

    llama_print_timings: load time = X ms
    llama_print_timings: sample time = Y ms
    llama_print_timings: eval time = Z ms
"""
import os
from pathlib import Path
from typing import Optional
from adapters.base import BaseCLIAdapter


class LlamaCppAdapter(BaseCLIAdapter):
    """Adapter for llama.cpp CLI tool (llama-cli) with auto-discovery."""

    # Default search paths for GGUF model files
    DEFAULT_SEARCH_PATHS = [
        "~/.cache/llama.cpp/models",
        "~/models",
        "~/llama.cpp/models",
        "/usr/local/share/llama.cpp/models",
        "~/.ollama/models",  # Ollama's model directory
        "~/.lmstudio/models",  # LM Studio's model directory
    ]

    def __init__(
        self,
        command: str = "llama-cli",
        args: list[str] | None = None,
        timeout: int = 120,
        search_paths: list[str] | None = None,
    ):
        """
        Initialize llama.cpp adapter with auto-discovery.

        Args:
            command: Command to execute (default: "llama-cli")
            args: List of argument templates (from config.yaml)
            timeout: Timeout in seconds (default: 120, as local inference can be slow)
            search_paths: Custom search paths for models (uses DEFAULT_SEARCH_PATHS if None)

        Raises:
            ValueError: If args is not provided
        """
        if args is None:
            raise ValueError("args must be provided from config.yaml")
        super().__init__(command=command, args=args, timeout=timeout)
        self.search_paths = search_paths or self.DEFAULT_SEARCH_PATHS

    async def invoke(
        self,
        prompt: str,
        model: str,
        context: Optional[str] = None,
        is_deliberation: bool = True,
    ) -> str:
        """
        Invoke llama.cpp with auto-discovery for model paths.

        Args:
            prompt: The prompt to send to the model
            model: Model identifier (can be name or full path)
            context: Optional additional context
            is_deliberation: Whether this is part of a deliberation

        Returns:
            Parsed response from the model

        Raises:
            FileNotFoundError: If model cannot be found
            TimeoutError: If execution exceeds timeout
            RuntimeError: If CLI process fails
        """
        # Resolve model to actual path
        resolved_model = self._resolve_model_path(model)

        # Call parent's invoke with resolved path
        return await super().invoke(
            prompt=prompt,
            model=resolved_model,
            context=context,
            is_deliberation=is_deliberation,
        )

    def _resolve_model_path(self, model: str) -> str:
        """
        Resolve a model name or path to an actual file path.

        Supports:
        - Full absolute paths: "/path/to/model.gguf"
        - Relative paths: "./models/model.gguf"
        - Model names: "llama-2-7b-chat" (searches for .gguf files)
        - Fuzzy names: "llama-2-7b" (finds "llama-2-7b-chat.Q4_K_M.gguf")

        Args:
            model: Model identifier (name or path)

        Returns:
            Resolved absolute path to model file

        Raises:
            FileNotFoundError: If model cannot be found
        """
        # If it's already a valid absolute path, return it
        if os.path.isabs(model) and os.path.exists(model):
            return model

        # If it's a valid relative path, resolve and return
        if os.path.exists(model):
            return os.path.abspath(model)

        # Try to find model by name in search paths
        found_models = self._find_models_by_name(model)

        if not found_models:
            raise FileNotFoundError(
                f"Model not found: '{model}'\n\n"
                f"Searched in:\n" + "\n".join(f"  - {p}" for p in self._get_expanded_search_paths()) + "\n\n"
                f"Available models:\n" + self._format_available_models() + "\n\n"
                f"Tips:\n"
                f"  - Use full path: '/path/to/model.gguf'\n"
                f"  - Download models from: https://huggingface.co/models?library=gguf\n"
                f"  - Set LLAMA_CPP_MODEL_PATH environment variable to add search paths"
            )

        # If exactly one match, use it
        if len(found_models) == 1:
            return str(found_models[0])

        # Multiple matches - prefer exact name match, then shortest path
        for candidate in found_models:
            if candidate.stem == model or candidate.name == model:
                return str(candidate)

        # No exact match, return shortest path (most likely to be correct)
        shortest = min(found_models, key=lambda p: len(str(p)))
        return str(shortest)

    def _find_models_by_name(self, name: str) -> list[Path]:
        """
        Find GGUF model files matching the given name.

        Performs fuzzy matching - "llama-2-7b" matches "llama-2-7b-chat.Q4_K_M.gguf".

        Args:
            name: Model name (can be partial)

        Returns:
            List of matching Path objects
        """
        matches = []
        name_lower = name.lower()

        for search_path in self._get_expanded_search_paths():
            if not search_path.exists():
                continue

            # Search recursively for .gguf files
            for model_file in search_path.rglob("*.gguf"):
                # Check if name appears in filename (fuzzy match)
                if name_lower in model_file.stem.lower():
                    matches.append(model_file)

        return matches

    def _get_expanded_search_paths(self) -> list[Path]:
        """
        Get search paths with environment variables and ~ expanded.

        Also checks LLAMA_CPP_MODEL_PATH environment variable.

        Returns:
            List of expanded Path objects
        """
        paths = []

        # Add paths from environment variable
        env_path = os.environ.get("LLAMA_CPP_MODEL_PATH")
        if env_path:
            paths.extend(env_path.split(":"))

        # Add default search paths
        paths.extend(self.search_paths)

        # Expand and deduplicate
        expanded = []
        seen = set()
        for path_str in paths:
            expanded_path = Path(path_str).expanduser()
            if str(expanded_path) not in seen:
                seen.add(str(expanded_path))
                expanded.append(expanded_path)

        return expanded

    def _format_available_models(self) -> str:
        """
        Format a list of available models for error messages.

        Returns:
            Formatted string listing available models
        """
        all_models = []

        for search_path in self._get_expanded_search_paths():
            if not search_path.exists():
                continue

            for model_file in search_path.rglob("*.gguf"):
                # Show relative path if in search dir, else full path
                try:
                    rel_path = model_file.relative_to(search_path)
                    display_path = f"{search_path.name}/{rel_path}"
                except ValueError:
                    display_path = str(model_file)

                all_models.append(f"  - {model_file.stem} ({display_path})")

        if not all_models:
            return "  (No .gguf models found in search paths)"

        # Limit to first 10 to avoid overwhelming output
        if len(all_models) > 10:
            return "\n".join(all_models[:10]) + f"\n  ... and {len(all_models) - 10} more"

        return "\n".join(all_models)

    def parse_output(self, raw_output: str) -> str:
        """
        Parse llama.cpp CLI output to extract model response.

        llama.cpp outputs verbose metadata before and after the actual response.
        This parser identifies and removes:
        - llama_model_loader lines (model loading info)
        - llm_load_print_meta lines (model metadata)
        - llama_new_context_with_model lines (context setup)
        - sampling: lines (sampling parameters)
        - generate: lines (generation settings)
        - llama_print_timings lines (performance metrics)

        The actual model response is typically the text between these metadata blocks.

        Args:
            raw_output: Raw stdout from llama.cpp CLI

        Returns:
            Extracted model response with metadata removed
        """
        lines = raw_output.strip().split("\n")

        # Metadata prefixes to filter out
        metadata_prefixes = [
            "llama_model_loader:",
            "llm_load_print_meta:",
            "llama_new_context_with_model:",
            "llama_print_timings:",
            "sampling:",
            "generate:",
            "llm_load_tensors:",
            "llama_kv_cache_init:",
            "system_info:",
            "ggml_",  # ggml library messages
            "gguf_",  # gguf format messages
        ]

        # Exact matches to filter out (interactive prompts, EOF markers)
        metadata_exact = [
            "> EOF by user",
            ">",
            "EOF",
        ]

        # Filter out metadata lines
        response_lines = []
        for line in lines:
            stripped = line.strip()

            # Check if line starts with any metadata prefix
            is_metadata = any(
                stripped.startswith(prefix) for prefix in metadata_prefixes
            )

            # Check if line exactly matches any metadata pattern
            is_exact_match = stripped in metadata_exact

            # Keep line if it's not metadata
            if not is_metadata and not is_exact_match:
                response_lines.append(line)

        # Join and strip the result
        response = "\n".join(response_lines).strip()
        return response
