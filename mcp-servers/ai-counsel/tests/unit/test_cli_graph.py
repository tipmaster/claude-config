"""Unit tests for cli/graph.py Click commands.

This module tests all CLI commands in the graph command group using strict TDD.
Tests cover:
- 'graph similar': similarity search with all options
- 'graph contradictions': contradiction detection
- 'graph timeline': decision evolution tracing
- 'graph analyze': pattern analysis
- 'graph export': data export in multiple formats
- Error handling and edge cases
- Output formatting (summary, detailed, json, table)
- File I/O operations
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from cli.graph import contradictions, export, graph, similar, timeline
from decision_graph.schema import DecisionNode, ParticipantStance
from decision_graph.storage import DecisionGraphStorage
from deliberation.query_engine import (Contradiction, QueryEngine,
                                       SimilarResult, Timeline, TimelineEntry)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_decisions():
    """Create sample decision nodes for testing."""
    return [
        DecisionNode(
            id="dec-1",
            question="Should we adopt TypeScript for the frontend?",
            timestamp=datetime(2025, 10, 1, 10, 0, 0),
            consensus="TypeScript adoption recommended with phased migration",
            winning_option="Yes, adopt TypeScript",
            convergence_status="unanimous_consensus",
            participants=["opus@claude", "gpt4@codex"],
            transcript_path="/transcripts/typescript_adoption.md",
            metadata={"scope": "frontend"},
        ),
        DecisionNode(
            id="dec-2",
            question="Should we migrate backend to Python 3.12?",
            timestamp=datetime(2025, 10, 2, 14, 30, 0),
            consensus="Upgrade to Python 3.12 after testing",
            winning_option="Upgrade after Q2 2025",
            convergence_status="majority_decision",
            participants=["opus@claude", "gpt4@codex", "gemini@google"],
            transcript_path="/transcripts/python_upgrade.md",
            metadata={"scope": "backend"},
        ),
        DecisionNode(
            id="dec-3",
            question="Frontend framework selection: React vs Vue",
            timestamp=datetime(2025, 10, 3, 9, 15, 0),
            consensus="React chosen for larger ecosystem and team familiarity",
            winning_option="React",
            convergence_status="converged",
            participants=["opus@claude", "gemini@google"],
            transcript_path="/transcripts/framework_choice.md",
            metadata={"scope": "frontend"},
        ),
    ]


@pytest.fixture
def sample_stances():
    """Create sample participant stances for testing."""
    return [
        ParticipantStance(
            decision_id="dec-1",
            participant="opus@claude",
            vote_option="Yes",
            confidence=0.95,
            rationale="Strong type safety benefits outweigh migration costs",
            final_position="TypeScript is the clear choice for long-term maintainability",
        ),
        ParticipantStance(
            decision_id="dec-1",
            participant="gpt4@codex",
            vote_option="Yes",
            confidence=0.88,
            rationale="Developer experience improvements and error reduction",
            final_position="Agree with TypeScript adoption",
        ),
        ParticipantStance(
            decision_id="dec-2",
            participant="opus@claude",
            vote_option="Upgrade",
            confidence=0.85,
            rationale="Python 3.12 offers performance improvements",
            final_position="Gradual migration recommended",
        ),
        ParticipantStance(
            decision_id="dec-3",
            participant="opus@claude",
            vote_option="React",
            confidence=0.8,
            rationale="Team expertise and ecosystem maturity",
            final_position="React is the pragmatic choice",
        ),
    ]


@pytest.fixture
def mock_storage(sample_decisions, sample_stances):
    """Create mocked DecisionGraphStorage."""
    storage = Mock(spec=DecisionGraphStorage)
    storage.get_all_decisions.return_value = sample_decisions
    storage.get_decision_node = Mock(
        side_effect=lambda id: next((d for d in sample_decisions if d.id == id), None)
    )
    storage.get_participant_stances = Mock(
        side_effect=lambda id: [s for s in sample_stances if s.decision_id == id]
    )
    return storage


@pytest.fixture
def mock_query_engine(sample_decisions, sample_stances):
    """Create mocked QueryEngine with typical responses."""
    engine = Mock(spec=QueryEngine)

    # Mock similar search
    engine._search_similar_sync.return_value = [
        SimilarResult(
            decision=sample_decisions[0],
            score=0.92,
        ),
        SimilarResult(
            decision=sample_decisions[2],
            score=0.78,
        ),
    ]

    # Mock contradictions
    engine._find_contradictions_sync.return_value = [
        Contradiction(
            decision_id_1="dec-1",
            decision_id_2="dec-3",
            question_1="Should we adopt TypeScript for the frontend?",
            question_2="Frontend framework selection: React vs Vue",
            conflict_type="conflicting_consensus",
            severity=0.75,
            description="Different consensus on similar topic: 'TypeScript adoption' vs 'React chosen'",
        )
    ]

    # Mock timeline
    engine._trace_evolution_sync.return_value = Timeline(
        decision_id="dec-1",
        question="Should we adopt TypeScript for the frontend?",
        consensus="TypeScript adoption recommended",
        status="unanimous_consensus",
        participants=["opus@claude", "gpt4@codex"],
        rounds=[
            TimelineEntry(
                round_num=1,
                timestamp="2025-10-01T10:00:00",
                consensus="TypeScript adoption recommended",
                confidence=0.92,
                participant_positions=[
                    {"participant": "opus@claude", "option": "Yes", "confidence": 0.95},
                    {"participant": "gpt4@codex", "option": "Yes", "confidence": 0.88},
                ],
            )
        ],
        related_decisions=[
            {
                "id": "dec-3",
                "question": "Frontend framework selection",
                "similarity": 0.68,
                "consensus": "React chosen",
            }
        ],
    )

    return engine


# ============================================================================
# TEST: graph similar command
# ============================================================================


class TestGraphSimilarCommand:
    """Tests for 'graph similar' command."""

    def test_should_search_similar_decisions_when_query_provided(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test basic similar search with query parameter."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar, ["--query", "TypeScript adoption", "--limit", "5"]
                )

        assert result.exit_code == 0
        mock_query_engine._search_similar_sync.assert_called_once_with(
            "TypeScript adoption", 5, 0.7
        )

    def test_should_respect_custom_threshold_when_provided(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test that custom threshold is passed to query engine."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar,
                    ["--query", "test", "--threshold", "0.85"],
                )

        assert result.exit_code == 0
        mock_query_engine._search_similar_sync.assert_called_once_with("test", 5, 0.85)

    def test_should_respect_custom_limit_when_provided(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test that custom limit is passed to query engine."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar,
                    ["--query", "test", "--limit", "10"],
                )

        assert result.exit_code == 0
        mock_query_engine._search_similar_sync.assert_called_once_with("test", 10, 0.7)

    def test_should_output_json_format_when_format_json_specified(
        self, cli_runner, mock_storage, mock_query_engine, sample_decisions
    ):
        """Test JSON output format contains expected structure."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar,
                    ["--query", "TypeScript", "--format", "json"],
                )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "query" in output
        assert output["query"] == "TypeScript"
        assert "count" in output
        assert "results" in output
        assert len(output["results"]) == 2
        assert output["results"][0]["id"] == "dec-1"
        assert output["results"][0]["score"] == 0.92

    def test_should_output_table_format_when_format_table_specified(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test table format calls DecisionGraphExporter."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                with patch(
                    "cli.graph.DecisionGraphExporter.to_summary_table"
                ) as mock_table:
                    mock_table.return_value = "╔═══╗\n║Table║\n╚═══╝"
                    result = cli_runner.invoke(
                        similar,
                        ["--query", "test", "--format", "table"],
                    )

        assert result.exit_code == 0
        mock_table.assert_called_once()
        assert "Table" in result.output

    def test_should_output_summary_format_when_format_summary_specified(
        self, cli_runner, mock_storage, mock_query_engine, sample_decisions
    ):
        """Test summary format displays key fields."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar,
                    ["--query", "test", "--format", "summary"],
                )

        assert result.exit_code == 0
        assert "Should we adopt TypeScript" in result.output
        assert "Score: 92%" in result.output
        assert "unanimous_consensus" in result.output

    def test_should_fail_when_query_parameter_missing(self, cli_runner):
        """Test that missing --query parameter causes error."""
        result = cli_runner.invoke(similar, [])

        assert result.exit_code != 0
        assert "Missing option '--query'" in result.output

    def test_should_use_custom_database_path_when_db_option_provided(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test that custom database path is used."""
        with patch("cli.graph.DecisionGraphStorage") as mock_storage_class:
            mock_storage_class.return_value = mock_storage
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar,
                    ["--query", "test", "--db", "/custom/path.db"],
                )

        assert result.exit_code == 0
        mock_storage_class.assert_called_once_with("/custom/path.db")

    def test_should_handle_exception_and_exit_with_error(self, cli_runner):
        """Test that exceptions are caught and reported."""
        with patch("cli.graph.DecisionGraphStorage") as mock_storage_class:
            mock_storage_class.side_effect = Exception("Database connection failed")
            result = cli_runner.invoke(
                similar,
                ["--query", "test"],
            )

        assert result.exit_code == 1
        assert "Error: Database connection failed" in result.output


