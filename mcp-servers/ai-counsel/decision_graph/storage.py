"""SQLite storage layer for decision graph memory.

This module provides persistent storage for completed deliberations, participant
stances, and similarity relationships using SQLite. It handles database initialization,
CRUD operations, and efficient querying with proper indexing.
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional, Tuple

from decision_graph.schema import (DecisionNode, DecisionSimilarity,
                                   ParticipantStance)

logger = logging.getLogger(__name__)


class DecisionGraphStorage:
    """SQLite storage layer for decision graph memory.

    Provides persistence for:
    - DecisionNode: Completed deliberations with metadata
    - ParticipantStance: Individual participant positions and votes
    - DecisionSimilarity: Pre-computed similarity relationships

    Supports both file-based and in-memory databases for testing.
    """

    def __init__(self, db_path: str = "decision_graph.db"):
        """Initialize storage with SQLite database.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory database.

        Raises:
            RuntimeError: If database initialization or schema verification fails.
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

        # Ensure parent directory exists (unless using in-memory database)
        if db_path != ":memory:":
            from pathlib import Path
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured parent directory exists: {db_file.parent}")

        try:
            # Force connection creation before initializing schema
            # This ensures the database file is created immediately
            _ = self.conn
            logger.debug(f"Database connection established: {db_path}")

            # Initialize database schema
            self._initialize_db()

            # Verify schema was properly created
            if not self._verify_schema():
                raise RuntimeError(
                    f"Database schema verification failed for {db_path}. "
                    "Tables may not have been created properly."
                )

            logger.info(f"Initialized DecisionGraphStorage at {db_path}")

        except Exception as e:
            # Clean up corrupted 0-byte database file
            if db_path != ":memory:" and os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                if file_size == 0:
                    logger.warning(
                        f"Removing corrupted 0-byte database file: {db_path}"
                    )
                    try:
                        os.remove(db_path)
                    except OSError as remove_err:
                        logger.error(f"Failed to remove corrupted file: {remove_err}")

            # Close connection if it was opened
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

            logger.error(
                f"Failed to initialize DecisionGraphStorage at {db_path}: {e}",
                exc_info=True
            )
            raise RuntimeError(
                f"Database initialization failed: {e}. "
                "Check logs and file permissions."
            ) from e

    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection, creating if needed."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            # Enable foreign key constraints
            self._conn.execute("PRAGMA foreign_keys = ON")
            # Return rows as Row objects for dict-like access
            self._conn.row_factory = sqlite3.Row
        return self._conn

    @contextmanager
    def transaction(self):
        """Context manager for database transactions with automatic rollback on error."""
        conn = self.conn
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise

    def _initialize_db(self) -> None:
        """Create database schema if it doesn't exist."""
        with self.transaction() as conn:
            # Create decision_nodes table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_nodes (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    consensus TEXT NOT NULL,
                    winning_option TEXT,
                    convergence_status TEXT NOT NULL,
                    participants TEXT NOT NULL,
                    transcript_path TEXT NOT NULL,
                    metadata TEXT
                )
            """
            )

            # Create participant_stances table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS participant_stances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT NOT NULL,
                    participant TEXT NOT NULL,
                    vote_option TEXT,
                    confidence REAL,
                    rationale TEXT,
                    final_position TEXT,
                    FOREIGN KEY (decision_id) REFERENCES decision_nodes(id)
                )
            """
            )

            # Create decision_similarities table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_similarities (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    similarity_score REAL NOT NULL,
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id),
                    FOREIGN KEY (source_id) REFERENCES decision_nodes(id),
                    FOREIGN KEY (target_id) REFERENCES decision_nodes(id)
                )
            """
            )

            # Create indexes for efficient querying
            # PRIMARY: Most queries filter by recency (timestamp ordering)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decision_timestamp
                ON decision_nodes(timestamp DESC)
            """
            )

            # For duplicate detection and question-based filtering
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decision_question
                ON decision_nodes(question)
            """
            )

            # For gathering decision context (participant stances)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_participant_decision
                ON participant_stances(decision_id)
            """
            )

            # For similarity lookups (source-based queries)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_similarity_source
                ON decision_similarities(source_id)
            """
            )

            # For similarity score-based filtering and ordering
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_similarity_score
                ON decision_similarities(similarity_score DESC)
            """
            )

            logger.debug("Database schema and indexes initialized successfully")

    def _verify_schema(self) -> bool:
        """Verify that the database schema was properly created.

        Returns:
            True if all required tables exist, False otherwise.
        """
        try:
            cursor = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}
            required_tables = {'decision_nodes', 'participant_stances', 'decision_similarities'}

            if not required_tables.issubset(tables):
                missing = required_tables - tables
                logger.error(f"Missing required tables: {missing}")
                return False

            # Verify the database file has actual content (not 0 bytes)
            if self.db_path != ":memory:":
                if os.path.exists(self.db_path):
                    file_size = os.path.getsize(self.db_path)
                    if file_size == 0:
                        logger.error(f"Database file exists but is empty (0 bytes): {self.db_path}")
                        return False
                    logger.debug(f"Database file size: {file_size} bytes")
                else:
                    logger.error(f"Database file does not exist: {self.db_path}")
                    return False

            logger.debug("Database schema verification successful")
            return True
        except Exception as e:
            logger.error(f"Schema verification failed: {e}", exc_info=True)
            return False

    def save_decision_node(self, node: DecisionNode) -> str:
        """Save a decision node to the database.

        Args:
            node: DecisionNode to save

        Returns:
            The decision node ID

        Raises:
            sqlite3.IntegrityError: If a node with this ID already exists
        """
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO decision_nodes (
                    id, question, timestamp, consensus, winning_option,
                    convergence_status, participants, transcript_path, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.question,
                    node.timestamp.isoformat(),
                    node.consensus,
                    node.winning_option,
                    node.convergence_status,
                    json.dumps(node.participants),
                    node.transcript_path,
                    json.dumps(node.metadata) if node.metadata else None,
                ),
            )
            logger.info(f"Saved decision node {node.id}")
            return node.id

    def get_decision_node(self, decision_id: str) -> Optional[DecisionNode]:
        """Retrieve a decision node by ID.

        Args:
            decision_id: UUID of the decision node

        Returns:
            DecisionNode if found, None otherwise
        """
        cursor = self.conn.execute(
            """
            SELECT id, question, timestamp, consensus, winning_option,
                   convergence_status, participants, transcript_path, metadata
            FROM decision_nodes
            WHERE id = ?
            """,
            (decision_id,),
        )
        row = cursor.fetchone()

        if row is None:
            logger.debug(f"Decision node {decision_id} not found")
            return None

        return self._row_to_decision_node(row)

    def get_all_decisions(
        self, limit: int = 100, offset: int = 0
    ) -> List[DecisionNode]:
        """List all decisions ordered by timestamp (newest first).

        Args:
            limit: Maximum number of decisions to return
            offset: Number of decisions to skip (for pagination)

        Returns:
            List of DecisionNode objects
        """
        cursor = self.conn.execute(
            """
            SELECT id, question, timestamp, consensus, winning_option,
                   convergence_status, participants, transcript_path, metadata
            FROM decision_nodes
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

        nodes = [self._row_to_decision_node(row) for row in cursor.fetchall()]
        logger.debug(
            f"Retrieved {len(nodes)} decision nodes (limit={limit}, offset={offset})"
        )
        return nodes

    def save_participant_stance(self, stance: ParticipantStance) -> int:
        """Save a participant stance to the database.

        Args:
            stance: ParticipantStance to save

        Returns:
            Row ID of the inserted stance

        Raises:
            sqlite3.IntegrityError: If decision_id doesn't exist (foreign key violation)
        """
        with self.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO participant_stances (
                    decision_id, participant, vote_option, confidence,
                    rationale, final_position
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stance.decision_id,
                    stance.participant,
                    stance.vote_option,
                    stance.confidence,
                    stance.rationale,
                    stance.final_position,
                ),
            )
            row_id = cursor.lastrowid
            logger.debug(
                f"Saved participant stance for {stance.participant} "
                f"in decision {stance.decision_id} (row_id={row_id})"
            )
            return row_id

    def get_participant_stances(self, decision_id: str) -> List[ParticipantStance]:
        """Get all participant stances for a decision.

        Args:
            decision_id: UUID of the decision

        Returns:
            List of ParticipantStance objects (may be empty)
        """
        cursor = self.conn.execute(
            """
            SELECT decision_id, participant, vote_option, confidence,
                   rationale, final_position
            FROM participant_stances
            WHERE decision_id = ?
            ORDER BY participant
            """,
            (decision_id,),
        )

        stances = [self._row_to_participant_stance(row) for row in cursor.fetchall()]
        logger.debug(f"Retrieved {len(stances)} stances for decision {decision_id}")
        return stances

    def save_similarity(self, similarity: DecisionSimilarity) -> None:
        """Save or update a similarity relationship.

        Uses INSERT OR REPLACE to handle both new and updated similarities.

        Args:
            similarity: DecisionSimilarity to save

        Raises:
            sqlite3.IntegrityError: If source_id or target_id don't exist
        """
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO decision_similarities (
                    source_id, target_id, similarity_score, computed_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    similarity.source_id,
                    similarity.target_id,
                    similarity.similarity_score,
                    similarity.computed_at.isoformat(),
                ),
            )
            logger.debug(
                f"Saved similarity: {similarity.source_id} -> {similarity.target_id} "
                f"(score={similarity.similarity_score:.3f})"
            )

    def get_similar_decisions(
        self, decision_id: str, threshold: float = 0.7, limit: int = 10
    ) -> List[Tuple[DecisionNode, float]]:
        """Get decisions similar to a given decision above threshold.

        Returns decisions ordered by similarity score (highest first).

        Args:
            decision_id: UUID of the source decision
            threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum number of results to return

        Returns:
            List of (DecisionNode, similarity_score) tuples
        """
        cursor = self.conn.execute(
            """
            SELECT
                dn.id, dn.question, dn.timestamp, dn.consensus, dn.winning_option,
                dn.convergence_status, dn.participants, dn.transcript_path, dn.metadata,
                ds.similarity_score
            FROM decision_similarities ds
            JOIN decision_nodes dn ON ds.target_id = dn.id
            WHERE ds.source_id = ? AND ds.similarity_score >= ?
            ORDER BY ds.similarity_score DESC
            LIMIT ?
            """,
            (decision_id, threshold, limit),
        )

        results = []
        for row in cursor.fetchall():
            node = self._row_to_decision_node(row)
            similarity_score = row["similarity_score"]
            results.append((node, similarity_score))

        logger.debug(
            f"Found {len(results)} similar decisions for {decision_id} "
            f"(threshold={threshold}, limit={limit})"
        )
        return results

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug(f"Closed database connection to {self.db_path}")

    def _row_to_decision_node(self, row: sqlite3.Row) -> DecisionNode:
        """Convert database row to DecisionNode model.

        Args:
            row: SQLite row from decision_nodes table

        Returns:
            DecisionNode instance
        """
        return DecisionNode(
            id=row["id"],
            question=row["question"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            consensus=row["consensus"],
            winning_option=row["winning_option"],
            convergence_status=row["convergence_status"],
            participants=json.loads(row["participants"]),
            transcript_path=row["transcript_path"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_participant_stance(self, row: sqlite3.Row) -> ParticipantStance:
        """Convert database row to ParticipantStance model.

        Args:
            row: SQLite row from participant_stances table

        Returns:
            ParticipantStance instance
        """
        return ParticipantStance(
            decision_id=row["decision_id"],
            participant=row["participant"],
            vote_option=row["vote_option"],
            confidence=row["confidence"],
            rationale=row["rationale"],
            final_position=row["final_position"],
        )

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection when exiting context."""
        self.close()
        return False
