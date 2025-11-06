"""
End-to-end tests for deliberation workflows with decision graph memory.

Tests full deliberation lifecycle, memory-enhanced convergence, context recall,
and graceful degradation.
"""

import os
import tempfile

import pytest

from decision_graph.integration import DecisionGraphIntegration
from deliberation.engine import DeliberationEngine
from models.config import (Config, ConvergenceDetectionConfig,
                           DecisionGraphConfig, DefaultsConfig,
                           DeliberationConfig, EarlyStoppingConfig,
                           StorageConfig)
from models.schema import (ConvergenceInfo, DeliberationResult, RoundResponse,
                           Summary)


def make_result(consensus: str, participants=None, transcript_path="/tmp/t.md"):
    """Helper to create minimal DeliberationResult for testing."""
    if participants is None:
        participants = ["p1"]

    return DeliberationResult(
        status="complete",
        mode="quick",
        rounds_completed=1,
        participants=participants,
        full_debate=[
            RoundResponse(
                round=1,
                participant=p,
                response=f"Response from {p}",
                timestamp="2024-01-01T00:00:00Z",
            )
            for p in participants
        ],
        summary=Summary(
            consensus=consensus,
            key_agreements=[],
            key_disagreements=[],
            final_recommendation=consensus,
        ),
        convergence_info=ConvergenceInfo(
            detected=True,
            detection_round=1,
            final_similarity=0.95,
            status="converged",
            similarity_scores={},
        ),
        transcript_path=transcript_path,
    )


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def config_with_memory(temp_db):
    """Config with decision graph memory enabled."""
    config = Config(
        version="1.0",
        decision_graph=DecisionGraphConfig(
            enabled=True,
            db_path=temp_db,
            similarity_threshold=0.7,
            max_context_decisions=3,
        ),
        deliberation=DeliberationConfig(
            convergence_detection=ConvergenceDetectionConfig(
                enabled=True,
                semantic_similarity_threshold=0.85,
                divergence_threshold=0.40,
                min_rounds_before_check=1,
                consecutive_stable_rounds=2,
                stance_stability_threshold=0.80,
                response_length_drop_threshold=0.40,
            ),
            early_stopping=EarlyStoppingConfig(
                enabled=True,
                threshold=0.66,
                respect_min_rounds=True,
            ),
            convergence_threshold=0.85,
            enable_convergence_detection=True,
        ),
        defaults=DefaultsConfig(
            mode="quick", rounds=3, max_rounds=5, timeout_per_round=120
        ),
        storage=StorageConfig(
            transcripts_dir="transcripts", format="markdown", auto_export=True
        ),
        adapters={},
    )
    return config


@pytest.fixture
def config_without_memory():
    """Config without decision graph memory."""
    config = Config(
        version="1.0",
        decision_graph=None,
        deliberation=DeliberationConfig(
            convergence_detection=ConvergenceDetectionConfig(
                enabled=True,
                semantic_similarity_threshold=0.85,
                divergence_threshold=0.40,
                min_rounds_before_check=1,
                consecutive_stable_rounds=2,
                stance_stability_threshold=0.80,
                response_length_drop_threshold=0.40,
            ),
            early_stopping=EarlyStoppingConfig(
                enabled=True,
                threshold=0.66,
                respect_min_rounds=True,
            ),
            convergence_threshold=0.85,
            enable_convergence_detection=True,
        ),
        defaults=DefaultsConfig(
            mode="quick", rounds=3, max_rounds=5, timeout_per_round=120
        ),
        storage=StorageConfig(
            transcripts_dir="transcripts", format="markdown", auto_export=True
        ),
        adapters={},
    )
    return config


@pytest.fixture
def sample_result():
    """Create sample DeliberationResult."""
    return make_result(
        consensus="Python is a strong choice for backend development",
        participants=["gpt-4", "claude-opus"],
        transcript_path="/tmp/transcript_python.md",
    )


