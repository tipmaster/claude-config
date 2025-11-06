#!/usr/bin/env python3
"""
Benchmark script to demonstrate database index performance improvements.

This script creates a test database, populates it with decisions, and measures
query performance with and without indexes to demonstrate their impact.
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_graph.schema import DecisionNode
from decision_graph.storage import DecisionGraphStorage


def create_test_database_without_indexes(db_path: str, num_decisions: int = 1000):
    """Create a test database without indexes for comparison."""
    conn = sqlite3.connect(db_path)

    # Create tables without indexes
    conn.execute(
        """
        CREATE TABLE decision_nodes (
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

    conn.execute(
        """
        CREATE TABLE participant_stances (
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

    conn.execute(
        """
        CREATE TABLE decision_similarities (
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

    # Populate with test data
    print(f"Populating database with {num_decisions} decisions...")
    for i in range(num_decisions):
        decision_id = f"test-{i:06d}"
        conn.execute(
            """
            INSERT INTO decision_nodes (
                id, question, timestamp, consensus, winning_option,
                convergence_status, participants, transcript_path, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                f"Question {i} about topic {i % 50}",
                datetime.now().isoformat(),
                "Test consensus",
                "Option A",
                "converged",
                json.dumps(["claude", "codex"]),
                f"/tmp/transcript_{i}.md",
                None,
            ),
        )

        # Add participant stances
        for participant in ["claude", "codex"]:
            conn.execute(
                """
                INSERT INTO participant_stances (
                    decision_id, participant, vote_option, confidence,
                    rationale, final_position
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    participant,
                    "Option A",
                    0.85,
                    "Test rationale",
                    "Test position",
                ),
            )

    conn.commit()
    conn.close()
    print("✓ Database populated")


def benchmark_query(db_path: str, query: str, description: str) -> float:
    """Run a query and measure execution time."""
    conn = sqlite3.connect(db_path)

    start = time.perf_counter()
    cursor = conn.execute(query)
    results = cursor.fetchall()
    elapsed_ms = (time.perf_counter() - start) * 1000

    conn.close()
    return elapsed_ms, len(results)


def main():
    """Run benchmark comparing indexed vs non-indexed database."""
    num_decisions = 1000

    print("=" * 70)
    print("Database Index Performance Benchmark")
    print("=" * 70)
    print()

    # Create database without indexes
    with tempfile.NamedTemporaryFile(suffix="_no_idx.db", delete=False) as f:
        db_no_idx = f.name

    create_test_database_without_indexes(db_no_idx, num_decisions)

    # Create database with indexes (using our storage class)
    with tempfile.NamedTemporaryFile(suffix="_with_idx.db", delete=False) as f:
        db_with_idx = f.name

    storage = DecisionGraphStorage(db_path=db_with_idx)
    print(f"Creating indexed database with {num_decisions} decisions...")
    for i in range(num_decisions):
        node = DecisionNode(
            id=f"test-{i:06d}",
            question=f"Question {i} about topic {i % 50}",
            timestamp=datetime.now(),
            consensus="Test consensus",
            convergence_status="converged",
            participants=["claude", "codex"],
            transcript_path=f"/tmp/transcript_{i}.md",
        )
        storage.save_decision_node(node)
    storage.close()
    print("✓ Indexed database created")
    print()

    # Define benchmark queries
    queries = [
        (
            "SELECT * FROM decision_nodes ORDER BY timestamp DESC LIMIT 10",
            "Timestamp-ordered query (LIMIT 10)",
        ),
        (
            "SELECT * FROM participant_stances WHERE decision_id = 'test-000500'",
            "Participant stances lookup",
        ),
        (
            "SELECT COUNT(*) FROM decision_nodes WHERE timestamp > '2025-01-01'",
            "Timestamp filter count",
        ),
    ]

    # Run benchmarks
    print("Benchmark Results:")
    print("-" * 70)
    print(f"{'Query':<40} {'No Index':<15} {'With Index':<15} {'Speedup':<10}")
    print("-" * 70)

    for query, description in queries:
        time_no_idx, results_no_idx = benchmark_query(db_no_idx, query, description)
        time_with_idx, results_with_idx = benchmark_query(
            db_with_idx, query, description
        )

        speedup = time_no_idx / time_with_idx if time_with_idx > 0 else 0

        print(
            f"{description:<40} {time_no_idx:>10.2f}ms {time_with_idx:>10.2f}ms {speedup:>8.1f}x"
        )

    print("-" * 70)
    print()

    # Show database sizes
    size_no_idx = os.path.getsize(db_no_idx) / 1024
    size_with_idx = os.path.getsize(db_with_idx) / 1024
    overhead = (size_with_idx / size_no_idx) if size_no_idx > 0 else 0

    print("Database Size Analysis:")
    print(f"  Without indexes: {size_no_idx:>10.2f} KB")
    print(f"  With indexes:    {size_with_idx:>10.2f} KB")
    print(f"  Overhead:        {overhead:>10.2f}×")
    print()

    # Show query plans
    print("Query Plan Analysis (Indexed Database):")
    print("-" * 70)

    conn = sqlite3.connect(db_with_idx)
    for query, description in queries:
        print(f"\n{description}:")
        cursor = conn.execute(f"EXPLAIN QUERY PLAN {query}")
        for row in cursor.fetchall():
            print(f"  {row[3]}")
    conn.close()

    print()
    print("=" * 70)

    # Cleanup
    os.unlink(db_no_idx)
    os.unlink(db_with_idx)

    print("\n✓ Benchmark complete")


if __name__ == "__main__":
    main()
