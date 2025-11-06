"""Codex CLI adapter."""
from adapters.base import BaseCLIAdapter


class CodexAdapter(BaseCLIAdapter):
    """Adapter for codex CLI tool."""

    def __init__(
        self, command: str = "codex", args: list[str] | None = None, timeout: int = 60
    ):
        """
        Initialize Codex adapter.

        Args:
            command: Command to execute (default: "codex")
            args: List of argument templates (from config.yaml)
            timeout: Timeout in seconds (default: 60)

        Note:
            The codex CLI uses `codex exec "prompt"` syntax.
            Model is configured via ~/.codex/config.toml, not passed as CLI arg.
        """
        if args is None:
            raise ValueError("args must be provided from config.yaml")
        super().__init__(command=command, args=args, timeout=timeout)

    def parse_output(self, raw_output: str) -> str:
        """
        Parse codex output.

        Codex outputs clean responses without header/footer text,
        so we simply strip whitespace.

        Args:
            raw_output: Raw stdout from codex

        Returns:
            Parsed model response
        """
        return raw_output.strip()
