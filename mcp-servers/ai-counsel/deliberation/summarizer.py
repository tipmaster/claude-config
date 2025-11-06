"""AI-powered summary generation for deliberations."""
import logging
from typing import Dict, List, Union

from adapters.base import BaseCLIAdapter
from adapters.base_http import BaseHTTPAdapter
from models.schema import RoundResponse, Summary

logger = logging.getLogger(__name__)


class DeliberationSummarizer:
    """
    Generates AI-powered summaries of deliberations.

    Uses a designated AI adapter to analyze the full debate and extract:
    - Overall consensus (if any)
    - Key areas of agreement
    - Key areas of disagreement
    - Final recommendation
    """

    def __init__(self, adapter: Union[BaseCLIAdapter, BaseHTTPAdapter], model: str):
        """
        Initialize summarizer.

        Args:
            adapter: Adapter to use for summary generation (CLI or HTTP)
            model: Model identifier to use (e.g., "sonnet" for Claude)
        """
        self.adapter = adapter
        self.model = model

    async def generate_summary(
        self, question: str, responses: List[RoundResponse]
    ) -> Summary:
        """
        Generate summary from deliberation responses.

        Args:
            question: Original deliberation question
            responses: All responses from all rounds

        Returns:
            Summary object with consensus, agreements, disagreements, and recommendation
        """
        # Build formatted debate text
        debate_text = self._format_debate(question, responses)

        # Create summarization prompt
        prompt = self._create_summary_prompt(debate_text)

        try:
            # Get AI summary
            summary_text = await self.adapter.invoke(
                prompt=prompt, model=self.model, context=None
            )

            # Parse the summary
            return self._parse_summary(summary_text)

        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            # Return placeholder on error
            return Summary(
                consensus="[Summary generation failed]",
                key_agreements=["Error occurred during summary generation"],
                key_disagreements=[],
                final_recommendation="Please review the full debate below.",
            )

    def _format_debate(self, question: str, responses: List[RoundResponse]) -> str:
        """
        Format debate into readable text.

        Args:
            question: Original question
            responses: All responses

        Returns:
            Formatted debate text
        """
        lines = [f"Question: {question}\n"]

        # Group by round
        rounds: Dict[int, List[RoundResponse]] = {}
        for resp in responses:
            if resp.round not in rounds:
                rounds[resp.round] = []
            rounds[resp.round].append(resp)

        # Format each round
        for round_num in sorted(rounds.keys()):
            lines.append(f"\n--- Round {round_num} ---")
            for resp in rounds[round_num]:
                lines.append(f"\n{resp.participant}:")
                lines.append(resp.response)

        return "\n".join(lines)

    def _create_summary_prompt(self, debate_text: str) -> str:
        """
        Create prompt for summary generation.

        Args:
            debate_text: Formatted debate text

        Returns:
            Prompt for AI model
        """
        return f"""Analyze the following AI deliberation and provide a structured summary.

{debate_text}

Please provide your analysis in the following format:

CONSENSUS:
[A 1-2 sentence statement of the overall consensus, if one was reached.
If no consensus, state "No clear consensus reached" and briefly explain the divide.]

KEY AGREEMENTS:
- [Agreement 1]
- [Agreement 2]
- [Agreement 3]
[List 2-5 key points where all or most participants agreed]

KEY DISAGREEMENTS:
- [Disagreement 1]
- [Disagreement 2]
[List any significant points of disagreement, or state "None" if all agreed]

FINAL RECOMMENDATION:
[1-3 sentences providing the best path forward based on the deliberation]

Please be concise and focus on the substance of the arguments, not formatting or style."""

    def _parse_summary(self, summary_text: str) -> Summary:
        """
        Parse AI-generated summary into Summary object.

        Args:
            summary_text: Raw summary text from AI

        Returns:
            Parsed Summary object
        """
        # Initialize with defaults
        consensus: str = "No consensus information provided"
        agreements: List[str] = []
        disagreements: List[str] = []
        recommendation: str = "No recommendation provided"

        # Split into sections
        sections: Dict[str, str | None] = {
            "consensus": None,
            "agreements": None,
            "disagreements": None,
            "recommendation": None,
        }

        current_section = None
        buffer: List[str] = []

        for line in summary_text.split("\n"):
            line_upper = line.strip().upper()

            # Detect section headers
            if "CONSENSUS:" in line_upper:
                if current_section and buffer:
                    sections[current_section] = "\n".join(buffer).strip()
                current_section = "consensus"
                buffer = []
                # Include any text after the header on the same line
                after_header = line.split(":", 1)[1].strip() if ":" in line else ""
                if after_header:
                    buffer.append(after_header)
            elif "KEY AGREEMENT" in line_upper:
                if current_section and buffer:
                    sections[current_section] = "\n".join(buffer).strip()
                current_section = "agreements"
                buffer = []
            elif "KEY DISAGREEMENT" in line_upper:
                if current_section and buffer:
                    sections[current_section] = "\n".join(buffer).strip()
                current_section = "disagreements"
                buffer = []
            elif (
                "FINAL RECOMMENDATION" in line_upper or "RECOMMENDATION:" in line_upper
            ):
                if current_section and buffer:
                    sections[current_section] = "\n".join(buffer).strip()
                current_section = "recommendation"
                buffer = []
                # Include any text after the header on the same line
                after_header = line.split(":", 1)[1].strip() if ":" in line else ""
                if after_header:
                    buffer.append(after_header)
            elif current_section:
                buffer.append(line)

        # Don't forget the last section
        if current_section and buffer:
            sections[current_section] = "\n".join(buffer).strip()

        # Parse consensus
        if sections["consensus"]:
            consensus = sections["consensus"]

        # Parse agreements (bullet points)
        if sections["agreements"]:
            agreements = self._extract_bullet_points(sections["agreements"])

        # Parse disagreements (bullet points)
        if sections["disagreements"]:
            disagreements = self._extract_bullet_points(sections["disagreements"])

        # Parse recommendation
        if sections["recommendation"]:
            recommendation = sections["recommendation"]

        return Summary(
            consensus=consensus,
            key_agreements=agreements
            if agreements
            else ["No specific agreements identified"],
            key_disagreements=disagreements
            if disagreements
            else ["No significant disagreements"],
            final_recommendation=recommendation,
        )

    def _extract_bullet_points(self, text: str) -> List[str]:
        """
        Extract bullet points from text.

        Args:
            text: Text containing bullet points

        Returns:
            List of bullet point contents
        """
        points = []
        for line in text.split("\n"):
            line = line.strip()
            # Match various bullet formats: -, *, •, 1., etc.
            if line and (
                line.startswith("-")
                or line.startswith("*")
                or line.startswith("•")
                or (len(line) > 2 and line[0].isdigit() and line[1] in ".)")
            ):
                # Remove bullet/number prefix
                if line.startswith(("-", "*", "•")):
                    content = line[1:].strip()
                else:
                    # Remove number prefix (e.g., "1. " or "1) ")
                    content = line.split(None, 1)[1] if " " in line else line

                if content:
                    points.append(content)

        return points
