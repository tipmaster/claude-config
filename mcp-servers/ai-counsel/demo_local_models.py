#!/usr/bin/env python3
"""
Demo: Local Model Support - Zero API Costs with Ollama

This script demonstrates:
1. Running deliberation with local Ollama model (zero API costs)
2. Mixing local and cloud models in single deliberation
3. Cost comparison between local and cloud models
4. Performance metrics and trade-offs
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import asyncio
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from deliberation.engine import DeliberationEngine
from models.config import load_config
from models.schema import DeliberateRequest, Participant


async def demo():
    """Run demonstration of local model support with cost comparison."""

    # Load configuration
    config = load_config("config.yaml")
    print("\n" + "=" * 70)
    print("AI COUNSEL - LOCAL MODEL SUPPORT DEMO")
    print("=" * 70)

    # Initialize deliberation engine
    engine = DeliberationEngine(config)

    print("\n💰 Local Model Benefits:")
    print("   • Zero API costs for local inference")
    print("   • Complete data privacy (everything stays on your machine)")
    print("   • No rate limits or usage quotas")
    print("   • Mix with cloud models for hybrid approach")
    print("   • Full control over model versions and configurations")

    # Cost comparison
    print("\n" + "-" * 70)
    print("COST COMPARISON: Local vs Cloud (100 deliberations)")
    print("-" * 70)
    print("\nScenario: 100 technical decisions, 3 models, 2 rounds each")
    print("Total API calls: 600 (100 deliberations × 3 models × 2 rounds)")
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ Configuration          │ Cost per Call │ Total Cost       │")
    print("├────────────────────────┼───────────────┼──────────────────┤")
    print("│ All Local (Ollama)     │ $0            │ $0               │")
    print("│ All Cloud (Claude)     │ ~$0.50        │ ~$300            │")
    print("│ Hybrid (2 local + 1    │ ~$0.17        │ ~$100            │")
    print("│ cloud)                 │               │                  │")
    print("└────────────────────────┴───────────────┴──────────────────┘")
    print("\nSavings with local models: $200-300 per 100 deliberations")

    # First deliberation - pure local with Ollama
    print("\n" + "-" * 70)
    print("DELIBERATION #1: Pure Local (Ollama Only)")
    print("-" * 70)

    question_1 = """
    Should we add comprehensive unit tests to all new features before merging?

    Consider:
    1. Development velocity impact
    2. Bug reduction benefits
    3. Refactoring confidence
    4. Team onboarding efficiency
    """

    participants_1 = [
        Participant(cli="ollama", model="llama2"),
    ]

    request_1 = DeliberateRequest(
        question=question_1,
        participants=participants_1,
        rounds=2,
        context="Small startup team, rapid iteration cycle",
    )

    print(f"\nQuestion: {question_1.strip()}")
    print(f"Participants: {len(participants_1)} local model (Ollama)")
    print(f"Rounds: {request_1.rounds}")
    print("API Cost: $0.00")

    print("\n🔄 Running deliberation with local model...")
    start_time = time.time()
    result_1 = await engine.execute(request_1)
    duration_1 = time.time() - start_time

    print("\n✅ Deliberation #1 Complete:")
    print(f"   • Duration: {duration_1:.2f} seconds")
    print("   • API Cost: $0.00")
    print(f"   • Consensus: {result_1.consensus}")
    print(f"   • Convergence Status: {result_1.convergence_info.status}")
    print(f"   • Transcript: {result_1.transcript_path}")

    # Second deliberation - hybrid (local + cloud)
    print("\n" + "-" * 70)
    print("DELIBERATION #2: Hybrid (Local + Cloud Models)")
    print("-" * 70)

    question_2 = """
    For a user authentication system, should we use JWT tokens or session-based auth?

    Trade-offs:
    1. Scalability (stateless vs. stateful)
    2. Security (token theft vs. session hijacking)
    3. Performance (token validation vs. session lookup)
    4. Logout capability (token revocation vs. session deletion)
    """

    participants_2 = [
        Participant(cli="ollama", model="llama2"),
        Participant(cli="claude", model="sonnet"),
    ]

    request_2 = DeliberateRequest(
        question=question_2,
        participants=participants_2,
        rounds=2,
        context="E-commerce platform with 50K active users, Redis available",
    )

    print(f"\nQuestion: {question_2.strip()}")
    print(f"Participants: {len(participants_2)} models (1 local + 1 cloud)")
    print(f"Rounds: {request_2.rounds}")
    print("Estimated API Cost: ~$0.50 (only for Claude)")

    print("\n🔄 Running hybrid deliberation...")
    start_time = time.time()
    result_2 = await engine.execute(request_2)
    duration_2 = time.time() - start_time

    print("\n✅ Deliberation #2 Complete:")
    print(f"   • Duration: {duration_2:.2f} seconds")
    print("   • Estimated API Cost: ~$0.50")
    print(f"   • Consensus: {result_2.consensus}")
    print(f"   • Convergence Status: {result_2.convergence_info.status}")
    print(f"   • Transcript: {result_2.transcript_path}")

    # Performance comparison
    print("\n" + "=" * 70)
    print("📊 PERFORMANCE ANALYSIS")
    print("=" * 70)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ Configuration          │ Duration      │ Cost per Run     │")
    print("├────────────────────────┼───────────────┼──────────────────┤")
    print(f"│ Pure Local (Ollama)    │ {duration_1:>6.2f}s       │ $0.00            │")
    print(f"│ Hybrid (1 local + 1    │ {duration_2:>6.2f}s       │ ~$0.50           │")
    print("│ cloud)                 │               │                  │")
    print("└────────────────────────┴───────────────┴──────────────────┘")

    # Key insights
    print("\n" + "=" * 70)
    print("💡 KEY INSIGHTS & RECOMMENDATIONS")
    print("=" * 70)
    print(
        """
    ✓ Cost Savings: Local models eliminate API costs entirely
      → Ideal for: prototyping, high-volume testing, cost-sensitive deployments

    ✓ Privacy: All data stays on-premises with local models
      → Ideal for: sensitive data, regulated industries, internal tools

    ✓ Hybrid Strategy: Mix local + cloud for best of both worlds
      → Local models: fast iteration, zero cost
      → Cloud models: higher quality responses, specialized capabilities

    ✓ Performance Trade-offs:
      → Local models: Faster for small models (Llama 2 7B)
      → Cloud models: Better quality, slower due to network latency
      → Hybrid: Balanced approach with cost optimization

    ✓ Use Cases by Configuration:
      → All Local: Development, testing, high-volume automation
      → Hybrid: Production systems requiring quality + cost efficiency
      → All Cloud: Critical decisions requiring highest model quality
    """
    )

    # Setup guide
    print("\n" + "=" * 70)
    print("🚀 GETTING STARTED WITH LOCAL MODELS")
    print("=" * 70)
    print(
        """
    1. Install Ollama (https://ollama.ai):
       curl -fsSL https://ollama.ai/install.sh | sh

    2. Pull a model:
       ollama pull llama2

    3. Verify Ollama is running:
       curl http://localhost:11434/api/tags

    4. Update config.yaml (already configured):
       adapters:
         ollama:
           type: http
           base_url: "http://localhost:11434"
           timeout: 120

    5. Use in deliberations:
       {cli: "ollama", model: "llama2"}

    Alternative Local Options:
    - LM Studio: OpenAI-compatible GUI app
    - llamacpp: Direct GGUF inference (maximum control)
    """
    )

    print("\n📚 Documentation:")
    print("   - HTTP Adapters: docs/http-adapters/intro.md")
    print("   - Ollama Quickstart: docs/http-adapters/ollama-quickstart.md")
    print("   - LM Studio Setup: docs/http-adapters/lmstudio-quickstart.md")

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