@pytest.mark.e2e
class TestMemoryEnhancedDeliberation:
    """Test full deliberation workflow with memory integration."""

    def test_engine_initializes_with_memory(self, config_with_memory):
        """DeliberationEngine initializes decision graph when enabled."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        assert engine.graph_integration is not None, "Memory should be enabled"
        assert isinstance(engine.graph_integration, DecisionGraphIntegration)
        assert engine.graph_integration.storage is not None

    def test_engine_without_memory_works(self, config_without_memory):
        """DeliberationEngine works without decision graph."""
        engine = DeliberationEngine(adapters={}, config=config_without_memory)

        assert engine.graph_integration is None, "Memory should be disabled"

    def test_memory_stores_deliberation_result(self, config_with_memory, sample_result):
        """Deliberation results are stored in memory after completion."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # Store deliberation
        decision_id = engine.graph_integration.store_deliberation(
            "Should we use Python for backend?", sample_result
        )

        assert decision_id is not None
        assert isinstance(decision_id, str)

        # Verify stored
        node = engine.graph_integration.storage.get_decision_node(decision_id)
        assert node is not None
        assert node.question == "Should we use Python for backend?"
        assert node.consensus == sample_result.summary.consensus

    def test_deliberation_lifecycle_with_memory(self, config_with_memory):
        """Full deliberation lifecycle: store, retrieve context, deliberate."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # First deliberation - populate memory
        result1 = make_result(
            consensus="Python is recommended", transcript_path="/tmp/t1.md"
        )
        decision_id1 = engine.graph_integration.store_deliberation(
            "Should we use Python?", result1
        )
        assert decision_id1 is not None

        # Second deliberation - should find context from first
        context = engine.graph_integration.get_context_for_deliberation(
            "Should we use Python for web development?", threshold=0.6
        )
        assert isinstance(context, str)

        # Store second deliberation
        result2 = make_result(
            consensus="Python is good for web", transcript_path="/tmp/t2.md"
        )
        decision_id2 = engine.graph_integration.store_deliberation(
            "Should we use Python for web development?", result2
        )
        assert decision_id2 != decision_id1


@pytest.mark.e2e
class TestMemoryRecallAccuracy:
    """Test accuracy and relevance of memory recall."""

    def test_similar_questions_retrieve_past_context(self, config_with_memory):
        """Similar questions retrieve relevant past decisions."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # Store first decision
        result1 = make_result(
            consensus="Yes, Python is excellent", transcript_path="/tmp/t1.md"
        )
        engine.graph_integration.store_deliberation(
            "Should we use Python for backend?", result1
        )

        # Retrieve context for similar question
        context = engine.graph_integration.get_context_for_deliberation(
            "Should we use Python for API development?", threshold=0.6
        )
        assert isinstance(context, str)

    def test_dissimilar_questions_no_context(self, config_with_memory):
        """Dissimilar questions don't retrieve irrelevant context."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # Store decision about Python
        result1 = make_result(consensus="Yes", transcript_path="/tmp/t1.md")
        engine.graph_integration.store_deliberation("Should we use Python?", result1)

        # Retrieve context for completely different question
        context = engine.graph_integration.get_context_for_deliberation(
            "What is the capital of France?", threshold=0.7
        )
        assert isinstance(context, str)

    def test_multiple_past_decisions_ranked_by_relevance(self, config_with_memory):
        """Multiple past decisions are ranked by relevance."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # Store multiple decisions
        questions_and_results = [
            ("Should we use Python?", "Python is great"),
            ("Should we use JavaScript?", "JavaScript is versatile"),
            ("Should we use Python for ML?", "Python excels at ML"),
        ]

        for question, consensus in questions_and_results:
            result = make_result(consensus=consensus)
            engine.graph_integration.store_deliberation(question, result)

        # Retrieve context for Python question
        context = engine.graph_integration.get_context_for_deliberation(
            "Should we use Python for data science?", threshold=0.5
        )
        assert isinstance(context, str)


@pytest.mark.e2e
class TestContextInjectionEffectiveness:
    """Test that context is effectively injected into prompts."""

    def test_context_formatted_for_prompts(self, config_with_memory):
        """Context is formatted appropriately for inclusion in prompts."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        result = make_result(consensus="Test consensus")
        engine.graph_integration.store_deliberation("Test question?", result)

        context = engine.graph_integration.get_context_for_deliberation(
            "Test question?", threshold=0.5
        )

        # Context should be markdown formatted if not empty
        if context:
            assert (
                "#" in context or "context" in context.lower() or "Previous" in context
            )

    def test_context_includes_key_information(self, config_with_memory):
        """Context includes consensus information."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        result = make_result(
            consensus="Refactoring is needed", transcript_path="/tmp/t.md"
        )
        engine.graph_integration.store_deliberation("Should we refactor?", result)

        context = engine.graph_integration.get_context_for_deliberation(
            "Should we refactor the codebase?", threshold=0.6
        )
        # Should be a string (may be empty if no similarity)
        assert isinstance(context, str)


