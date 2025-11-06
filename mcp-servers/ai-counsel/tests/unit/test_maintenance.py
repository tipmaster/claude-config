"""Unit tests for decision graph maintenance module.

Tests verify:
- Database statistics collection
- Growth rate analysis
- Archival benefit estimation
- Health check validation
- Migration SQL generation
- Performance requirements (<100ms stats, <200ms growth, <1s health)
"""

import time
from datetime import datetime, timedelta
from typing import Generator

import pytest

from decision_graph.maintenance import DecisionGraphMaintenance
from decision_graph.schema import (DecisionNode, DecisionSimilarity,
                                   ParticipantStance)
from decision_graph.storage import DecisionGraphStorage


@pytest.fixture
def temp_storage() -> Generator[DecisionGraphStorage, None, None]:
    """Create temporary in-memory storage for testing."""
    storage = DecisionGraphStorage(db_path=":memory:")
    yield storage
    storage.close()


@pytest.fixture
def maintenance(temp_storage: DecisionGraphStorage) -> DecisionGraphMaintenance:
    """Create maintenance instance with temp storage."""
    return DecisionGraphMaintenance(temp_storage)


@pytest.fixture
def sample_decision() -> DecisionNode:
    """Create sample decision node for testing."""
    return DecisionNode(
        question="Should we implement feature X?",
        timestamp=datetime.now(),
        consensus="Yes, implement feature X with caution",
        convergence_status="converged",
        participants=["claude-sonnet-4-5", "gpt-5-codex"],
        transcript_path="/tmp/transcript.md",
    )


