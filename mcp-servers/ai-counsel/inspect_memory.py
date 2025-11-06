#!/usr/bin/env python3
"""
Inspect Decision Graph Memory

Shows you what decisions have been stored and how they're related.
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from decision_graph.storage import DecisionGraphStorage


def inspect_memory():
    """Inspect the decision graph memory."""

    print("\n" + "=" * 70)
    print("DECISION GRAPH MEMORY INSPECTOR")
    print("=" * 70)

    # Initialize storage
    db_path = "decision_graph.db"
    storage = DecisionGraphStorage(db_path)

    print(f"\n📦 Database: {db_path}")

    # Get statistics
    stats = storage.get_graph_stats()
    print("\n📊 Graph Statistics:")
    print(f"   • Total decisions: {stats['node_count']}")
    print(f"   • Relationships: {stats['edge_count']}")
    print(f"   • Avg similarity: {stats.get('avg_similarity', 'N/A')}")

    # List all decisions
    if stats["node_count"] > 0:
        print("\n📋 Stored Decisions:")
        decisions = storage.get_all_decisions(limit=100)

        for i, decision in enumerate(decisions, 1):
            print(f"\n   [{i}] {decision.question[:60]}...")
            print(f"       ID: {decision.id}")
            print(f"       Consensus: {decision.consensus}")
            print(f"       Convergence: {decision.convergence_status}")
            print(f"       Participants: {', '.join(decision.participants)}")
            print(f"       Timestamp: {decision.timestamp}")
            print(f"       Transcript: {decision.transcript_path}")

            # Get related decisions
            similar = storage.get_similar_decisions(decision.id, threshold=0.7, limit=3)
            if similar:
                print("       Related decisions:")
                for j, (similar_decision, score) in enumerate(similar, 1):
                    print(
                        f"         • {j}. {similar_decision.question[:50]}... (score: {score:.2f})"
                    )

    else:
        print("\n   ℹ️  No decisions stored yet.")
        print("   Run demo_memory_system.py to generate sample data.")

    # Show health
    print("\n🏥 Graph Health:")
    health = storage.health_check()
    print(f"   • Status: {health['status']}")
    for key, value in health.items():
        if key != "status":
            print(f"   • {key}: {value}")

    # Close connection
    storage.close()

    print("\n" + "=" * 70)
    print("✅ Inspection complete\n")


if __name__ == "__main__":
    try:
        inspect_memory()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
