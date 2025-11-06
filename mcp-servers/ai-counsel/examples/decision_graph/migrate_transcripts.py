#!/usr/bin/env python3
"""
Migration example: Back-fill transcripts into decision graph

This example shows how to take existing deliberation transcripts
and populate the decision graph with them. Useful for organizations
that have existing deliberation history and want to enable the
graph feature retroactively.

Requirements:
- AI Counsel installed with decision graph enabled
- Existing transcripts in transcripts/ directory
"""

# ruff: noqa: E402  # Standalone script requires sys.path manipulation before imports

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from decision_graph.schema import DecisionNode
from decision_graph.storage import DecisionGraphStorage
from models.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_metadata_from_transcript(transcript_path: Path) -> dict:
    """
    Extract metadata from a transcript markdown file.

    This is a simplified parser that looks for key sections.
    Real implementation would parse more sophisticated formats.
    """
    metadata = {
        "question": "Unknown question",
        "consensus": "See transcript for details",
        "participants": [],
        "timestamp": datetime.now(),
    }

    try:
        content = transcript_path.read_text()

        # Extract question from filename or content
        # Filename format: YYYYMMDD_HHMMSS_Question_truncated.md
        filename = transcript_path.stem
        parts = filename.split("_", 2)
        if len(parts) > 2:
            question = parts[2].replace("_", " ")
            metadata["question"] = question

        # Try to extract timestamp from filename
        if len(parts) >= 2:
            try:
                date_str = parts[0] + parts[1]
                ts = datetime.strptime(date_str, "%Y%m%d%H%M%S")
                metadata["timestamp"] = ts
            except ValueError:
                pass

        # Look for summary section
        if "## Summary" in content:
            summary_start = content.find("## Summary")
            summary_section = content[summary_start : summary_start + 500]
            if "**Consensus:** " in summary_section:
                consensus_line = [
                    line
                    for line in summary_section.split("\n")
                    if "**Consensus:** " in line
                ]
                if consensus_line:
                    metadata["consensus"] = (
                        consensus_line[0].replace("**Consensus:** ", "").strip()
                    )

        # Look for participants
        if "**Participants:** " in content:
            for line in content.split("\n"):
                if "**Participants:** " in line:
                    participants_str = line.replace("**Participants:** ", "").strip()
                    metadata["participants"] = [
                        p.strip() for p in participants_str.split(",")
                    ]
                    break

    except Exception as e:
        logger.warning(f"Could not parse transcript {transcript_path}: {e}")

    return metadata


async def migrate_transcripts_to_graph(
    transcripts_dir: Path = None, dry_run: bool = True
) -> int:
    """
    Migrate existing transcripts into the decision graph.

    Args:
        transcripts_dir: Path to transcripts directory (default: ./transcripts)
        dry_run: If True, only show what would be migrated (no modifications)

    Returns:
        Number of transcripts migrated
    """

    if transcripts_dir is None:
        transcripts_dir = Path("transcripts")

    if not transcripts_dir.exists():
        logger.error(f"Transcripts directory not found: {transcripts_dir}")
        return 0

    # Load config
    config = load_config()

    if not config.decision_graph.enabled:
        logger.error(
            "Decision graph must be enabled in config.yaml\n"
            "Enable: decision_graph.enabled: true"
        )
        return 0

    # Find all transcripts
    transcripts = list(transcripts_dir.glob("*.md"))
    logger.info(f"Found {len(transcripts)} transcripts to migrate\n")

    if not transcripts:
        logger.warning("No transcripts found in: " + str(transcripts_dir))
        return 0

    # Initialize storage
    storage = DecisionGraphStorage(config.decision_graph.db_path)

    migrated_count = 0

    for transcript_path in transcripts:
        logger.info(f"Processing: {transcript_path.name}")

        # Extract metadata
        metadata = extract_metadata_from_transcript(transcript_path)
        logger.info(f"  Question: {metadata['question'][:60]}...")
        logger.info(f"  Consensus: {metadata['consensus'][:60]}...")
        logger.info(f"  Participants: {', '.join(metadata['participants'])}")

        if not dry_run:
            try:
                # Create decision node
                decision = DecisionNode(
                    question=metadata["question"],
                    timestamp=metadata["timestamp"],
                    consensus=metadata["consensus"],
                    convergence_status="imported",
                    participants=metadata["participants"],
                    transcript_path=str(transcript_path),
                )

                # Save to storage
                storage.save_decision(decision)
                logger.info("  ✓ Saved to graph")
                migrated_count += 1

            except Exception as e:
                logger.error(f"  ✗ Error saving: {e}")
        else:
            logger.info("  [DRY RUN] Would be saved to graph")
            migrated_count += 1

        logger.info("")

    return migrated_count


async def main():
    """Run migration example."""

    logger.info("🔄 Decision Graph Migration Example\n")
    logger.info("=" * 60)

    # Dry run first (no modifications)
    logger.info("📋 DRY RUN: Showing what would be migrated...\n")
    count_dry = await migrate_transcripts_to_graph(dry_run=True)

    logger.info("=" * 60)
    logger.info(f"\n✅ Dry run complete: {count_dry} transcripts would be migrated\n")

    # Ask for confirmation
    if count_dry > 0:
        response = input("Proceed with migration? (y/n): ").strip().lower()

        if response == "y":
            logger.info("\n🚀 Running actual migration...\n")
            logger.info("=" * 60 + "\n")

            count_actual = await migrate_transcripts_to_graph(dry_run=False)

            logger.info("=" * 60)
            logger.info(f"\n✨ Migration complete: {count_actual} transcripts migrated")
            logger.info("\nNext steps:")
            logger.info(
                "- Query the graph: ai-counsel graph similar --query 'your topic'"
            )
            logger.info("- View graph stats: ai-counsel graph analyze")
        else:
            logger.info("Migration cancelled.")
    else:
        logger.info("No transcripts to migrate.")


if __name__ == "__main__":
    asyncio.run(main())
