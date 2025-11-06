"""Maintenance and monitoring infrastructure for decision graph.

This module provides monitoring, analysis, and archival preparation capabilities
for the decision graph. It implements Phase 1 (monitoring only) with preparation
for future Phase 2 (soft archival) once database size warrants it.

Phase 1 (Current): Monitoring and analysis
- Database statistics and growth tracking
- Health checks and data integrity validation
- Archival benefit estimation (simulation only)
- Migration SQL generation for future Phase 2

Phase 2 (Future, Month 6+): Soft archival
- Archive old, unused decisions (marked archived=TRUE, kept in DB)
- Requires migration to add 'archived' and 'last_accessed' columns
- Triggered when >5000 decisions AND unused >180 days
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from decision_graph.storage import DecisionGraphStorage

logger = logging.getLogger(__name__)


class DecisionGraphMaintenance:
    """Maintenance and monitoring for decision graph.

    Provides infrastructure for:
    - Database statistics collection and growth analysis
    - Health checks and data integrity validation
    - Archival candidate identification (Phase 2 preparation)
    - Migration SQL generation for future archival support

    Phase 1 (Current):
        All methods are monitoring-only. No data modification occurs.
        Archival methods return simulations and estimations.

    Phase 2 (Future):
        After migration, archival methods will soft-archive old decisions
        by setting archived=TRUE (keeping data in DB for queries).
    """

    # Phase 2 archive triggers (not enforced in Phase 1)
    ARCHIVE_TRIGGER_DECISIONS = 5000
    ARCHIVE_TRIGGER_AGE_DAYS = 180
    ARCHIVE_TRIGGER_UNUSED_DAYS = 90

    def __init__(self, storage: DecisionGraphStorage):
        """Initialize maintenance manager.

        Args:
            storage: DecisionGraphStorage instance to monitor
        """
        self.storage = storage
        logger.info("Initialized DecisionGraphMaintenance (Phase 1: monitoring only)")

    # PHASE 1: Monitoring and analysis

    def get_database_stats(self) -> Dict[str, int | float]:
        """Get current database statistics.

        Returns:
            Dictionary with keys:
                - total_decisions: Total decision nodes in database
                - total_stances: Total participant stances
                - total_similarities: Total similarity relationships
                - db_size_bytes: Database file size in bytes
                - db_size_mb: Database file size in megabytes

        Performance: <100ms target
        """
        try:
            cursor = self.storage.conn.cursor()

            # Count decision nodes
            cursor.execute("SELECT COUNT(*) FROM decision_nodes")
            total_decisions = cursor.fetchone()[0]

            # Count participant stances
            cursor.execute("SELECT COUNT(*) FROM participant_stances")
            total_stances = cursor.fetchone()[0]

            # Count similarity relationships
            cursor.execute("SELECT COUNT(*) FROM decision_similarities")
            total_similarities = cursor.fetchone()[0]

            # Get database file size
            db_size_bytes = 0
            if self.storage.db_path != ":memory:":
                if os.path.exists(self.storage.db_path):
                    db_size_bytes = os.path.getsize(self.storage.db_path)

            stats = {
                "total_decisions": total_decisions,
                "total_stances": total_stances,
                "total_similarities": total_similarities,
                "db_size_bytes": db_size_bytes,
                "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
            }

            logger.debug(
                f"Database stats: {total_decisions} decisions, "
                f"{total_stances} stances, {total_similarities} similarities, "
                f"{stats['db_size_mb']} MB"
            )

            return stats

        except Exception as e:
            logger.error(f"Error collecting database stats: {e}", exc_info=True)
            return {
                "total_decisions": 0,
                "total_stances": 0,
                "total_similarities": 0,
                "db_size_bytes": 0,
                "db_size_mb": 0.0,
            }

    def analyze_growth(self, days: int = 30) -> Dict:
        """Analyze decision graph growth rate over recent period.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            Dictionary with keys:
                - analysis_period_days: Days analyzed
                - decisions_in_period: Decisions created in period
                - avg_decisions_per_day: Average decisions per day
                - projected_decisions_30d: Projected decisions in next 30 days
                - oldest_decision_date: ISO timestamp of oldest decision
                - newest_decision_date: ISO timestamp of newest decision

        Performance: <200ms target
        """
        try:
            cursor = self.storage.conn.cursor()

            # Get decisions from specified period
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute(
                """
                SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM decision_nodes
                WHERE timestamp >= ?
                """,
                (cutoff_date.isoformat(),),
            )
            row = cursor.fetchone()
            decisions_in_period = row[0] or 0
            # Note: row[1] (MIN timestamp) and row[2] (MAX timestamp) are fetched but not used

            # Calculate growth rate
            avg_per_day = decisions_in_period / days if days > 0 else 0
            projected_30d = int(avg_per_day * 30)

            # Get overall oldest and newest
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM decision_nodes")
            row = cursor.fetchone()
            oldest_overall = row[0]
            newest_overall = row[1]

            analysis = {
                "analysis_period_days": days,
                "decisions_in_period": decisions_in_period,
                "avg_decisions_per_day": round(avg_per_day, 2),
                "projected_decisions_30d": projected_30d,
                "oldest_decision_date": oldest_overall,
                "newest_decision_date": newest_overall,
            }

            logger.debug(
                f"Growth analysis: {decisions_in_period} decisions in {days} days, "
                f"{analysis['avg_decisions_per_day']}/day avg, "
                f"projected {projected_30d} in next 30 days"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing growth: {e}", exc_info=True)
            return {
                "analysis_period_days": days,
                "decisions_in_period": 0,
                "avg_decisions_per_day": 0.0,
                "projected_decisions_30d": 0,
                "oldest_decision_date": None,
                "newest_decision_date": None,
            }

    def estimate_archival_benefit(self) -> Dict:
        """Estimate space savings if archival were triggered (simulation only).

        This method identifies what WOULD be archived in Phase 2 but does not
        actually modify any data. Used for planning and capacity management.

        Returns:
            Dictionary with keys:
                - archive_eligible_count: Decisions that would be archived
                - archive_eligible_percent: Percentage of total decisions
                - estimated_space_savings_mb: Estimated space to be freed
                - would_trigger_archival: Whether triggers would activate
                - trigger_reason: Why archival would/wouldn't trigger

        Performance: <500ms target
        """
        try:
            stats = self.get_database_stats()
            total_decisions = stats["total_decisions"]

            if total_decisions == 0:
                return {
                    "archive_eligible_count": 0,
                    "archive_eligible_percent": 0.0,
                    "estimated_space_savings_mb": 0.0,
                    "would_trigger_archival": False,
                    "trigger_reason": "No decisions in database",
                }

            # Simulate Phase 2 archival logic
            # Decisions are candidates if:
            # - Created >180 days ago AND
            # - Not accessed in last 90 days (we don't track this yet, so assume all old)
            cutoff_age = datetime.now() - timedelta(days=self.ARCHIVE_TRIGGER_AGE_DAYS)

            cursor = self.storage.conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM decision_nodes
                WHERE timestamp < ?
                """,
                (cutoff_age.isoformat(),),
            )
            eligible_count = cursor.fetchone()[0] or 0

            eligible_percent = (
                (eligible_count / total_decisions * 100) if total_decisions > 0 else 0
            )

            # Estimate space savings (rough: avg decision ~15KB including relationships)
            # This is conservative; actual savings depend on compression
            avg_decision_size_kb = 15
            estimated_savings_mb = (eligible_count * avg_decision_size_kb) / 1024

            # Check if archival would trigger in Phase 2
            would_trigger = (
                total_decisions >= self.ARCHIVE_TRIGGER_DECISIONS and eligible_count > 0
            )

            if would_trigger:
                trigger_reason = (
                    f"Database has {total_decisions} decisions (>={self.ARCHIVE_TRIGGER_DECISIONS}) "
                    f"and {eligible_count} are >{self.ARCHIVE_TRIGGER_AGE_DAYS} days old"
                )
            elif total_decisions < self.ARCHIVE_TRIGGER_DECISIONS:
                trigger_reason = (
                    f"Database has only {total_decisions} decisions "
                    f"(<{self.ARCHIVE_TRIGGER_DECISIONS} trigger threshold)"
                )
            else:
                trigger_reason = (
                    f"No decisions >{self.ARCHIVE_TRIGGER_AGE_DAYS} days old"
                )

            result = {
                "archive_eligible_count": eligible_count,
                "archive_eligible_percent": round(eligible_percent, 2),
                "estimated_space_savings_mb": round(estimated_savings_mb, 2),
                "would_trigger_archival": would_trigger,
                "trigger_reason": trigger_reason,
            }

            logger.debug(
                f"Archival estimation: {eligible_count} eligible ({eligible_percent:.1f}%), "
                f"~{estimated_savings_mb:.1f}MB savings, trigger={would_trigger}"
            )

            return result

        except Exception as e:
            logger.error(f"Error estimating archival benefit: {e}", exc_info=True)
            return {
                "archive_eligible_count": 0,
                "archive_eligible_percent": 0.0,
                "estimated_space_savings_mb": 0.0,
                "would_trigger_archival": False,
                "trigger_reason": f"Error: {str(e)}",
            }

    def health_check(self) -> Dict:
        """Validate database health and data integrity.

        Checks for:
        - Orphaned participant stances (decision_id doesn't exist)
        - Orphaned similarities (source_id or target_id doesn't exist)
        - Corrupted timestamps
        - Missing required fields

        Returns:
            Dictionary with keys:
                - healthy: Boolean indicating overall health
                - checks_passed: Number of checks that passed
                - checks_failed: Number of checks that failed
                - issues: List of issue descriptions (empty if healthy)
                - details: Dict of check results

        Performance: <1s target
        """
        try:
            issues = []
            details = {}

            cursor = self.storage.conn.cursor()

            # Check 1: Orphaned participant stances
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM participant_stances ps
                WHERE NOT EXISTS (
                    SELECT 1 FROM decision_nodes dn
                    WHERE dn.id = ps.decision_id
                )
            """
            )
            orphaned_stances = cursor.fetchone()[0] or 0
            details["orphaned_stances"] = orphaned_stances
            if orphaned_stances > 0:
                issues.append(f"Found {orphaned_stances} orphaned participant stances")

            # Check 2: Orphaned similarities (source)
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM decision_similarities ds
                WHERE NOT EXISTS (
                    SELECT 1 FROM decision_nodes dn
                    WHERE dn.id = ds.source_id
                )
            """
            )
            orphaned_similarities_source = cursor.fetchone()[0] or 0
            details["orphaned_similarities_source"] = orphaned_similarities_source
            if orphaned_similarities_source > 0:
                issues.append(
                    f"Found {orphaned_similarities_source} similarities with missing source"
                )

            # Check 3: Orphaned similarities (target)
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM decision_similarities ds
                WHERE NOT EXISTS (
                    SELECT 1 FROM decision_nodes dn
                    WHERE dn.id = ds.target_id
                )
            """
            )
            orphaned_similarities_target = cursor.fetchone()[0] or 0
            details["orphaned_similarities_target"] = orphaned_similarities_target
            if orphaned_similarities_target > 0:
                issues.append(
                    f"Found {orphaned_similarities_target} similarities with missing target"
                )

            # Check 4: Invalid timestamps (future dates)
            future_cutoff = datetime.now() + timedelta(days=1)
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM decision_nodes
                WHERE timestamp > ?
                """,
                (future_cutoff.isoformat(),),
            )
            future_timestamps = cursor.fetchone()[0] or 0
            details["future_timestamps"] = future_timestamps
            if future_timestamps > 0:
                issues.append(
                    f"Found {future_timestamps} decisions with future timestamps"
                )

            # Check 5: Missing required fields
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM decision_nodes
                WHERE question IS NULL OR question = ''
                   OR consensus IS NULL
                   OR convergence_status IS NULL OR convergence_status = ''
                   OR participants IS NULL OR participants = '[]'
            """
            )
            missing_fields = cursor.fetchone()[0] or 0
            details["missing_required_fields"] = missing_fields
            if missing_fields > 0:
                issues.append(
                    f"Found {missing_fields} decisions with missing required fields"
                )

            # Check 6: Invalid similarity scores
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM decision_similarities
                WHERE similarity_score < 0.0 OR similarity_score > 1.0
            """
            )
            invalid_scores = cursor.fetchone()[0] or 0
            details["invalid_similarity_scores"] = invalid_scores
            if invalid_scores > 0:
                issues.append(
                    f"Found {invalid_scores} similarities with invalid scores (not 0.0-1.0)"
                )

            # Calculate summary
            checks_total = 6
            checks_failed = len(issues)
            checks_passed = checks_total - checks_failed
            healthy = checks_failed == 0

            result = {
                "healthy": healthy,
                "checks_passed": checks_passed,
                "checks_failed": checks_failed,
                "issues": issues,
                "details": details,
            }

            if healthy:
                logger.info("Health check passed: database is healthy")
            else:
                logger.warning(
                    f"Health check found {checks_failed} issues: {', '.join(issues)}"
                )

            return result

        except Exception as e:
            logger.error(f"Error running health check: {e}", exc_info=True)
            return {
                "healthy": False,
                "checks_passed": 0,
                "checks_failed": 1,
                "issues": [f"Health check error: {str(e)}"],
                "details": {},
            }

    # PHASE 2: Archival methods (skeleton only, not implemented)

    def identify_archive_candidates(
        self, age_days: Optional[int] = None, unused_days: Optional[int] = None
    ) -> List[str]:
        """Identify decisions eligible for archival (Phase 2 - NOT IMPLEMENTED).

        Phase 2 will identify decisions that are:
        - Created >age_days ago (default: 180 days)
        - Not accessed in last unused_days (default: 90 days)

        Args:
            age_days: Minimum age in days for archival (default: 180)
            unused_days: Days since last access for archival (default: 90)

        Returns:
            List of decision IDs eligible for archival

        Note:
            PHASE 1: Returns empty list (not implemented)
            PHASE 2: Will require 'last_accessed' column migration
        """
        logger.info(
            "identify_archive_candidates() called but not implemented (Phase 2 feature)"
        )
        return []

    def archive_old_decisions(self, dry_run: bool = True) -> Dict:
        """Soft archive old, unused decisions (Phase 2 - NOT IMPLEMENTED).

        Phase 2 will mark decisions as archived=TRUE, keeping them in DB for queries
        but potentially optimizing storage/indexes for active decisions.

        Args:
            dry_run: If True, simulate archival without modifying data

        Returns:
            Dictionary with archival results

        Note:
            PHASE 1: Returns not_implemented status
            PHASE 2: Will require migration to add 'archived' column
        """
        logger.info(
            "archive_old_decisions() called but not implemented (Phase 2 feature)"
        )
        return {
            "status": "not_implemented",
            "phase": "Phase 1",
            "message": (
                "Archival is not implemented in Phase 1. "
                "This feature will be enabled in Phase 2 (Month 6+) "
                "after migration adds 'archived' and 'last_accessed' columns."
            ),
            "archived_count": 0,
            "dry_run": dry_run,
        }

    def get_pending_migrations(self) -> List[str]:
        """Get list of SQL migrations needed for Phase 2 archival support.

        Returns:
            List of SQL statements to add archival infrastructure
        """
        migrations = [
            # Migration 1: Add archived column (default FALSE)
            """
            ALTER TABLE decision_nodes
            ADD COLUMN archived BOOLEAN DEFAULT FALSE;
            """,
            # Migration 2: Add last_accessed column (default to timestamp)
            """
            ALTER TABLE decision_nodes
            ADD COLUMN last_accessed TEXT DEFAULT NULL;
            """,
            # Migration 3: Initialize last_accessed to timestamp for existing rows
            """
            UPDATE decision_nodes
            SET last_accessed = timestamp
            WHERE last_accessed IS NULL;
            """,
            # Migration 4: Add index on archived column for queries
            """
            CREATE INDEX IF NOT EXISTS idx_decision_archived
            ON decision_nodes(archived);
            """,
            # Migration 5: Add index on last_accessed for archival queries
            """
            CREATE INDEX IF NOT EXISTS idx_decision_last_accessed
            ON decision_nodes(last_accessed DESC);
            """,
        ]

        logger.debug(f"Generated {len(migrations)} pending migrations for Phase 2")
        return migrations
