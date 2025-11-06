#!/usr/bin/env python3
"""
Basic usage example: Decision graph memory with deliberations

This example demonstrates how decision graph memory works by running
two deliberations - the first populates the graph, the second uses
context from the first to accelerate convergence.

Requirements:
- AI Counsel installed with decision graph enabled in config.yaml
- At least one AI CLI tool available (claude, codex, droid, gemini)
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deliberation.engine import DeliberationEngine
from models.config import load_config
from models.schema import DeliberateRequest, Participant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run basic usage example."""

    # Load configuration
    config = load_config()

    # Check if decision graph is enabled
    if not config.decision_graph.enabled:
        logger.warning(
            "⚠️  Decision graph is disabled in config.yaml\n"
            "   Enable it by setting: decision_graph.enabled: true"
        )
        return

    logger.info("🚀 Decision Graph Memory - Basic Usage Example\n")

    # Create deliberation engine
    engine = DeliberationEngine(config)

    # First deliberation: Populates the decision graph
    logger.info("📝 Deliberation 1: Architecture decision (stored in graph)")
    logger.info("-" * 60)

    request1 = DeliberateRequest(
        question="To scale database writes, should we use event sourcing or traditional replication?",
        participants=[
            Participant(cli="claude", model="sonnet"),
            Participant(cli="droid", model="claude-sonnet-4-5-20250929"),
        ],
        rounds=2,
        mode="conference",
    )

    result1 = await engine.execute(request1)
    logger.info("\n✅ Deliberation 1 complete")
    logger.info(
        f"   Consensus: {result1.summary.consensus if result1.summary else 'N/A'}"
    )
    logger.info(f"   Rounds: {len(result1.rounds)}")

    # Second deliberation: Uses context from first deliberation
    logger.info("\n📝 Deliberation 2: Audit trail question (uses graph context)")
    logger.info("-" * 60)

    request2 = DeliberateRequest(
        question="How should we implement audit logging for compliance?",
        participants=[
            Participant(cli="claude", model="sonnet"),
            Participant(cli="droid", model="claude-sonnet-4-5-20250929"),
        ],
        rounds=2,
        mode="conference",
    )

    result2 = await engine.execute(request2)
    logger.info("\n✅ Deliberation 2 complete")
    logger.info(
        f"   Consensus: {result2.summary.consensus if result2.summary else 'N/A'}"
    )
    logger.info(f"   Rounds: {len(result2.rounds)}")

    if result2.graph_context_summary:
        logger.info("\n📚 Graph Context Used:")
        logger.info(f"   {result2.graph_context_summary[:200]}...")
    else:
        logger.info(
            "\n📚 No similar past decisions found in graph\n"
            "   (This is normal on first run - graph builds over time)"
        )

    logger.info("\n" + "=" * 60)
    logger.info("✨ Example complete!")
    logger.info("\nNext steps:")
    logger.info("- Run more deliberations to build up graph history")
    logger.info("- Query the graph: ai-counsel graph similar --query 'audit trail'")
    logger.info("- See transcripts in: transcripts/")
    logger.info("- See decision graph database: decision_graph.db")


if __name__ == "__main__":
    asyncio.run(main())
