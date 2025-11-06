"""Transcript management for deliberations."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.schema import DeliberationResult


class TranscriptManager:
    """
    Manages saving deliberation transcripts.

    Generates markdown files with full debate history and summary.
    """

    def __init__(
        self, output_dir: str = "transcripts", server_dir: Optional[Path] = None
    ):
        """
        Initialize transcript manager.

        Args:
            output_dir: Directory to save transcripts (default: transcripts/)
            server_dir: Server directory to resolve relative paths from
        """
        output_path = Path(output_dir)
        # Make output_dir absolute - if relative and server_dir provided, resolve from server directory
        if not output_path.is_absolute() and server_dir is not None:
            self.output_dir = server_dir / output_path
        else:
            self.output_dir = output_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _format_tool_executions_section(self, result: DeliberationResult) -> list[str]:
        """
        Format tool executions section for markdown transcript.

        Args:
            result: Deliberation result containing tool execution data

        Returns:
            List of markdown lines for tool executions section
        """
        if not result.tool_executions:
            return []

        lines = [
            "---",
            "",
            "## Tool Executions",
            "",
        ]

        for execution in result.tool_executions:
            lines.extend([
                f"### {execution.request.name} (Round {execution.round_number})",
                "",
                f"**Requested by:** {execution.requested_by}",
                f"**Timestamp:** {execution.timestamp}",
                "",
                "**Arguments:**",
                "```json",
                str(execution.request.arguments),
                "```",
                "",
            ])

            if execution.result.success:
                # Truncate long outputs
                output = execution.result.output
                if output and len(output) > 2000:
                    output = output[:2000] + "\n... (truncated)"

                lines.extend([
                    f"**Status:** ✅ Success",
                    "",
                    "**Output:**",
                    "```",
                    output or "(empty)",
                    "```",
                    "",
                ])
            else:
                lines.extend([
                    f"**Status:** ❌ Failed",
                    "",
                    f"**Error:** {execution.result.error}",
                    "",
                ])

        return lines

    def _format_voting_section(self, result: DeliberationResult) -> list[str]:
        """
        Format voting results section for markdown transcript.

        Args:
            result: Deliberation result containing voting data

        Returns:
            List of markdown lines for voting section
        """
        if not result.voting_result:
            return []

        lines = [
            "---",
            "",
            "## Voting Results",
            "",
            "### Final Tally",
            "",
        ]

        # Sort by vote count (descending) for better readability
        sorted_tally = sorted(
            result.voting_result.final_tally.items(), key=lambda x: x[1], reverse=True
        )

        for option, count in sorted_tally:
            winning_indicator = (
                " ✓" if option == result.voting_result.winning_option else ""
            )
            lines.append(f"- **{option}**: {count} vote(s){winning_indicator}")

        lines.extend(
            [
                "",
                f"**Consensus Reached:** {'Yes' if result.voting_result.consensus_reached else 'No'}",
                "",
            ]
        )

        if result.voting_result.winning_option:
            lines.append(f"**Winning Option:** {result.voting_result.winning_option}")
        else:
            lines.append("**Winning Option:** No winner (tie or insufficient votes)")

        lines.extend(
            [
                "",
                "### Votes by Round",
                "",
            ]
        )

        # Group votes by round
        current_voting_round = None
        for round_vote in result.voting_result.votes_by_round:
            if round_vote.round != current_voting_round:
                current_voting_round = round_vote.round
                lines.extend(
                    [
                        f"#### Round {current_voting_round}",
                        "",
                    ]
                )

            lines.extend(
                [
                    f"**{round_vote.participant}**",
                    f"- Option: {round_vote.vote.option}",
                    f"- Confidence: {round_vote.vote.confidence:.2f}",
                    f"- Continue Debate: {'Yes' if round_vote.vote.continue_debate else 'No'}",
                    f"- Rationale: {round_vote.vote.rationale}",
                    "",
                ]
            )

        lines.extend(
            [
                "",
            ]
        )

        return lines

    def generate_markdown(self, result: DeliberationResult) -> str:
        """
        Generate markdown transcript from result.

        Args:
            result: Deliberation result

        Returns:
            Markdown formatted transcript
        """
        lines = [
            "# AI Counsel Deliberation Transcript",
            "",
            f"**Status:** {result.status}",
            f"**Mode:** {result.mode}",
            f"**Rounds Completed:** {result.rounds_completed}",
            f"**Participants:** {', '.join(result.participants)}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"**Consensus:** {result.summary.consensus}",
            "",
            "### Key Agreements",
            "",
        ]

        for agreement in result.summary.key_agreements:
            lines.append(f"- {agreement}")

        lines.extend(
            [
                "",
                "### Key Disagreements",
                "",
            ]
        )

        for disagreement in result.summary.key_disagreements:
            lines.append(f"- {disagreement}")

        lines.extend(
            [
                "",
                f"**Final Recommendation:** {result.summary.final_recommendation}",
                "",
            ]
        )

        # Add voting results if available
        voting_lines = self._format_voting_section(result)
        if voting_lines:
            lines.extend(voting_lines)

        # Add tool executions if available
        tool_lines = self._format_tool_executions_section(result)
        if tool_lines:
            lines.extend(tool_lines)

        # Add decision graph context section if available
        if result.graph_context_summary:
            lines.extend(
                [
                    "---",
                    "",
                    "## Decision Graph Context",
                    "",
                    result.graph_context_summary,
                    "",
                    "*Past deliberations were analyzed for similar topics and their outcomes were considered in this deliberation.*",
                    "",
                ]
            )

        lines.extend(
            [
                "---",
                "",
                "## Full Debate",
                "",
            ]
        )

        # Group by round
        current_round = None
        for response in result.full_debate:
            if response.round != current_round:
                current_round = response.round
                lines.extend(
                    [
                        f"### Round {current_round}",
                        "",
                    ]
                )

            lines.extend(
                [
                    f"**{response.participant}**",
                    "",
                    response.response,
                    "",
                    f"*{response.timestamp}*",
                    "",
                    "---",
                    "",
                ]
            )

        return "\n".join(lines)

    def save(
        self, result: DeliberationResult, question: str, filename: Optional[str] = None
    ) -> str:
        """
        Save deliberation transcript to file.

        Args:
            result: Deliberation result
            question: Original question
            filename: Optional custom filename (default: auto-generated)

        Returns:
            Path to saved file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Create safe filename from question
            safe_question = "".join(
                c for c in question[:50] if c.isalnum() or c in (" ", "-", "_")
            )
            safe_question = safe_question.strip().replace(" ", "_")
            filename = f"{timestamp}_{safe_question}.md"

        # Ensure .md extension
        if not filename.endswith(".md"):
            filename += ".md"

        filepath = self.output_dir / filename

        # Ensure destination directory exists (handles cases where it was deleted after initialization)
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - defensive path
            raise RuntimeError(
                f"Failed to create transcript directory '{filepath.parent}': {exc}"
            ) from exc

        # Generate markdown with question at top
        markdown = f"# {question}\n\n" + self.generate_markdown(result)

        # Save
        try:
            filepath.write_text(markdown, encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive path
            raise RuntimeError(
                f"Failed to write transcript to '{filepath}': {exc}"
            ) from exc

        return str(filepath)
