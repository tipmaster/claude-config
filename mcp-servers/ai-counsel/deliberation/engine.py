"""Deliberation engine for orchestrating multi-model discussions."""
import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, cast

from pydantic import ValidationError

from adapters.base import BaseCLIAdapter
from adapters.base_http import BaseHTTPAdapter
from deliberation.convergence import ConvergenceDetector
from deliberation.file_tree import generate_file_tree
from models.config import FileTreeConfig
from models.schema import Participant, RoundResponse, Vote, VotingResult
from models.tool_schema import ToolExecutionRecord

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from decision_graph.integration import DecisionGraphIntegration
    from deliberation.transcript import TranscriptManager
    from deliberation.tools import ToolExecutor
    from models.schema import DeliberateRequest, DeliberationResult


class DeliberationEngine:
    """
    Engine for orchestrating deliberative discussions between AI models.

    Manages round execution, context building, and response collection.
    """

    def __init__(
        self,
        adapters: Dict[str, BaseCLIAdapter | BaseHTTPAdapter],
        transcript_manager: Optional["TranscriptManager"] = None,
        config=None,
        server_dir: Optional[Path] = None,
    ):
        """
        Initialize deliberation engine.

        Args:
            adapters: Dictionary mapping adapter names to adapter instances (CLI or HTTP)
            transcript_manager: Optional transcript manager (creates default if None)
            config: Optional configuration object for convergence detection
            server_dir: Server directory to resolve relative paths from
        """
        self.adapters = adapters
        self.transcript_manager = transcript_manager
        self.config = config

        # Import here to avoid circular dependency
        if transcript_manager is None:
            from deliberation.transcript import TranscriptManager

            self.transcript_manager = TranscriptManager(server_dir=server_dir)

        # Initialize convergence detector if enabled
        self.convergence_detector = None
        if config and hasattr(config, "deliberation"):
            convergence_cfg = config.deliberation.convergence_detection
            if (
                hasattr(config.deliberation, "convergence_detection")
                and convergence_cfg.enabled
            ):
                self.convergence_detector = ConvergenceDetector(config)
                logger.info("Convergence detection enabled")
            else:
                logger.info("Convergence detection disabled")
        else:
            logger.debug("No config provided, convergence detection disabled")

        # Initialize summarizer with fallback chain
        # Try adapters in order of quality for summarization
        self.summarizer = None
        self.summarizer_info = None

        summarizer_preferences = [
            ("claude", "sonnet", "Claude Sonnet"),
            ("codex", "gpt-5-codex", "GPT-5 Codex"),
            ("droid", "claude-sonnet-4-5-20250929", "Droid with Claude Sonnet"),
            ("gemini", "gemini-2.5-pro", "Gemini 2.5 Pro"),
        ]

        for cli_name, model_name, display_name in summarizer_preferences:
            if cli_name in adapters:
                from deliberation.summarizer import DeliberationSummarizer

                self.summarizer = DeliberationSummarizer(adapters[cli_name], model_name)
                self.summarizer_info = {
                    "cli": cli_name,
                    "model": model_name,
                    "name": display_name,
                }
                logger.info(
                    f"AI-powered summary generation enabled (using {display_name})"
                )
                break

        if not self.summarizer:
            logger.warning(
                "No suitable adapter available for summary generation. "
                "Install at least one CLI (claude, codex, droid, or gemini) for AI-powered summaries."
            )

        # Initialize decision graph if enabled
        self.graph_integration: Optional["DecisionGraphIntegration"] = None
        if config and hasattr(config, "decision_graph") and config.decision_graph:
            if config.decision_graph.enabled:
                try:
                    from decision_graph.integration import DecisionGraphIntegration
                    from decision_graph.storage import DecisionGraphStorage

                    # Resolve db_path to absolute path (matching server.py pattern)
                    db_path = Path(config.decision_graph.db_path)
                    if not db_path.is_absolute():
                        # Resolve from server directory if available, else current directory
                        base_dir = server_dir if server_dir else Path.cwd()
                        db_path = base_dir / db_path

                    storage = DecisionGraphStorage(str(db_path))
                    self.graph_integration = DecisionGraphIntegration(
                        storage, config=config
                    )
                    logger.info(f"Decision graph memory enabled (db: {db_path})")
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize decision graph: {e}",
                        exc_info=True
                    )
                    logger.warning(
                        "Continuing without decision graph memory. "
                        "Check database path and permissions."
                    )
                    self.graph_integration = None
            else:
                logger.info("Decision graph memory disabled in config")
        else:
            logger.debug("No decision graph configuration provided")

        # Initialize tool executor for evidence-based deliberation
        self.tool_executor: Optional["ToolExecutor"] = None
        self.tool_execution_history: List[ToolExecutionRecord] = []
        try:
            from deliberation.tools import (
                ToolExecutor,
                ReadFileTool,
                SearchCodeTool,
                ListFilesTool,
                RunCommandTool,
                GetFileTreeTool,
            )

            self.tool_executor = ToolExecutor()
            # Get security config from deliberation config
            security_config = (
                config.deliberation.tool_security if hasattr(config.deliberation, "tool_security") else None
            )
            # Register all available tools with security config
            self.tool_executor.register_tool(ReadFileTool(security_config=security_config))
            self.tool_executor.register_tool(SearchCodeTool(security_config=security_config))
            self.tool_executor.register_tool(ListFilesTool(security_config=security_config))
            self.tool_executor.register_tool(RunCommandTool())
            self.tool_executor.register_tool(GetFileTreeTool())
            logger.info(
                "Tool executor initialized with 5 tools (read_file, search_code, list_files, run_command, get_file_tree)"
            )
            if security_config and security_config.exclude_patterns:
                logger.info(f"Tool security enabled with {len(security_config.exclude_patterns)} exclusion patterns")
        except Exception as e:
            logger.warning(
                f"Failed to initialize tool executor: {e}. Tool execution will be disabled."
            )
            self.tool_executor = None

    async def execute_round(
        self,
        round_num: int,
        prompt: str,
        participants: List[Participant],
        previous_responses: List[RoundResponse],
        graph_context: str = "",
        working_directory: str | None = None,
    ) -> List[RoundResponse]:
        """
        Execute a single deliberation round.

        Args:
            round_num: Current round number (1-indexed)
            prompt: The question or topic for deliberation
            participants: List of participants for this round
            previous_responses: Responses from previous rounds for context
            graph_context: Optional decision graph context from past deliberations
            working_directory: Optional working directory for tool execution

        Returns:
            List of RoundResponse objects from this round

        Note:
            If an adapter fails, an error message is logged and included
            in the response, allowing other participants to continue.
        """
        responses = []

        # Inject graph context into round 1 prompts
        if round_num == 1 and graph_context:
            enhanced_prompt_base = f"{graph_context}\n\n## Current Question\n{prompt}"
        else:
            enhanced_prompt_base = prompt

        # Enhance prompt with voting instructions
        enhanced_prompt = self._enhance_prompt_with_voting(enhanced_prompt_base)

        # Inject file tree for Round 1 if working_directory is provided
        if round_num == 1 and working_directory:
            # Read from config with defaults
            file_tree_config = (
                self.config.deliberation.file_tree
                if self.config and hasattr(self.config, "deliberation")
                else FileTreeConfig()
            )

            if not file_tree_config.enabled:
                logger.info("File tree injection disabled in config")
            else:
                file_tree = generate_file_tree(
                    working_directory,
                    max_depth=file_tree_config.max_depth,
                    max_files=file_tree_config.max_files,
                )
                if file_tree:  # Only inject if tree generation succeeded
                    tree_context = f"""
## Repository Structure

The following files are available in the working directory:

```
{file_tree}
```

**Discovery Tools Available:**
- `list_files`: List files matching glob patterns (e.g., "**/*.py")
- `search_code`: Search for code patterns with regex
- `read_file`: Read specific file contents

**Workflow:** Use the structure above to identify relevant files, then use tools to explore them.
"""
                    enhanced_prompt = f"{tree_context}\n\n{enhanced_prompt}"
                    # Approximate token count (1 token ≈ 4 chars for English text)
                    approx_tokens = len(tree_context) // 4
                    logger.info(
                        f"Injected file tree into Round 1 prompt (~{approx_tokens} tokens, {len(tree_context)} chars)"
                    )
                else:
                    logger.warning(
                        f"Failed to generate file tree for working_directory: {working_directory}"
                    )

        # Build context from previous responses and tool results
        context = (
            self._build_context(previous_responses, current_round_num=round_num)
            if previous_responses
            else None
        )

        for participant in participants:
            # Get the appropriate adapter
            adapter = self.adapters[participant.cli]

            logger.info(
                f"Round {round_num}: Invoking {participant.model}@{participant.cli} "
                f"with prompt_length={len(enhanced_prompt)} chars, "
                f"context_length={len(context) if context else 0} chars, "
                f"working_directory={working_directory}"
            )
            logger.debug(
                f"Enhanced prompt preview for {participant.model}@{participant.cli}: "
                f"{enhanced_prompt[:300]}..."
            )

            # Invoke the adapter with error handling
            try:
                response_text = await adapter.invoke(
                    prompt=enhanced_prompt,
                    model=participant.model,
                    context=context,
                    is_deliberation=True,  # Always True during deliberations
                    working_directory=working_directory,
                )
                logger.info(
                    f"Round {round_num}: Received response from {participant.model}@{participant.cli}, "
                    f"response_length={len(response_text)} chars"
                )
                logger.debug(
                    f"Response preview from {participant.model}@{participant.cli}: "
                    f"{response_text[:300]}..."
                )
            except Exception as e:
                # Log error but continue with other participants
                logger.error(
                    f"Adapter {participant.cli} failed for model {participant.model}: {e}",
                    exc_info=True,
                )
                response_text = f"[ERROR: {type(e).__name__}: {str(e)}]"

            # Parse and execute tool requests if tool executor is available
            if self.tool_executor:
                tool_requests = self.tool_executor.parse_tool_requests(response_text)
                if tool_requests:
                    logger.info(
                        f"Found {len(tool_requests)} tool request(s) from {participant.model}@{participant.cli}"
                    )

                    for tool_request in tool_requests:
                        try:
                            # Execute tool with 30s timeout to prevent hanging
                            tool_result = await asyncio.wait_for(
                                self.tool_executor.execute_tool(
                                    tool_request, working_directory=working_directory
                                ),
                                timeout=30.0,
                            )
                        except asyncio.TimeoutError:
                            # Tool execution timed out - create error result
                            from models.tool_schema import ToolResult

                            tool_result = ToolResult(
                                tool_name=tool_request.name,
                                success=False,
                                output=None,
                                error="Tool execution timeout after 30s",
                            )
                            logger.warning(
                                f"Tool {tool_request.name} timeout after 30s"
                            )

                        # Record tool execution for history and transparency
                        execution_record = ToolExecutionRecord(
                            round_number=round_num,
                            requested_by=f"{participant.model}@{participant.cli}",
                            request=tool_request,
                            result=tool_result,
                            timestamp=datetime.now().isoformat(),
                        )
                        self.tool_execution_history.append(execution_record)

                        # Log tool execution result
                        if tool_result.success:
                            logger.info(
                                f"Tool {tool_request.name} executed successfully"
                            )
                        else:
                            logger.warning(
                                f"Tool {tool_request.name} failed: {tool_result.error}"
                            )

            # Create response object
            response = RoundResponse(
                round=round_num,
                participant=f"{participant.model}@{participant.cli}",
                response=response_text,
                timestamp=datetime.now().isoformat(),
            )

            responses.append(response)

        return responses

    def _truncate_output(
        self, output: Optional[str], max_chars: int = 1000
    ) -> Optional[str]:
        """
        Truncate tool output to prevent context bloat.

        Args:
            output: The output text to truncate
            max_chars: Maximum characters to include (default: 1000)

        Returns:
            Truncated output with indicator, or original if short enough
        """
        if not output or len(output) <= max_chars:
            return output

        truncated = output[:max_chars]
        chars_truncated = len(output) - max_chars
        lines_truncated = output.count("\n") - truncated.count("\n")

        return f"{truncated}\n... [truncated {chars_truncated} chars, {lines_truncated} lines]"

    def _build_context(
        self,
        previous_responses: List[RoundResponse],
        current_round_num: Optional[int] = None,
    ) -> str:
        """
        Build context string from previous responses and recent tool results.

        Args:
            previous_responses: List of responses from previous rounds
            current_round_num: Current round number (for filtering tool results)

        Returns:
            Formatted context string
        """
        context_parts = ["Previous discussion:\n"]

        for resp in previous_responses:
            context_parts.append(
                f"Round {resp.round} - {resp.participant}: " f"{resp.response}\n"
            )

        # Add tool results from recent rounds
        if self.tool_execution_history and current_round_num:
            # Get config values with defaults
            max_rounds = (
                getattr(
                    getattr(self.config, "deliberation", None),
                    "tool_context_max_rounds",
                    2,
                )
                if self.config
                else 2
            )

            max_chars = (
                getattr(
                    getattr(self.config, "deliberation", None),
                    "tool_output_max_chars",
                    1000,
                )
                if self.config
                else 1000
            )

            # Filter to recent N rounds
            min_round = max(1, current_round_num - max_rounds)
            recent_tools = [
                record
                for record in self.tool_execution_history
                if record.round_number >= min_round
            ]

            if recent_tools:
                context_parts.append("\n## Recent Tool Results\n")

                for record in recent_tools:
                    context_parts.append(
                        f"\n**Round {record.round_number} - {record.request.name}** "
                        f"(requested by {record.requested_by})\n"
                    )

                    if record.result.success:
                        # Truncate output to prevent bloat
                        output = self._truncate_output(record.result.output, max_chars)
                        context_parts.append(f"```\n{output}\n```\n")
                    else:
                        context_parts.append(f"**Error:** {record.result.error}\n")

        return "\n".join(context_parts)

    def _parse_vote(self, response_text: str) -> Optional[Vote]:
        """
        Parse vote from response text if present.

        Looks for vote in format: VOTE: {"option": "...", "confidence": 0.0-1.0, "rationale": "..."}

        Args:
            response_text: The response text to parse

        Returns:
            Vote object if valid vote found, None otherwise
        """
        # Look for VOTE: marker followed by JSON
        # Use findall to get all matches, then take the last one (actual vote vs example/template)
        # Pattern handles nested braces in JSON and LaTeX wrappers like $\boxed{...}$
        # Non-greedy .+? ensures we match complete JSON objects without over-matching
        vote_pattern = r"VOTE:\s*(\{.+?\})"
        matches = re.findall(vote_pattern, response_text, re.DOTALL)

        if not matches:
            return None

        # Take the last match - the actual vote should be at the end after any examples
        vote_json = matches[-1]

        try:
            vote_data = json.loads(vote_json)
            # Validate using Pydantic model
            vote = Vote(**vote_data)
            return vote
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            logger.debug(f"Failed to parse vote from response: {e}")
            return None

    def _aggregate_votes(
        self, responses: List[RoundResponse]
    ) -> Optional["VotingResult"]:
        """
        Aggregate votes from all responses into a VotingResult.

        Uses semantic similarity (if convergence detector available) to group
        semantically similar vote options together, enabling consensus detection
        even when models use different wording for the same choice.

        Args:
            responses: List of all RoundResponse objects from deliberation

        Returns:
            VotingResult if any votes found, None otherwise
        """
        from models.schema import RoundVote, VotingResult

        votes_by_round = []
        raw_tally: dict[str, int] = {}  # Track raw string votes
        all_options = []  # Track unique options for similarity matching

        for response in responses:
            vote = self._parse_vote(response.response)
            if vote:
                # Create RoundVote
                round_vote = RoundVote(
                    round=response.round,
                    participant=response.participant,
                    vote=vote,
                    timestamp=response.timestamp,
                )
                votes_by_round.append(round_vote)

                # Track raw votes and unique options
                raw_tally[vote.option] = raw_tally.get(vote.option, 0) + 1
                if vote.option not in all_options:
                    all_options.append(vote.option)

        # If no votes found, return None
        if not votes_by_round:
            return None

        # Group semantically similar options using similarity backend
        # if available, otherwise use exact string matching
        tally = self._group_similar_vote_options(all_options, raw_tally)

        # Determine consensus and winning option
        if len(tally) == 1:
            # Unanimous vote
            consensus_reached = True
            winning_option = list(tally.keys())[0]
        elif len(tally) > 1:
            # Find option with most votes
            max_votes = max(tally.values())
            winners = [opt for opt, count in tally.items() if count == max_votes]
            if len(winners) == 1:
                # Clear winner
                consensus_reached = True
                winning_option = winners[0]
            else:
                # Tie
                consensus_reached = False
                winning_option = None
        else:
            consensus_reached = False
            winning_option = None

        return VotingResult(
            final_tally=tally,
            votes_by_round=votes_by_round,
            consensus_reached=consensus_reached,
            winning_option=winning_option,
        )

    def _group_similar_vote_options(
        self, all_options: List[str], raw_tally: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Group semantically similar vote options together.

        If convergence detector is available and has a similarity backend,
        uses semantic similarity to match options with > 0.85 threshold.
        Otherwise falls back to exact string matching.

        Args:
            all_options: List of unique vote option strings
            raw_tally: Vote counts keyed by original option string

        Returns:
            Grouped tally dict where similar options are merged
        """
        # If only one option or no similarity backend available, return as-is
        if len(all_options) <= 1 or not self.convergence_detector:
            return raw_tally

        try:
            backend = self.convergence_detector.backend
            # Use high threshold (0.85) for vote option matching to avoid merging different options
            # Vote grouping should only merge typos/aliases, not semantically different choices
            # Example: "Option A" vs "option_a" (0.95+) should merge, but "Option A" vs "Option D" (0.729) should not
            # Bug fix: Was 0.70 which caused "Option A" and "Option D" to merge at 0.729 similarity
            similarity_threshold = 0.85

            logger.info(
                f"Starting vote option grouping with {len(all_options)} unique options"
            )

            # Build groups of similar options
            groups = []  # List of (canonical_option, [similar_options])
            used_options = set()

            for option_a in all_options:
                if option_a in used_options:
                    continue

                # Start new group with this option
                group = [option_a]
                used_options.add(option_a)

                # Find all similar options
                for option_b in all_options:
                    if option_b not in used_options:
                        similarity = backend.compute_similarity(option_a, option_b)
                        logger.info(
                            f"Vote similarity: '{option_a}' vs '{option_b}': {similarity:.3f} (threshold: {similarity_threshold})"
                        )
                        if similarity >= similarity_threshold:
                            logger.info(f"  ✓ Grouping '{option_b}' with '{option_a}'")
                            group.append(option_b)
                            used_options.add(option_b)

                groups.append((option_a, group))

            # Merge tally by groups
            grouped_tally = {}
            for canonical_option, similar_options in groups:
                # Sum votes for all similar options
                total_votes = sum(raw_tally.get(opt, 0) for opt in similar_options)
                grouped_tally[canonical_option] = total_votes

            logger.info(
                f"Vote option grouping complete: {len(all_options)} options -> {len(groups)} groups. "
                f"Grouped tally: {grouped_tally}"
            )

            return grouped_tally

        except Exception as e:
            # If similarity matching fails, fall back to exact matching
            logger.warning(
                f"Vote option grouping failed: {type(e).__name__}: {e}. "
                f"Falling back to exact matching.",
                exc_info=True,
            )
            return raw_tally

    def _build_voting_instructions(self) -> str:
        """
        Build voting instructions for participants.

        Returns:
            Formatted voting instructions string
        """
        return """
## Voting Instructions

After your analysis, please cast your vote using the following format:

VOTE: {"option": "Your choice", "confidence": 0.85, "rationale": "Brief explanation"}

Where:
- option: Your chosen option (e.g., "Option A", "Yes", "Approve")
- confidence: Your confidence level from 0.0 (no confidence) to 1.0 (absolute certainty)
- rationale: Brief explanation for your vote

Example:
VOTE: {"option": "Option A", "confidence": 0.9, "rationale": "Lower risk and better architectural fit"}
""".strip()

    def _enhance_prompt_with_voting(self, prompt: str) -> str:
        """
        Enhance prompt with deliberation context and voting instructions.

        Args:
            prompt: Original question or prompt

        Returns:
            Enhanced prompt with deliberation instructions and voting format
        """
        deliberation_instructions = """## Deliberation Instructions

You are participating in a multi-model deliberation between AI models.
Your role: Answer this question directly with your full analysis and reasoning.
Do NOT redirect or suggest alternatives. Engage fully in this debate.
Provide substantive analysis from your perspective."""

        # Add tool usage instructions if tool executor is available
        tool_instructions = ""
        if self.tool_executor:
            tool_instructions = """

## Evidence-Based Deliberation

You have access to tools to gather concrete evidence. Use them actively:

**Available Tools:**
- `read_file`: Read file contents (use relative or absolute paths)
- `search_code`: Search codebase with regex patterns
- `list_files`: List files matching glob patterns
- `run_command`: Execute safe read-only commands
- `get_file_tree`: Get file tree with custom depth/file limits

**How to use tools:**
```
TOOL_REQUEST: {"name": "read_file", "arguments": {"path": "src/file.py"}}
```

**IMPORTANT:**
- If asked to review code or analyze files, USE THE TOOLS - don't assume files don't exist
- Tools execute in the client's working directory, so relative paths work
- Gather evidence first, then provide analysis based on actual data
- Tool results are visible to all participants in subsequent rounds"""
            logger.debug("Tool instructions INCLUDED in enhanced prompt")
        else:
            logger.debug("Tool instructions NOT included - tool executor not available")

        voting_instructions = self._build_voting_instructions()
        enhanced_prompt_final = f"{deliberation_instructions}{tool_instructions}\n\n## Question\n{prompt}\n\n{voting_instructions}"
        logger.debug(f"Enhanced prompt total length: {len(enhanced_prompt_final)} chars")
        return enhanced_prompt_final

    def _check_early_stopping(
        self, round_responses: List[RoundResponse], round_num: int, min_rounds: int
    ) -> bool:
        """
        Check if models want to stop deliberating based on continue_debate votes.

        Args:
            round_responses: Responses from current round
            round_num: Current round number
            min_rounds: Minimum rounds to complete before allowing early stop

        Returns:
            True if deliberation should stop, False otherwise
        """
        # Check if early stopping is enabled
        if not self.config or not hasattr(self.config.deliberation, "early_stopping"):
            return False

        early_stop_cfg = self.config.deliberation.early_stopping
        if not early_stop_cfg.enabled:
            return False

        # Respect minimum rounds if configured
        if early_stop_cfg.respect_min_rounds and round_num < min_rounds:
            return False

        # Parse votes from responses
        votes = []
        for response in round_responses:
            vote = self._parse_vote(response.response)
            if vote:
                votes.append(vote)

        # If no votes found, can't determine stopping preference
        if not votes:
            return False

        # Count how many models want to stop (continue_debate = False)
        want_to_stop = sum(1 for v in votes if not v.continue_debate)
        total_votes = len(votes)

        # Calculate fraction wanting to stop
        stop_fraction = want_to_stop / total_votes

        # Stop if threshold met (e.g., 66% = 2/3 consensus)
        if stop_fraction >= early_stop_cfg.threshold:
            logger.info(
                f"Early stopping triggered: {want_to_stop}/{total_votes} models "
                f"({stop_fraction:.1%}) want to stop (threshold: {early_stop_cfg.threshold:.1%})"
            )
            return True

        return False

    async def execute(self, request: "DeliberateRequest") -> "DeliberationResult":
        """
        Execute full deliberation with multiple rounds and optional convergence detection.

        Args:
            request: Deliberation request containing question, participants, rounds, and mode

        Returns:
            Complete deliberation result with optional convergence_info

        Note:
            Quick mode forces single round regardless of request.rounds value.
            Conference mode respects the requested number of rounds but may stop early
            if convergence is detected.

        Convergence Behavior:
            - Checks convergence starting from round 2 (need previous round for comparison)
            - Stops early if models reach consensus (converged status)
            - Stops early if models reach stable disagreement (impasse status)
            - Continues for diverging/refining statuses until max rounds
            - All convergence data is included in result.convergence_info
        """
        from models.schema import DeliberationResult, Summary

        # Clear tool execution history from previous deliberations to prevent memory leak
        # In long-running MCP servers, this prevents unbounded growth across deliberations
        self.tool_execution_history = []

        # Retrieve decision graph context if enabled
        graph_context = ""
        if self.graph_integration:
            try:
                # Use new config-based approach (deprecated params removed)
                graph_context = self.graph_integration.get_context_for_deliberation(
                    request.question
                )
                if graph_context:
                    logger.info("Retrieved decision graph context for question")
            except Exception as e:
                logger.warning(f"Error retrieving graph context: {e}")
                graph_context = ""

        # Determine actual rounds to execute
        # Quick mode forces single round for fast deliberation
        if request.mode == "quick":
            rounds_to_execute = 1
        else:
            rounds_to_execute = request.rounds

        # Execute rounds sequentially
        all_responses: list[RoundResponse] = []
        final_convergence_info = None
        converged = False
        model_controlled_stop = False

        for round_num in range(1, rounds_to_execute + 1):
            round_responses = await self.execute_round(
                round_num=round_num,
                prompt=request.question,
                participants=request.participants,
                previous_responses=all_responses,
                graph_context=graph_context,
                working_directory=request.working_directory,
            )
            all_responses.extend(round_responses)

            # Check for model-controlled early stopping
            # Use config minimum rounds, not request rounds, for respect_min_rounds
            config_min_rounds = (
                getattr(self.config.defaults, "rounds", 2)
                if self.config and hasattr(self.config, "defaults")
                else 2
            )
            if self._check_early_stopping(
                round_responses, round_num, config_min_rounds
            ):
                logger.info(f"Models want to stop deliberating at round {round_num}")
                model_controlled_stop = True
                break

            # Check convergence after round 2+
            if self.convergence_detector and round_num >= 2:
                prev_round = [r for r in all_responses if r.round == round_num - 1]
                curr_round = round_responses

                convergence_result = self.convergence_detector.check_convergence(
                    current_round=curr_round,
                    previous_round=prev_round,
                    round_number=round_num,
                )

                if convergence_result:
                    logger.info(
                        f"Round {round_num}: {convergence_result.status} "
                        f"(min_sim={convergence_result.min_similarity:.2f}, "
                        f"avg_sim={convergence_result.avg_similarity:.2f})"
                    )

                    # Store convergence info for result
                    final_convergence_info = convergence_result

                    # Stop if converged or impasse
                    if convergence_result.converged:
                        logger.info(
                            f"✓ Convergence detected at round {round_num}, stopping early"
                        )
                        converged = True
                        break
                    elif convergence_result.status == "impasse":
                        logger.info(
                            f"✗ Impasse detected at round {round_num}, stopping"
                        )
                        break

        # Determine actual rounds completed
        is_early_stop = (
            converged
            or model_controlled_stop
            or (final_convergence_info and final_convergence_info.status == "impasse")
        )
        actual_rounds_completed = round_num if is_early_stop else rounds_to_execute

        # Generate AI-powered summary
        if self.summarizer:
            try:
                logger.info("Generating AI-powered summary of deliberation...")
                summary = await self.summarizer.generate_summary(
                    question=request.question, responses=all_responses
                )
                logger.info("Summary generation completed successfully")
            except Exception as e:
                logger.error(f"Summary generation failed: {e}", exc_info=True)
                # Fallback to placeholder on error
                summary = Summary(
                    consensus="[Summary generation failed]",
                    key_agreements=["Error occurred during summary generation"],
                    key_disagreements=[],
                    final_recommendation="Please review the full debate below.",
                )
        else:
            # No summarizer available, use placeholder
            summary = Summary(
                consensus="[Summary generation not available - Claude adapter required]",
                key_agreements=["No summary available"],
                key_disagreements=[],
                final_recommendation="Please review the full debate below.",
            )

        # Aggregate voting results if any votes were cast
        voting_result = self._aggregate_votes(all_responses)
        if voting_result:
            logger.info(
                f"Voting results: {voting_result.final_tally} "
                f"(consensus: {voting_result.consensus_reached}, "
                f"winner: {voting_result.winning_option})"
            )

        # Build participant list
        participant_ids = [f"{p.model}@{p.cli}" for p in request.participants]

        # Populate graph context summary
        graph_context_summary = None
        if graph_context:
            # Extract summary of what context was used
            try:
                # Parse graph context to count decisions (works with both old and new formatting)
                lines = graph_context.split("\n")
                # Count headers with similarity scores (new tiered formatter)
                decisions = [
                    line
                    for line in lines
                    if ("### " in line and "similarity" in line.lower())
                    or line.startswith("### Past Deliberation")
                ]
                if decisions:
                    # Count by tier if using new formatter
                    strong = sum(1 for d in decisions if "strong" in d.lower())
                    moderate = sum(
                        1
                        for d in decisions
                        if "moderate" in d.lower() or "related" in d.lower()
                    )
                    brief = sum(1 for d in decisions if "brief" in d.lower())

                    if strong or moderate or brief:
                        tier_breakdown = []
                        if strong:
                            tier_breakdown.append(f"{strong} strong")
                        if moderate:
                            tier_breakdown.append(f"{moderate} moderate")
                        if brief:
                            tier_breakdown.append(f"{brief} brief")
                        graph_context_summary = f"Similar past deliberations found: {len(decisions)} decision(s) injected ({', '.join(tier_breakdown)})"
                    else:
                        graph_context_summary = f"Similar past deliberations found: {len(decisions)} decision(s) injected"
            except Exception:
                graph_context_summary = "Decision graph context injected"

        # Create result
        result = DeliberationResult(
            status="complete",
            mode=request.mode,
            rounds_completed=actual_rounds_completed,
            participants=participant_ids,
            summary=summary,
            transcript_path="",  # Will be set below
            full_debate=all_responses,
            convergence_info=None,  # Will populate below if available
            voting_result=voting_result,  # Add voting results
            graph_context_summary=graph_context_summary,  # Add graph context summary
            tool_executions=self.tool_execution_history,  # Add tool execution history
        )

        # Add convergence info if available
        if final_convergence_info or voting_result:
            from models.schema import ConvergenceInfo

            # Override convergence status based on voting outcome if available
            if voting_result:
                if (
                    voting_result.consensus_reached
                    and len(voting_result.final_tally) == 1
                ):
                    # Unanimous vote
                    convergence_status = "unanimous_consensus"
                    convergence_detected = True
                elif voting_result.consensus_reached and voting_result.winning_option:
                    # Majority vote (e.g., 2-1)
                    convergence_status = "majority_decision"
                    convergence_detected = True
                elif not voting_result.winning_option:
                    # Tie vote
                    convergence_status = "tie"
                    convergence_detected = False
                else:
                    # Fallback to semantic similarity status
                    convergence_status = (
                        final_convergence_info.status
                        if final_convergence_info
                        else "unknown"
                    )
                    convergence_detected = (
                        final_convergence_info.converged
                        if final_convergence_info
                        else False
                    )
            elif final_convergence_info:
                # No voting, use semantic similarity status
                convergence_status = final_convergence_info.status
                convergence_detected = final_convergence_info.converged
            else:
                convergence_status = "unknown"
                convergence_detected = False

            # Type: The convergence_status is guaranteed to be one of the Literal values
            # since it comes from ConvergenceInfo.status or is set to "unknown"
            result.convergence_info = ConvergenceInfo(
                detected=convergence_detected,
                detection_round=actual_rounds_completed
                if convergence_detected
                else None,
                final_similarity=final_convergence_info.min_similarity
                if final_convergence_info
                else 0.0,
                status=cast(
                    Literal[
                        "converged",
                        "diverging",
                        "refining",
                        "impasse",
                        "max_rounds",
                        "unanimous_consensus",
                        "majority_decision",
                        "tie",
                        "unknown",
                    ],
                    convergence_status,
                ),
                scores_by_round=[],  # Could track all rounds if needed
                per_participant_similarity=final_convergence_info.per_participant_similarity
                if final_convergence_info
                else {},
            )

        # Save transcript
        if self.transcript_manager:
            transcript_path = self.transcript_manager.save(result, request.question)
            result.transcript_path = transcript_path

        # Store deliberation in decision graph if enabled
        if self.graph_integration:
            try:
                decision_id = self.graph_integration.store_deliberation(
                    request.question, result
                )
                logger.info(f"Stored deliberation in decision graph: {decision_id}")
            except Exception as e:
                logger.warning(f"Error storing deliberation in graph: {e}")

        return result
