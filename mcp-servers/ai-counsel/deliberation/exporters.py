"""Export decision graph data to various formats.

Supports GraphML, Graphviz DOT, JSON, and Markdown formats for
visualization and analysis in external tools.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from decision_graph.schema import DecisionNode, DecisionSimilarity
from deliberation.query_engine import SimilarResult

logger = logging.getLogger(__name__)


class DecisionGraphExporter:
    """Export decision graph to various formats."""

    @staticmethod
    def to_json(
        decisions: List[DecisionNode],
        similarities: Optional[List[DecisionSimilarity]] = None,
    ) -> str:
        """Export decisions to JSON format.

        Args:
            decisions: List of DecisionNode objects
            similarities: Optional list of DecisionSimilarity relationships

        Returns:
            JSON string with decision graph data
        """
        data = {
            "format": "decision_graph_json",
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "decisions": [
                {
                    "id": d.id,
                    "question": d.question,
                    "timestamp": d.timestamp.isoformat(),
                    "consensus": d.consensus,
                    "winning_option": d.winning_option,
                    "convergence_status": d.convergence_status,
                    "participants": d.participants,
                    "transcript_path": d.transcript_path,
                    "metadata": d.metadata,
                }
                for d in decisions
            ],
        }

        if similarities:
            data["similarities"] = [
                {
                    "source_id": s.source_id,
                    "target_id": s.target_id,
                    "similarity_score": s.similarity_score,
                    "computed_at": s.computed_at.isoformat(),
                }
                for s in similarities
            ]

        return json.dumps(data, indent=2)

    @staticmethod
    def to_graphml(
        decisions: List[DecisionNode],
        similarities: Optional[List[DecisionSimilarity]] = None,
    ) -> str:
        """Export decisions to GraphML format (Gephi compatible).

        Args:
            decisions: List of DecisionNode objects
            similarities: Optional list of DecisionSimilarity relationships

        Returns:
            GraphML XML string
        """
        graphml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
            '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '  xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
            '  http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
            '  <graph mode="static" defaultedgetype="directed">',
            "    <!-- Nodes -->",
        ]

        # Add node attributes
        graphml.extend(
            [
                '    <key id="d_question" for="node" attr.name="question" attr.type="string"/>',
                '    <key id="d_consensus" for="node" attr.name="consensus" attr.type="string"/>',
                '    <key id="d_status" for="node" attr.name="status" attr.type="string"/>',
                '    <key id="d_timestamp" for="node" attr.name="timestamp" attr.type="string"/>',
            ]
        )

        # Add nodes
        for decision in decisions:
            graphml.append(f'    <node id="{decision.id}">')
            graphml.append(
                f'      <data key="d_question">{_escape_xml(decision.question)}</data>'
            )
            graphml.append(
                f'      <data key="d_consensus">{_escape_xml(decision.consensus)}</data>'
            )
            graphml.append(
                f'      <data key="d_status">{decision.convergence_status}</data>'
            )
            graphml.append(
                f'      <data key="d_timestamp">{decision.timestamp.isoformat()}</data>'
            )
            graphml.append("    </node>")

        graphml.append("    <!-- Edges -->")
        graphml.append(
            '    <key id="d_weight" for="edge" attr.name="weight" attr.type="double"/>'
        )

        # Add edges (similarities)
        if similarities:
            for sim in similarities:
                graphml.append(
                    f'    <edge source="{sim.source_id}" target="{sim.target_id}">'
                )
                graphml.append(
                    f'      <data key="d_weight">{sim.similarity_score}</data>'
                )
                graphml.append("    </edge>")

        graphml.extend(
            [
                "  </graph>",
                "</graphml>",
            ]
        )

        return "\n".join(graphml)

    @staticmethod
    def to_dot(
        decisions: List[DecisionNode],
        similarities: Optional[List[DecisionSimilarity]] = None,
    ) -> str:
        """Export decisions to Graphviz DOT format.

        Args:
            decisions: List of DecisionNode objects
            similarities: Optional list of DecisionSimilarity relationships

        Returns:
            Graphviz DOT string
        """
        lines = [
            "digraph DecisionGraph {",
            "  rankdir=LR;",
            "  node [shape=box, style=rounded];",
        ]

        # Add nodes
        for decision in decisions:
            label = _truncate_text(decision.question, 40)
            status_color = {
                "converged": "lightgreen",
                "refining": "lightyellow",
                "diverging": "lightcoral",
                "unanimous_consensus": "lightblue",
                "majority_decision": "lightcyan",
                "tie": "lightgray",
            }.get(decision.convergence_status, "white")

            lines.append(
                f'  "{decision.id}" [label="{label}", fillcolor={status_color}, style="rounded,filled"];'
            )

        # Add edges
        if similarities:
            for sim in similarities:
                weight = sim.similarity_score
                # Only show strong similarities
                if weight > 0.6:
                    lines.append(
                        f'  "{sim.source_id}" -> "{sim.target_id}" [label="{weight:.2f}", weight={weight}];'
                    )

        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def to_markdown(
        decisions: List[DecisionNode],
        similarities: Optional[List[DecisionSimilarity]] = None,
    ) -> str:
        """Export decisions to Markdown format.

        Args:
            decisions: List of DecisionNode objects
            similarities: Optional list of DecisionSimilarity relationships

        Returns:
            Markdown formatted string
        """
        lines = [
            "# Decision Graph Memory Report",
            f"\n_Generated: {datetime.now().isoformat()}_\n",
            f"## Summary\n- Total Decisions: {len(decisions)}\n",
        ]

        if similarities:
            lines.append(f"- Total Relationships: {len(similarities)}\n")

        lines.extend(
            [
                "\n## Decisions\n",
            ]
        )

        for i, decision in enumerate(decisions, 1):
            lines.extend(
                [
                    f"### {i}. {_escape_markdown(decision.question)}\n",
                    f"- **ID**: `{decision.id}`",
                    f"- **Timestamp**: {decision.timestamp.isoformat()}",
                    f"- **Consensus**: {_escape_markdown(decision.consensus)}",
                    f"- **Status**: {decision.convergence_status}",
                    f"- **Participants**: {', '.join(decision.participants)}",
                    f"- **Transcript**: {decision.transcript_path}",
                    f"- **Winning Option**: {decision.winning_option or 'N/A'}\n",
                ]
            )

        if similarities:
            lines.extend(
                [
                    "\n## Relationships\n",
                    "| Source | Target | Similarity |",
                    "|--------|--------|------------|",
                ]
            )

            for sim in sorted(
                similarities, key=lambda s: s.similarity_score, reverse=True
            )[
                :20
            ]:  # Top 20
                source_q = next(
                    (d.question[:20] for d in decisions if d.id == sim.source_id),
                    "Unknown",
                )
                target_q = next(
                    (d.question[:20] for d in decisions if d.id == sim.target_id),
                    "Unknown",
                )
                lines.append(
                    f"| {source_q}... | {target_q}... | {sim.similarity_score:.2%} |"
                )

        return "\n".join(lines)

    @staticmethod
    def to_summary_table(results: List[SimilarResult]) -> str:
        """Export search results as ASCII table.

        Args:
            results: List of SimilarResult objects

        Returns:
            ASCII formatted table
        """
        if not results:
            return "No results found."

        lines = [
            "\n╔═══════════════════════════════════════════════════════════════════╗",
            "║ Similar Decisions                                                 ║",
            "╠═════════╦═══════════════════════════════╦════════════╦═════════════╣",
            "║ Score   ║ Question                      ║ Consensus  ║ Status      ║",
            "╠═════════╬═══════════════════════════════╬════════════╬═════════════╣",
        ]

        for result in results[:10]:  # Show top 10
            score_str = f"{result.score:.0%}".center(7)
            question = _truncate_text(result.decision.question, 27)
            consensus = _truncate_text(result.decision.consensus, 10)
            status = result.decision.convergence_status[:11]

            lines.append(
                f"║ {score_str} ║ {question:<29} ║ {consensus:<10} ║ {status:<11} ║"
            )

        lines.append(
            "╚═════════╩═══════════════════════════════╩════════════╩═════════════╝\n"
        )

        return "\n".join(lines)


def _escape_xml(text: str) -> str:
    """Escape text for XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _escape_markdown(text: str) -> str:
    """Escape text for Markdown."""
    return text.replace("|", "\\|").replace("\n", " ")


def _truncate_text(text: str, max_len: int) -> str:
    """Truncate text to max length."""
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text