class TestDatabaseStats:
    """Tests for database statistics collection."""

    def test_get_database_stats_empty(self, maintenance: DecisionGraphMaintenance):
        """Stats should return zeros for empty database."""
        stats = maintenance.get_database_stats()

        assert stats["total_decisions"] == 0
        assert stats["total_stances"] == 0
        assert stats["total_similarities"] == 0
        assert stats["db_size_bytes"] == 0  # In-memory DB
        assert stats["db_size_mb"] == 0.0

    def test_get_database_stats_with_data(
        self,
        maintenance: DecisionGraphMaintenance,
        temp_storage: DecisionGraphStorage,
        sample_decision: DecisionNode,
    ):
        """Stats should accurately count database contents."""
        # Add 5 decisions
        decision_ids = []
        for i in range(5):
            decision = DecisionNode(
                question=f"Question {i}?",
                timestamp=datetime.now(),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5", "gpt-5-codex"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            decision_id = temp_storage.save_decision_node(decision)
            decision_ids.append(decision_id)

            # Add 2 stances per decision
            for participant in decision.participants:
                stance = ParticipantStance(
                    decision_id=decision_id,
                    participant=participant,
                    final_position=f"Position of {participant}",
                )
                temp_storage.save_participant_stance(stance)

        # Add some similarities
        for i in range(3):
            similarity = DecisionSimilarity(
                source_id=decision_ids[0],
                target_id=decision_ids[i + 1],
                similarity_score=0.8,
            )
            temp_storage.save_similarity(similarity)

        stats = maintenance.get_database_stats()

        assert stats["total_decisions"] == 5
        assert stats["total_stances"] == 10  # 5 decisions * 2 participants
        assert stats["total_similarities"] == 3

    def test_get_database_stats_performance(
        self,
        maintenance: DecisionGraphMaintenance,
        temp_storage: DecisionGraphStorage,
        sample_decision: DecisionNode,
    ):
        """Stats collection should be <100ms even with 100 decisions."""
        # Add 100 decisions
        for i in range(100):
            decision = DecisionNode(
                question=f"Question {i}?",
                timestamp=datetime.now(),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        # Benchmark stats collection
        start = time.perf_counter()
        stats = maintenance.get_database_stats()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert (
            elapsed_ms < 100
        ), f"Stats collection took {elapsed_ms:.2f}ms, expected <100ms"
        assert stats["total_decisions"] == 100

    def test_get_database_stats_error_handling(
        self, temp_storage: DecisionGraphStorage
    ):
        """Stats should handle errors gracefully."""
        maintenance = DecisionGraphMaintenance(temp_storage)

        # Close storage to simulate error
        temp_storage.close()

        stats = maintenance.get_database_stats()

        # Should return zeros, not raise exception
        assert stats["total_decisions"] == 0
        assert stats["total_stances"] == 0


class TestGrowthAnalysis:
    """Tests for growth rate analysis."""

    def test_analyze_growth_empty(self, maintenance: DecisionGraphMaintenance):
        """Growth analysis should handle empty database."""
        analysis = maintenance.analyze_growth(days=30)

        assert analysis["analysis_period_days"] == 30
        assert analysis["decisions_in_period"] == 0
        assert analysis["avg_decisions_per_day"] == 0.0
        assert analysis["projected_decisions_30d"] == 0
        assert analysis["oldest_decision_date"] is None
        assert analysis["newest_decision_date"] is None

    def test_analyze_growth_with_data(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Growth analysis should calculate rates correctly."""
        now = datetime.now()

        # Add 10 decisions over last 10 days
        for i in range(10):
            decision = DecisionNode(
                question=f"Question {i}?",
                timestamp=now - timedelta(days=i),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        analysis = maintenance.analyze_growth(days=30)

        assert analysis["analysis_period_days"] == 30
        assert analysis["decisions_in_period"] == 10
        # 10 decisions in 30 days = 0.33 per day
        assert 0.3 <= analysis["avg_decisions_per_day"] <= 0.4
        # Projected: ~10 in next 30 days
        assert 8 <= analysis["projected_decisions_30d"] <= 12

    def test_analyze_growth_custom_period(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Growth analysis should respect custom period."""
        now = datetime.now()

        # Add 7 decisions in last 7 days
        for i in range(7):
            decision = DecisionNode(
                question=f"Recent question {i}?",
                timestamp=now - timedelta(days=i),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        # Add 3 old decisions (>7 days ago)
        for i in range(3):
            decision = DecisionNode(
                question=f"Old question {i}?",
                timestamp=now - timedelta(days=20 + i),
                consensus=f"Old consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/old_transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        # Analyze last 7 days
        analysis = maintenance.analyze_growth(days=7)

        assert analysis["decisions_in_period"] == 7  # Only recent ones
        assert analysis["avg_decisions_per_day"] == 1.0  # 7 / 7 days

    def test_analyze_growth_performance(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Growth analysis should be <200ms even with 100 decisions."""
        now = datetime.now()

        # Add 100 decisions spread over 30 days
        for i in range(100):
            decision = DecisionNode(
                question=f"Question {i}?",
                timestamp=now - timedelta(days=i % 30),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        # Benchmark growth analysis
        start = time.perf_counter()
        analysis = maintenance.analyze_growth(days=30)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert (
            elapsed_ms < 200
        ), f"Growth analysis took {elapsed_ms:.2f}ms, expected <200ms"
        assert analysis["decisions_in_period"] == 100


class TestArchivalEstimation:
    """Tests for archival benefit estimation."""

    def test_estimate_archival_benefit_empty(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Archival estimation should handle empty database."""
        estimate = maintenance.estimate_archival_benefit()

        assert estimate["archive_eligible_count"] == 0
        assert estimate["archive_eligible_percent"] == 0.0
        assert estimate["estimated_space_savings_mb"] == 0.0
        assert estimate["would_trigger_archival"] is False
        assert "No decisions" in estimate["trigger_reason"]

    def test_estimate_archival_benefit_no_old_decisions(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Archival should not trigger if all decisions are recent."""
        now = datetime.now()

        # Add 100 recent decisions (last 30 days)
        for i in range(100):
            decision = DecisionNode(
                question=f"Recent question {i}?",
                timestamp=now - timedelta(days=i % 30),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        estimate = maintenance.estimate_archival_benefit()

        assert estimate["archive_eligible_count"] == 0
        assert estimate["would_trigger_archival"] is False
        # Reason should mention either no old decisions or below threshold
        assert (
            "No decisions" in estimate["trigger_reason"]
            or "100 decisions" in estimate["trigger_reason"]
        )

    def test_estimate_archival_benefit_with_old_decisions(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Archival estimation should identify old decisions correctly."""
        now = datetime.now()

        # Add 60 old decisions (>180 days)
        for i in range(60):
            decision = DecisionNode(
                question=f"Old question {i}?",
                timestamp=now - timedelta(days=200 + i),
                consensus=f"Old consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/old_transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        # Add 40 recent decisions
        for i in range(40):
            decision = DecisionNode(
                question=f"Recent question {i}?",
                timestamp=now - timedelta(days=i),
                consensus=f"Recent consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/recent_transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        estimate = maintenance.estimate_archival_benefit()

        assert estimate["archive_eligible_count"] == 60
        assert estimate["archive_eligible_percent"] == 60.0  # 60 / 100
        # 60 decisions * 15KB/decision = 900KB ≈ 0.88MB
        assert 0.8 <= estimate["estimated_space_savings_mb"] <= 1.0
        # Should not trigger (need 5000 decisions)
        assert estimate["would_trigger_archival"] is False

    def test_estimate_archival_benefit_would_trigger(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Archival should trigger when thresholds are met."""
        now = datetime.now()

        # Add 5500 old decisions to exceed trigger threshold
        # (We'll use a loop with commits to avoid memory issues)
        for batch_start in range(0, 5500, 100):
            for i in range(batch_start, min(batch_start + 100, 5500)):
                decision = DecisionNode(
                    question=f"Old question {i}?",
                    timestamp=now - timedelta(days=200),
                    consensus=f"Consensus {i}",
                    convergence_status="converged",
                    participants=["claude-sonnet-4-5"],
                    transcript_path=f"/tmp/transcript_{i}.md",
                )
                temp_storage.save_decision_node(decision)

        estimate = maintenance.estimate_archival_benefit()

        assert estimate["archive_eligible_count"] == 5500
        assert estimate["would_trigger_archival"] is True
        assert "5500 decisions" in estimate["trigger_reason"]

    def test_estimate_archival_benefit_performance(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Archival estimation should be <500ms."""
        now = datetime.now()

        # Add 100 decisions with mixed ages
        for i in range(100):
            decision = DecisionNode(
                question=f"Question {i}?",
                timestamp=now - timedelta(days=i * 2),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        # Benchmark estimation
        start = time.perf_counter()
        maintenance.estimate_archival_benefit()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert (
            elapsed_ms < 500
        ), f"Archival estimation took {elapsed_ms:.2f}ms, expected <500ms"


class TestHealthCheck:
    """Tests for database health validation."""

    def test_health_check_empty_db(self, maintenance: DecisionGraphMaintenance):
        """Health check should pass on empty database."""
        health = maintenance.health_check()

        assert health["healthy"] is True
        assert health["checks_passed"] == 6
        assert health["checks_failed"] == 0
        assert len(health["issues"]) == 0

    def test_health_check_healthy_db(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Health check should pass on valid data."""
        # Add valid decision
        decision = DecisionNode(
            question="Valid question?",
            timestamp=datetime.now(),
            consensus="Valid consensus",
            convergence_status="converged",
            participants=["claude-sonnet-4-5"],
            transcript_path="/tmp/transcript.md",
        )
        decision_id = temp_storage.save_decision_node(decision)

        # Add valid stance
        stance = ParticipantStance(
            decision_id=decision_id,
            participant="claude-sonnet-4-5",
            final_position="Valid position",
        )
        temp_storage.save_participant_stance(stance)

        health = maintenance.health_check()

        assert health["healthy"] is True
        assert health["checks_passed"] == 6
        assert health["checks_failed"] == 0
        assert len(health["issues"]) == 0

    def test_health_check_orphaned_stances(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Health check should detect orphaned stances."""
        # Manually insert orphaned stance (bypassing foreign key)
        # Temporarily disable foreign keys to insert orphaned data
        temp_storage.conn.execute("PRAGMA foreign_keys = OFF")
        temp_storage.conn.execute(
            """
            INSERT INTO participant_stances (decision_id, participant, final_position)
            VALUES ('nonexistent-id', 'claude-sonnet-4-5', 'orphaned position')
            """
        )
        temp_storage.conn.commit()
        temp_storage.conn.execute("PRAGMA foreign_keys = ON")

        health = maintenance.health_check()

        assert health["healthy"] is False
        assert health["checks_failed"] == 1
        assert len(health["issues"]) == 1
        assert "orphaned participant stances" in health["issues"][0]
        assert health["details"]["orphaned_stances"] == 1

    def test_health_check_orphaned_similarities(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Health check should detect orphaned similarities."""
        # Manually insert orphaned similarity
        # Temporarily disable foreign keys to insert orphaned data
        temp_storage.conn.execute("PRAGMA foreign_keys = OFF")
        temp_storage.conn.execute(
            """
            INSERT INTO decision_similarities (source_id, target_id, similarity_score, computed_at)
            VALUES ('nonexistent-source', 'nonexistent-target', 0.8, ?)
            """,
            (datetime.now().isoformat(),),
        )
        temp_storage.conn.commit()
        temp_storage.conn.execute("PRAGMA foreign_keys = ON")

        health = maintenance.health_check()

        assert health["healthy"] is False
        assert health["checks_failed"] >= 1
        assert health["details"]["orphaned_similarities_source"] == 1
        assert health["details"]["orphaned_similarities_target"] == 1

    def test_health_check_future_timestamps(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Health check should detect future timestamps."""
        future_date = datetime.now() + timedelta(days=10)
        decision = DecisionNode(
            question="Future question?",
            timestamp=future_date,
            consensus="Future consensus",
            convergence_status="converged",
            participants=["claude-sonnet-4-5"],
            transcript_path="/tmp/transcript.md",
        )
        temp_storage.save_decision_node(decision)

        health = maintenance.health_check()

        assert health["healthy"] is False
        assert "future timestamps" in str(health["issues"])
        assert health["details"]["future_timestamps"] == 1

    def test_health_check_missing_fields(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Health check should detect missing required fields."""
        # Manually insert decision with missing question
        temp_storage.conn.execute(
            """
            INSERT INTO decision_nodes (
                id, question, timestamp, consensus, convergence_status,
                participants, transcript_path
            ) VALUES (?, '', ?, ?, '', '[]', '')
            """,
            ("test-id", datetime.now().isoformat(), "consensus"),
        )
        temp_storage.conn.commit()

        health = maintenance.health_check()

        assert health["healthy"] is False
        assert health["details"]["missing_required_fields"] >= 1

    def test_health_check_invalid_similarity_scores(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Health check should detect invalid similarity scores."""
        # Create valid decisions first
        decision1 = DecisionNode(
            question="Question 1?",
            timestamp=datetime.now(),
            consensus="Consensus 1",
            convergence_status="converged",
            participants=["claude-sonnet-4-5"],
            transcript_path="/tmp/transcript1.md",
        )
        decision2 = DecisionNode(
            question="Question 2?",
            timestamp=datetime.now(),
            consensus="Consensus 2",
            convergence_status="converged",
            participants=["claude-sonnet-4-5"],
            transcript_path="/tmp/transcript2.md",
        )
        id1 = temp_storage.save_decision_node(decision1)
        id2 = temp_storage.save_decision_node(decision2)

        # Insert similarity with invalid score
        temp_storage.conn.execute(
            """
            INSERT INTO decision_similarities (source_id, target_id, similarity_score, computed_at)
            VALUES (?, ?, 1.5, ?)
            """,
            (id1, id2, datetime.now().isoformat()),
        )
        temp_storage.conn.commit()

        health = maintenance.health_check()

        assert health["healthy"] is False
        assert health["details"]["invalid_similarity_scores"] == 1

    def test_health_check_performance(
        self, maintenance: DecisionGraphMaintenance, temp_storage: DecisionGraphStorage
    ):
        """Health check should complete in <1s."""
        # Add 100 decisions
        for i in range(100):
            decision = DecisionNode(
                question=f"Question {i}?",
                timestamp=datetime.now(),
                consensus=f"Consensus {i}",
                convergence_status="converged",
                participants=["claude-sonnet-4-5"],
                transcript_path=f"/tmp/transcript_{i}.md",
            )
            temp_storage.save_decision_node(decision)

        # Benchmark health check
        start = time.perf_counter()
        health = maintenance.health_check()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert (
            elapsed_ms < 1000
        ), f"Health check took {elapsed_ms:.2f}ms, expected <1000ms"
        assert health["healthy"] is True


class TestArchivalMethods:
    """Tests for Phase 2 archival methods (skeleton only)."""

    def test_identify_archive_candidates_not_implemented(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Archive candidate identification should return empty list in Phase 1."""
        candidates = maintenance.identify_archive_candidates()

        assert candidates == []
        assert isinstance(candidates, list)

    def test_archive_old_decisions_not_implemented(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Archive operation should return not_implemented status in Phase 1."""
        result = maintenance.archive_old_decisions(dry_run=True)

        assert result["status"] == "not_implemented"
        assert result["phase"] == "Phase 1"
        assert result["archived_count"] == 0
        assert "Phase 2" in result["message"]

    def test_archive_old_decisions_respects_dry_run(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Archive dry_run parameter should be passed through."""
        result = maintenance.archive_old_decisions(dry_run=False)

        assert result["dry_run"] is False


class TestMigrationGeneration:
    """Tests for migration SQL generation."""

    def test_get_pending_migrations_returns_list(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Pending migrations should return list of SQL statements."""
        migrations = maintenance.get_pending_migrations()

        assert isinstance(migrations, list)
        assert len(migrations) > 0

    def test_get_pending_migrations_includes_archived_column(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Migrations should include archived column addition."""
        migrations = maintenance.get_pending_migrations()

        # Join all migrations to search
        migrations_text = " ".join(migrations)

        assert "archived" in migrations_text.lower()
        assert "ALTER TABLE decision_nodes" in migrations_text

    def test_get_pending_migrations_includes_last_accessed_column(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Migrations should include last_accessed column addition."""
        migrations = maintenance.get_pending_migrations()

        migrations_text = " ".join(migrations)

        assert "last_accessed" in migrations_text.lower()

    def test_get_pending_migrations_includes_indexes(
        self, maintenance: DecisionGraphMaintenance
    ):
        """Migrations should include indexes for archival queries."""
        migrations = maintenance.get_pending_migrations()

        migrations_text = " ".join(migrations)

        assert "CREATE INDEX" in migrations_text
        assert (
            "idx_decision_archived" in migrations_text
            or "archived" in migrations_text.lower()
        )

    def test_get_pending_migrations_count(self, maintenance: DecisionGraphMaintenance):
        """Should have expected number of migrations."""
        migrations = maintenance.get_pending_migrations()

        # Should have at least: archived column, last_accessed column, indexes
        assert len(migrations) >= 3


class TestErrorHandling:
    """Tests for error handling and graceful degradation."""

    def test_stats_with_closed_connection(self, temp_storage: DecisionGraphStorage):
        """Stats should handle closed connection gracefully."""
        maintenance = DecisionGraphMaintenance(temp_storage)
        temp_storage.close()

        stats = maintenance.get_database_stats()

        # Should not raise, should return zeros
        assert stats["total_decisions"] == 0

    def test_growth_analysis_with_closed_connection(
        self, temp_storage: DecisionGraphStorage
    ):
        """Growth analysis should handle errors gracefully."""
        maintenance = DecisionGraphMaintenance(temp_storage)
        temp_storage.close()

        analysis = maintenance.analyze_growth()

        # Should not raise, should return zeros
        assert analysis["decisions_in_period"] == 0

    def test_health_check_with_closed_connection(
        self, temp_storage: DecisionGraphStorage
    ):
        """Health check should handle errors gracefully."""
        maintenance = DecisionGraphMaintenance(temp_storage)
        temp_storage.close()

        health = maintenance.health_check()

        # Should not raise, should report unhealthy with error
        assert health["healthy"] is False
        assert len(health["issues"]) > 0


class TestMaintenanceInitialization:
    """Tests for maintenance manager initialization."""

    def test_initialization_with_storage(self, temp_storage: DecisionGraphStorage):
        """Maintenance should initialize with storage."""
        maintenance = DecisionGraphMaintenance(temp_storage)

        assert maintenance.storage == temp_storage
        assert maintenance.ARCHIVE_TRIGGER_DECISIONS == 5000
        assert maintenance.ARCHIVE_TRIGGER_AGE_DAYS == 180
        assert maintenance.ARCHIVE_TRIGGER_UNUSED_DAYS == 90

    def test_initialization_logs_phase(
        self, temp_storage: DecisionGraphStorage, caplog
    ):
        """Initialization should log Phase 1 status."""
        import logging

        caplog.set_level(logging.INFO)
        DecisionGraphMaintenance(temp_storage)

        assert "Phase 1" in caplog.text or "monitoring only" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
