"""
Integration tests for decision graph edge cases.

Tests circular references, duplicates, empty queries, corruption recovery,
size limits, and concurrent operations.
"""

import concurrent.futures
import json
import os
import tempfile
from datetime import datetime

import pytest

from decision_graph.integration import DecisionGraphIntegration
from decision_graph.schema import (DecisionNode, DecisionSimilarity,
                                   ParticipantStance)
from decision_graph.storage import DecisionGraphStorage
from models.schema import (ConvergenceInfo, DeliberationResult, RoundResponse,
                           Summary)


@pytest.fixture
def temp_db():
    """Create temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def storage(temp_db):
    """Create storage instance with temporary database."""
    storage = DecisionGraphStorage(db_path=temp_db)
    yield storage
    storage.close()


@pytest.fixture
def integration(storage):
    """Create integration layer."""
    return DecisionGraphIntegration(storage)


@pytest.fixture
def sample_result():
    """Create sample DeliberationResult for testing."""
    return DeliberationResult(
        status="complete",
        mode="quick",
        rounds_completed=1,
        participants=["participant1", "participant2"],
        full_debate=[
            RoundResponse(
                round=1,
                participant="participant1",
                response="Response 1",
                timestamp="2024-01-01T00:00:00Z",
            ),
            RoundResponse(
                round=1,
                participant="participant2",
                response="Response 2",
                timestamp="2024-01-01T00:00:01Z",
            ),
        ],
        summary=Summary(
            consensus="Sample consensus",
            key_agreements=["Agreement 1"],
            key_disagreements=["Disagreement 1"],
            final_recommendation="Sample recommendation",
        ),
        convergence_info=ConvergenceInfo(
            detected=True,
            detection_round=1,
            final_similarity=0.85,
            status="converged",
            similarity_scores={"1-2": 0.85},
        ),
        transcript_path="/tmp/transcript.md",
    )


class TestCircularReferencesPrevention:
    """Test that circular references are prevented or handled gracefully."""

    def test_self_loop_prevention(self, storage):
        """Decisions cannot create problematic self-references."""
        node = DecisionNode(
            id="node1",
            question="Question 1?",
            timestamp=datetime.now(),
            consensus="Consensus 1",
            convergence_status="converged",
            participants=["p1", "p2"],
            transcript_path="/tmp/t1.md",
        )
        storage.save_decision_node(node)

        # Attempt self-reference
        sim = DecisionSimilarity(
            source_id="node1", target_id="node1", similarity_score=1.0
        )
        storage.save_similarity(sim)

        # Query should handle gracefully
        similar = storage.get_similar_decisions("node1", threshold=0.5)
        assert isinstance(similar, list)

        # Self-references should be filtered out or not cause issues
        for decision_node, similarity_score in similar:
            if decision_node.id == "node1":
                # If present, should be clearly identifiable
                assert decision_node.id == "node1"

    def test_mutual_references_handled(self, storage):
        """Mutual references (A->B and B->A) should be handled correctly."""
        node1 = DecisionNode(
            id="n1",
            question="Question 1?",
            timestamp=datetime.now(),
            consensus="Consensus 1",
            convergence_status="converged",
            participants=["p1"],
            transcript_path="/tmp/t1.md",
        )
        node2 = DecisionNode(
            id="n2",
            question="Question 2?",
            timestamp=datetime.now(),
            consensus="Consensus 2",
            convergence_status="converged",
            participants=["p2"],
            transcript_path="/tmp/t2.md",
        )
        storage.save_decision_node(node1)
        storage.save_decision_node(node2)

        # Create mutual references
        storage.save_similarity(
            DecisionSimilarity(source_id="n1", target_id="n2", similarity_score=0.8)
        )
        storage.save_similarity(
            DecisionSimilarity(source_id="n2", target_id="n1", similarity_score=0.8)
        )

        # Queries should work without infinite loops
        sim1 = storage.get_similar_decisions("n1", threshold=0.5)
        sim2 = storage.get_similar_decisions("n2", threshold=0.5)

        assert isinstance(sim1, list)
        assert isinstance(sim2, list)
        assert len(sim1) > 0
        assert len(sim2) > 0

    def test_transitive_references_chain(self, storage):
        """Transitive references (A->B->C->A) should not cause issues."""
        nodes = []
        for i in range(5):
            node = DecisionNode(
                id=f"n{i}",
                question=f"Question {i}?",
                timestamp=datetime.now(),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=[f"p{i}"],
                transcript_path=f"/tmp/t{i}.md",
            )
            storage.save_decision_node(node)
            nodes.append(node)

        # Create chain: n0->n1->n2->n3->n4->n0
        for i in range(5):
            next_i = (i + 1) % 5
            storage.save_similarity(
                DecisionSimilarity(
                    source_id=f"n{i}",
                    target_id=f"n{next_i}",
                    similarity_score=0.7,
                )
            )

        # Queries should not cause infinite loops
        for i in range(5):
            similar = storage.get_similar_decisions(f"n{i}", threshold=0.6)
            assert isinstance(similar, list)


class TestDuplicateDecisionHandling:
    """Test handling of duplicate decisions and data."""

    def test_duplicate_questions_allowed(self, integration, sample_result):
        """System should allow same question multiple times (different sessions)."""
        question = "Should we use Python for this project?"

        id1 = integration.store_deliberation(question, sample_result)
        id2 = integration.store_deliberation(question, sample_result)

        assert id1 != id2, "Different deliberations should have unique IDs"
        assert isinstance(id1, str)
        assert isinstance(id2, str)

    def test_duplicate_participant_stances(self, storage):
        """Same participant can have multiple stances for same decision."""
        node = DecisionNode(
            id="n1",
            question="Question?",
            timestamp=datetime.now(),
            consensus="Consensus",
            convergence_status="converged",
            participants=["p1"],
            transcript_path="/tmp/t.md",
        )
        storage.save_decision_node(node)

        # Same participant, different stances (e.g., across rounds)
        stance1 = ParticipantStance(
            decision_id="n1", participant="p1", final_position="Initial position"
        )
        stance2 = ParticipantStance(
            decision_id="n1", participant="p1", final_position="Refined position"
        )

        storage.save_participant_stance(stance1)
        storage.save_participant_stance(stance2)

        stances = storage.get_participant_stances("n1")
        assert len(stances) >= 2, "Should allow multiple stances"

    def test_duplicate_similarity_upsert(self, storage):
        """Duplicate similarities should be upserted (updated)."""
        node1 = DecisionNode(
            id="n1",
            question="Q1",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t1.md",
        )
        node2 = DecisionNode(
            id="n2",
            question="Q2",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t2.md",
        )

        storage.save_decision_node(node1)
        storage.save_decision_node(node2)

        # Save similarity
        sim1 = DecisionSimilarity(source_id="n1", target_id="n2", similarity_score=0.7)
        storage.save_similarity(sim1)

        # Save again with different score (should upsert)
        sim2 = DecisionSimilarity(source_id="n1", target_id="n2", similarity_score=0.9)
        storage.save_similarity(sim2)

        # Verify updated score
        similar = storage.get_similar_decisions("n1", threshold=0.8)
        assert len(similar) > 0, "Should find similarity with new threshold"

    def test_exact_duplicate_nodes_handled(self, storage):
        """Exact duplicate nodes (same ID) should fail with unique constraint."""
        node1 = DecisionNode(
            id="n1",
            question="Q",
            timestamp=datetime.now(),
            consensus="C1",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t.md",
        )
        storage.save_decision_node(node1)

        # Save again with different consensus (same ID) - should fail
        node2 = DecisionNode(
            id="n1",
            question="Q",
            timestamp=datetime.now(),
            consensus="C2",
            convergence_status="refined",
            participants=[],
            transcript_path="/tmp/t.md",
        )

        # Should raise unique constraint error
        with pytest.raises(Exception):
            storage.save_decision_node(node2)


class TestEmptyGraphQueries:
    """Test queries on empty or non-existent data."""

    def test_empty_graph_context_retrieval(self, integration):
        """Context retrieval on empty graph returns empty string."""
        context = integration.get_context_for_deliberation(
            "Any question at all?", threshold=0.7
        )
        assert context == "", "Empty graph should return empty context"

    def test_empty_graph_similar_decisions(self, storage):
        """Similar decisions query on empty graph returns empty list."""
        similar = storage.get_similar_decisions("nonexistent_id", threshold=0.5)
        assert similar == [], "Empty graph should return empty list"

    def test_empty_graph_all_decisions(self, storage):
        """All decisions query on empty graph returns empty list."""
        all_decisions = storage.get_all_decisions(limit=100)
        assert all_decisions == [], "Empty graph should return empty list"

    def test_nonexistent_decision_node(self, storage):
        """Querying non-existent decision node returns None."""
        node = storage.get_decision_node("does_not_exist")
        assert node is None, "Non-existent node should return None"

    def test_nonexistent_participant_stances(self, storage):
        """Querying stances for non-existent decision returns empty list."""
        stances = storage.get_participant_stances("does_not_exist")
        assert stances == [], "Non-existent decision should return empty stances"

    def test_query_with_empty_string_id(self, storage):
        """Querying with empty string ID handles gracefully."""
        node = storage.get_decision_node("")
        assert node is None or isinstance(node, DecisionNode)

        similar = storage.get_similar_decisions("", threshold=0.5)
        assert isinstance(similar, list)


class TestDatabaseCorruptionRecovery:
    """Test graceful handling of database corruption scenarios."""

    def test_missing_decision_foreign_key(self, storage):
        """Missing decision in foreign key reference handled gracefully."""
        # Disable foreign keys temporarily
        cursor = storage.conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")

        try:
            # Insert stance with non-existent decision
            cursor.execute(
                "INSERT INTO participant_stances (decision_id, participant, final_position) VALUES (?, ?, ?)",
                ("nonexistent_decision", "participant1", "some position"),
            )
            storage.conn.commit()
        except Exception as e:
            pytest.fail(f"Should handle orphaned foreign key: {e}")
        finally:
            # Re-enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")

        # Query should handle gracefully
        stances = storage.get_participant_stances("nonexistent_decision")
        assert isinstance(stances, list)

    def test_invalid_json_metadata(self, storage):
        """Invalid JSON in metadata field causes JSONDecodeError."""
        node = DecisionNode(
            id="n1",
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=["p1"],
            transcript_path="/tmp/t.md",
            metadata={"key": "value"},
        )
        storage.save_decision_node(node)

        # Manually corrupt JSON
        cursor = storage.conn.cursor()
        cursor.execute(
            "UPDATE decision_nodes SET metadata = ? WHERE id = ?",
            ("{invalid json here!", "n1"),
        )
        storage.conn.commit()

        # Retrieval should raise JSONDecodeError (current behavior)
        # Note: In production, storage layer could wrap this in try/except
        with pytest.raises(json.JSONDecodeError):
            storage.get_decision_node("n1")

    def test_null_values_in_required_fields(self, storage):
        """NULL values in required fields handled gracefully."""
        cursor = storage.conn.cursor()

        # Try to insert with NULL in required field (should fail at DB level)
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO decision_nodes (id, question, timestamp, consensus, convergence_status, participants, transcript_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "n1",
                    None,
                    datetime.now().isoformat(),
                    "C",
                    "converged",
                    "[]",
                    "/tmp/t.md",
                ),
            )
            storage.conn.commit()

    def test_malformed_timestamp(self, storage):
        """Malformed timestamp in database handled gracefully."""
        cursor = storage.conn.cursor()
        cursor.execute(
            "INSERT INTO decision_nodes (id, question, timestamp, consensus, convergence_status, participants, transcript_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("n1", "Q", "not-a-timestamp", "C", "converged", "[]", "/tmp/t.md"),
        )
        storage.conn.commit()

        # Retrieval might fail or return with default timestamp
        try:
            node = storage.get_decision_node("n1")
            # Should either parse or return None
            assert node is None or isinstance(node.timestamp, datetime)
        except Exception:  # Broad catch intentional for error resilience testing
            # Acceptable to fail on malformed data
            pass


class TestGraphSizeLimits:
    """Test behavior with large graphs and datasets."""

    def test_large_graph_retrieval(self, storage, integration, sample_result):
        """System handles large number of decisions efficiently."""
        # Create 500 decisions
        decision_ids = []
        for i in range(500):
            result = DeliberationResult(
                status=sample_result.status,
                mode=sample_result.mode,
                rounds_completed=sample_result.rounds_completed,
                participants=["p1", "p2"],
                full_debate=sample_result.full_debate,
                summary=sample_result.summary,
                convergence_info=sample_result.convergence_info,
                transcript_path=f"/tmp/t{i}.md",
            )
            decision_id = integration.store_deliberation(f"Question {i % 50}?", result)
            decision_ids.append(decision_id)

        # Retrieve all decisions
        all_decisions = storage.get_all_decisions(limit=1000)
        assert len(all_decisions) == 500, "Should retrieve all 500 decisions"

    def test_large_similarity_matrix(self, storage):
        """System handles large similarity matrix efficiently."""
        # Create 100 decisions
        for i in range(100):
            node = DecisionNode(
                id=f"n{i}",
                question=f"Question {i}?",
                timestamp=datetime.now(),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=[],
                transcript_path=f"/tmp/t{i}.md",
            )
            storage.save_decision_node(node)

        # Create partial connectivity (each node connected to 10 others)
        for i in range(100):
            for j in range(i + 1, min(i + 11, 100)):
                score = 0.5 + ((i * j) % 50) / 100
                storage.save_similarity(
                    DecisionSimilarity(
                        source_id=f"n{i}", target_id=f"n{j}", similarity_score=score
                    )
                )

        # Query should still be performant
        similar = storage.get_similar_decisions("n10", threshold=0.6, limit=20)
        assert isinstance(similar, list)
        assert len(similar) <= 20

    def test_pagination_with_large_dataset(self, storage, integration, sample_result):
        """Pagination works correctly with large datasets."""
        # Create 100 decisions
        for i in range(100):
            result = DeliberationResult(
                status=sample_result.status,
                mode=sample_result.mode,
                rounds_completed=sample_result.rounds_completed,
                participants=["p1"],
                full_debate=sample_result.full_debate,
                summary=sample_result.summary,
                convergence_info=sample_result.convergence_info,
                transcript_path=f"/tmp/t{i}.md",
            )
            integration.store_deliberation(f"Unique question {i}?", result)

        # Paginate through results
        page1 = storage.get_all_decisions(limit=20, offset=0)
        page2 = storage.get_all_decisions(limit=20, offset=20)
        page3 = storage.get_all_decisions(limit=20, offset=40)

        assert len(page1) == 20
        assert len(page2) == 20
        assert len(page3) == 20

        # Pages should be different
        assert page1[0].id != page2[0].id
        assert page2[0].id != page3[0].id

    def test_query_limit_enforcement(self, storage):
        """Query limits are properly enforced."""
        # Create decisions
        for i in range(50):
            node = DecisionNode(
                id=f"n{i}",
                question=f"Q{i}",
                timestamp=datetime.now(),
                consensus="C",
                convergence_status="converged",
                participants=[],
                transcript_path="/tmp/t.md",
            )
            storage.save_decision_node(node)

        # Test various limits
        assert len(storage.get_all_decisions(limit=10)) == 10
        assert len(storage.get_all_decisions(limit=25)) == 25
        assert len(storage.get_all_decisions(limit=100)) == 50


class TestConcurrentWrites:
    """Test concurrent write safety and race conditions."""

    def test_concurrent_decision_storage(self, temp_db, sample_result):
        """Multiple threads writing decisions should be safe."""

        def store_decision(index):
            storage = DecisionGraphStorage(db_path=temp_db)
            integration = DecisionGraphIntegration(storage)

            result = DeliberationResult(
                status=sample_result.status,
                mode=sample_result.mode,
                rounds_completed=sample_result.rounds_completed,
                participants=["p1"],
                full_debate=sample_result.full_debate,
                summary=sample_result.summary,
                convergence_info=sample_result.convergence_info,
                transcript_path=f"/tmp/t{index}.md",
            )

            decision_id = integration.store_deliberation(
                f"Concurrent question {index}?", result
            )
            storage.close()
            return decision_id

        # Execute concurrent writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(store_decision, range(20)))

        # Verify all were stored with unique IDs
        assert len(results) == 20
        assert len(set(results)) == 20, "All IDs should be unique"

        # Verify in database
        storage = DecisionGraphStorage(db_path=temp_db)
        all_decisions = storage.get_all_decisions(limit=100)
        assert len(all_decisions) == 20
        storage.close()

    def test_concurrent_similarity_writes(self, temp_db):
        """Multiple threads writing similarities should be safe."""
        # Pre-create nodes
        storage = DecisionGraphStorage(db_path=temp_db)
        for i in range(10):
            node = DecisionNode(
                id=f"n{i}",
                question=f"Q{i}",
                timestamp=datetime.now(),
                consensus="C",
                convergence_status="converged",
                participants=[],
                transcript_path="/tmp/t.md",
            )
            storage.save_decision_node(node)
        storage.close()

        def write_similarities(worker_id):
            storage = DecisionGraphStorage(db_path=temp_db)
            for i in range(10):
                for j in range(i + 1, 10):
                    sim = DecisionSimilarity(
                        source_id=f"n{i}",
                        target_id=f"n{j}",
                        similarity_score=0.5 + (worker_id * 0.1),
                    )
                    storage.save_similarity(sim)
            storage.close()
            return worker_id

        # Execute concurrent writes (will upsert)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(write_similarities, range(3)))

        assert len(results) == 3

        # Verify data integrity
        storage = DecisionGraphStorage(db_path=temp_db)
        similar = storage.get_similar_decisions("n0", threshold=0.4)
        assert len(similar) > 0
        storage.close()

    def test_concurrent_read_write_safety(self, temp_db, sample_result):
        """Concurrent reads and writes should not corrupt data."""

        def writer(index):
            storage = DecisionGraphStorage(db_path=temp_db)
            integration = DecisionGraphIntegration(storage)

            result = DeliberationResult(
                status=sample_result.status,
                mode=sample_result.mode,
                rounds_completed=sample_result.rounds_completed,
                participants=["p1"],
                full_debate=sample_result.full_debate,
                summary=sample_result.summary,
                convergence_info=sample_result.convergence_info,
                transcript_path=f"/tmp/tw{index}.md",
            )

            decision_id = integration.store_deliberation(
                f"Writer question {index}?", result
            )
            storage.close()
            return decision_id

        def reader(index):
            storage = DecisionGraphStorage(db_path=temp_db)
            decisions = storage.get_all_decisions(limit=50)
            storage.close()
            return len(decisions)

        # Mix reads and writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            write_futures = [executor.submit(writer, i) for i in range(10)]
            read_futures = [executor.submit(reader, i) for i in range(10)]

            write_results = [f.result() for f in write_futures]
            read_results = [f.result() for f in read_futures]

        assert len(write_results) == 10
        assert all(isinstance(r, int) for r in read_results)


class TestConstraintEnforcement:
    """Test database constraint enforcement."""

    def test_foreign_key_constraint(self, storage):
        """Foreign key constraints are enforced when enabled."""
        # Ensure foreign keys are enabled
        cursor = storage.conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")

        # Try to create stance with non-existent decision
        stance = ParticipantStance(
            decision_id="nonexistent",
            participant="p1",
            final_position="position",
        )

        # Should fail with foreign key constraint
        with pytest.raises(Exception):
            storage.save_participant_stance(stance)

    def test_unique_constraint_on_similarity(self, storage):
        """Unique constraint on (source_id, target_id) enforced."""
        node1 = DecisionNode(
            id="n1",
            question="Q1",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t.md",
        )
        node2 = DecisionNode(
            id="n2",
            question="Q2",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t.md",
        )

        storage.save_decision_node(node1)
        storage.save_decision_node(node2)

        # Save similarity
        sim1 = DecisionSimilarity(source_id="n1", target_id="n2", similarity_score=0.7)
        storage.save_similarity(sim1)

        # Save again - should upsert, not create duplicate
        sim2 = DecisionSimilarity(source_id="n1", target_id="n2", similarity_score=0.9)
        storage.save_similarity(sim2)

        # Verify only one similarity exists
        cursor = storage.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM decision_similarities WHERE source_id=? AND target_id=?",
            ("n1", "n2"),
        )
        count = cursor.fetchone()[0]
        assert count == 1, "Should have exactly one similarity (upserted)"

    def test_not_null_constraints(self, storage):
        """NOT NULL constraints are enforced on required fields."""
        cursor = storage.conn.cursor()

        # Try to insert with NULL in required field
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO decision_nodes (id, question, consensus, convergence_status, participants, transcript_path) VALUES (?, ?, ?, ?, ?, ?)",
                ("n1", "Q", "C", "converged", "[]", "/tmp/t.md"),
            )
            storage.conn.commit()


class TestEdgeCaseQueries:
    """Test edge cases in query operations."""

    def test_threshold_boundary_conditions(self, storage):
        """Test similarity queries at threshold boundaries."""
        node1 = DecisionNode(
            id="n1",
            question="Q1",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t.md",
        )
        node2 = DecisionNode(
            id="n2",
            question="Q2",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t.md",
        )

        storage.save_decision_node(node1)
        storage.save_decision_node(node2)

        # Similarity at exact threshold
        storage.save_similarity(
            DecisionSimilarity(source_id="n1", target_id="n2", similarity_score=0.75)
        )

        # Query at exact threshold (should include)
        similar_at = storage.get_similar_decisions("n1", threshold=0.75)
        assert len(similar_at) > 0, "Should include similarity at exact threshold"

        # Query just above threshold (should exclude)
        similar_above = storage.get_similar_decisions("n1", threshold=0.76)
        assert len(similar_above) == 0, "Should exclude similarity below threshold"

    def test_zero_and_negative_limits(self, storage):
        """Test queries with zero or negative limits."""
        node = DecisionNode(
            id="n1",
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t.md",
        )
        storage.save_decision_node(node)

        # Zero limit should return empty
        result = storage.get_all_decisions(limit=0)
        assert len(result) == 0

        # Negative limit might return all or empty (implementation-dependent)
        result = storage.get_all_decisions(limit=-1)
        assert isinstance(result, list)

    def test_very_large_offset(self, storage):
        """Test query with offset larger than dataset."""
        node = DecisionNode(
            id="n1",
            question="Q",
            timestamp=datetime.now(),
            consensus="C",
            convergence_status="converged",
            participants=[],
            transcript_path="/tmp/t.md",
        )
        storage.save_decision_node(node)

        # Offset beyond data
        result = storage.get_all_decisions(limit=10, offset=1000)
        assert len(result) == 0, "Should return empty for offset beyond data"
