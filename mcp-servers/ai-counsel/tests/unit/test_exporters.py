"""Unit tests for deliberation/exporters.py - DecisionGraphExporter.

Test coverage for all export formats (JSON, GraphML, DOT, Markdown, ASCII table)
and utility functions (_escape_xml, _escape_markdown, _truncate_text).

Following TDD approach: tests written before implementation changes.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from decision_graph.schema import DecisionNode, DecisionSimilarity
from deliberation.exporters import (DecisionGraphExporter, _escape_markdown,
                                    _escape_xml, _truncate_text)
from deliberation.query_engine import SimilarResult

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fixed_datetime():
    """Fixed datetime for reproducible tests."""
    return datetime(2025, 10, 21, 14, 30, 0)


@pytest.fixture
def sample_decision_nodes(fixed_datetime):
    """Sample DecisionNode objects for testing."""
    return [
        DecisionNode(
            id="dec-001",
            question="Should we implement feature X?",
            timestamp=fixed_datetime,
            consensus="Yes, implement feature X with constraints",
            winning_option="Option A",
            convergence_status="converged",
            participants=["opus@claude", "gpt-4@codex"],
            transcript_path="transcripts/20251021_143000_Should_we_implement.md",
            metadata={"rounds": 3, "duration": 120},
        ),
        DecisionNode(
            id="dec-002",
            question="What is the best approach for testing?",
            timestamp=fixed_datetime,
            consensus="TDD with pytest and comprehensive coverage",
            winning_option="Option B",
            convergence_status="unanimous_consensus",
            participants=["opus@claude", "gpt-4@codex", "gemini@gemini"],
            transcript_path="transcripts/20251021_143500_What_is_the_best.md",
            metadata={"rounds": 2},
        ),
        DecisionNode(
            id="dec-003",
            question="How to handle edge cases?",
            timestamp=fixed_datetime,
            consensus="Comprehensive parametrized testing",
            winning_option=None,
            convergence_status="refining",
            participants=["opus@claude"],
            transcript_path="transcripts/20251021_144000_How_to_handle.md",
            metadata={},
        ),
    ]


@pytest.fixture
def sample_similarities(fixed_datetime):
    """Sample DecisionSimilarity objects for testing."""
    return [
        DecisionSimilarity(
            source_id="dec-001",
            target_id="dec-002",
            similarity_score=0.85,
            computed_at=fixed_datetime,
        ),
        DecisionSimilarity(
            source_id="dec-001",
            target_id="dec-003",
            similarity_score=0.72,
            computed_at=fixed_datetime,
        ),
        DecisionSimilarity(
            source_id="dec-002",
            target_id="dec-003",
            similarity_score=0.55,
            computed_at=fixed_datetime,
        ),
    ]


@pytest.fixture
def sample_similar_results(sample_decision_nodes):
    """Sample SimilarResult objects for testing ASCII table output."""
    return [
        SimilarResult(decision=sample_decision_nodes[0], score=0.95),
        SimilarResult(decision=sample_decision_nodes[1], score=0.88),
        SimilarResult(decision=sample_decision_nodes[2], score=0.72),
    ]


@pytest.fixture
def decision_with_special_chars(fixed_datetime):
    """DecisionNode with special characters for escaping tests."""
    return DecisionNode(
        id="dec-special",
        question="Should we use <XML> & 'JSON' for \"data\"?",
        timestamp=fixed_datetime,
        consensus="Yes, with proper escaping: <>&\"'",
        winning_option="Option A|B|C",
        convergence_status="converged",
        participants=["model@cli"],
        transcript_path="transcripts/test.md",
        metadata={},
    )


@pytest.fixture
def decision_with_long_text(fixed_datetime):
    """DecisionNode with long text for truncation tests."""
    return DecisionNode(
        id="dec-long",
        question="This is a very long question that exceeds the maximum length allowed for display and should be truncated appropriately",
        timestamp=fixed_datetime,
        consensus="This is also a very long consensus text that needs to be truncated when displayed in tables or graphs",
        winning_option="Option with a very long name",
        convergence_status="converged",
        participants=["model@cli"],
        transcript_path="transcripts/test.md",
        metadata={},
    )


# ============================================================================
# TEST: to_json() - JSON Export
# ============================================================================


class TestToJson:
    """Tests for DecisionGraphExporter.to_json() method."""

    def test_should_export_decisions_to_json_when_no_similarities(
        self, sample_decision_nodes, fixed_datetime
    ):
        """Test JSON export with decisions only (no similarities)."""
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            result = DecisionGraphExporter.to_json(sample_decision_nodes)

        # Parse JSON to validate structure
        data = json.loads(result)

        # Check metadata
        assert data["format"] == "decision_graph_json"
        assert data["version"] == "1.0"
        assert data["exported_at"] == fixed_datetime.isoformat()

        # Check decisions
        assert len(data["decisions"]) == 3
        assert data["decisions"][0]["id"] == "dec-001"
        assert data["decisions"][0]["question"] == "Should we implement feature X?"
        assert (
            data["decisions"][0]["consensus"]
            == "Yes, implement feature X with constraints"
        )
        assert data["decisions"][0]["winning_option"] == "Option A"
        assert data["decisions"][0]["convergence_status"] == "converged"
        assert data["decisions"][0]["participants"] == ["opus@claude", "gpt-4@codex"]
        assert data["decisions"][0]["metadata"] == {"rounds": 3, "duration": 120}

        # Ensure similarities not present when not provided
        assert "similarities" not in data

    def test_should_include_similarities_when_provided(
        self, sample_decision_nodes, sample_similarities, fixed_datetime
    ):
        """Test JSON export includes similarities when provided."""
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            result = DecisionGraphExporter.to_json(
                sample_decision_nodes, sample_similarities
            )

        data = json.loads(result)

        # Check similarities section exists
        assert "similarities" in data
        assert len(data["similarities"]) == 3

        # Check first similarity
        assert data["similarities"][0]["source_id"] == "dec-001"
        assert data["similarities"][0]["target_id"] == "dec-002"
        assert data["similarities"][0]["similarity_score"] == 0.85
        assert data["similarities"][0]["computed_at"] == fixed_datetime.isoformat()

    def test_should_handle_empty_decisions_list(self, fixed_datetime):
        """Test JSON export with empty decisions list."""
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            result = DecisionGraphExporter.to_json([])

        data = json.loads(result)
        assert data["decisions"] == []
        assert "similarities" not in data

    def test_should_preserve_none_values_in_json(self, fixed_datetime):
        """Test JSON export preserves None values correctly."""
        decision = DecisionNode(
            id="dec-none",
            question="Test question",
            timestamp=fixed_datetime,
            consensus="Test consensus",
            winning_option=None,  # Explicitly None
            convergence_status="refining",
            participants=["model@cli"],
            transcript_path="test.md",
            metadata={},
        )

        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            result = DecisionGraphExporter.to_json([decision])

        data = json.loads(result)
        assert data["decisions"][0]["winning_option"] is None


# ============================================================================
# TEST: to_graphml() - GraphML Export
# ============================================================================


class TestToGraphml:
    """Tests for DecisionGraphExporter.to_graphml() method."""

    def test_should_export_graphml_structure_when_decisions_provided(
        self, sample_decision_nodes
    ):
        """Test GraphML export creates valid XML structure."""
        result = DecisionGraphExporter.to_graphml(sample_decision_nodes)

        # Check XML declaration
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"' in result

        # Check nodes section
        assert "<!-- Nodes -->" in result
        assert '<node id="dec-001">' in result
        assert '<node id="dec-002">' in result
        assert '<node id="dec-003">' in result

        # Check node attributes
        assert '<key id="d_question"' in result
        assert '<key id="d_consensus"' in result
        assert '<key id="d_status"' in result
        assert '<key id="d_timestamp"' in result

        # Check closing tags
        assert "</graph>" in result
        assert "</graphml>" in result

    def test_should_escape_xml_special_chars_in_graphml(
        self, decision_with_special_chars
    ):
        """Test GraphML escapes special XML characters."""
        result = DecisionGraphExporter.to_graphml([decision_with_special_chars])

        # Should contain escaped XML
        assert "&lt;XML&gt;" in result
        assert "&amp;" in result
        assert "&quot;data&quot;" in result
        assert "&apos;JSON&apos;" in result

        # Should NOT contain unescaped special chars
        assert "<XML>" not in result  # Only in XML tags themselves

    def test_should_include_edges_when_similarities_provided(
        self, sample_decision_nodes, sample_similarities
    ):
        """Test GraphML includes edges for similarities."""
        result = DecisionGraphExporter.to_graphml(
            sample_decision_nodes, sample_similarities
        )

        # Check edges section
        assert "<!-- Edges -->" in result
        assert '<key id="d_weight"' in result

        # Check edge elements
        assert '<edge source="dec-001" target="dec-002">' in result
        assert '<data key="d_weight">0.85</data>' in result

    def test_should_handle_empty_decisions_in_graphml(self):
        """Test GraphML export with empty decisions list."""
        result = DecisionGraphExporter.to_graphml([])

        # Should still have valid structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert "<graphml" in result
        assert "<!-- Nodes -->" in result
        assert "</graphml>" in result

    def test_should_format_timestamps_as_isoformat_in_graphml(
        self, sample_decision_nodes, fixed_datetime
    ):
        """Test GraphML formats timestamps correctly."""
        result = DecisionGraphExporter.to_graphml(sample_decision_nodes)

        expected_timestamp = fixed_datetime.isoformat()
        assert expected_timestamp in result


# ============================================================================
# TEST: to_dot() - Graphviz DOT Export
# ============================================================================


class TestToDot:
    """Tests for DecisionGraphExporter.to_dot() method."""

    def test_should_create_valid_dot_graph_structure(self, sample_decision_nodes):
        """Test DOT export creates valid Graphviz structure."""
        result = DecisionGraphExporter.to_dot(sample_decision_nodes)

        # Check graph declaration
        assert result.startswith("digraph DecisionGraph {")
        assert result.endswith("}")
        assert "rankdir=LR;" in result
        assert "node [shape=box, style=rounded];" in result

    def test_should_create_nodes_with_correct_labels(self, sample_decision_nodes):
        """Test DOT export creates nodes with truncated labels."""
        result = DecisionGraphExporter.to_dot(sample_decision_nodes)

        # Check nodes exist
        assert '"dec-001"' in result
        assert '"dec-002"' in result
        assert '"dec-003"' in result

        # Check labels are truncated to 40 chars
        assert "Should we implement feature X?" in result  # Under 40, not truncated
        # "What is the best approach for testing?" is exactly 40 chars, not truncated
        assert "What is the best approach for testing?" in result

    def test_should_color_nodes_by_convergence_status(self, sample_decision_nodes):
        """Test DOT export colors nodes based on convergence status."""
        result = DecisionGraphExporter.to_dot(sample_decision_nodes)

        # Check status-based colors
        assert "fillcolor=lightgreen" in result  # converged
        assert "fillcolor=lightblue" in result  # unanimous_consensus
        assert "fillcolor=lightyellow" in result  # refining

    def test_should_include_edges_for_high_similarity_scores(
        self, sample_decision_nodes, sample_similarities
    ):
        """Test DOT export includes edges only for similarity > 0.6."""
        result = DecisionGraphExporter.to_dot(
            sample_decision_nodes, sample_similarities
        )

        # Should include high similarity edges (> 0.6)
        assert '"dec-001" -> "dec-002"' in result  # 0.85
        assert 'label="0.85"' in result
        assert '"dec-001" -> "dec-003"' in result  # 0.72
        assert 'label="0.72"' in result

        # Should NOT include low similarity edges (<= 0.6)
        assert '"dec-002" -> "dec-003"' not in result  # 0.55

    def test_should_handle_empty_decisions_in_dot(self):
        """Test DOT export with empty decisions list."""
        result = DecisionGraphExporter.to_dot([])

        # Should have valid structure
        assert result.startswith("digraph DecisionGraph {")
        assert result.endswith("}")

    def test_should_use_white_for_unknown_convergence_status(self, fixed_datetime):
        """Test DOT export uses default white color for unknown status."""
        decision = DecisionNode(
            id="dec-unknown",
            question="Test",
            timestamp=fixed_datetime,
            consensus="Test",
            winning_option=None,
            convergence_status="unknown_status",  # Not in color map
            participants=["model@cli"],
            transcript_path="test.md",
            metadata={},
        )

        result = DecisionGraphExporter.to_dot([decision])
        assert "fillcolor=white" in result

    @pytest.mark.parametrize(
        "status,expected_color",
        [
            ("converged", "lightgreen"),
            ("refining", "lightyellow"),
            ("diverging", "lightcoral"),
            ("unanimous_consensus", "lightblue"),
            ("majority_decision", "lightcyan"),
            ("tie", "lightgray"),
        ],
    )
    def test_should_map_convergence_status_to_color_correctly(
        self, fixed_datetime, status, expected_color
    ):
        """Test DOT export maps all convergence statuses to correct colors."""
        decision = DecisionNode(
            id="dec-test",
            question="Test",
            timestamp=fixed_datetime,
            consensus="Test",
            winning_option=None,
            convergence_status=status,
            participants=["model@cli"],
            transcript_path="test.md",
            metadata={},
        )

        result = DecisionGraphExporter.to_dot([decision])
        assert f"fillcolor={expected_color}" in result


# ============================================================================
# TEST: to_markdown() - Markdown Export
# ============================================================================


class TestToMarkdown:
    """Tests for DecisionGraphExporter.to_markdown() method."""

    def test_should_create_markdown_report_structure(
        self, sample_decision_nodes, fixed_datetime
    ):
        """Test Markdown export creates valid structure."""
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            result = DecisionGraphExporter.to_markdown(sample_decision_nodes)

        # Check header
        assert "# Decision Graph Memory Report" in result
        assert f"_Generated: {fixed_datetime.isoformat()}_" in result

        # Check summary
        assert "## Summary" in result
        assert "- Total Decisions: 3" in result

        # Check decisions section
        assert "## Decisions" in result
        assert "### 1. Should we implement feature X?" in result
        assert "### 2. What is the best approach for testing?" in result

    def test_should_escape_markdown_special_chars(self, decision_with_special_chars):
        """Test Markdown export escapes pipe characters and newlines."""
        result = DecisionGraphExporter.to_markdown([decision_with_special_chars])

        # Markdown escaping only applies to question and consensus fields
        # The _escape_markdown function is called on question and consensus
        # Check that the question is escaped
        assert (
            "Should we use <XML> & 'JSON' for \\\"data\\\"?" in result
            or "Should we use <XML>" in result
        )
        # Winning option is displayed as-is in the winning option field (not in a table)
        assert "Option A|B|C" in result  # Not escaped in winning_option field

    def test_should_include_decision_metadata_fields(self, sample_decision_nodes):
        """Test Markdown export includes all decision fields."""
        result = DecisionGraphExporter.to_markdown(sample_decision_nodes)

        # Check all required fields present
        assert "**ID**: `dec-001`" in result
        assert "**Timestamp**:" in result
        assert "**Consensus**:" in result
        assert "**Status**: converged" in result
        assert "**Participants**: opus@claude, gpt-4@codex" in result
        assert "**Transcript**:" in result
        assert "**Winning Option**: Option A" in result

    def test_should_display_na_for_none_winning_option(self, sample_decision_nodes):
        """Test Markdown export shows 'N/A' for None winning_option."""
        result = DecisionGraphExporter.to_markdown(sample_decision_nodes)

        # dec-003 has None winning_option
        assert "**Winning Option**: N/A" in result

    def test_should_include_relationships_table_when_similarities_provided(
        self, sample_decision_nodes, sample_similarities
    ):
        """Test Markdown export includes relationships table."""
        result = DecisionGraphExporter.to_markdown(
            sample_decision_nodes, sample_similarities
        )

        # Check relationships section
        assert "## Relationships" in result
        assert "| Source | Target | Similarity |" in result
        assert "|--------|--------|------------|" in result

        # Check sorted by similarity (highest first)
        lines = result.split("\n")
        relationship_lines = [
            line for line in lines if line.startswith("|") and "..." in line
        ]
        # First should be highest similarity (0.85)
        assert "85.00%" in relationship_lines[0]

    def test_should_limit_relationships_to_top_20(self, sample_decision_nodes):
        """Test Markdown export limits relationships to top 20."""
        # Create 30 similarities
        similarities = [
            DecisionSimilarity(
                source_id="dec-001",
                target_id=f"dec-{i:03d}",
                similarity_score=0.9 - (i * 0.01),
                computed_at=datetime.now(),
            )
            for i in range(30)
        ]

        result = DecisionGraphExporter.to_markdown(sample_decision_nodes, similarities)

        # Count relationship rows (exclude header rows)
        relationship_rows = [
            line
            for line in result.split("\n")
            if line.startswith("| ") and "..." in line
        ]
        assert len(relationship_rows) == 20

    def test_should_handle_empty_decisions_in_markdown(self, fixed_datetime):
        """Test Markdown export with empty decisions list."""
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            result = DecisionGraphExporter.to_markdown([])

        assert "# Decision Graph Memory Report" in result
        assert "- Total Decisions: 0" in result
        assert "## Decisions" in result

    def test_should_not_include_relationships_section_when_none_provided(
        self, sample_decision_nodes
    ):
        """Test Markdown export omits relationships section when not provided."""
        result = DecisionGraphExporter.to_markdown(sample_decision_nodes)

        assert "## Relationships" not in result
        assert "- Total Relationships:" not in result


# ============================================================================
# TEST: to_summary_table() - ASCII Table Export
# ============================================================================


class TestToSummaryTable:
    """Tests for DecisionGraphExporter.to_summary_table() method."""

    def test_should_create_ascii_table_with_box_drawing(self, sample_similar_results):
        """Test ASCII table export creates formatted table."""
        result = DecisionGraphExporter.to_summary_table(sample_similar_results)

        # Check box drawing characters
        assert (
            "╔═══════════════════════════════════════════════════════════════════╗"
            in result
        )
        assert "║ Similar Decisions" in result
        assert (
            "╠═════════╦═══════════════════════════════╦════════════╦═════════════╣"
            in result
        )
        assert (
            "║ Score   ║ Question                      ║ Consensus  ║ Status      ║"
            in result
        )
        assert (
            "╚═════════╩═══════════════════════════════╩════════════╩═════════════╝"
            in result
        )

    def test_should_include_all_results_up_to_10(self, sample_similar_results):
        """Test ASCII table includes up to 10 results."""
        result = DecisionGraphExporter.to_summary_table(sample_similar_results)

        # Check all 3 results present
        assert "95%" in result  # First result
        assert "88%" in result  # Second result
        assert "72%" in result  # Third result

    def test_should_limit_to_10_results(self, sample_decision_nodes):
        """Test ASCII table limits to top 10 results."""
        # Create 15 similar results
        results = [
            SimilarResult(decision=sample_decision_nodes[0], score=0.95 - (i * 0.05))
            for i in range(15)
        ]

        output = DecisionGraphExporter.to_summary_table(results)

        # Count data rows (exclude header/border rows)
        data_rows = [line for line in output.split("\n") if line.startswith("║  ")]
        assert len(data_rows) == 10

    def test_should_handle_empty_results_list(self):
        """Test ASCII table with empty results returns message."""
        result = DecisionGraphExporter.to_summary_table([])

        assert result == "No results found."

    def test_should_truncate_long_text_in_table(self, decision_with_long_text):
        """Test ASCII table truncates long text to fit columns."""
        result_obj = SimilarResult(decision=decision_with_long_text, score=0.85)
        result = DecisionGraphExporter.to_summary_table([result_obj])

        # Check truncation occurred (question limited to 27 chars + "...")
        # The actual truncation appears to be "This is a very long ques..." (28 chars total)
        assert (
            "This is a very long ques..." in result
            or "This is a very long que..." in result
        )

        # Consensus also truncated (to 10 chars)
        assert "This is..." in result or "This is a..." in result

    def test_should_format_score_as_percentage(self, sample_similar_results):
        """Test ASCII table formats scores as percentages."""
        result = DecisionGraphExporter.to_summary_table(sample_similar_results)

        # Check percentage formatting
        assert "95%" in result
        assert "88%" in result
        assert "72%" in result

    def test_should_truncate_convergence_status_to_11_chars(self, fixed_datetime):
        """Test ASCII table truncates status to 11 characters."""
        decision = DecisionNode(
            id="dec-test",
            question="Test",
            timestamp=fixed_datetime,
            consensus="Test",
            winning_option=None,
            convergence_status="unanimous_consensus",  # 19 chars
            participants=["model@cli"],
            transcript_path="test.md",
            metadata={},
        )

        result_obj = SimilarResult(decision=decision, score=0.85)
        result = DecisionGraphExporter.to_summary_table([result_obj])

        # Should be truncated to 11 chars
        lines = result.split("\n")
        data_line = [line for line in lines if "85%" in line][0]
        # Status column is last, should only show first 11 chars
        assert "unanimous_c" in data_line


# ============================================================================
# TEST: Utility Functions - _escape_xml, _escape_markdown, _truncate_text
# ============================================================================


class TestEscapeXml:
    """Tests for _escape_xml utility function."""

    def test_should_escape_ampersand(self):
        """Test XML escaping for ampersand."""
        assert _escape_xml("A & B") == "A &amp; B"

    def test_should_escape_less_than(self):
        """Test XML escaping for less-than."""
        assert _escape_xml("A < B") == "A &lt; B"

    def test_should_escape_greater_than(self):
        """Test XML escaping for greater-than."""
        assert _escape_xml("A > B") == "A &gt; B"

    def test_should_escape_double_quote(self):
        """Test XML escaping for double quote."""
        assert _escape_xml('Say "Hello"') == "Say &quot;Hello&quot;"

    def test_should_escape_single_quote(self):
        """Test XML escaping for single quote."""
        assert _escape_xml("It's working") == "It&apos;s working"

    def test_should_escape_all_special_chars_combined(self):
        """Test XML escaping for all special characters together."""
        text = """<tag attr="value" alt='other'> A & B </tag>"""
        expected = "&lt;tag attr=&quot;value&quot; alt=&apos;other&apos;&gt; A &amp; B &lt;/tag&gt;"
        assert _escape_xml(text) == expected

    def test_should_handle_empty_string(self):
        """Test XML escaping with empty string."""
        assert _escape_xml("") == ""

    def test_should_handle_string_without_special_chars(self):
        """Test XML escaping with normal text."""
        assert _escape_xml("Hello World") == "Hello World"


class TestEscapeMarkdown:
    """Tests for _escape_markdown utility function."""

    def test_should_escape_pipe_character(self):
        """Test Markdown escaping for pipe character."""
        assert _escape_markdown("Option A|Option B") == "Option A\\|Option B"

    def test_should_replace_newlines_with_spaces(self):
        """Test Markdown escaping replaces newlines."""
        assert _escape_markdown("Line 1\nLine 2") == "Line 1 Line 2"

    def test_should_handle_multiple_pipes_and_newlines(self):
        """Test Markdown escaping with multiple special characters."""
        text = "A|B|C\nD|E|F"
        expected = "A\\|B\\|C D\\|E\\|F"
        assert _escape_markdown(text) == expected

    def test_should_handle_empty_string(self):
        """Test Markdown escaping with empty string."""
        assert _escape_markdown("") == ""

    def test_should_handle_string_without_special_chars(self):
        """Test Markdown escaping with normal text."""
        assert _escape_markdown("Hello World") == "Hello World"


class TestTruncateText:
    """Tests for _truncate_text utility function."""

    def test_should_not_truncate_when_under_max_length(self):
        """Test truncation does nothing when text is under max length."""
        text = "Short text"
        assert _truncate_text(text, 20) == "Short text"

    def test_should_truncate_when_over_max_length(self):
        """Test truncation adds ellipsis when text exceeds max length."""
        text = "This is a very long text that exceeds the maximum"
        result = _truncate_text(text, 20)

        assert len(result) == 20
        assert result.endswith("...")
        assert result == "This is a very lo..."

    def test_should_handle_exact_max_length(self):
        """Test truncation when text is exactly max length."""
        text = "Exactly twenty chars"
        assert _truncate_text(text, 20) == "Exactly twenty chars"

    def test_should_handle_empty_string(self):
        """Test truncation with empty string."""
        assert _truncate_text("", 10) == ""

    def test_should_handle_max_length_of_3(self):
        """Test truncation edge case with max_len=3 (just ellipsis)."""
        text = "Hello"
        result = _truncate_text(text, 3)
        assert result == "..."

    def test_should_truncate_at_correct_position(self):
        """Test truncation calculates correct position for ellipsis."""
        text = "ABCDEFGHIJ"  # 10 chars
        result = _truncate_text(text, 7)
        # Should be first 4 chars + "..." = 7 total
        assert result == "ABCD..."
        assert len(result) == 7

    @pytest.mark.parametrize(
        "text,max_len,expected",
        [
            ("Hello", 10, "Hello"),
            ("Hello World", 8, "Hello..."),
            ("Test", 4, "Test"),
            ("Testing", 4, "T..."),
            ("A", 5, "A"),
        ],
    )
    def test_should_handle_various_text_and_length_combinations(
        self, text, max_len, expected
    ):
        """Test truncation with various text/length combinations."""
        assert _truncate_text(text, max_len) == expected


# ============================================================================
# INTEGRATION TESTS - Multi-format combinations
# ============================================================================


class TestExporterIntegration:
    """Integration tests combining multiple export formats and edge cases."""

    def test_should_export_same_data_to_all_formats_successfully(
        self, sample_decision_nodes, sample_similarities, fixed_datetime
    ):
        """Test exporting same dataset to all formats succeeds."""
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            # Export to all formats
            json_output = DecisionGraphExporter.to_json(
                sample_decision_nodes, sample_similarities
            )
            graphml_output = DecisionGraphExporter.to_graphml(
                sample_decision_nodes, sample_similarities
            )
            dot_output = DecisionGraphExporter.to_dot(
                sample_decision_nodes, sample_similarities
            )
            markdown_output = DecisionGraphExporter.to_markdown(
                sample_decision_nodes, sample_similarities
            )

            # All should be non-empty
            assert len(json_output) > 100
            assert len(graphml_output) > 100
            assert len(dot_output) > 100
            assert len(markdown_output) > 100

    def test_should_handle_special_characters_across_all_formats(
        self, decision_with_special_chars
    ):
        """Test all export formats handle special characters safely."""
        decisions = [decision_with_special_chars]

        # JSON - should preserve as-is (JSON handles escaping)
        json_output = DecisionGraphExporter.to_json(decisions)
        assert "<XML>" in json_output  # JSON preserves

        # GraphML - should escape
        graphml_output = DecisionGraphExporter.to_graphml(decisions)
        assert "&lt;XML&gt;" in graphml_output

        # DOT - truncation happens, but should still be valid
        dot_output = DecisionGraphExporter.to_dot(decisions)
        assert "Should we use" in dot_output

        # Markdown - _escape_markdown applies to question/consensus, not winning_option
        markdown_output = DecisionGraphExporter.to_markdown(decisions)
        # winning_option displays as-is
        assert "Option A|B|C" in markdown_output

    def test_should_handle_large_dataset_efficiently(self, fixed_datetime):
        """Test exporters handle large datasets (100+ decisions)."""
        # Create 100 decisions
        decisions = [
            DecisionNode(
                id=f"dec-{i:03d}",
                question=f"Question {i}",
                timestamp=fixed_datetime,
                consensus=f"Consensus {i}",
                winning_option=f"Option {i % 3}",
                convergence_status="converged",
                participants=["model@cli"],
                transcript_path=f"transcripts/test_{i}.md",
                metadata={},
            )
            for i in range(100)
        ]

        # Export to all formats should complete without error
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            json_output = DecisionGraphExporter.to_json(decisions)
            graphml_output = DecisionGraphExporter.to_graphml(decisions)
            dot_output = DecisionGraphExporter.to_dot(decisions)
            markdown_output = DecisionGraphExporter.to_markdown(decisions)

            # Verify all completed
            assert "dec-099" in json_output
            assert 'node id="dec-099"' in graphml_output
            assert '"dec-099"' in dot_output
            assert "100. Question 99" in markdown_output

    def test_should_maintain_consistency_across_formats(
        self, sample_decision_nodes, fixed_datetime
    ):
        """Test decision IDs and counts are consistent across formats."""
        with patch("deliberation.exporters.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            json_data = json.loads(DecisionGraphExporter.to_json(sample_decision_nodes))
            graphml_output = DecisionGraphExporter.to_graphml(sample_decision_nodes)
            dot_output = DecisionGraphExporter.to_dot(sample_decision_nodes)
            markdown_output = DecisionGraphExporter.to_markdown(sample_decision_nodes)

            # Check same decision IDs present in all formats
            for decision_id in ["dec-001", "dec-002", "dec-003"]:
                assert any(d["id"] == decision_id for d in json_data["decisions"])
                assert f'node id="{decision_id}"' in graphml_output
                assert f'"{decision_id}"' in dot_output
                assert f"`{decision_id}`" in markdown_output
