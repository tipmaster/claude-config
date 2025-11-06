"""Tests for config migration script."""
import pytest
import yaml


class TestMigrateConfig:
    """Tests for config migration functionality."""

    def test_migrate_cli_tools_to_adapters(self, tmp_path):
        """Test migration adds type: cli to existing tools."""
        from scripts.migrate_config import migrate_config_dict

        old_config = {
            "version": "1.0",
            "cli_tools": {
                "claude": {
                    "command": "claude",
                    "args": ["--model", "{model}"],
                    "timeout": 60,
                },
                "codex": {
                    "command": "codex",
                    "args": ["exec", "{prompt}"],
                    "timeout": 120,
                },
            },
            "defaults": {
                "mode": "quick",
                "rounds": 2,
                "max_rounds": 5,
                "timeout_per_round": 120,
            },
            "storage": {
                "transcripts_dir": "transcripts",
                "format": "markdown",
                "auto_export": True,
            },
            "deliberation": {
                "convergence_detection": {
                    "enabled": True,
                    "semantic_similarity_threshold": 0.85,
                    "divergence_threshold": 0.40,
                    "min_rounds_before_check": 1,
                    "consecutive_stable_rounds": 2,
                    "stance_stability_threshold": 0.80,
                    "response_length_drop_threshold": 0.40,
                },
                "early_stopping": {
                    "enabled": True,
                    "threshold": 0.66,
                    "respect_min_rounds": True,
                },
                "convergence_threshold": 0.8,
                "enable_convergence_detection": True,
            },
        }

        # Run migration
        new_config = migrate_config_dict(old_config)

        # Verify structure
        assert "adapters" in new_config
        assert "cli_tools" not in new_config
        assert new_config["adapters"]["claude"]["type"] == "cli"
        assert new_config["adapters"]["codex"]["type"] == "cli"
        assert new_config["adapters"]["claude"]["command"] == "claude"
        assert new_config["adapters"]["codex"]["timeout"] == 120

        # Verify other sections preserved
        assert new_config["version"] == "1.0"
        assert new_config["defaults"]["mode"] == "quick"
        assert new_config["storage"]["transcripts_dir"] == "transcripts"

    def test_migrate_creates_backup(self, tmp_path):
        """Test that migration creates .bak file."""
        from scripts.migrate_config import migrate_config_file

        old_config = {
            "version": "1.0",
            "cli_tools": {"claude": {"command": "claude", "args": [], "timeout": 60}},
            "defaults": {
                "mode": "quick",
                "rounds": 2,
                "max_rounds": 5,
                "timeout_per_round": 120,
            },
            "storage": {
                "transcripts_dir": "transcripts",
                "format": "markdown",
                "auto_export": True,
            },
            "deliberation": {
                "convergence_detection": {
                    "enabled": True,
                    "semantic_similarity_threshold": 0.85,
                    "divergence_threshold": 0.40,
                    "min_rounds_before_check": 1,
                    "consecutive_stable_rounds": 2,
                    "stance_stability_threshold": 0.80,
                    "response_length_drop_threshold": 0.40,
                },
                "early_stopping": {
                    "enabled": True,
                    "threshold": 0.66,
                    "respect_min_rounds": True,
                },
                "convergence_threshold": 0.8,
                "enable_convergence_detection": True,
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(old_config, f)

        migrate_config_file(str(config_file))

        backup_file = tmp_path / "config.yaml.bak"
        assert backup_file.exists()

        # Verify backup contains original
        with open(backup_file, "r") as f:
            backup_config = yaml.safe_load(f)
        assert "cli_tools" in backup_config

    def test_migrate_already_migrated_is_idempotent(self, tmp_path):
        """Test migrating already-migrated config doesn't break."""
        from scripts.migrate_config import migrate_config_dict

        already_migrated = {
            "version": "1.0",
            "adapters": {
                "claude": {
                    "type": "cli",
                    "command": "claude",
                    "args": [],
                    "timeout": 60,
                }
            },
            "defaults": {
                "mode": "quick",
                "rounds": 2,
                "max_rounds": 5,
                "timeout_per_round": 120,
            },
            "storage": {
                "transcripts_dir": "transcripts",
                "format": "markdown",
                "auto_export": True,
            },
            "deliberation": {
                "convergence_detection": {
                    "enabled": True,
                    "semantic_similarity_threshold": 0.85,
                    "divergence_threshold": 0.40,
                    "min_rounds_before_check": 1,
                    "consecutive_stable_rounds": 2,
                    "stance_stability_threshold": 0.80,
                    "response_length_drop_threshold": 0.40,
                },
                "early_stopping": {
                    "enabled": True,
                    "threshold": 0.66,
                    "respect_min_rounds": True,
                },
                "convergence_threshold": 0.8,
                "enable_convergence_detection": True,
            },
        }

        # Should not raise error
        result = migrate_config_dict(already_migrated)

        # Should be unchanged
        assert result == already_migrated

    def test_migrate_preserves_all_tools(self, tmp_path):
        """Test all CLI tools are migrated."""
        from scripts.migrate_config import migrate_config_dict

        old_config = {
            "version": "1.0",
            "cli_tools": {
                "claude": {"command": "claude", "args": [], "timeout": 60},
                "codex": {"command": "codex", "args": [], "timeout": 120},
                "droid": {"command": "droid", "args": [], "timeout": 180},
                "gemini": {"command": "gemini", "args": [], "timeout": 90},
            },
            "defaults": {
                "mode": "quick",
                "rounds": 2,
                "max_rounds": 5,
                "timeout_per_round": 120,
            },
            "storage": {
                "transcripts_dir": "transcripts",
                "format": "markdown",
                "auto_export": True,
            },
            "deliberation": {
                "convergence_detection": {
                    "enabled": True,
                    "semantic_similarity_threshold": 0.85,
                    "divergence_threshold": 0.40,
                    "min_rounds_before_check": 1,
                    "consecutive_stable_rounds": 2,
                    "stance_stability_threshold": 0.80,
                    "response_length_drop_threshold": 0.40,
                },
                "early_stopping": {
                    "enabled": True,
                    "threshold": 0.66,
                    "respect_min_rounds": True,
                },
                "convergence_threshold": 0.8,
                "enable_convergence_detection": True,
            },
        }

        new_config = migrate_config_dict(old_config)

        assert len(new_config["adapters"]) == 4
        assert all(
            tool in new_config["adapters"]
            for tool in ["claude", "codex", "droid", "gemini"]
        )
        assert all(
            new_config["adapters"][tool]["type"] == "cli"
            for tool in ["claude", "codex", "droid", "gemini"]
        )

    def test_migrate_file_not_found(self):
        """Test that missing file raises error."""
        from scripts.migrate_config import migrate_config_file

        with pytest.raises(FileNotFoundError):
            migrate_config_file("/nonexistent/path/config.yaml")
