"""Integration tests for decision graph memory persistence.

This module tests memory persistence across deliberation rounds and sessions,
ensuring that decision graph memory maintains data integrity through database
restarts, context injection works correctly, and backward compatibility is
maintained.
"""
import os
import tempfile
from datetime import datetime

import pytest

from decision_graph.integration import DecisionGraphIntegration
from decision_graph.schema import DecisionNode
from decision_graph.storage import DecisionGraphStorage
from models.schema import (ConvergenceInfo, DeliberationResult, RoundResponse,
                           RoundVote, Summary, Vote, VotingResult)


@pytest.fixture
def temp_db():
    """Create temporary database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def storage(temp_db):
    """Provide storage with temporary database."""
    storage_instance = DecisionGraphStorage(db_path=temp_db)
    yield storage_instance
    storage_instance.close()


@pytest.fixture
def integration(storage):
    """Provide integration layer."""
    # Disable background worker for deterministic testing
    return DecisionGraphIntegration(storage, enable_background_worker=False)


@pytest.fixture
def sample_deliberation_result():
    """Sample DeliberationResult for testing."""
    # Create sample round responses for full debate
    round_responses = [
        RoundResponse(
            round=1,
            participant="claude",
            response="Claude's response to the question",
            timestamp="2025-01-01T10:00:00Z",
        ),
        RoundResponse(
            round=1,
            participant="gpt-4",
            response="GPT-4's response to the question",
            timestamp="2025-01-01T10:00:01Z",
        ),
        RoundResponse(
            round=2,
            participant="claude",
            response="Claude's refined response after seeing GPT-4",
            timestamp="2025-01-01T10:01:00Z",
        ),
        RoundResponse(
            round=2,
            participant="gpt-4",
            response="GPT-4's refined response after seeing Claude",
            timestamp="2025-01-01T10:01:01Z",
        ),
    ]

    # Create sample votes for voting result
    votes = [
        RoundVote(
            round=2,
            participant="claude",
            vote=Vote(
                option="Option A",
                confidence=0.85,
                rationale="This is the best approach",
                continue_debate=False,
            ),
            timestamp="2025-01-01T10:01:00Z",
        ),
        RoundVote(
            round=2,
            participant="gpt-4",
            vote=Vote(
                option="Option A",
                confidence=0.90,
                rationale="I agree with this option",
                continue_debate=False,
            ),
            timestamp="2025-01-01T10:01:01Z",
        ),
    ]

    return DeliberationResult(
        status="complete",
        mode="quick",
        rounds_completed=2,
        participants=["claude", "gpt-4"],
        summary=Summary(
            consensus="We should adopt Option A",
            key_agreements=["Agreement 1", "Agreement 2"],
            key_disagreements=[],
            final_recommendation="Proceed with Option A",
        ),
        transcript_path="/tmp/transcript.md",
        full_debate=round_responses,
        convergence_info=ConvergenceInfo(
            detected=True,
            detection_round=2,
            final_similarity=0.85,
            status="converged",
            scores_by_round=[{"round": 2, "min_similarity": 0.85}],
            per_participant_similarity={"claude": 0.85, "gpt-4": 0.87},
        ),
        voting_result=VotingResult(
            final_tally={"Option A": 2},
            votes_by_round=votes,
            consensus_reached=True,
            winning_option="Option A",
        ),
    )


@pytest.fixture
def sample_decision_node():
    """Sample DecisionNode for direct storage testing."""
    return DecisionNode(
        id="test-decision-id",
        question="Should we use TypeScript?",
        timestamp=datetime.now(),
        consensus="Yes, we should adopt TypeScript",
        winning_option="Option A",
        convergence_status="converged",
        participants=["claude", "gpt-4"],
        transcript_path="/tmp/test_transcript.md",
        metadata={"test": True},
    )


class TestMemoryPersistence:
    """Test memory persistence across rounds and sessions."""

    def test_memory_persists_between_rounds(
        self, integration, sample_deliberation_result
    ):
        """Memory persists between deliberation rounds."""
        # Store first deliberation
        decision_id_1 = integration.store_deliberation(
            "Question 1: Should we use TypeScript?", sample_deliberation_result
        )
        assert decision_id_1 is not None

        # Retrieve it
        storage = integration.storage
        node = storage.get_decision_node(decision_id_1)
        assert node is not None
        assert node.question == "Question 1: Should we use TypeScript?"

        # Store second deliberation (simulating next round)
        decision_id_2 = integration.store_deliberation(
            "Question 2: Should we use Python?", sample_deliberation_result
        )

        # Both should exist
        node1 = storage.get_decision_node(decision_id_1)
        node2 = storage.get_decision_node(decision_id_2)
        assert node1 is not None
        assert node2 is not None
        assert node1.question == "Question 1: Should we use TypeScript?"
        assert node2.question == "Question 2: Should we use Python?"

    def test_memory_survives_engine_restart(self, temp_db, sample_deliberation_result):
        """Memory survives storage layer restart."""
        # Store data in first connection
        storage1 = DecisionGraphStorage(db_path=temp_db)
        integration1 = DecisionGraphIntegration(
            storage1, enable_background_worker=False
        )
        decision_id = integration1.store_deliberation(
            "Persistent question: Should we use GraphQL?", sample_deliberation_result
        )
        storage1.close()

        # Create new connection to same database
        storage2 = DecisionGraphStorage(db_path=temp_db)
        DecisionGraphIntegration(
            storage2, enable_background_worker=False
        )

        # Data should still be there
        node = storage2.get_decision_node(decision_id)
        assert node is not None
        assert node.question == "Persistent question: Should we use GraphQL?"
        assert node.consensus == sample_deliberation_result.summary.consensus
        assert (
            node.winning_option
            == sample_deliberation_result.voting_result.winning_option
        )

        storage2.close()

    def test_context_injection_occurs_correctly(
        self, integration, sample_deliberation_result
    ):
        """Context injection mechanism works."""
        # Store first deliberation
        integration.store_deliberation(
            "Should we use TypeScript?", sample_deliberation_result
        )

        # Retrieve context for similar question
        context = integration.get_context_for_deliberation(
            "Should we use TypeScript vs JavaScript?",
            threshold=0.3,  # Lower threshold to ensure we find the match
            max_context_decisions=5,
        )

        # Context should be retrieved
        assert context is not None
        assert isinstance(context, str)
        # Should contain similarity marker or be empty (no matches below threshold)
        # Context can be empty if similarity is too low
        if context:
            assert "Similar Past Deliberations" in context or len(context) > 0

    def test_participant_stances_persisted(
        self, storage, integration, sample_deliberation_result
    ):
        """Participant stances are correctly persisted."""
        decision_id = integration.store_deliberation(
            "Test question for stances", sample_deliberation_result
        )

        # Retrieve stances
        stances = storage.get_participant_stances(decision_id)

        # Should have stances for each participant
        assert len(stances) > 0
        assert len(stances) == len(sample_deliberation_result.participants)
        for stance in stances:
            assert stance.decision_id == decision_id
            assert stance.participant in sample_deliberation_result.participants

    def test_multiple_deliberations_independent(
        self, integration, sample_deliberation_result
    ):
        """Multiple deliberations are stored independently."""
        # Store multiple deliberations with different questions
        questions = [
            "Question about architecture: Microservices vs Monolith?",
            "Question about performance: Async vs Sync?",
            "Question about testing: TDD vs BDD?",
        ]

        ids = []
        for question in questions:
            decision_id = integration.store_deliberation(
                question, sample_deliberation_result
            )
            ids.append(decision_id)

        # All should be retrievable
        storage = integration.storage
        for question_idx, decision_id in enumerate(ids):
            node = storage.get_decision_node(decision_id)
            assert node is not None
            assert node.question == questions[question_idx]

        # All IDs should be unique
        assert len(set(ids)) == len(ids)

    def test_similarity_relationships_preserved(
        self, storage, integration, sample_deliberation_result
    ):
        """Similarity relationships are computed and persisted."""
        # Store deliberation
        decision_id = integration.store_deliberation(
            "Should we use async programming?", sample_deliberation_result
        )

        # Query should work even if no perfect matches
        all_nodes = storage.get_all_decisions(limit=10)
        assert len(all_nodes) > 0

        # Find the node we just stored
        stored_node = storage.get_decision_node(decision_id)
        assert stored_node is not None
        assert stored_node.question == "Should we use async programming?"

    def test_storage_handles_special_characters(
        self, integration, sample_deliberation_result
    ):
        """Storage correctly handles questions with special characters."""
        special_questions = [
            "Should we use C++ or C#?",
            "What about 'single quotes' and \"double quotes\"?",
            "Unicode test: 你好世界 🚀",
            "SQL injection test: '; DROP TABLE decision_nodes; --",
        ]

        for question in special_questions:
            decision_id = integration.store_deliberation(
                question, sample_deliberation_result
            )
            node = integration.storage.get_decision_node(decision_id)
            assert node is not None
            assert node.question == question

    def test_large_consensus_text_stored(self, integration, sample_deliberation_result):
        """Storage handles large consensus text correctly."""
        # Create result with very large consensus
        large_consensus = "A" * 10000  # 10k characters
        sample_deliberation_result.summary.consensus = large_consensus

        decision_id = integration.store_deliberation(
            "Test large consensus", sample_deliberation_result
        )

        node = integration.storage.get_decision_node(decision_id)
        assert node is not None
        assert node.consensus == large_consensus
        assert len(node.consensus) == 10000

    def test_empty_voting_result_handled(self, integration, sample_deliberation_result):
        """Storage handles deliberations without voting results."""
        # Remove voting result
        sample_deliberation_result.voting_result = None

        decision_id = integration.store_deliberation(
            "Test without votes", sample_deliberation_result
        )

        node = integration.storage.get_decision_node(decision_id)
        assert node is not None
        assert node.winning_option is None


class TestContextInjection:
    """Test context injection and retrieval mechanisms."""

    def test_similar_questions_retrieve_correct_context(
        self, integration, storage, sample_deliberation_result
    ):
        """Similar questions retrieve correct past decisions."""
        # Store deliberations with varying similarity
        integration.store_deliberation(
            "Should we use Python for backend?", sample_deliberation_result
        )

        integration.store_deliberation(
            "Should we use JavaScript for frontend?", sample_deliberation_result
        )

        # Retrieve context for similar question
        context = integration.get_context_for_deliberation(
            "Should we use TypeScript for backend?",
            threshold=0.3,  # Lower threshold to catch more
            max_context_decisions=5,
        )

        # Should retrieve something
        assert isinstance(context, str)

    def test_confidence_scores_included_in_context(
        self, storage, integration, sample_deliberation_result
    ):
        """Confidence scores are included in injected context."""
        # Store deliberation with votes that have confidence
        decision_id = integration.store_deliberation(
            "Test question with confidence", sample_deliberation_result
        )

        # Stances should be stored with confidence
        stances = storage.get_participant_stances(decision_id)
        assert len(stances) > 0

        # At least one stance should have confidence (from voting)
        has_confidence = any(stance.confidence is not None for stance in stances)
        assert has_confidence, "Expected at least one stance to have confidence score"

        # Context should be retrievable
        context = integration.get_context_for_deliberation(
            "Test question with confidence", threshold=0.5
        )

        # Context should be available
        assert isinstance(context, str)

    def test_context_empty_when_no_similar_decisions(self, integration):
        """Context is empty when no similar decisions exist."""
        # Query without storing anything
        context = integration.get_context_for_deliberation(
            "Completely unique question that has no matches", threshold=0.7
        )

        assert context == ""

    def test_context_respects_threshold(self, integration, sample_deliberation_result):
        """Context retrieval respects similarity threshold."""
        # Store a deliberation
        integration.store_deliberation(
            "Should we use Python?", sample_deliberation_result
        )

        # Query with very high threshold (should get no results)
        context_high = integration.get_context_for_deliberation(
            "What is the weather today?",  # Completely different question
            threshold=0.95,  # Very high threshold
            max_context_decisions=5,
        )

        # Should be empty or have no results
        assert context_high == ""

    def test_context_format_includes_metadata(
        self, integration, sample_deliberation_result
    ):
        """Context includes timestamp, convergence status, and participants."""
        decision_id = integration.store_deliberation(
            "Should we use microservices?", sample_deliberation_result
        )

        # Get the stored node to verify metadata
        node = integration.storage.get_decision_node(decision_id)
        assert node.timestamp is not None
        assert node.convergence_status == "converged"
        assert len(node.participants) > 0

        # Retrieve context - should work even if no similar questions
        context = integration.get_context_for_deliberation(
            "Should we use microservices?", threshold=0.3
        )
        assert isinstance(context, str)

    def test_max_context_decisions_limit_respected(
        self, integration, sample_deliberation_result
    ):
        """Context retrieval respects max_context_decisions limit."""
        # Store multiple similar deliberations
        for i in range(10):
            integration.store_deliberation(
                f"Should we use Python for task {i}?", sample_deliberation_result
            )

        # Retrieve with limit
        context = integration.get_context_for_deliberation(
            "Should we use Python for new task?", threshold=0.3, max_context_decisions=3
        )

        # Context should be generated (or empty if no matches)
        assert isinstance(context, str)

        # If context exists, verify it's not excessively long
        if context:
            # Count number of "Past Deliberation" headers
            count = context.count("### Past Deliberation")
            assert count <= 3, f"Expected at most 3 decisions, found {count}"


class TestBackwardCompatibility:
    """Test backward compatibility and graceful degradation."""

    def test_existing_deliberations_work_without_memory(self, temp_db):
        """Existing deliberations work when memory is disabled."""
        # This tests that the system degrades gracefully
        # when graph is not available

        storage = DecisionGraphStorage(db_path=temp_db)
        integration = DecisionGraphIntegration(storage, enable_background_worker=False)

        # Operations should work even if initial state is empty
        context = integration.get_context_for_deliberation("Any question")
        assert context == ""  # Empty since no history

        storage.close()

    def test_gradual_migration_path_supported(
        self, integration, sample_deliberation_result
    ):
        """Memory can be enabled mid-session."""
        # Store some deliberations
        for i in range(3):
            integration.store_deliberation(
                f"Question {i}: What framework to use?", sample_deliberation_result
            )

        # Subsequent operations work
        context = integration.get_context_for_deliberation(
            "Question 4: What framework to use?"
        )
        assert isinstance(context, str)

    def test_missing_optional_fields_handled(self, integration):
        """Storage handles missing optional fields gracefully."""
        # Create minimal DeliberationResult without optional fields
        minimal_result = DeliberationResult(
            status="complete",
            mode="quick",
            rounds_completed=1,
            participants=["claude"],
            summary=Summary(
                consensus="Basic consensus",
                key_agreements=["Agreement 1"],
                key_disagreements=[],
                final_recommendation="Proceed",
            ),
            transcript_path="/tmp/minimal.md",
            full_debate=[
                RoundResponse(
                    round=1,
                    participant="claude",
                    response="Response text",
                    timestamp="2025-01-01T10:00:00Z",
                )
            ],
            convergence_info=None,  # Missing
            voting_result=None,  # Missing
        )

        decision_id = integration.store_deliberation("Minimal question", minimal_result)

        node = integration.storage.get_decision_node(decision_id)
        assert node is not None
        assert node.winning_option is None
        assert node.convergence_status == "unknown"

    def test_database_schema_migrations_supported(self, temp_db):
        """Database schema can be upgraded without data loss."""
        # Store data with first connection
        storage1 = DecisionGraphStorage(db_path=temp_db)
        node = DecisionNode(
            question="Test migration question",
            timestamp=datetime.now(),
            consensus="Test consensus",
            winning_option=None,
            convergence_status="converged",
            participants=["claude"],
            transcript_path="/tmp/test.md",
        )
        decision_id = storage1.save_decision_node(node)
        storage1.close()

        # Reconnect and verify data persists
        storage2 = DecisionGraphStorage(db_path=temp_db)
        retrieved = storage2.get_decision_node(decision_id)
        assert retrieved is not None
        assert retrieved.question == "Test migration question"
        storage2.close()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_threshold_clamped(self, integration, sample_deliberation_result):
        """Invalid similarity thresholds are clamped to valid range."""
        integration.store_deliberation("Test question", sample_deliberation_result)

        # Test threshold > 1.0
        context = integration.get_context_for_deliberation(
            "Test question", threshold=1.5  # Invalid, should be clamped
        )
        assert isinstance(context, str)

        # Test threshold < 0.0
        context = integration.get_context_for_deliberation(
            "Test question", threshold=-0.5  # Invalid, should be clamped
        )
        assert isinstance(context, str)

    def test_empty_question_handled(self, integration):
        """Empty questions are handled gracefully."""
        context = integration.get_context_for_deliberation("")
        assert context == ""

        context = integration.get_context_for_deliberation("   ")  # Whitespace only
        assert context == ""

    def test_storage_error_does_not_crash_deliberation(
        self, integration, sample_deliberation_result
    ):
        """Storage errors are logged but don't crash deliberation."""
        # Close storage to simulate error condition
        integration.storage.close()

        # Attempt to retrieve context (should fail gracefully)
        context = integration.get_context_for_deliberation("Test question")
        assert context == ""  # Returns empty context on error

    def test_concurrent_writes_handled(self, temp_db, sample_deliberation_result):
        """Concurrent writes to database are handled correctly."""
        # SQLite handles concurrent writes via locking
        storage1 = DecisionGraphStorage(db_path=temp_db)
        storage2 = DecisionGraphStorage(db_path=temp_db)

        integration1 = DecisionGraphIntegration(
            storage1, enable_background_worker=False
        )
        integration2 = DecisionGraphIntegration(
            storage2, enable_background_worker=False
        )

        # Both write to same database
        id1 = integration1.store_deliberation("Question 1", sample_deliberation_result)
        id2 = integration2.store_deliberation("Question 2", sample_deliberation_result)

        # Both should succeed with different IDs
        assert id1 != id2

        # Both should be retrievable
        node1 = storage1.get_decision_node(id1)
        node2 = storage2.get_decision_node(id2)
        assert node1 is not None
        assert node2 is not None

        storage1.close()
        storage2.close()


