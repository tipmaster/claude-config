#!/usr/bin/env python3
"""
Quick verification script to check that all 5 critical indexes are present
in the decision graph database.

Usage:
    python scripts/verify_indexes.py [database_path]

If no database path is provided, creates a temporary database to verify
index creation logic.
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_graph.storage import DecisionGraphStorage


def verify_indexes(db_path: str) -> bool:
    """Verify all 5 critical indexes exist."""
    storage = DecisionGraphStorage(db_path=db_path)

    # Query for all indexes
    cursor = storage.conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
    )
    indexes = cursor.fetchall()
    index_names = [idx[0] for idx in indexes]

    # Expected indexes
    expected = [
        "idx_decision_question",
        "idx_decision_timestamp",
        "idx_participant_decision",
        "idx_similarity_score",
        "idx_similarity_source",
    ]

    print("=" * 70)
    print("Database Index Verification")
    print("=" * 70)
    print(f"\nDatabase: {db_path}")
    print(f"\nExpected indexes: {len(expected)}")
    print(f"Found indexes:    {len(index_names)}")
    print()

    # Check each expected index
    all_present = True
    for idx in expected:
        if idx in index_names:
            print(f"  ✓ {idx}")
        else:
            print(f"  ✗ {idx} (MISSING)")
            all_present = False

    # Check for unexpected indexes
    unexpected = [idx for idx in index_names if idx not in expected]
    if unexpected:
        print("\nUnexpected indexes found:")
        for idx in unexpected:
            print(f"  ? {idx}")

    print()
    print("=" * 70)

    if all_present:
        print("✓ All required indexes present")
        print("=" * 70)
    else:
        print("✗ Some indexes missing")
        print("=" * 70)

    storage.close()
    return all_present


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Verify specific database
        db_path = sys.argv[1]
        if not os.path.exists(db_path):
            print(f"Error: Database file not found: {db_path}")
            sys.exit(1)
        success = verify_indexes(db_path)
    else:
        # Create temporary database to verify index creation logic
        print(
            "No database specified, creating temporary database to verify index creation..."
        )
        print()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        try:
            success = verify_indexes(temp_db)
        finally:
            os.unlink(temp_db)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
