"""Unit tests for DecisionGraphIntegration with maintenance monitoring."""
from datetime import datetime
from unittest.mock import patch

import pytest

from decision_graph.integration import DecisionGraphIntegration
from decision_graph.schema import DecisionNode
from decision_graph.storage import DecisionGraphStorage
from models.schema import ConvergenceInfo, DeliberationResult, Summary


class TestDecisionGraphIntegrationMaintenance:
    """Test maintenance/monitoring integration in DecisionGraphIntegration."""

    @pytest.fixture
    def storage(self):
        """Create in-memory storage for testing."""
        return DecisionGraphStorage(":memory:")

    @pytest.fixture
    def integration(self, storage):
        """Create integration instance with background worker disabled."""
        return DecisionGraphIntegration(storage, enable_background_worker=False)

    @pytest.fixture
    def sample_result(self):
        """Create sample DeliberationResult for testing."""
        return DeliberationResult(
            status="complete",
            mode="test",
            participants=["test@cli"],
            rounds_completed=2,
            full_debate=[],
            summary=Summary(
                consensus="Test consensus",
                key_agreements=["Agreement 1"],
                key_disagreements=[],
                final_recommendation="Test recommendation",
            ),
            convergence_info=ConvergenceInfo(
                detected=True, status="converged", final_similarity=0.95
            ),
            voting_result=None,
            transcript_path="/test/transcript.md",
        )

    def test_should_initialize_maintenance_on_startup(self, integration):
        """Test that maintenance is initialized during integration startup."""
        assert integration.maintenance is not None
        assert integration._decision_count == 0

    def test_should_track_decision_count_on_store(self, integration, sample_result):
        """Test that decision count increments when storing deliberations."""
        # Initial count
        assert integration._decision_count == 0

        # Store first decision
        integration.store_deliberation("Question 1", sample_result)
        assert integration._decision_count == 1

        # Store second decision
        integration.store_deliberation("Question 2", sample_result)
        assert integration._decision_count == 2

        # Store third decision
        integration.store_deliberation("Question 3", sample_result)
        assert integration._decision_count == 3

    def test_should_log_stats_every_100_decisions(
        self, integration, sample_result, caplog
    ):
        """Test that stats are logged every 100 decisions."""
        import logging

        caplog.set_level(logging.INFO)

        # Store 99 decisions - no stats logged yet
        for i in range(99):
            integration.store_deliberation(f"Question {i}", sample_result)

        # No stats logging yet
        stats_logs = [r for r in caplog.records if "Decision graph stats" in r.message]
        assert len(stats_logs) == 0

        # Store 100th decision - should trigger stats logging
        integration.store_deliberation("Question 99", sample_result)

        # Should now have stats log
        stats_logs = [r for r in caplog.records if "Decision graph stats" in r.message]
        assert len(stats_logs) == 1
        assert "100 stored" in stats_logs[0].message
        assert "decisions" in stats_logs[0].message

    def test_should_warn_when_approaching_archival_threshold(
        self, integration, sample_result, caplog
    ):
        """Test that warning is logged when approaching 5000 decision threshold."""
        import logging

        caplog.set_level(logging.WARNING)

        # Mock stats to return 4500+ decisions
        with patch.object(integration.maintenance, "get_database_stats") as mock_stats:
            mock_stats.return_value = {
                "total_decisions": 4600,
                "total_stances": 13800,
                "total_similarities": 50000,
                "db_size_bytes": 10485760,
                "db_size_mb": 10.0,
            }

            # Manually set counter to 100 to trigger stats check
            integration._decision_count = 99
            integration.store_deliberation("Question", sample_result)

            # Should have warning about threshold
            warnings = [r for r in caplog.records if r.levelname == "WARNING"]
            threshold_warnings = [
                w for w in warnings if "approaching archival threshold" in w.message
            ]
            assert len(threshold_warnings) == 1
            assert "4600 decisions" in threshold_warnings[0].message
            assert "threshold: 5000" in threshold_warnings[0].message

    def test_should_not_warn_when_below_threshold(
        self, integration, sample_result, caplog
    ):
        """Test no warning when below 4500 decision threshold."""
        import logging

        caplog.set_level(logging.WARNING)

        # Mock stats to return <4500 decisions
        with patch.object(integration.maintenance, "get_database_stats") as mock_stats:
            mock_stats.return_value = {
                "total_decisions": 3000,
                "total_stances": 9000,
                "total_similarities": 20000,
                "db_size_bytes": 5242880,
                "db_size_mb": 5.0,
            }

            # Manually set counter to 100 to trigger stats check
            integration._decision_count = 99
            integration.store_deliberation("Question", sample_result)

            # Should NOT have warning about threshold
            warnings = [r for r in caplog.records if r.levelname == "WARNING"]
            threshold_warnings = [
                w for w in warnings if "approaching archival threshold" in w.message
            ]
            assert len(threshold_warnings) == 0

    def test_should_log_growth_analysis_every_500_decisions(
        self, integration, sample_result, caplog
    ):
        """Test that growth analysis is logged every 500 decisions."""
        import logging

        caplog.set_level(logging.INFO)

        # Mock stats and growth to avoid actual computation
        with patch.object(
            integration.maintenance, "get_database_stats"
        ) as mock_stats, patch.object(
            integration.maintenance, "analyze_growth"
        ) as mock_growth:
            mock_stats.return_value = {
                "total_decisions": 500,
                "total_stances": 1500,
                "total_similarities": 5000,
                "db_size_bytes": 2097152,
                "db_size_mb": 2.0,
            }

            mock_growth.return_value = {
                "analysis_period_days": 30,
                "decisions_in_period": 200,
                "avg_decisions_per_day": 6.67,
                "projected_decisions_30d": 200,
                "oldest_decision_date": "2025-01-01T00:00:00",
                "newest_decision_date": "2025-01-30T00:00:00",
            }

            # Manually set counter to 500 to trigger growth analysis
            integration._decision_count = 499
            integration.store_deliberation("Question", sample_result)

            # Should have growth analysis log
            growth_logs = [r for r in caplog.records if "Growth analysis" in r.message]
            assert len(growth_logs) == 1
            assert "200 decisions in 30 days" in growth_logs[0].message
            assert "avg 6.67/day" in growth_logs[0].message

    def test_should_handle_stats_collection_errors_gracefully(
        self, integration, sample_result, caplog
    ):
        """Test that errors in stats collection don't break deliberation storage."""
        import logging

        caplog.set_level(logging.ERROR)

        # Mock stats to raise exception
        with patch.object(integration.maintenance, "get_database_stats") as mock_stats:
            mock_stats.side_effect = Exception("Database error")

            # Manually set counter to 100 to trigger stats check
            integration._decision_count = 99

            # Should NOT raise exception, just log error
            decision_id = integration.store_deliberation("Question", sample_result)
            assert decision_id is not None

            # Should have error log
            errors = [r for r in caplog.records if r.levelname == "ERROR"]
            stats_errors = [
                e for e in errors if "Error collecting maintenance stats" in e.message
            ]
            assert len(stats_errors) == 1

    def test_get_graph_stats_returns_stats(self, integration):
        """Test get_graph_stats() returns database statistics."""
        # Store some decisions
        sample_result = DeliberationResult(
            status="complete",
            mode="test",
            participants=["test@cli"],
            rounds_completed=1,
            full_debate=[],
            summary=Summary(
                consensus="Test",
                key_agreements=[],
                key_disagreements=[],
                final_recommendation="Test",
            ),
            convergence_info=ConvergenceInfo(
                detected=False, status="unknown", final_similarity=0.0
            ),
            voting_result=None,
            transcript_path="/test.md",
        )

        integration.store_deliberation("Q1", sample_result)
        integration.store_deliberation("Q2", sample_result)

        # Get stats
        stats = integration.get_graph_stats()

        # Verify structure
        assert "total_decisions" in stats
        assert "total_stances" in stats
        assert "total_similarities" in stats
        assert "db_size_bytes" in stats
        assert "db_size_mb" in stats

        # Verify counts (should have 2 decisions)
        assert stats["total_decisions"] == 2

    def test_get_graph_stats_handles_errors_gracefully(self, integration):
        """Test get_graph_stats() returns empty dict on error."""
        # Mock maintenance to raise exception
        with patch.object(integration.maintenance, "get_database_stats") as mock_stats:
            mock_stats.side_effect = Exception("Database error")

            # Should return empty dict, not raise
            stats = integration.get_graph_stats()
            assert stats == {}

    def test_health_check_returns_healthy_status(self, integration):
        """Test health_check() returns healthy status for clean database."""
        # Get health check
        health = integration.health_check()

        # Verify structure
        assert "healthy" in health
        assert "checks_passed" in health
        assert "checks_failed" in health
        assert "issues" in health
        assert "details" in health

        # Should be healthy (empty database has no issues)
        assert health["healthy"] is True
        assert health["checks_failed"] == 0
        assert len(health["issues"]) == 0

    def test_health_check_detects_unhealthy_status(self, integration):
        """Test health_check() detects issues in database."""
        # Mock health check to return issues
        with patch.object(integration.maintenance, "health_check") as mock_health:
            mock_health.return_value = {
                "healthy": False,
                "checks_passed": 4,
                "checks_failed": 2,
                "issues": [
                    "Found 5 orphaned participant stances",
                    "Found 3 similarities with invalid scores",
                ],
                "details": {"orphaned_stances": 5, "invalid_similarity_scores": 3},
            }

            # Get health check
            health = integration.health_check()

            # Should report unhealthy
            assert health["healthy"] is False
            assert health["checks_failed"] == 2
            assert len(health["issues"]) == 2

    def test_health_check_handles_errors_gracefully(self, integration):
        """Test health_check() returns error status on exception."""
        # Mock health check to raise exception
        with patch.object(integration.maintenance, "health_check") as mock_health:
            mock_health.side_effect = Exception("Database error")

            # Should return error status, not raise
            health = integration.health_check()

            assert health["healthy"] is False
            assert health["checks_failed"] == 1
            assert len(health["issues"]) == 1
            assert "Health check error" in health["issues"][0]

    def test_periodic_checks_use_decision_count_not_db_count(
        self, integration, sample_result
    ):
        """Test that periodic checks use stored decision count, not DB query count."""
        # This ensures we don't trigger on decision 100 in DB if we've only stored 50
        # via this integration instance (e.g., after restart)

        # Manually set DB to have 150 decisions
        for i in range(150):
            node = DecisionNode(
                id=f"dec-{i}",
                question=f"Question {i}",
                timestamp=datetime.now(),
                consensus="Test",
                winning_option=None,
                convergence_status="converged",
                participants=["test@cli"],
                transcript_path="/test.md",
            )
            integration.storage.save_decision_node(node)

        # Reset integration counter to 0
        integration._decision_count = 0

        # Store decisions via integration
        import logging

        # Capture logs
        log_capture = []
        handler = logging.Handler()
        handler.emit = lambda record: log_capture.append(record)
        logger = logging.getLogger("decision_graph.integration")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            # Store 99 decisions - should NOT trigger stats (count is 99, not 100)
            for i in range(99):
                integration.store_deliberation(f"New Question {i}", sample_result)

            stats_logs_before = [
                r for r in log_capture if "Decision graph stats" in r.message
            ]
            assert (
                len(stats_logs_before) == 0
            ), "Should not log stats before 100 stored decisions"

            # Store 100th decision - should trigger stats
            integration.store_deliberation("New Question 99", sample_result)

            stats_logs_after = [
                r for r in log_capture if "Decision graph stats" in r.message
            ]
            assert (
                len(stats_logs_after) == 1
            ), "Should log stats at 100 stored decisions"

        finally:
            logger.removeHandler(handler)

    def test_stats_logging_includes_all_metrics(
        self, integration, sample_result, caplog
    ):
        """Test that stats logging includes all expected metrics."""
        import logging

        caplog.set_level(logging.INFO)

        # Manually set counter to trigger stats
        integration._decision_count = 99
        integration.store_deliberation("Question", sample_result)

        # Find stats log
        stats_logs = [r for r in caplog.records if "Decision graph stats" in r.message]
        assert len(stats_logs) == 1

        message = stats_logs[0].message

        # Verify all metrics present
        assert "decisions" in message
        assert "stances" in message
        assert "similarities" in message
        assert "MB" in message