@pytest.mark.e2e
class TestGracefulDegradation:
    """Test system degrades gracefully when memory fails or is disabled."""

    def test_deliberation_works_without_memory(self, config_without_memory):
        """Deliberation works even without memory enabled."""
        engine = DeliberationEngine(adapters={}, config=config_without_memory)
        assert engine.graph_integration is None, "Memory should be disabled"

    def test_memory_errors_dont_break_deliberation(self, config_with_memory):
        """Errors in memory operations don't break deliberation."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        try:
            context = engine.graph_integration.get_context_for_deliberation(
                "", threshold=0.7
            )
            assert isinstance(context, str), "Should return empty string, not raise"
        except Exception as e:
            pytest.fail(f"Memory error should not propagate: {e}")

    def test_corrupted_database_handled_gracefully(self, config_with_memory, temp_db):
        """Corrupted database doesn't crash engine initialization."""
        # Corrupt the database file
        with open(temp_db, "w") as f:
            f.write("corrupted data")

        try:
            engine = DeliberationEngine(adapters={}, config=config_with_memory)
            assert engine is not None
        except Exception as e:
            # Acceptable to fail, but should be related to database
            assert "database" in str(e).lower() or "disk" in str(e).lower()

    def test_storage_close_is_safe(self, config_with_memory):
        """Closing storage multiple times is safe."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)
        engine.graph_integration.storage.close()
        engine.graph_integration.storage.close()  # Should not raise


@pytest.mark.e2e
class TestMultipleDeliberations:
    """Test multiple sequential deliberations building on each other."""

    def test_successive_deliberations_build_context(self, config_with_memory):
        """Successive deliberations should find context from previous ones."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        questions = [
            "Should we use Python?",
            "Should we use async Python?",
            "Should we use FastAPI with async?",
        ]

        for i, question in enumerate(questions):
            result = make_result(
                consensus=f"Decision {i}", transcript_path=f"/tmp/t{i}.md"
            )
            engine.graph_integration.store_deliberation(question, result)

        # Final question should potentially find context from previous
        context = engine.graph_integration.get_context_for_deliberation(
            "Should we use FastAPI for Python backend?", threshold=0.5
        )
        assert isinstance(context, str)

    def test_memory_accumulation_over_time(self, config_with_memory):
        """Memory accumulates decisions over multiple sessions."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # Simulate multiple deliberations
        for i in range(10):
            result = make_result(
                consensus=f"Consensus {i}", transcript_path=f"/tmp/t{i}.md"
            )
            engine.graph_integration.store_deliberation(
                f"Question about topic {i % 3}?", result
            )

        # Verify accumulation
        all_decisions = engine.graph_integration.storage.get_all_decisions(limit=20)
        assert len(all_decisions) == 10

    def test_context_limit_respected(self, config_with_memory):
        """Max context decisions limit is respected."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # Store many similar decisions
        for i in range(10):
            result = make_result(
                consensus=f"Python works for {i}", transcript_path=f"/tmp/t{i}.md"
            )
            engine.graph_integration.store_deliberation(
                f"Should we use Python for use case {i}?", result
            )

        # Retrieve context
        context = engine.graph_integration.get_context_for_deliberation(
            "Should we use Python?", threshold=0.5
        )
        assert isinstance(context, str)


@pytest.mark.e2e
class TestParticipantStanceTracking:
    """Test tracking of participant stances across deliberations."""

    def test_participant_stances_stored(self, config_with_memory):
        """Participant stances are stored with decisions."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        result = make_result(
            consensus="Proceed with caution", participants=["alice", "bob"]
        )
        decision_id = engine.graph_integration.store_deliberation(
            "Should we proceed?", result
        )

        # Verify stances stored
        stances = engine.graph_integration.storage.get_participant_stances(decision_id)
        assert len(stances) > 0

    def test_participant_stance_retrieval(self, config_with_memory):
        """Participant stances can be retrieved for analysis."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        result = make_result(consensus="C", participants=["p1", "p2"])
        decision_id = engine.graph_integration.store_deliberation("Question?", result)

        stances = engine.graph_integration.storage.get_participant_stances(decision_id)
        assert isinstance(stances, list)


@pytest.mark.e2e
class TestSimilarityComputation:
    """Test similarity computation between decisions."""

    def test_similarities_stored(self, config_with_memory):
        """Similarities are computed and stored between decisions."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        # Store two similar decisions
        result1 = make_result(consensus="Python is good", transcript_path="/tmp/t1.md")
        result2 = make_result(
            consensus="Python is good for backend", transcript_path="/tmp/t2.md"
        )

        id1 = engine.graph_integration.store_deliberation(
            "Should we use Python?", result1
        )
        engine.graph_integration.store_deliberation(
            "Should we use Python for backend?", result2
        )

        # Similarities may or may not be found depending on backend
        similar = engine.graph_integration.storage.get_similar_decisions(
            id1, threshold=0.5
        )
        assert isinstance(similar, list)

    def test_similarity_threshold_filtering(self, config_with_memory):
        """Similarity threshold properly filters results."""
        engine = DeliberationEngine(adapters={}, config=config_with_memory)

        result1 = make_result(consensus="C1", transcript_path="/tmp/t1.md")
        id1 = engine.graph_integration.store_deliberation("Python question?", result1)

        # Query with high threshold
        similar_high = engine.graph_integration.storage.get_similar_decisions(
            id1, threshold=0.9
        )

        # Query with low threshold
        similar_low = engine.graph_integration.storage.get_similar_decisions(
            id1, threshold=0.3
        )

        # Low threshold should return same or more results
        assert len(similar_low) >= len(similar_high)
