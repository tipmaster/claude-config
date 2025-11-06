"""Droid CLI adapter."""
import asyncio
import logging
from typing import Optional

from adapters.base import BaseCLIAdapter

logger = logging.getLogger(__name__)


class DroidAdapter(BaseCLIAdapter):
    """Adapter for droid CLI tool (Factory AI)."""

    # Permission levels to try in order (graceful degradation)
    PERMISSION_LEVELS = ["low", "medium", "high"]

    def __init__(
        self, command: str = "droid", args: list[str] | None = None, timeout: int = 60
    ):
        """
        Initialize Droid adapter.

        Args:
            command: Command to execute (default: "droid")
            args: List of argument templates (from config.yaml)
            timeout: Timeout in seconds (default: 60)

        Note:
            The droid CLI uses `droid exec "prompt"` syntax for non-interactive mode.
            Implements graceful permission degradation: starts with --auto low,
            automatically retries with --auto medium or --auto high if permission
            errors occur.
        """
        if args is None:
            raise ValueError("args must be provided from config.yaml")
        super().__init__(command=command, args=args, timeout=timeout)

    async def invoke(
        self,
        prompt: str,
        model: str,
        context: Optional[str] = None,
        is_deliberation: bool = True,
        working_directory: Optional[str] = None,
    ) -> str:
        """
        Invoke droid with graceful permission degradation.

        Attempts execution starting with --auto low permissions.
        If permission error occurs, automatically retries with higher
        permission levels (medium, then high).

        Args:
            prompt: The prompt to send to the model
            model: Model identifier
            context: Optional additional context
            is_deliberation: Whether this is part of a deliberation
            working_directory: Optional working directory for subprocess execution

        Returns:
            Parsed response from the model

        Raises:
            RuntimeError: If all permission levels fail
            TimeoutError: If execution exceeds timeout
        """
        # Try with each permission level
        last_error = None

        for perm_level in self.PERMISSION_LEVELS:
            try:
                # Attempt with current permission level
                result = await self._invoke_with_permission(
                    prompt=prompt,
                    model=model,
                    context=context,
                    is_deliberation=is_deliberation,
                    permission_level=perm_level,
                    working_directory=working_directory,
                )

                # Log success if we needed to escalate
                if perm_level != "low":
                    logger.info(
                        f"Droid succeeded with --auto {perm_level} "
                        f"(required escalation from lower levels)"
                    )

                return result

            except RuntimeError as e:
                error_msg = str(e)

                # Check if this is a permission error
                if "insufficient permission to proceed" in error_msg.lower():
                    last_error = e
                    logger.debug(
                        f"Droid --auto {perm_level} permission denied, "
                        f"trying next level..."
                    )
                    continue
                else:
                    # Not a permission error, raise immediately
                    raise

        # All permission levels failed
        logger.error(
            f"Droid failed with all permission levels {self.PERMISSION_LEVELS}. "
            f"Last error: {last_error}"
        )
        raise RuntimeError(f"Droid CLI failed with all permission levels: {last_error}")

    async def _invoke_with_permission(
        self,
        prompt: str,
        model: str,
        context: Optional[str],
        is_deliberation: bool,
        permission_level: str,
        working_directory: Optional[str] = None,
    ) -> str:
        """
        Execute droid with specified permission level.

        Args:
            prompt: The prompt to send
            model: Model identifier
            context: Optional context
            is_deliberation: Whether this is deliberation
            permission_level: Permission level to use (low, medium, high)
            working_directory: Optional working directory for subprocess execution

        Returns:
            Parsed response from droid

        Raises:
            RuntimeError: If CLI fails
            TimeoutError: If execution exceeds timeout
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

        # Adjust args based on context
        args = self._adjust_args_for_context(is_deliberation)

        # Inject permission level into args
        # Expected format: ["exec", "--model", "{model}", "{prompt}"]
        # We inject: ["exec", "--auto", permission_level, "--model", "{model}", "{prompt}"]
        args_with_permission = self._inject_permission_level(args, permission_level)

        # Format arguments
        formatted_args = [
            arg.format(model=model, prompt=full_prompt) for arg in args_with_permission
        ]

        # Execute subprocess
        try:
            # Determine working directory for subprocess
            # Use provided working_directory if specified, otherwise use current directory
            import os

            cwd = working_directory if working_directory else os.getcwd()

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
                raise RuntimeError(f"CLI process failed: {error_msg}")

            raw_output = stdout.decode("utf-8", errors="replace")
            return self.parse_output(raw_output)

        except asyncio.TimeoutError:
            raise TimeoutError(f"CLI invocation timed out after {self.timeout}s")

    def _inject_permission_level(
        self, args: list[str], permission_level: str
    ) -> list[str]:
        """
        Inject --auto permission_level into droid args.

        Converts:
            ["exec", "-m", "{model}", "{prompt}"]
        To:
            ["exec", "--auto", "low", "-m", "{model}", "{prompt}"]

        Args:
            args: Original argument list
            permission_level: Permission level to inject (low, medium, high)

        Returns:
            Modified argument list with permission level injected
        """
        if not args or args[0] != "exec":
            logger.warning(
                f"Unexpected droid args format: {args}. Injecting permission level anyway."
            )

        # Insert --auto and permission_level after "exec"
        new_args = args.copy()
        if new_args and new_args[0] == "exec":
            new_args.insert(1, "--auto")
            new_args.insert(2, permission_level)
        else:
            # Fallback: prepend after first element
            new_args.insert(1, "--auto")
            new_args.insert(2, permission_level)

        return new_args

    def parse_output(self, raw_output: str) -> str:
        """
        Parse droid output.

        Droid outputs clean responses without header/footer text,
        so we simply strip whitespace.

        Args:
            raw_output: Raw stdout from droid

        Returns:
            Parsed model response
        """
        return raw_output.strip()
