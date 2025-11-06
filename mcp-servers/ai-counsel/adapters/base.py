"""Base CLI adapter with subprocess management."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseCLIAdapter(ABC):
    """
    Abstract base class for CLI tool adapters.

    Handles subprocess execution, timeout management, and error handling.
    Subclasses must implement parse_output() for tool-specific parsing.
    """

    def __init__(self, command: str, args: list[str], timeout: int = 60):
        """
        Initialize CLI adapter.

        Args:
            command: CLI command to execute
            args: List of argument templates (may contain {model}, {prompt} placeholders)
            timeout: Timeout in seconds (default: 60)
        """
        self.command = command
        self.args = args
        self.timeout = timeout

    async def invoke(
        self,
        prompt: str,
        model: str,
        context: Optional[str] = None,
        is_deliberation: bool = True,
        working_directory: Optional[str] = None,
    ) -> str:
        """
        Invoke the CLI tool with the given prompt and model.

        Args:
            prompt: The prompt to send to the model
            model: Model identifier
            context: Optional additional context
            is_deliberation: Whether this is part of a deliberation (auto-adjusts -p flag for Claude)
            working_directory: Optional working directory for subprocess execution (defaults to current directory)

        Returns:
            Parsed response from the model

        Raises:
            TimeoutError: If execution exceeds timeout
            RuntimeError: If CLI process fails
        """
        # Build full prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"

        # Validate prompt length if adapter supports it
        if hasattr(self, "validate_prompt_length"):
            if not self.validate_prompt_length(full_prompt):
                raise ValueError(
                    f"Prompt too long ({len(full_prompt)} chars). "
                    f"Maximum allowed: {getattr(self, 'MAX_PROMPT_CHARS', 'unknown')} chars. "
                    "This prevents API rejection errors."
                )

        # Adjust args based on context (for auto-detecting deliberation mode)
        args = self._adjust_args_for_context(is_deliberation)

        # Determine working directory for subprocess
        # Use provided working_directory if specified, otherwise use current directory
        import os

        cwd = working_directory if working_directory else os.getcwd()

        # Format arguments with {model}, {prompt}, and {working_directory} placeholders
        formatted_args = [
            arg.format(model=model, prompt=full_prompt, working_directory=cwd)
            for arg in args
        ]

        # Log the command being executed
        logger.info(
            f"Executing CLI adapter: command={self.command}, "
            f"model={model}, cwd={cwd}, "
            f"prompt_length={len(full_prompt)} chars"
        )
        logger.debug(f"Full command: {self.command} {' '.join(formatted_args[:3])}... (args truncated)")

        # Execute subprocess
        try:

            process = await asyncio.create_subprocess_exec(
                self.command,
                *formatted_args,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                logger.error(
                    f"CLI process failed: command={self.command}, "
                    f"model={model}, returncode={process.returncode}, "
                    f"error={error_msg[:200]}"
                )
                raise RuntimeError(f"CLI process failed: {error_msg}")

            raw_output = stdout.decode("utf-8", errors="replace")
            logger.info(
                f"CLI adapter completed successfully: command={self.command}, "
                f"model={model}, output_length={len(raw_output)} chars"
            )
            logger.debug(f"Raw output preview: {raw_output[:500]}...")
            return self.parse_output(raw_output)

        except asyncio.TimeoutError:
            logger.error(
                f"CLI invocation timed out: command={self.command}, "
                f"model={model}, timeout={self.timeout}s"
            )
            raise TimeoutError(f"CLI invocation timed out after {self.timeout}s")

    def _adjust_args_for_context(self, is_deliberation: bool) -> list[str]:
        """
        Adjust CLI arguments based on context (deliberation vs regular Claude Code work).

        By default, returns args as-is. Subclasses can override for context-specific behavior.
        Example: Claude adapter adds -p flag for Claude Code work, removes it for deliberation.

        Args:
            is_deliberation: True if running as part of a multi-model deliberation

        Returns:
            Adjusted argument list
        """
        return self.args

    @abstractmethod
    def parse_output(self, raw_output: str) -> str:
        """
        Parse raw CLI output to extract model response.

        Must be implemented by subclasses based on their output format.

        Args:
            raw_output: Raw stdout from CLI tool

        Returns:
            Parsed model response text
        """
        pass
