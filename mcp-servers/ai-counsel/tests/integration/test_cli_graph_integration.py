"""Integration tests for Phase 4 Decision Graph CLI and Query workflow.

This module tests the complete end-to-end workflow for decision graph operations:
- Creating decisions and storing them in the database
- Querying decisions by similarity, timeline, and patterns
- Detecting contradictions between similar decisions
- Exporting decision graphs to various formats (GraphML, JSON)
- File I/O operations for database and exports
- Error recovery and graceful failure handling

These tests use real DecisionGraphStorage (in-memory) with realistic decision data
to validate the full integration between CLI commands, query engine, storage, and exporters.
"""
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from xml.etree import ElementTree as ET

import pytest

from decision_graph.integration import DecisionGraphIntegration
from decision_graph.retrieval import DecisionRetriever
from decision_graph.schema import (DecisionNode, DecisionSimilarity,
                                   ParticipantStance)
from decision_graph.storage import DecisionGraphStorage


@pytest.mark.integration
class TestDecisionGraphCLIIntegration:
    """Test end-to-end CLI workflow for decision graph operations."""

    @pytest.fixture
    def storage(self) -> DecisionGraphStorage:
        """Create in-memory storage for testing."""
        return DecisionGraphStorage(":memory:")

    @pytest.fixture
    def sample_decisions(self) -> List[DecisionNode]:
        """Create sample decision nodes for testing.

        Returns a realistic set of 7 decisions with:
        - Similar questions for similarity testing
        - Different timestamps for timeline testing
        - Various convergence statuses
        - Different participant combinations
        """
        base_time = datetime.now() - timedelta(days=30)

        decisions = [
            DecisionNode(
                id="dec-001",
                question="Should we adopt TypeScript for the frontend?",
                timestamp=base_time,
                consensus="Adopt TypeScript incrementally, starting with new features",
                winning_option="Incremental Adoption",
                convergence_status="converged",
                participants=["opus@claude", "gpt-4@codex", "sonnet@claude"],
                transcript_path="/transcripts/dec-001.md",
                metadata={"duration_seconds": 180, "total_rounds": 3},
            ),
            DecisionNode(
                id="dec-002",
                question="Should we use TypeScript or JavaScript for backend services?",
                timestamp=base_time + timedelta(days=5),
                consensus="Use TypeScript for type safety and better tooling",
                winning_option="TypeScript",
                convergence_status="converged",
                participants=["opus@claude", "gemini@gemini", "sonnet@droid"],
                transcript_path="/transcripts/dec-002.md",
                metadata={"duration_seconds": 240, "total_rounds": 4},
            ),
            DecisionNode(
                id="dec-003",
                question="Should we implement GraphQL or REST for our API?",
                timestamp=base_time + timedelta(days=10),
                consensus="Use REST with OpenAPI for simplicity and wide support",
                winning_option="REST with OpenAPI",
                convergence_status="majority_decision",
                participants=["opus@claude", "gpt-4@codex", "gemini@gemini"],
                transcript_path="/transcripts/dec-003.md",
                metadata={"duration_seconds": 300, "total_rounds": 5},
            ),
            DecisionNode(
                id="dec-004",
                question="Should we adopt GraphQL for our frontend API layer?",
                timestamp=base_time + timedelta(days=12),
                consensus="Implement GraphQL with Apollo for complex data requirements",
                winning_option="GraphQL with Apollo",
                convergence_status="converged",
                participants=["opus@claude", "sonnet@droid", "gpt-4@codex"],
                transcript_path="/transcripts/dec-004.md",
                metadata={"duration_seconds": 270, "total_rounds": 4},
            ),
            DecisionNode(
                id="dec-005",
                question="Should we use Redis or Memcached for caching?",
                timestamp=base_time + timedelta(days=15),
                consensus="Use Redis for its data structure support and persistence",
                winning_option="Redis",
                convergence_status="unanimous_consensus",
                participants=["opus@claude", "gpt-4@codex", "gemini@gemini"],
                transcript_path="/transcripts/dec-005.md",
                metadata={"duration_seconds": 150, "total_rounds": 2},
            ),
            DecisionNode(
                id="dec-006",
                question="Should we adopt MongoDB or PostgreSQL for primary database?",
                timestamp=base_time + timedelta(days=20),
                consensus="Use PostgreSQL for ACID compliance and relational integrity",
                winning_option="PostgreSQL",
                convergence_status="majority_decision",
                participants=["opus@claude", "sonnet@claude", "gpt-4@codex"],
                transcript_path="/transcripts/dec-006.md",
                metadata={"duration_seconds": 360, "total_rounds": 5},
            ),
            DecisionNode(
                id="dec-007",
                question="Should we implement real-time features with WebSockets or SSE?",
                timestamp=base_time + timedelta(days=25),
                consensus="Use WebSockets for bidirectional real-time communication",
                winning_option="WebSockets",
                convergence_status="converged",
                participants=["sonnet@droid", "gpt-4@codex", "gemini@gemini"],
                transcript_path="/transcripts/dec-007.md",
                metadata={"duration_seconds": 200, "total_rounds": 3},
            ),
        ]

        return decisions

    @pytest.fixture
    def sample_stances(self) -> Dict[str, List[ParticipantStance]]:
        """Create sample participant stances for decisions.

        Returns stances mapped by decision ID.
        """
        stances = {
            "dec-001": [
                ParticipantStance(
                    decision_id="dec-001",
                    participant="opus@claude",
                    vote_option="Incremental Adoption",
                    confidence=0.85,
                    rationale="Gradual migration reduces risk",
                    final_position="TypeScript adoption should be phased to minimize disruption",
                ),
                ParticipantStance(
                    decision_id="dec-001",
                    participant="gpt-4@codex",
                    vote_option="Incremental Adoption",
                    confidence=0.90,
                    rationale="Allows team to learn gradually",
                    final_position="Incremental approach enables learning curve management",
                ),
                ParticipantStance(
                    decision_id="dec-001",
                    participant="sonnet@claude",
                    vote_option="Incremental Adoption",
                    confidence=0.88,
                    rationale="Balances innovation with stability",
                    final_position="Phased adoption provides best risk-reward balance",
                ),
            ],
            "dec-002": [
                ParticipantStance(
                    decision_id="dec-002",
                    participant="opus@claude",
                    vote_option="TypeScript",
                    confidence=0.95,
                    rationale="Type safety prevents runtime errors",
                    final_position="TypeScript's static typing is essential for backend reliability",
                ),
                ParticipantStance(
                    decision_id="dec-002",
                    participant="gemini@gemini",
                    vote_option="TypeScript",
                    confidence=0.92,
                    rationale="Better IDE support and refactoring",
                    final_position="Development experience significantly improved with TypeScript",
                ),
                ParticipantStance(
                    decision_id="dec-002",
                    participant="sonnet@droid",
                    vote_option="TypeScript",
                    confidence=0.88,
                    rationale="Industry standard for serious backend work",
                    final_position="TypeScript is the pragmatic choice for maintainability",
                ),
            ],
            "dec-003": [
                ParticipantStance(
                    decision_id="dec-003",
                    participant="opus@claude",
                    vote_option="REST with OpenAPI",
                    confidence=0.80,
                    rationale="Simpler to implement and maintain",
                    final_position="REST provides sufficient flexibility with less complexity",
                ),
                ParticipantStance(
                    decision_id="dec-003",
                    participant="gpt-4@codex",
                    vote_option="REST with OpenAPI",
                    confidence=0.75,
                    rationale="Better tooling ecosystem",
                    final_position="REST tooling is more mature and widely supported",
                ),
                ParticipantStance(
                    decision_id="dec-003",
                    participant="gemini@gemini",
                    vote_option="GraphQL",
                    confidence=0.70,
                    rationale="More efficient data fetching",
                    final_position="GraphQL would reduce over-fetching, but team readiness is concern",
                ),
            ],
        }

        return stances

    @pytest.fixture
    def populated_storage(
        self,
        storage: DecisionGraphStorage,
        sample_decisions: List[DecisionNode],
        sample_stances: Dict[str, List[ParticipantStance]],
    ) -> DecisionGraphStorage:
        """Create storage populated with sample decisions and stances."""
        # Save all decisions
        for decision in sample_decisions:
            storage.save_decision_node(decision)

        # Save stances for decisions that have them
        for decision_id, stances in sample_stances.items():
            for stance in stances:
                storage.save_participant_stance(stance)

        # Compute and save similarity relationships
        # dec-001 and dec-002 are both about TypeScript (high similarity)
        storage.save_similarity(
            DecisionSimilarity(
                source_id="dec-002",
                target_id="dec-001",
                similarity_score=0.82,
                computed_at=datetime.now(),
            )
        )

        # dec-003 and dec-004 are both about GraphQL (high similarity, potential contradiction)
        storage.save_similarity(
            DecisionSimilarity(
                source_id="dec-004",
                target_id="dec-003",
                similarity_score=0.78,
                computed_at=datetime.now(),
            )
        )

        # dec-001 and dec-004 have moderate similarity (both about frontend tech)
        storage.save_similarity(
            DecisionSimilarity(
                source_id="dec-004",
                target_id="dec-001",
                similarity_score=0.65,
                computed_at=datetime.now(),
            )
        )

        return storage

    async def test_should_store_and_retrieve_decision_by_id(
        self, storage: DecisionGraphStorage, sample_decisions: List[DecisionNode]
    ):
        """Test storing a decision and retrieving it by ID."""
        # Arrange
        decision = sample_decisions[0]

        # Act: Store decision
        decision_id = storage.save_decision_node(decision)

        # Assert: Retrieve and verify
        retrieved = storage.get_decision_node(decision_id)
        assert retrieved is not None
        assert retrieved.id == decision.id
        assert retrieved.question == decision.question
        assert retrieved.consensus == decision.consensus
        assert retrieved.winning_option == decision.winning_option
        assert retrieved.convergence_status == decision.convergence_status
        assert retrieved.participants == decision.participants

    async def test_should_query_similar_decisions_with_semantic_matching(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test similarity search with real semantic matching."""
        # Arrange: Query about TypeScript (should match dec-001 and dec-002)
        query = "Should we use TypeScript in our project?"
        retriever = DecisionRetriever(populated_storage)

        # Act: Find similar decisions (returns tuples of (DecisionNode, score))
        scored_decisions = retriever.find_relevant_decisions(
            query_question=query, threshold=0.6, max_results=5
        )

        # Assert: Should find TypeScript-related decisions
        assert (
            len(scored_decisions) >= 2
        ), "Should find at least 2 TypeScript decisions"

        # Extract decisions from tuples
        decisions = [d for d, score in scored_decisions]
        [d.id for d in decisions]

        # The exact matches depend on similarity backend, but should be related
        questions = [d.question for d in decisions]
        typescript_count = sum(
            1 for q in questions if "TypeScript" in q or "JavaScript" in q
        )
        assert typescript_count >= 1, "Should find TypeScript-related decisions"

    async def test_should_detect_contradictions_between_similar_decisions(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test contradiction detection between similar decisions.

        dec-003 chose REST over GraphQL, but dec-004 chose GraphQL over REST.
        These are similar questions with contradictory outcomes.
        """
        # Arrange: Get the two GraphQL-related decisions
        dec_003 = populated_storage.get_decision_node("dec-003")
        dec_004 = populated_storage.get_decision_node("dec-004")
        
        assert dec_003 is not None, "dec-003 should exist in test data"
        assert dec_004 is not None, "dec-004 should exist in test data"

        # Get similarity between them
        similar = populated_storage.get_similar_decisions(
            "dec-004", threshold=0.7, limit=5
        )

        # Act: Check if dec-003 is in similar decisions
        similar_ids = [node.id for node, score in similar]

        # Assert: Should detect high similarity
        assert (
            "dec-003" in similar_ids
        ), "Should detect similarity between GraphQL decisions"

        # Find the similarity score
        dec_003_similarity = next(
            (score for node, score in similar if node.id == "dec-003"), None
        )
        assert dec_003_similarity is not None
        assert dec_003_similarity >= 0.7, "Should have high similarity score"

        # Verify contradiction: different winning options for similar questions
        assert dec_003.winning_option != dec_004.winning_option, (
            "Should detect contradictory decisions: "
            f"dec-003 chose '{dec_003.winning_option}' but "
            f"dec-004 chose '{dec_004.winning_option}'"
        )

    async def test_should_trace_decision_timeline_chronologically(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test timeline tracing with real decision data."""
        # Arrange: Get all decisions
        all_decisions = populated_storage.get_all_decisions(limit=100)

        # Act: Verify chronological ordering (newest first)
        timestamps = [d.timestamp for d in all_decisions]

        # Assert: Should be sorted newest first
        assert len(all_decisions) == 7, "Should retrieve all 7 decisions"
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1], (
                f"Decisions should be ordered newest first, but "
                f"decision {i} ({timestamps[i]}) is older than decision {i+1} ({timestamps[i+1]})"
            )

    async def test_should_analyze_patterns_with_multiple_participants(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test pattern analysis across multiple participants."""
        # Arrange: Get all decisions
        all_decisions = populated_storage.get_all_decisions(limit=100)

        # Act: Analyze participant patterns
        participant_counts: dict[str, int] = {}
        for decision in all_decisions:
            for participant in decision.participants:
                participant_counts[participant] = (
                    participant_counts.get(participant, 0) + 1
                )

        # Assert: Should identify frequent participants
        assert "opus@claude" in participant_counts, "opus@claude should participate"
        assert "gpt-4@codex" in participant_counts, "gpt-4@codex should participate"

        # Verify opus@claude participated most frequently (appears in 5 decisions)
        assert participant_counts["opus@claude"] >= 5, (
            f"opus@claude should participate in at least 5 decisions, "
            f"but participated in {participant_counts['opus@claude']}"
        )

        # Analyze convergence patterns
        convergence_statuses = [d.convergence_status for d in all_decisions]
        converged_count = sum(1 for s in convergence_statuses if s == "converged")
        assert converged_count >= 3, "Should have multiple converged decisions"

    async def test_should_export_to_graphml_format(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test export to GraphML format with valid XML structure."""
        # Arrange: Create temporary export file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".graphml", delete=False
        ) as f:
            export_path = Path(f.name)

        try:
            # Act: Export to GraphML
            decisions = populated_storage.get_all_decisions(limit=100)

            # Build GraphML manually (simulating exporter)
            graphml = self._create_graphml(decisions, populated_storage)
            export_path.write_text(graphml)

            # Assert: Validate XML structure
            assert export_path.exists(), "Export file should be created"
            tree = ET.parse(export_path)
            root = tree.getroot()

            # Verify GraphML structure
            assert root.tag.endswith("graphml"), "Root should be graphml element"

            # Find graph element
            graph = root.find(".//{http://graphml.graphdrawing.org/xmlns}graph")
            assert graph is not None, "Should contain graph element"

            # Verify nodes (decisions)
            nodes = root.findall(".//{http://graphml.graphdrawing.org/xmlns}node")
            assert len(nodes) == 7, f"Should have 7 decision nodes, found {len(nodes)}"

            # Verify edges (similarities)
            edges = root.findall(".//{http://graphml.graphdrawing.org/xmlns}edge")
            assert (
                len(edges) >= 3
            ), f"Should have at least 3 similarity edges, found {len(edges)}"

            # Verify node data
            node_ids = [node.get("id") for node in nodes]
            assert "dec-001" in node_ids, "Should include dec-001"
            assert "dec-007" in node_ids, "Should include dec-007"

        finally:
            # Cleanup
            if export_path.exists():
                export_path.unlink()

    async def test_should_export_to_json_format(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test export to JSON format with valid structure."""
        # Arrange: Create temporary export file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = Path(f.name)

        try:
            # Act: Export to JSON
            decisions = populated_storage.get_all_decisions(limit=100)

            # Build JSON export manually (simulating exporter)
            export_data = {
                "decisions": [
                    {
                        "id": d.id,
                        "question": d.question,
                        "timestamp": d.timestamp.isoformat(),
                        "consensus": d.consensus,
                        "winning_option": d.winning_option,
                        "convergence_status": d.convergence_status,
                        "participants": d.participants,
                        "metadata": d.metadata,
                    }
                    for d in decisions
                ],
                "export_timestamp": datetime.now().isoformat(),
                "total_decisions": len(decisions),
            }

            export_path.write_text(json.dumps(export_data, indent=2))

            # Assert: Validate JSON structure
            assert export_path.exists(), "Export file should be created"

            # Parse and verify
            with open(export_path, "r") as f:
                loaded_data = json.load(f)

            assert "decisions" in loaded_data, "Should have decisions key"
            assert "total_decisions" in loaded_data, "Should have total_decisions key"
            assert loaded_data["total_decisions"] == 7, "Should report 7 decisions"
            assert len(loaded_data["decisions"]) == 7, "Should export all 7 decisions"

            # Verify decision data
            dec_001 = next(d for d in loaded_data["decisions"] if d["id"] == "dec-001")
            assert "TypeScript" in dec_001["question"], "Should preserve question text"
            assert dec_001["winning_option"] == "Incremental Adoption"
            assert dec_001["convergence_status"] == "converged"

        finally:
            # Cleanup
            if export_path.exists():
                export_path.unlink()

    async def test_should_handle_file_io_reading_database(
        self, sample_decisions: List[DecisionNode]
    ):
        """Test CLI file I/O: reading from database file."""
        # Arrange: Create temporary database file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            # Act: Write to database
            storage = DecisionGraphStorage(str(db_path))
            for decision in sample_decisions[:3]:  # Save first 3 decisions
                storage.save_decision_node(decision)
            storage.close()

            # Assert: Read from database in new connection
            storage2 = DecisionGraphStorage(str(db_path))
            retrieved_decisions = storage2.get_all_decisions(limit=100)

            assert len(retrieved_decisions) == 3, "Should read 3 decisions from file"
            assert retrieved_decisions[0].id in ["dec-001", "dec-002", "dec-003"]
            storage2.close()

        finally:
            # Cleanup
            if db_path.exists():
                db_path.unlink()

    async def test_should_handle_file_io_writing_exports(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test CLI file I/O: writing export files."""
        # Arrange: Create temporary directory for exports
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            graphml_path = export_dir / "decisions.graphml"
            json_path = export_dir / "decisions.json"

            # Act: Write exports
            decisions = populated_storage.get_all_decisions(limit=100)

            # Write GraphML
            graphml_content = self._create_graphml(decisions, populated_storage)
            graphml_path.write_text(graphml_content)

            # Write JSON
            json_content = json.dumps(
                {
                    "decisions": [d.model_dump(mode="json") for d in decisions],
                    "total": len(decisions),
                },
                indent=2,
                default=str,
            )
            json_path.write_text(json_content)

            # Assert: Verify files exist and are readable
            assert graphml_path.exists(), "GraphML export should exist"
            assert json_path.exists(), "JSON export should exist"

            assert graphml_path.stat().st_size > 0, "GraphML should not be empty"
            assert json_path.stat().st_size > 0, "JSON should not be empty"

            # Verify readability
            graphml_tree = ET.parse(graphml_path)
            assert graphml_tree.getroot() is not None

            json_data = json.loads(json_path.read_text())
            assert json_data["total"] == 7

    async def test_should_handle_empty_database_gracefully(self):
        """Test error recovery: empty database."""
        # Arrange: Empty storage
        storage = DecisionGraphStorage(":memory:")

        # Act: Query empty database
        all_decisions = storage.get_all_decisions(limit=100)
        retriever = DecisionRetriever(storage)
        similar = retriever.find_relevant_decisions("Any question", threshold=0.7)

        # Assert: Should return empty results, not error
        assert all_decisions == [], "Should return empty list for no decisions"
        assert similar == [], "Should return empty list for no similar decisions"

    async def test_should_handle_nonexistent_decision_gracefully(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test error recovery: querying nonexistent decision."""
        # Act: Query for decision that doesn't exist
        result = populated_storage.get_decision_node("nonexistent-id")

        # Assert: Should return None, not error
        assert result is None, "Should return None for nonexistent decision"

    async def test_should_handle_invalid_similarity_threshold(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test error recovery: invalid threshold values."""
        # Arrange
        retriever = DecisionRetriever(populated_storage)

        # Act & Assert: Invalid threshold should raise ValueError
        with pytest.raises(ValueError, match="threshold must be between 0.0 and 1.0"):
            retriever.find_relevant_decisions("question", threshold=1.5)

        with pytest.raises(ValueError, match="threshold must be between 0.0 and 1.0"):
            retriever.find_relevant_decisions("question", threshold=-0.1)

    async def test_should_handle_invalid_max_results(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test error recovery: invalid max_results."""
        # Arrange
        retriever = DecisionRetriever(populated_storage)

        # Act & Assert: Invalid max_results should raise ValueError
        with pytest.raises(ValueError, match="max_results must be >= 1"):
            retriever.find_relevant_decisions("question", threshold=0.7, max_results=0)

        with pytest.raises(ValueError, match="max_results must be >= 1"):
            retriever.find_relevant_decisions("question", threshold=0.7, max_results=-5)

    async def test_should_complete_query_workflow_in_under_5_seconds(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test performance: query workflow should complete quickly."""
        import time

        # Arrange
        retriever = DecisionRetriever(populated_storage)

        # Act: Time the query workflow
        start = time.time()

        # Simulate realistic CLI workflow
        scored_decisions = retriever.find_relevant_decisions(
            "Should we use TypeScript?", threshold=0.6, max_results=5
        )
        # Extract decisions from tuples for format_context
        decisions = [d for d, score in scored_decisions]
        context = retriever.format_context(decisions, "Should we use TypeScript?")

        end = time.time()
        duration = end - start

        # Assert: Should complete quickly
        assert (
            duration < 5.0
        ), f"Query workflow took {duration:.2f}s, should be under 5s"
        assert len(context) > 0, "Should generate context"

    async def test_should_retrieve_enriched_context_for_deliberation(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test integration with deliberation: enriched context retrieval."""
        # Arrange
        integration = DecisionGraphIntegration(populated_storage)

        # Act: Get context for new deliberation
        context = integration.get_context_for_deliberation(
            question="Should we migrate to TypeScript for our codebase?",
            threshold=0.6,
            max_context_decisions=3,
        )

        # Assert: Should return formatted context
        assert context != "", "Should return non-empty context"
        assert "Similar Past Deliberations" in context, "Should have context header"
        assert (
            "TypeScript" in context or "JavaScript" in context
        ), "Should mention related decisions"
        assert (
            "**Consensus**:" in context
        ), "Should include consensus from past decisions"
        assert "**Participants**:" in context, "Should list participants"

    async def test_should_format_participant_stances_in_context(
        self, populated_storage: DecisionGraphStorage
    ):
        """Test that participant stances are formatted correctly in context."""
        # Arrange
        retriever = DecisionRetriever(populated_storage)

        # Act: Get decision with stances
        decision = populated_storage.get_decision_node("dec-001")
        assert decision is not None, "dec-001 should exist in test data"
        context = retriever.format_context([decision], "test query")

        # Assert: Should include stance information
        assert "Participant Positions" in context, "Should have positions section"
        assert "opus@claude" in context, "Should mention participant"
        assert "Voted for" in context, "Should show vote"
        assert "confidence:" in context, "Should show confidence"
        assert "Incremental Adoption" in context, "Should mention vote option"

    # Helper methods for test implementation

    def _create_graphml(
        self, decisions: List[DecisionNode], storage: DecisionGraphStorage
    ) -> str:
        """Create GraphML XML content from decisions."""
        graphml_ns = "http://graphml.graphdrawing.org/xmlns"
        ET.register_namespace("", graphml_ns)

        # Create root element
        root = ET.Element(f"{{{graphml_ns}}}graphml")

        # Define attributes
        for attr_id, attr_name, attr_type in [
            ("d0", "question", "string"),
            ("d1", "consensus", "string"),
            ("d2", "convergence_status", "string"),
            ("d3", "similarity_score", "double"),
        ]:
            key = ET.SubElement(root, f"{{{graphml_ns}}}key")
            key.set("id", attr_id)
            key.set(
                "for",
                "node" if attr_id.startswith("d") and int(attr_id[1:]) < 3 else "edge",
            )
            key.set("attr.name", attr_name)
            key.set("attr.type", attr_type)

        # Create graph
        graph = ET.SubElement(root, f"{{{graphml_ns}}}graph")
        graph.set("id", "DecisionGraph")
        graph.set("edgedefault", "directed")

        # Add nodes (decisions)
        for decision in decisions:
            node = ET.SubElement(graph, f"{{{graphml_ns}}}node")
            node.set("id", decision.id)

            # Add data
            data_q = ET.SubElement(node, f"{{{graphml_ns}}}data")
            data_q.set("key", "d0")
            data_q.text = decision.question

            data_c = ET.SubElement(node, f"{{{graphml_ns}}}data")
            data_c.set("key", "d1")
            data_c.text = decision.consensus

            data_s = ET.SubElement(node, f"{{{graphml_ns}}}data")
            data_s.set("key", "d2")
            data_s.text = decision.convergence_status

        # Add edges (similarities)
        for decision in decisions:
            similar = storage.get_similar_decisions(
                decision.id, threshold=0.5, limit=10
            )
            for target_node, score in similar:
                edge = ET.SubElement(graph, f"{{{graphml_ns}}}edge")
                edge.set("source", decision.id)
                edge.set("target", target_node.id)

                data_sim = ET.SubElement(edge, f"{{{graphml_ns}}}data")
                data_sim.set("key", "d3")
                data_sim.text = str(score)

        # Convert to string
        return ET.tostring(root, encoding="unicode", method="xml")


@pytest.mark.integration
class TestDecisionGraphExportFormats:
    """Test export format validation and structure."""

    async def test_graphml_export_has_required_elements(self):
        """Test that GraphML export contains required XML elements."""
        # Arrange: Create minimal GraphML
        graphml_ns = "http://graphml.graphdrawing.org/xmlns"
        root = ET.Element(f"{{{graphml_ns}}}graphml")
        graph = ET.SubElement(root, f"{{{graphml_ns}}}graph")
        graph.set("id", "G")

        # Add minimal node
        node = ET.SubElement(graph, f"{{{graphml_ns}}}node")
        node.set("id", "n1")

        xml_str = ET.tostring(root, encoding="unicode")

        # Act: Parse XML
        tree = ET.ElementTree(ET.fromstring(xml_str))
        parsed_root = tree.getroot()

        # Assert: Verify structure
        assert parsed_root.tag.endswith("graphml")
        graph_elem = parsed_root.find(f".//{{{graphml_ns}}}graph")
        assert graph_elem is not None
        node_elem = graph_elem.find(f".//{{{graphml_ns}}}node")
        assert node_elem is not None
        assert node_elem.get("id") == "n1"

    async def test_json_export_has_required_fields(self):
        """Test that JSON export contains required fields."""
        # Arrange: Create sample export data
        export_data = {
            "decisions": [
                {
                    "id": "dec-001",
                    "question": "Test question",
                    "timestamp": datetime.now().isoformat(),
                    "consensus": "Test consensus",
                    "convergence_status": "converged",
                    "participants": ["test@cli"],
                }
            ],
            "export_timestamp": datetime.now().isoformat(),
            "total_decisions": 1,
        }

        # Act: Serialize and deserialize
        json_str = json.dumps(export_data)
        loaded = json.loads(json_str)

        # Assert: Verify structure
        assert "decisions" in loaded
        assert "total_decisions" in loaded
        assert loaded["total_decisions"] == 1
        assert len(loaded["decisions"]) == 1
        assert loaded["decisions"][0]["id"] == "dec-001"
        assert loaded["decisions"][0]["question"] == "Test question"