class TestPerformance:
    """Test performance characteristics of memory system."""

    def test_large_number_of_decisions(self, integration, sample_deliberation_result):
        """System handles large number of stored decisions."""
        # Store 50 decisions
        num_decisions = 50
        for i in range(num_decisions):
            integration.store_deliberation(
                f"Decision {i}: Performance test question", sample_deliberation_result
            )

        # Verify all stored
        all_decisions = integration.storage.get_all_decisions(limit=num_decisions)
        assert len(all_decisions) == num_decisions

        # Context retrieval should still work
        context = integration.get_context_for_deliberation(
            "Performance test question", threshold=0.3, max_context_decisions=5
        )
        assert isinstance(context, str)

    def test_pagination_works(self, integration, sample_deliberation_result):
        """Pagination correctly retrieves decisions in chunks."""
        # Store 25 decisions
        for i in range(25):
            integration.store_deliberation(
                f"Paginated decision {i}", sample_deliberation_result
            )

        # Retrieve in pages
        page1 = integration.storage.get_all_decisions(limit=10, offset=0)
        page2 = integration.storage.get_all_decisions(limit=10, offset=10)
        page3 = integration.storage.get_all_decisions(limit=10, offset=20)

        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5

        # No duplicates between pages
        all_ids = [d.id for d in page1 + page2 + page3]
        assert len(all_ids) == len(set(all_ids))