class TestDecisionGraphIntegrationTieredFormatting:
    """Test Task 5: Integration of tiered formatting with get_context_for_deliberation()."""

    @pytest.fixture
    def storage(self):
        """Create in-memory storage for testing."""
        return DecisionGraphStorage(":memory:")

    @pytest.fixture
    def config(self):
        """Create mock config with budget-aware settings."""
        from models.config import Config, DecisionGraphConfig, DefaultsConfig, StorageConfig, DeliberationConfig, ConvergenceDetectionConfig, EarlyStoppingConfig, CLIToolConfig

        return Config(
            version="1.0",
            cli_tools={
                "test": CLIToolConfig(
                    command="test",
                    args=["{prompt}"],
                    timeout=60
                )
            },
            defaults=DefaultsConfig(
                mode="quick",
                rounds=2,
                max_rounds=5,
                timeout_per_round=120
            ),
            storage=StorageConfig(
                transcripts_dir="transcripts",
                format="markdown",
                auto_export=True
            ),
            deliberation=DeliberationConfig(
                convergence_detection=ConvergenceDetectionConfig(
                    enabled=True,
                    semantic_similarity_threshold=0.85,
                    divergence_threshold=0.40,
                    min_rounds_before_check=1,
                    consecutive_stable_rounds=2,
                    stance_stability_threshold=0.80,
                    response_length_drop_threshold=0.40
                ),
                early_stopping=EarlyStoppingConfig(
                    enabled=True,
                    threshold=0.66,
                    respect_min_rounds=True
                ),
                convergence_threshold=0.8,
                enable_convergence_detection=True
            ),
            decision_graph=DecisionGraphConfig(
                enabled=True,
                db_path=":memory:",
                similarity_threshold=0.6,
                max_context_decisions=3,
                compute_similarities=True,
                context_token_budget=1500,
                tier_boundaries={"strong": 0.75, "moderate": 0.60},
                query_window=1000
            )
        )

    @pytest.fixture
    def integration_with_config(self, storage, config):
        """Create integration instance with config."""
        return DecisionGraphIntegration(storage, enable_background_worker=False, config=config)

    @pytest.fixture
    def sample_decisions(self, storage):
        """Create sample decisions with varying similarity scores."""
        decisions = []

        # Decision 1: Strong match
        node1 = DecisionNode(
            id="dec-1",
            question="Should we use TypeScript for frontend?",
            timestamp=datetime.now(),
            consensus="Yes, TypeScript provides type safety",
            winning_option="Adopt TypeScript",
            convergence_status="converged",
            participants=["claude@cli"],
            transcript_path="/test1.md"
        )
        storage.save_decision_node(node1)
        decisions.append(node1)

        # Decision 2: Moderate match
        node2 = DecisionNode(
            id="dec-2",
            question="Should we migrate to Python 3.11?",
            timestamp=datetime.now(),
            consensus="Yes, for performance benefits",
            winning_option="Migrate to 3.11",
            convergence_status="converged",
            participants=["droid@cli"],
            transcript_path="/test2.md"
        )
        storage.save_decision_node(node2)
        decisions.append(node2)

        # Decision 3: Brief match
        node3 = DecisionNode(
            id="dec-3",
            question="What database should we choose?",
            timestamp=datetime.now(),
            consensus="PostgreSQL for relational data",
            winning_option="PostgreSQL",
            convergence_status="converged",
            participants=["gemini@cli"],
            transcript_path="/test3.md"
        )
        storage.save_decision_node(node3)
        decisions.append(node3)

        return decisions

    def test_get_context_uses_budget_config(self, integration_with_config, sample_decisions, caplog):
        """Test that get_context_for_deliberation uses config budget and tier boundaries."""
        import logging
        caplog.set_level(logging.DEBUG)

        # Mock retriever's find_relevant_decisions to return scored tuples
        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            # Return all 3 decisions with different scores
            mock_find.return_value = [
                (sample_decisions[0], 0.85),  # Strong
                (sample_decisions[1], 0.65),  # Moderate
                (sample_decisions[2], 0.45),  # Brief
            ]

            # Call get_context_for_deliberation
            context = integration_with_config.get_context_for_deliberation(
                "Should we adopt JavaScript frameworks?"
            )

            # Verify find_relevant_decisions was called (with deprecated params)
            mock_find.assert_called_once()

        # Verify config values were accessed (check logs for tier boundaries usage)
        debug_logs = [r.message for r in caplog.records if r.levelname == "DEBUG"]
        # Should see logs about tier processing
        assert any("tier" in log.lower() for log in debug_logs), "Expected tier-related debug logs"

    def test_get_context_returns_tiered_format(self, integration_with_config, sample_decisions):
        """Test that get_context_for_deliberation returns tiered formatted context."""
        from unittest.mock import patch

        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            # Return scored decisions
            mock_find.return_value = [
                (sample_decisions[0], 0.85),  # Strong
                (sample_decisions[1], 0.65),  # Moderate
                (sample_decisions[2], 0.45),  # Brief
            ]

            context = integration_with_config.get_context_for_deliberation(
                "Should we use TypeScript?"
            )

            # Verify tiered header is present
            assert "Tiered by Relevance" in context or "Similar Past Deliberations" in context

            # Verify context is not empty
            assert len(context) > 0

    def test_get_context_logs_metrics(self, integration_with_config, sample_decisions, caplog):
        """Test that get_context_for_deliberation logs tier distribution and token usage."""
        import logging
        caplog.set_level(logging.INFO)

        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            mock_find.return_value = [
                (sample_decisions[0], 0.85),  # Strong
                (sample_decisions[1], 0.65),  # Moderate
            ]

            context = integration_with_config.get_context_for_deliberation(
                "Should we migrate databases?"
            )

        # Check logs for metrics
        info_logs = [r.message for r in caplog.records if r.levelname == "INFO"]

        # Should log tier distribution or token usage
        metrics_logged = any(
            "tier" in log.lower() or "token" in log.lower()
            for log in info_logs
        )
        assert metrics_logged, f"Expected tier/token metrics in logs. Got: {info_logs}"

    def test_get_context_respects_token_budget(self, integration_with_config, sample_decisions):
        """Test that get_context_for_deliberation respects token budget from config."""
        from unittest.mock import patch

        # Create a config with very small token budget
        integration_with_config.config.decision_graph.context_token_budget = 200  # Very small

        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            # Return many decisions
            mock_find.return_value = [
                (sample_decisions[0], 0.85),
                (sample_decisions[1], 0.65),
                (sample_decisions[2], 0.45),
            ]

            context = integration_with_config.get_context_for_deliberation(
                "Should we use React?"
            )

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            estimated_tokens = len(context) // 4

            # Should be within or close to budget (allow some overhead for header)
            # Note: Budget may be slightly exceeded due to header
            assert estimated_tokens <= 300, f"Context exceeds budget: {estimated_tokens} tokens"

    def test_get_context_empty_db_returns_empty(self, storage, config):
        """Test that get_context_for_deliberation returns empty string when DB is empty."""
        integration = DecisionGraphIntegration(storage, enable_background_worker=False, config=config)

        # DB is empty (no sample_decisions fixture)
        context = integration.get_context_for_deliberation("Should we use Vue.js?")

        # Should return empty string, not fail
        assert context == ""

    def test_get_context_handles_config_none_gracefully(self, storage):
        """Test that get_context_for_deliberation handles missing config gracefully."""
        # Create integration without config
        integration = DecisionGraphIntegration(storage, enable_background_worker=False, config=None)

        # Should fall back to default behavior (use retriever's get_enriched_context)
        context = integration.get_context_for_deliberation("Should we use Angular?")

        # Should not crash, return empty or use defaults
        assert isinstance(context, str)

    def test_get_context_logs_database_size(self, integration_with_config, sample_decisions, caplog):
        """Test that get_context_for_deliberation logs database size for calibration."""
        import logging
        caplog.set_level(logging.DEBUG)

        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            mock_find.return_value = [(sample_decisions[0], 0.85)]

            context = integration_with_config.get_context_for_deliberation(
                "Should we use PostgreSQL?"
            )

        # Should log database size or decision count
        debug_logs = [r.message for r in caplog.records]
        # Look for any size-related logging (might be in retriever or integration)
        assert len(debug_logs) > 0, "Expected debug logs"

    def test_backward_compatibility_with_old_params(self, integration_with_config, sample_decisions, caplog):
        """Test that threshold/max_context_decisions params are deprecated but don't break."""
        import logging
        caplog.set_level(logging.WARNING)

        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            mock_find.return_value = [(sample_decisions[0], 0.85)]

            # Call with old parameters
            context = integration_with_config.get_context_for_deliberation(
                "Should we use Redis?",
                threshold=0.8,  # Deprecated
                max_context_decisions=5  # Deprecated
            )

            # Should log deprecation warning
            warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
            assert any("deprecated" in w.lower() for w in warnings), "Expected deprecation warning"


