#!/usr/bin/env python3
"""
Demo: AI Counsel Decision Graph Memory System in Action

This script demonstrates:
1. First deliberation - stores a decision in memory
2. Related deliberation - retrieves past context and uses it
3. Shows memory system accelerating convergence
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from deliberation.engine import DeliberationEngine
from models.config import load_config
from models.schema import DeliberateRequest, Participant


async def demo():
    """Run demonstration of decision graph memory system."""

    # Load configuration
    config = load_config("config.yaml")
    print("\n" + "=" * 70)
    print("AI COUNSEL - DECISION GRAPH MEMORY SYSTEM DEMO")
    print("=" * 70)

    # Initialize deliberation engine
    engine = DeliberationEngine(config)

    print("\n📚 Decision Graph Status:")
    print(f"   ✓ Enabled: {config.decision_graph.enabled}")
    print(f"   ✓ Database: {config.decision_graph.db_path}")
    print(f"   ✓ Similarity Threshold: {config.decision_graph.similarity_threshold}")
    print(f"   ✓ Max Context Decisions: {config.decision_graph.max_context_decisions}")

    # First deliberation - vector database choice
    print("\n" + "-" * 70)
    print("DELIBERATION #1: Choosing a Vector Database")
    print("-" * 70)

    question_1 = """
    Our team needs to choose between three vector database options for our AI search system:
    1. Pinecone - Fully managed cloud service, easy to use, higher cost
    2. Weaviate - Open source, self-hosted, more control, operational overhead
    3. Milvus - Open source, high performance, complex deployment, excellent for large scale

    What are the trade-offs and which would you recommend for a startup?
    """

    participants_1 = [
        Participant(cli="claude", model="sonnet"),
        Participant(cli="codex", model="gpt-5-codex"),
    ]

    request_1 = DeliberateRequest(
        question=question_1,
        participants=participants_1,
        rounds=2,
        context="We have a lean team (5 engineers) and need to launch in 3 months",
    )

    print(f"\nQuestion: {question_1.strip()}")
    print(f"Participants: {len(participants_1)} models")
    print(f"Rounds: {request_1.rounds}")

    print("\n🔄 Running deliberation...")
    result_1 = await engine.execute(request_1)

    print("\n✅ Deliberation #1 Complete:")
    print(f"   • Consensus: {result_1.consensus}")
    print(f"   • Convergence Status: {result_1.convergence_info.status}")
    print(f"   • Rounds Completed: {len(result_1.rounds)}")
    print(f"   • Transcript: {result_1.transcript_path}")

    # Wait a moment for background similarity computation
    await asyncio.sleep(1)

    # Second deliberation - related but different question
    print("\n" + "-" * 70)
    print("DELIBERATION #2: Real-time Search Requirements")
    print("-" * 70)

    question_2 = """
    For a real-time search product, what are the critical vector database requirements?

    Specifically:
    1. Query latency requirements (p99 targets)
    2. Scalability needs (queries/second, data volume)
    3. Operational complexity trade-offs
    4. Cost considerations for early stage vs. scaled product

    Should we prioritize ease of deployment or performance optimization?
    """

    participants_2 = [
        Participant(cli="claude", model="opus"),
        Participant(cli="gemini", model="gemini-2.5-pro"),
    ]

    request_2 = DeliberateRequest(
        question=question_2,
        participants=participants_2,
        rounds=2,
        context="Building a product for enterprise customers with <50ms latency SLA",
    )

    print(f"\nQuestion: {question_2.strip()}")
    print(f"Participants: {len(participants_2)} models")
    print(f"Rounds: {request_2.rounds}")

    print("\n🧠 Memory System at Work:")
    print("   The engine is now searching for similar past decisions...")
    print("   Any relevant context from Deliberation #1 will be injected automatically")

    print("\n🔄 Running deliberation with memory context...")
    result_2 = await engine.execute(request_2)

    print("\n✅ Deliberation #2 Complete:")
    print(f"   • Consensus: {result_2.consensus}")
    print(f"   • Convergence Status: {result_2.convergence_info.status}")
    print(f"   • Rounds Completed: {len(result_2.rounds)}")
    print(f"   • Transcript: {result_2.transcript_path}")

    # Show graph statistics
    print("\n" + "=" * 70)
    print("📊 DECISION GRAPH STATISTICS")
    print("=" * 70)

    if engine.graph_integration:
        try:
            stats = engine.graph_integration.storage.get_graph_stats()
            print(f"\n✓ Decisions stored: {stats['node_count']}")
            print(f"✓ Relationships discovered: {stats['edge_count']}")
            print(f"✓ Avg. similarity score: {stats.get('avg_similarity', 'N/A')}")

            health = engine.graph_integration.storage.health_check()
            print(f"✓ Graph health: {health['status']}")
        except Exception as e:
            print(f"⚠ Could not retrieve stats: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("✨ MEMORY SYSTEM BENEFITS")
    print("=" * 70)
    print(
        """
    ✓ Context Injection: Related past decisions automatically injected
    ✓ Acceleration: Models converge faster with historical context
    ✓ Consistency: Reasoning patterns tracked across deliberations
    ✓ Learning: System improves recommendations over time
    ✓ Audit Trail: Full decision history with relationships

    Deliberations stored in:
    - SQLite database: decision_graph.db
    - Transcripts: transcripts/ directory
    - Relationships computed asynchronously (non-blocking)
    """
    )

    print("\n📂 View Your Decisions:")
    print("   - Transcripts: ls transcripts/")
    print("   - Database: sqlite3 decision_graph.db 'SELECT * FROM decision_nodes;'")
    print("   - Python API: from decision_graph.query_engine import QueryEngine")

    # Cleanup
    print("\n🛑 Shutting down...")
    await engine.shutdown()

    print("\n✅ Demo complete!\n")


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\n\n⚠ Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
