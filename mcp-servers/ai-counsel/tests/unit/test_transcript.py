"""Unit tests for transcript management."""
from pathlib import Path
import shutil

import pytest

from deliberation.transcript import TranscriptManager
from models.schema import DeliberationResult, RoundResponse, Summary


@pytest.fixture
def sample_result():
    """Fixture providing a sample deliberation result."""
    return DeliberationResult(
        status="complete",
        mode="conference",
        rounds_completed=2,
        participants=["claude-3-5-sonnet@claude-code", "gpt-4@codex"],
        summary=Summary(
            consensus="Strong agreement on TypeScript adoption",
            key_agreements=["Better type safety", "Improved IDE support"],
            key_disagreements=["Learning curve concerns"],
            final_recommendation="Adopt TypeScript for new modules",
        ),
        transcript_path="",
        full_debate=[
            RoundResponse(
                round=1,
                participant="claude-3-5-sonnet@claude-code",
                response="I think TypeScript offers...",
                timestamp="2025-10-12T15:30:00Z",
            ),
            RoundResponse(
                round=1,
                participant="gpt-4@codex",
                response="TypeScript is excellent because...",
                timestamp="2025-10-12T15:30:05Z",
            ),
        ],
    )


class TestTranscriptManager:
    """Tests for TranscriptManager."""

    def test_generate_markdown(self, sample_result, tmp_path):
        """Test generating markdown transcript."""
        manager = TranscriptManager(output_dir=str(tmp_path))

        markdown = manager.generate_markdown(sample_result)

        assert "# AI Counsel Deliberation Transcript" in markdown
        assert "## Summary" in markdown
        assert "Strong agreement on TypeScript" in markdown
        assert "## Round 1" in markdown
        assert "claude-3-5-sonnet@claude-code" in markdown
        assert "I think TypeScript offers" in markdown

    def test_save_transcript(self, sample_result, tmp_path):
        """Test saving transcript to file."""
        manager = TranscriptManager(output_dir=str(tmp_path))

        filepath = manager.save(sample_result, question="Should we use TypeScript?")

        assert Path(filepath).exists()
        assert Path(filepath).suffix == ".md"

        # Verify content
        content = Path(filepath).read_text()
        assert "Should we use TypeScript?" in content
        assert "Strong agreement on TypeScript" in content

    def test_generates_unique_filenames(self, sample_result, tmp_path):
        """Test that multiple saves generate unique filenames."""
        manager = TranscriptManager(output_dir=str(tmp_path))

        file1 = manager.save(sample_result, "Question 1")
        file2 = manager.save(sample_result, "Question 2")

        assert file1 != file2
        assert Path(file1).exists()
        assert Path(file2).exists()

    def test_save_recreates_missing_directory(self, sample_result, tmp_path):
        """Transcript saving should recreate output directory if it was removed."""
        output_dir = tmp_path / "transcripts"
        manager = TranscriptManager(output_dir=str(output_dir))

        # Remove directory after initialization to simulate external deletion
        shutil.rmtree(output_dir)

        filepath = manager.save(sample_result, "Recover Missing Dir")

        assert Path(filepath).exists()
        assert output_dir.exists()
