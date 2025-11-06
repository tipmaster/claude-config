"""Claude CLI adapter."""
from adapters.base import BaseCLIAdapter


class ClaudeAdapter(BaseCLIAdapter):
    """Adapter for claude CLI tool."""

    def __init__(
        self, command: str = "claude", args: list[str] | None = None, timeout: int = 60
    ):
        """
        Initialize Claude adapter.

        Args:
            command: Command to execute (default: "claude")
            args: List of argument templates (from config.yaml)
            timeout: Timeout in seconds (default: 60)
        """
        if args is None:
            raise ValueError("args must be provided from config.yaml")
        super().__init__(command=command, args=args, timeout=timeout)

    def _adjust_args_for_context(self, is_deliberation: bool) -> list[str]:
        """
        Auto-detect context and adjust -p flag accordingly.

        For deliberations (multi-model debates), removes -p flag so Claude engages fully.
        For regular Claude Code work, adds -p flag for project context awareness.

        Args:
            is_deliberation: True if running as part of a deliberation

        Returns:
            Adjusted argument list with -p flag added/removed as needed
        """
        args = self.args.copy()

        if is_deliberation:
            # Remove -p flag for deliberations (we want full engagement)
            if "-p" in args:
                args.remove("-p")
        else:
            # Add -p flag for Claude Code work (project context awareness)
            if "-p" not in args:
                # Insert -p after --model argument if it exists
                if "--model" in args:
                    model_idx = args.index("--model")
                    # Insert after --model and its value
                    args.insert(model_idx + 2, "-p")
                else:
                    # Otherwise insert at the beginning
                    args.insert(0, "-p")

        return args

    def parse_output(self, raw_output: str) -> str:
        """
        Parse claude CLI output.

        Claude CLI with -p flag typically outputs:
        - Header/initialization text
        - Blank lines
        - Actual model response

        We extract everything after the first substantial block of text.

        Args:
            raw_output: Raw stdout from claude CLI

        Returns:
            Parsed model response
        """
        lines = raw_output.strip().split("\n")

        # Skip header lines (typically start with "Claude Code", "Loading", etc.)
        # Find first line that looks like model output (substantial content)
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip() and not any(
                keyword in line.lower()
                for keyword in ["claude code", "loading", "version", "initializing"]
            ):
                start_idx = i
                break

        # Join remaining lines
        response = "\n".join(lines[start_idx:]).strip()
        return response