# ============================================================================
# TEST: graph contradictions command
# ============================================================================


class TestGraphContradictionsCommand:
    """Tests for 'graph contradictions' command."""

    def test_should_find_contradictions_when_invoked(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test basic contradiction detection."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(contradictions, [])

        assert result.exit_code == 0
        mock_query_engine._find_contradictions_sync.assert_called_once_with(None, 0.5)

    def test_should_filter_by_scope_when_scope_provided(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test scope filtering."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    contradictions,
                    ["--scope", "frontend"],
                )

        assert result.exit_code == 0
        mock_query_engine._find_contradictions_sync.assert_called_once_with(
            "frontend", 0.5
        )

    def test_should_respect_custom_threshold_when_provided(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test custom threshold parameter."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    contradictions,
                    ["--threshold", "0.8"],
                )

        assert result.exit_code == 0
        mock_query_engine._find_contradictions_sync.assert_called_once_with(None, 0.8)

    def test_should_output_json_format_when_format_json_specified(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test JSON output format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    contradictions,
                    ["--format", "json"],
                )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "count" in output
        assert output["count"] == 1
        assert "contradictions" in output
        assert len(output["contradictions"]) == 1
        assert output["contradictions"][0]["severity"] == 0.75
        assert output["contradictions"][0]["decision_id_1"] == "dec-1"

    def test_should_output_summary_format_when_format_summary_specified(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test summary output format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    contradictions,
                    ["--format", "summary"],
                )

        assert result.exit_code == 0
        assert "Found 1 contradictions" in result.output
        assert "Severity: 75%" in result.output
        assert "Should we adopt TypeScript" in result.output
        assert "Different consensus on similar topic" in result.output

    def test_should_handle_exception_and_exit_with_error(self, cli_runner):
        """Test exception handling."""
        with patch("cli.graph.DecisionGraphStorage") as mock_storage_class:
            mock_storage_class.side_effect = Exception("Database error")
            result = cli_runner.invoke(contradictions, [])

        assert result.exit_code == 1
        assert "Error: Database error" in result.output


# ============================================================================
# TEST: graph timeline command
# ============================================================================


class TestGraphTimelineCommand:
    """Tests for 'graph timeline' command."""

    def test_should_trace_timeline_when_id_provided(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test basic timeline tracing."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    timeline,
                    ["--id", "dec-1"],
                )

        assert result.exit_code == 0
        mock_query_engine._trace_evolution_sync.assert_called_once_with(
            "dec-1", include_related=False
        )

    def test_should_include_related_when_related_flag_set(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test --related flag includes related decisions."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    timeline,
                    ["--id", "dec-1", "--related"],
                )

        assert result.exit_code == 0
        mock_query_engine._trace_evolution_sync.assert_called_once_with(
            "dec-1", include_related=True
        )

    def test_should_output_json_format_when_format_json_specified(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test JSON output format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    timeline,
                    ["--id", "dec-1", "--format", "json"],
                )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["decision_id"] == "dec-1"
        assert "question" in output
        assert "consensus" in output
        assert "status" in output
        assert "participants" in output
        assert output["rounds"] == 1

    def test_should_output_summary_format_when_format_summary_specified(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test summary output format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    timeline,
                    ["--id", "dec-1", "--format", "summary"],
                )

        assert result.exit_code == 0
        assert "Decision Timeline: dec-1" in result.output
        assert "Should we adopt TypeScript" in result.output
        assert "unanimous_consensus" in result.output
        assert "opus@claude, gpt4@codex" in result.output

    def test_should_display_related_decisions_when_related_flag_and_data_present(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test related decisions are displayed."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    timeline,
                    ["--id", "dec-1", "--related"],
                )

        assert result.exit_code == 0
        assert "Related Decisions:" in result.output
        assert "Frontend framework selection" in result.output
        assert "similarity: 68%" in result.output

    def test_should_fail_when_id_parameter_missing(self, cli_runner):
        """Test missing --id parameter."""
        result = cli_runner.invoke(timeline, [])

        assert result.exit_code != 0
        assert "Missing option '--id'" in result.output

    def test_should_handle_value_error_for_nonexistent_decision(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test ValueError is caught and reported."""
        mock_query_engine._trace_evolution_sync.side_effect = ValueError(
            "Decision nonexistent-id not found"
        )

        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    timeline,
                    ["--id", "nonexistent-id"],
                )

        assert result.exit_code == 1
        assert "Error: Decision nonexistent-id not found" in result.output

    def test_should_handle_generic_exception_and_exit_with_error(self, cli_runner):
        """Test generic exception handling."""
        with patch("cli.graph.DecisionGraphStorage") as mock_storage_class:
            mock_storage_class.side_effect = Exception("Database error")
            result = cli_runner.invoke(timeline, ["--id", "dec-1"])

        assert result.exit_code == 1
        assert "Error: Database error" in result.output


# ============================================================================
# TEST: graph export command
# ============================================================================


class TestGraphExportCommand:
    """Tests for 'graph export' command."""

    def test_should_export_to_json_format_when_format_json_specified(
        self, cli_runner, mock_storage, sample_decisions
    ):
        """Test JSON export format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.DecisionGraphExporter.to_json") as mock_export:
                mock_export.return_value = '{"format": "decision_graph_json"}'
                result = cli_runner.invoke(
                    export,
                    ["--format", "json"],
                )

        assert result.exit_code == 0
        mock_export.assert_called_once_with(sample_decisions)
        assert '"format": "decision_graph_json"' in result.output

    def test_should_export_to_graphml_format_when_format_graphml_specified(
        self, cli_runner, mock_storage, sample_decisions
    ):
        """Test GraphML export format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.DecisionGraphExporter.to_graphml") as mock_export:
                mock_export.return_value = '<?xml version="1.0"?>'
                result = cli_runner.invoke(
                    export,
                    ["--format", "graphml"],
                )

        assert result.exit_code == 0
        mock_export.assert_called_once_with(sample_decisions)
        assert '<?xml version="1.0"?>' in result.output

    def test_should_export_to_dot_format_when_format_dot_specified(
        self, cli_runner, mock_storage, sample_decisions
    ):
        """Test Graphviz DOT export format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.DecisionGraphExporter.to_dot") as mock_export:
                mock_export.return_value = "digraph DecisionGraph {"
                result = cli_runner.invoke(
                    export,
                    ["--format", "dot"],
                )

        assert result.exit_code == 0
        mock_export.assert_called_once_with(sample_decisions)
        assert "digraph DecisionGraph {" in result.output

    def test_should_export_to_markdown_format_when_format_markdown_specified(
        self, cli_runner, mock_storage, sample_decisions
    ):
        """Test Markdown export format."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.DecisionGraphExporter.to_markdown") as mock_export:
                mock_export.return_value = "# Decision Graph Memory Report"
                result = cli_runner.invoke(
                    export,
                    ["--format", "markdown"],
                )

        assert result.exit_code == 0
        mock_export.assert_called_once_with(sample_decisions)
        assert "# Decision Graph Memory Report" in result.output

    def test_should_write_to_file_when_output_option_provided(
        self, cli_runner, mock_storage, sample_decisions
    ):
        """Test file output with --output option."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tf:
            temp_path = tf.name

        try:
            with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
                with patch("cli.graph.DecisionGraphExporter.to_json") as mock_export:
                    mock_export.return_value = '{"test": "data"}'
                    result = cli_runner.invoke(
                        export,
                        ["--format", "json", "--output", temp_path],
                    )

            assert result.exit_code == 0
            assert f"Exported 3 decisions to {temp_path}" in result.output

            # Verify file was written
            content = Path(temp_path).read_text()
            assert content == '{"test": "data"}'
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_should_output_to_stdout_when_no_output_option(
        self, cli_runner, mock_storage
    ):
        """Test stdout output when --output not specified."""
        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.DecisionGraphExporter.to_json") as mock_export:
                mock_export.return_value = '{"test": "stdout"}'
                result = cli_runner.invoke(
                    export,
                    ["--format", "json"],
                )

        assert result.exit_code == 0
        assert '{"test": "stdout"}' in result.output
        assert "Exported" not in result.output  # No file message

    def test_should_use_custom_database_path_when_db_option_provided(
        self, cli_runner, mock_storage
    ):
        """Test custom database path."""
        with patch("cli.graph.DecisionGraphStorage") as mock_storage_class:
            mock_storage_class.return_value = mock_storage
            with patch("cli.graph.DecisionGraphExporter.to_json") as mock_export:
                mock_export.return_value = "{}"
                result = cli_runner.invoke(
                    export,
                    ["--format", "json", "--db", "/custom/graph.db"],
                )

        assert result.exit_code == 0
        mock_storage_class.assert_called_once_with("/custom/graph.db")

    def test_should_exit_with_error_when_no_decisions_found(self, cli_runner):
        """Test error when database is empty."""
        empty_storage = Mock(spec=DecisionGraphStorage)
        empty_storage.get_all_decisions.return_value = []

        with patch("cli.graph.DecisionGraphStorage", return_value=empty_storage):
            result = cli_runner.invoke(
                export,
                ["--format", "json"],
            )

        assert result.exit_code == 1
        assert "No decisions found in graph." in result.output

    def test_should_handle_exception_and_exit_with_error(self, cli_runner):
        """Test exception handling."""
        with patch("cli.graph.DecisionGraphStorage") as mock_storage_class:
            mock_storage_class.side_effect = Exception("Database error")
            result = cli_runner.invoke(export, ["--format", "json"])

        assert result.exit_code == 1
        assert "Error: Database error" in result.output


# ============================================================================
# TEST: Error handling and edge cases
# ============================================================================


class TestErrorHandlingAndEdgeCases:
    """Tests for error conditions and edge cases."""

    def test_should_handle_missing_database_file(self, cli_runner):
        """Test graceful handling of missing database."""
        with patch("cli.graph.DecisionGraphStorage") as mock_storage_class:
            mock_storage_class.side_effect = FileNotFoundError(
                "Database file not found"
            )
            result = cli_runner.invoke(
                similar,
                ["--query", "test"],
            )

        assert result.exit_code == 1
        assert "Error:" in result.output

    def test_should_handle_invalid_format_choice(self, cli_runner):
        """Test that invalid format choices are rejected."""
        result = cli_runner.invoke(
            similar,
            ["--query", "test", "--format", "invalid"],
        )

        assert result.exit_code != 0
        assert "Invalid value for '--format'" in result.output

    def test_should_handle_invalid_threshold_type(self, cli_runner):
        """Test that non-float threshold is rejected."""
        result = cli_runner.invoke(
            similar,
            ["--query", "test", "--threshold", "not-a-number"],
        )

        assert result.exit_code != 0
        assert "Invalid value for '--threshold'" in result.output

    def test_should_handle_invalid_limit_type(self, cli_runner):
        """Test that non-integer limit is rejected."""
        result = cli_runner.invoke(
            similar,
            ["--query", "test", "--limit", "not-a-number"],
        )

        assert result.exit_code != 0
        assert "Invalid value for '--limit'" in result.output

    def test_should_handle_empty_query_string(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test handling of empty query string."""
        mock_query_engine._search_similar_sync.return_value = []

        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar,
                    ["--query", ""],
                )

        assert result.exit_code == 0  # Should succeed but return no results

    def test_should_handle_empty_results_gracefully(
        self, cli_runner, mock_storage, mock_query_engine
    ):
        """Test display when no results found."""
        mock_query_engine._search_similar_sync.return_value = []

        with patch("cli.graph.DecisionGraphStorage", return_value=mock_storage):
            with patch("cli.graph.QueryEngine", return_value=mock_query_engine):
                result = cli_runner.invoke(
                    similar,
                    ["--query", "nonexistent", "--format", "json"],
                )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["count"] == 0
        assert output["results"] == []


# ============================================================================
# TEST: Help text and documentation
# ============================================================================


class TestHelpTextAndDocumentation:
    """Tests for CLI help text and documentation."""

    def test_should_display_help_for_graph_group(self, cli_runner):
        """Test graph group help text."""
        result = cli_runner.invoke(graph, ["--help"])

        assert result.exit_code == 0
        assert "Decision graph memory commands." in result.output

    def test_should_display_help_for_similar_command(self, cli_runner):
        """Test similar command help text."""
        result = cli_runner.invoke(similar, ["--help"])

        assert result.exit_code == 0
        assert "Search for similar past deliberations" in result.output
        assert "--query" in result.output
        assert "--limit" in result.output
        assert "--threshold" in result.output
        assert "--format" in result.output

    def test_should_display_help_for_contradictions_command(self, cli_runner):
        """Test contradictions command help text."""
        result = cli_runner.invoke(contradictions, ["--help"])

        assert result.exit_code == 0
        assert "Find contradictions in decision history" in result.output
        assert "--scope" in result.output
        assert "--threshold" in result.output

    def test_should_display_help_for_timeline_command(self, cli_runner):
        """Test timeline command help text."""
        result = cli_runner.invoke(timeline, ["--help"])

        assert result.exit_code == 0
        assert "Trace the evolution of a decision" in result.output
        assert "--id" in result.output
        assert "--related" in result.output

    def test_should_display_help_for_export_command(self, cli_runner):
        """Test export command help text."""
        result = cli_runner.invoke(export, ["--help"])

        assert result.exit_code == 0
        assert "Export decision graph to external formats" in result.output
        assert "--format" in result.output
        assert "--output" in result.output
        assert "json" in result.output
        assert "graphml" in result.output
        assert "dot" in result.output
        assert "markdown" in result.output