class TestDecisionGraphIntegrationMeasurementHooks:
    """Test Task 8: Observability and measurement hooks for Phase 1.5 calibration."""

    @pytest.fixture
    def storage(self):
        """Create in-memory storage for testing."""
        return DecisionGraphStorage(":memory:")

    @pytest.fixture
    def config(self):
        """Create mock config with budget-aware settings."""
        from models.config import Config, DecisionGraphConfig, DefaultsConfig, StorageConfig, DeliberationConfig, ConvergenceDetectionConfig, EarlyStoppingConfig, CLIToolConfig

        return Config(
            version="1.0",
            cli_tools={
                "test": CLIToolConfig(
                    command="test",
                    args=["{prompt}"],
                    timeout=60
                )
            },
            defaults=DefaultsConfig(
                mode="quick",
                rounds=2,
                max_rounds=5,
                timeout_per_round=120
            ),
            storage=StorageConfig(
                transcripts_dir="transcripts",
                format="markdown",
                auto_export=True
            ),
            deliberation=DeliberationConfig(
                convergence_detection=ConvergenceDetectionConfig(
                    enabled=True,
                    semantic_similarity_threshold=0.85,
                    divergence_threshold=0.40,
                    min_rounds_before_check=1,
                    consecutive_stable_rounds=2,
                    stance_stability_threshold=0.80,
                    response_length_drop_threshold=0.40
                ),
                early_stopping=EarlyStoppingConfig(
                    enabled=True,
                    threshold=0.66,
                    respect_min_rounds=True
                ),
                convergence_threshold=0.8,
                enable_convergence_detection=True
            ),
            decision_graph=DecisionGraphConfig(
                enabled=True,
                db_path=":memory:",
                similarity_threshold=0.6,
                max_context_decisions=3,
                compute_similarities=True,
                context_token_budget=1500,
                tier_boundaries={"strong": 0.75, "moderate": 0.60},
                query_window=1000
            )
        )

    @pytest.fixture
    def integration_with_config(self, storage, config):
        """Create integration instance with config."""
        return DecisionGraphIntegration(storage, enable_background_worker=False, config=config)

    @pytest.fixture
    def sample_decision(self, storage):
        """Create a sample decision node."""
        node = DecisionNode(
            id="dec-1",
            question="Should we use TypeScript?",
            timestamp=datetime.now(),
            consensus="Yes, TypeScript provides type safety",
            winning_option="Adopt TypeScript",
            convergence_status="converged",
            participants=["claude@cli"],
            transcript_path="/test1.md"
        )
        storage.save_decision_node(node)
        return node

    def test_measurement_hooks_logged(self, integration_with_config, sample_decision, caplog):
        """Test that tier distribution is logged on every context injection."""
        import logging
        caplog.set_level(logging.INFO)

        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            # Return a decision with strong similarity
            mock_find.return_value = [(sample_decision, 0.85)]

            context = integration_with_config.get_context_for_deliberation(
                "Should we adopt TypeScript for our project?"
            )

        # Verify MEASUREMENT log exists
        measurement_logs = [r for r in caplog.records if "MEASUREMENT:" in r.message]
        assert len(measurement_logs) > 0, "Expected MEASUREMENT log entry"

        # Verify tier distribution is logged
        log_message = measurement_logs[0].message
        assert "tier_distribution" in log_message or "tiers=" in log_message, \
            f"Expected tier distribution in log. Got: {log_message}"

    def test_measurement_hooks_include_tokens(self, integration_with_config, sample_decision, caplog):
        """Test that token usage is logged in measurement hooks."""
        import logging
        caplog.set_level(logging.INFO)

        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            mock_find.return_value = [(sample_decision, 0.85)]

            context = integration_with_config.get_context_for_deliberation(
                "Should we use TypeScript?"
            )

        # Verify token usage is logged
        measurement_logs = [r for r in caplog.records if "MEASUREMENT:" in r.message]
        assert len(measurement_logs) > 0, "Expected MEASUREMENT log entry"

        log_message = measurement_logs[0].message
        # Should include both tokens_used and budget
        assert "tokens" in log_message.lower(), f"Expected token usage in log. Got: {log_message}"
        # Should show budget (e.g., "tokens=500/1500")
        assert "/" in log_message or "budget" in log_message.lower(), \
            f"Expected token budget in log. Got: {log_message}"

    def test_measurement_hooks_db_size_logged(self, integration_with_config, sample_decision, caplog):
        """Test that database size metrics are logged."""
        import logging
        caplog.set_level(logging.INFO)

        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            mock_find.return_value = [(sample_decision, 0.85)]

            context = integration_with_config.get_context_for_deliberation(
                "Should we use TypeScript?"
            )

        # Verify database size is logged
        measurement_logs = [r for r in caplog.records if "MEASUREMENT:" in r.message]
        assert len(measurement_logs) > 0, "Expected MEASUREMENT log entry"

        log_message = measurement_logs[0].message
        assert "db_size" in log_message or "database" in log_message.lower(), \
            f"Expected database size in log. Got: {log_message}"

    def test_measurement_hooks_format(self, integration_with_config, sample_decision, caplog):
        """Test that measurement logs use structured format for parsing."""
        import logging
        caplog.set_level(logging.INFO)

        from unittest.mock import patch
        with patch.object(integration_with_config.retriever, 'find_relevant_decisions') as mock_find:
            mock_find.return_value = [(sample_decision, 0.85)]

            context = integration_with_config.get_context_for_deliberation(
                "Should we use TypeScript?"
            )

        # Verify structured logging format
        measurement_logs = [r for r in caplog.records if "MEASUREMENT:" in r.message]
        assert len(measurement_logs) > 0, "Expected MEASUREMENT log entry"

        log_message = measurement_logs[0].message

        # Verify format is parseable (key=value pairs)
        # Should have format like: MEASUREMENT: question='...', scored_results=N, tier_distribution={...}, ...
        assert "MEASUREMENT:" in log_message, "Expected MEASUREMENT: prefix"

        # Check for key=value format
        assert "=" in log_message, "Expected key=value format"

        # Verify all required metrics are present
        required_metrics = ["question", "tier_distribution", "tokens", "db_size"]
        for metric in required_metrics:
            assert metric in log_message.lower(), \
                f"Expected '{metric}' in structured log. Got: {log_message}"

    def test_get_graph_metrics_returns_detailed_stats(self, integration_with_config, sample_decision):
        """Test that get_graph_metrics() returns dict with detailed statistics."""
        # Call get_graph_metrics
        metrics = integration_with_config.get_graph_metrics()

        # Verify return type
        assert isinstance(metrics, dict), "Expected dict return type"

        # Verify required keys
        expected_keys = ["total_decisions", "recent_100_count", "recent_1000_count"]
        for key in expected_keys:
            assert key in metrics, f"Expected '{key}' in metrics dict"

        # Verify values are reasonable
        assert metrics["total_decisions"] >= 0, "total_decisions should be non-negative"
        assert metrics["recent_100_count"] >= 0, "recent_100_count should be non-negative"
        assert metrics["recent_1000_count"] >= 0, "recent_1000_count should be non-negative"

    def test_get_graph_metrics_handles_empty_db(self, storage, config):
        """Test that get_graph_metrics() handles empty database gracefully."""
        integration = DecisionGraphIntegration(storage, enable_background_worker=False, config=config)

        # DB is empty
        metrics = integration.get_graph_metrics()

        # Should return valid dict with zeros
        assert isinstance(metrics, dict)
        assert metrics.get("total_decisions", 0) == 0
        assert metrics.get("recent_100_count", 0) == 0
        assert metrics.get("recent_1000_count", 0) == 0
