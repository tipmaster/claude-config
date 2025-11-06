"""CLI commands for decision graph memory queries.

Provides command-line interface for searching, analyzing, and exporting
decision graph data. Uses shared QueryEngine for consistent functionality
with MCP tools.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from decision_graph.storage import DecisionGraphStorage
from deliberation.exporters import DecisionGraphExporter
from deliberation.query_engine import QueryEngine

logger = logging.getLogger(__name__)


@click.group()
def graph():
    """Decision graph memory commands."""
    pass


@graph.command()
@click.option(
    "--query",
    "-q",
    required=True,
    help="Query text to search for similar decisions",
)
@click.option(
    "--limit",
    "-l",
    default=5,
    type=int,
    help="Maximum results to return",
)
@click.option(
    "--threshold",
    "-t",
    default=0.7,
    type=float,
    help="Minimum similarity threshold (0.0-1.0)",
)
@click.option(
    "--db",
    default="decision_graph.db",
    help="Path to decision graph database",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["summary", "detailed", "json", "table"]),
    default="table",
    help="Output format",
)
def similar(query: str, limit: int, threshold: float, db: str, format: str) -> None:
    """Search for similar past deliberations.

    Example:
        ai-counsel graph similar --query "TypeScript adoption" --limit 5
    """
    try:
        storage = DecisionGraphStorage(db)
        engine = QueryEngine(storage)

        results = engine._search_similar_sync(query, limit, threshold)

        if format == "json":
            output = json.dumps(
                {
                    "query": query,
                    "count": len(results),
                    "results": [
                        {
                            "id": r.decision.id,
                            "question": r.decision.question,
                            "score": r.score,
                            "consensus": r.decision.consensus,
                            "participants": r.decision.participants,
                        }
                        for r in results
                    ],
                },
                indent=2,
            )
            click.echo(output)

        elif format == "table":
            click.echo(DecisionGraphExporter.to_summary_table(results))

        else:
            for i, result in enumerate(results, 1):
                click.echo(f"\n{i}. {result.decision.question}")
                click.echo(f"   Score: {result.score:.0%}")
                click.echo(f"   Consensus: {result.decision.consensus}")
                click.echo(f"   Status: {result.decision.convergence_status}")

    except Exception as e:
        logger.error(f"Error in similar: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@graph.command()
@click.option(
    "--scope",
    "-s",
    help="Limit to specific scope/topic",
)
@click.option(
    "--threshold",
    "-t",
    default=0.5,
    type=float,
    help="Similarity threshold for contradictions",
)
@click.option(
    "--db",
    default="decision_graph.db",
    help="Path to decision graph database",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["summary", "json"]),
    default="summary",
    help="Output format",
)
def contradictions(
    scope: Optional[str], threshold: float, db: str, format: str
) -> None:
    """Find contradictions in decision history.

    Example:
        ai-counsel graph contradictions --threshold 0.7
    """
    try:
        storage = DecisionGraphStorage(db)
        engine = QueryEngine(storage)

        contradictions_list = engine._find_contradictions_sync(scope, threshold)

        if format == "json":
            output = json.dumps(
                {
                    "count": len(contradictions_list),
                    "contradictions": [
                        {
                            "decision_id_1": c.decision_id_1,
                            "decision_id_2": c.decision_id_2,
                            "question_1": c.question_1,
                            "question_2": c.question_2,
                            "severity": c.severity,
                            "description": c.description,
                        }
                        for c in contradictions_list
                    ],
                },
                indent=2,
            )
            click.echo(output)
        else:
            click.echo(f"\nFound {len(contradictions_list)} contradictions:\n")
            for i, c in enumerate(contradictions_list, 1):
                click.echo(f"{i}. Severity: {c.severity:.0%}")
                click.echo(f"   Q1: {c.question_1}")
                click.echo(f"   Q2: {c.question_2}")
                click.echo(f"   Issue: {c.description}\n")

    except Exception as e:
        logger.error(f"Error in contradictions: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@graph.command()
@click.option(
    "--id",
    "-i",
    "decision_id",
    required=True,
    help="Decision ID to trace",
)
@click.option(
    "--related",
    is_flag=True,
    help="Include related decisions",
)
@click.option(
    "--db",
    default="decision_graph.db",
    help="Path to decision graph database",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["summary", "detailed", "json"]),
    default="summary",
    help="Output format",
)
def timeline(decision_id: str, related: bool, db: str, format: str) -> None:
    """Trace the evolution of a decision.

    Example:
        ai-counsel graph timeline --id <decision-id> --related
    """
    try:
        storage = DecisionGraphStorage(db)
        engine = QueryEngine(storage)

        timeline_data = engine._trace_evolution_sync(
            decision_id, include_related=related
        )

        if format == "json":
            output = json.dumps(
                {
                    "decision_id": timeline_data.decision_id,
                    "question": timeline_data.question,
                    "consensus": timeline_data.consensus,
                    "status": timeline_data.status,
                    "participants": timeline_data.participants,
                    "rounds": len(timeline_data.rounds),
                    "related": timeline_data.related_decisions,
                },
                indent=2,
            )
            click.echo(output)
        else:
            click.echo(f"\nDecision Timeline: {decision_id}\n")
            click.echo(f"Question: {timeline_data.question}")
            click.echo(f"Consensus: {timeline_data.consensus}")
            click.echo(f"Status: {timeline_data.status}")
            click.echo(f"Participants: {', '.join(timeline_data.participants)}\n")

            if related and timeline_data.related_decisions:
                click.echo("Related Decisions:")
                for rel in timeline_data.related_decisions[:5]:
                    click.echo(
                        f"  - {rel['question']} (similarity: {rel['similarity']:.0%})"
                    )

    except ValueError as e:
        logger.error(f"Error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error in timeline: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@graph.command()
@click.option(
    "--participant",
    "-p",
    help="Filter analysis by participant",
)
@click.option(
    "--db",
    default="decision_graph.db",
    help="Path to decision graph database",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["summary", "json"]),
    default="summary",
    help="Output format",
)
def analyze(participant: Optional[str], db: str, format: str) -> None:
    """Analyze voting patterns and convergence statistics.

    Example:
        ai-counsel graph analyze --participant "opus@claude"
    """
    try:
        storage = DecisionGraphStorage(db)
        engine = QueryEngine(storage)

        analysis = engine._analyze_patterns_sync(participant)

        if format == "json":
            output = json.dumps(
                {
                    "total_decisions": analysis.total_decisions,
                    "total_participants": analysis.total_participants,
                    "voting_patterns": [
                        {
                            "participant": p.participant,
                            "total_votes": p.total_votes,
                            "avg_confidence": p.avg_confidence,
                            "preferred_options": p.preferred_options,
                        }
                        for p in analysis.voting_patterns
                    ],
                    "convergence_stats": analysis.convergence_stats,
                    "participation_metrics": analysis.participation_metrics,
                },
                indent=2,
            )
            click.echo(output)
        else:
            click.echo("\nAnalysis Summary\n")
            click.echo(f"Total Decisions: {analysis.total_decisions}")
            click.echo(f"Total Participants: {analysis.total_participants}\n")

            if analysis.convergence_stats:
                click.echo("Convergence Statistics:")
                for key, value in analysis.convergence_stats.items():
                    click.echo(f"  {key}: {value}")

            if analysis.voting_patterns:
                click.echo("\nVoting Patterns:")
                for pattern in analysis.voting_patterns[:5]:
                    click.echo(f"  {pattern.participant}:")
                    click.echo(f"    Total Votes: {pattern.total_votes}")
                    click.echo(f"    Avg Confidence: {pattern.avg_confidence:.2f}")
                    click.echo(f"    Preferred: {', '.join(pattern.preferred_options)}")

    except Exception as e:
        logger.error(f"Error in analyze: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@graph.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "graphml", "dot", "markdown"]),
    default="json",
    help="Export format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (default: stdout)",
)
@click.option(
    "--db",
    default="decision_graph.db",
    help="Path to decision graph database",
)
def export(format: str, output: Optional[str], db: str) -> None:
    """Export decision graph to external formats.

    Supports JSON, GraphML (Gephi), Graphviz DOT, and Markdown formats.

    Example:
        ai-counsel graph export --format graphml --output graph.graphml
        ai-counsel graph export --format dot | dot -Tpng > graph.png
    """
    try:
        storage = DecisionGraphStorage(db)
        decisions = storage.get_all_decisions()

        if not decisions:
            click.echo("No decisions found in graph.", err=True)
            sys.exit(1)

        # Export based on format
        if format == "json":
            result = DecisionGraphExporter.to_json(decisions)
        elif format == "graphml":
            result = DecisionGraphExporter.to_graphml(decisions)
        elif format == "dot":
            result = DecisionGraphExporter.to_dot(decisions)
        elif format == "markdown":
            result = DecisionGraphExporter.to_markdown(decisions)
        else:
            click.echo(f"Unknown format: {format}", err=True)
            sys.exit(1)

        # Write to file or stdout
        if output:
            Path(output).write_text(result)
            click.echo(f"Exported {len(decisions)} decisions to {output}")
        else:
            click.echo(result)

    except Exception as e:
        logger.error(f"Error in export: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
