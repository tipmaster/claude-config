#!/usr/bin/env python3
"""
Graph inspection example: Query and analyze decision graph

This example demonstrates how to query the decision graph to find
similar past deliberations, identify contradictions, and analyze
decision patterns.

Requirements:
- AI Counsel installed with decision graph enabled
- At least 2-3 existing deliberations in the graph
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from decision_graph.query_engine import QueryEngine
from decision_graph.storage import DecisionGraphStorage
from models.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run graph inspection example."""

    config = load_config()

    if not config.decision_graph.enabled:
        logger.error(
            "❌ Decision graph is disabled in config.yaml\n"
            "   Enable it: decision_graph.enabled: true"
        )
        return

    logger.info("🔍 Decision Graph Inspection Example\n")

    # Initialize storage to check what's in the graph
    storage = DecisionGraphStorage(config.decision_graph.db_path)

    # Get all decisions
    all_decisions = storage.get_all_decisions(limit=100)
    logger.info("📊 Graph Statistics:")
    logger.info(f"   Total decisions stored: {len(all_decisions)}")

    if not all_decisions:
        logger.warning(
            "\n⚠️  Graph is empty. Run some deliberations first:\n"
            "   python examples/decision_graph/basic_usage.py"
        )
        return

    # Display stored decisions
    logger.info("\n📋 Stored Decisions:")
    for i, decision in enumerate(all_decisions[:5], 1):
        logger.info(f"\n   {i}. {decision.question[:80]}...")
        logger.info(f"      ID: {decision.id[:8]}...")
        logger.info(f"      Consensus: {decision.consensus[:60]}...")
        logger.info(f"      Participants: {', '.join(decision.participants)}")
        logger.info(f"      Timestamp: {decision.timestamp}")

    # Initialize query engine
    engine = QueryEngine(config)

    # Search for similar deliberations
    logger.info("\n🔎 Searching for similar decisions...")
    query = "database architecture and scaling"
    similar = await engine.search_similar(query, limit=3)

    if similar:
        logger.info(f"\n   Found {len(similar)} similar decisions to: '{query}'")
        for result in similar:
            logger.info(f"\n   - Score: {result.get('score', 'N/A'):.2f}")
            logger.info(f"     Q: {result['question'][:80]}...")
            logger.info(f"     A: {result['consensus'][:100]}...")
    else:
        logger.info(f"\n   No similar decisions found for: '{query}'")

    # Find contradictions
    logger.info("\n⚠️  Looking for contradictions in decision history...")
    contradictions = await engine.find_contradictions(threshold=0.3)

    if contradictions:
        logger.info(f"\n   Found {len(contradictions)} contradictions:")
        for i, contradiction in enumerate(contradictions[:3], 1):
            logger.info(f"\n   {i}. {contradiction.get('type', 'Unknown')}")
            logger.info("      Between decisions on similar topics")
            logger.info("      Recommendation: Review and reconcile")
    else:
        logger.info("\n   No significant contradictions found ✓")

    # Analyze decision patterns
    logger.info("\n📈 Decision Patterns:")
    patterns = await engine.analyze_patterns()

    if patterns:
        logger.info(f"\n   Common themes: {patterns.get('common_themes', [])[:3]}")
        logger.info(
            f"   Models agreement: {patterns.get('avg_model_agreement', 0):.1%}"
        )
        logger.info(f"   Convergence time: {patterns.get('avg_rounds', 0):.1f} rounds")
    else:
        logger.info("\n   Insufficient data for pattern analysis yet")

    logger.info("\n" + "=" * 60)
    logger.info("✨ Inspection complete!")
    logger.info("\nMore commands:")
    logger.info("- Search: ai-counsel graph similar --query 'your question'")
    logger.info("- Timeline: ai-counsel graph timeline --decision-id <id>")
    logger.info(
        "- Export: ai-counsel graph export --format graphml > decisions.graphml"
    )


if __name__ == "__main__":
    asyncio.run(main())
