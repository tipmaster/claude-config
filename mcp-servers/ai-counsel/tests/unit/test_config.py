"""Unit tests for configuration loading."""
import os
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from models.config import load_config


class TestConfigLoading:
    """Tests for config loading."""

    def test_load_default_config(self):
        """Test loading default config.yaml."""
        config = load_config()
        assert config is not None
        assert config.version == "1.0"
        assert "claude" in config.cli_tools
        assert "codex" in config.cli_tools

    def test_cli_tool_config_structure(self):
        """Test CLI tool config has required fields."""
        config = load_config()
        claude = config.cli_tools["claude"]
        assert claude.command == "claude"
        assert isinstance(claude.args, list)
        assert claude.timeout == 300  # 5 minutes for reasoning models

    def test_defaults_loaded(self):
        """Test default settings are loaded."""
        config = load_config()
        assert config.defaults.mode == "quick"
        assert config.defaults.rounds == 2
        assert config.defaults.max_rounds == 5

    def test_storage_config_loaded(self):
        """Test storage configuration is loaded."""
        config = load_config()
        assert config.storage.transcripts_dir == "transcripts"
        assert config.storage.format == "markdown"
        assert config.storage.auto_export is True

    def test_invalid_config_path_raises_error(self):
        """Test that invalid config path raises error."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")


class TestCLIAdapterConfig:
    """Tests for CLI adapter configuration."""

    def test_valid_cli_adapter_config(self):
        """Test valid CLI adapter configuration."""
        from models.config import CLIAdapterConfig

        config = CLIAdapterConfig(
            type="cli",
            command="claude",
            args=["--model", "{model}", "{prompt}"],
            timeout=60,
        )
        assert config.type == "cli"
        assert config.command == "claude"
        assert config.timeout == 60

    def test_cli_adapter_requires_command(self):
        """Test that command field is required."""
        from models.config import CLIAdapterConfig

        with pytest.raises(ValidationError):
            CLIAdapterConfig(type="cli", args=["--model", "{model}"], timeout=60)


class TestHTTPAdapterConfig:
    """Tests for HTTP adapter configuration."""

    def test_valid_http_adapter_config(self):
        """Test valid HTTP adapter configuration."""
        from models.config import HTTPAdapterConfig

        config = HTTPAdapterConfig(
            type="http", base_url="http://localhost:11434", timeout=60
        )
        assert config.type == "http"
        assert config.base_url == "http://localhost:11434"
        assert config.timeout == 60

    def test_http_adapter_with_api_key_env_var(self):
        """Test HTTP adapter with environment variable substitution."""
        from models.config import HTTPAdapterConfig

        os.environ["TEST_API_KEY"] = "sk-test-123"
        config = HTTPAdapterConfig(
            type="http",
            base_url="https://api.example.com",
            api_key="${TEST_API_KEY}",
            timeout=60,
        )
        # After loading, ${TEST_API_KEY} should be resolved
        assert config.api_key == "sk-test-123"
        del os.environ["TEST_API_KEY"]

    def test_http_adapter_requires_base_url(self):
        """Test that base_url field is required."""
        from models.config import HTTPAdapterConfig

        with pytest.raises(ValidationError):
            HTTPAdapterConfig(type="http", timeout=60)

    def test_http_adapter_missing_api_key_env_var_becomes_none(self):
        """Test that missing api_key environment variable gracefully becomes None."""
        from models.config import HTTPAdapterConfig

        # Make sure the env var doesn't exist
        if "NONEXISTENT_VAR" in os.environ:
            del os.environ["NONEXISTENT_VAR"]

        # api_key is optional, so missing env var should result in None
        config = HTTPAdapterConfig(
            type="http",
            base_url="http://test",
            api_key="${NONEXISTENT_VAR}",
            timeout=60,
        )
        assert config.api_key is None

    def test_http_adapter_missing_base_url_env_var_raises_error(self):
        """Test that missing required base_url env var raises clear error."""
        from models.config import HTTPAdapterConfig

        # Make sure the env var doesn't exist
        if "NONEXISTENT_BASE_URL_VAR" in os.environ:
            del os.environ["NONEXISTENT_BASE_URL_VAR"]

        # base_url is required, so missing env var should raise error
        with pytest.raises(ValidationError) as exc_info:
            HTTPAdapterConfig(
                type="http",
                base_url="${NONEXISTENT_BASE_URL_VAR}",
                timeout=60,
            )

        assert "NONEXISTENT_BASE_URL_VAR" in str(exc_info.value)


class TestAdapterConfig:
    """Tests for discriminated adapter union."""

    def test_adapter_config_discriminates_cli_type(self):
        """Test AdapterConfig discriminates to CLIAdapterConfig."""
        from pydantic import TypeAdapter

        from models.config import CLIAdapterConfig

        data = {
            "type": "cli",
            "command": "claude",
            "args": ["--model", "{model}"],
            "timeout": 60,
        }

        # Use TypeAdapter for discriminated unions
        from models.config import AdapterConfig

        adapter = TypeAdapter(AdapterConfig)
        config = adapter.validate_python(data)
        assert isinstance(config, CLIAdapterConfig)

    def test_adapter_config_discriminates_http_type(self):
        """Test AdapterConfig discriminates to HTTPAdapterConfig."""
        from pydantic import TypeAdapter

        from models.config import HTTPAdapterConfig

        data = {"type": "http", "base_url": "http://localhost:11434", "timeout": 60}

        from models.config import AdapterConfig

        adapter = TypeAdapter(AdapterConfig)
        config = adapter.validate_python(data)
        assert isinstance(config, HTTPAdapterConfig)

    def test_invalid_adapter_type_raises_error(self):
        """Test that invalid type raises ValidationError."""
        from pydantic import TypeAdapter

        from models.config import AdapterConfig

        adapter = TypeAdapter(AdapterConfig)

        with pytest.raises(ValidationError):
            adapter.validate_python(
                {"type": "invalid", "command": "test", "timeout": 60}
            )


class TestConfigLoader:
    """Tests for config loader with adapter migration."""

    def test_load_config_with_adapters_section(self, tmp_path):
        """Test loading config with new adapters section."""
        config_data = {
            "version": "1.0",
            "adapters": {
                "claude": {
                    "type": "cli",
                    "command": "claude",
                    "args": ["--model", "{model}"],
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

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_file))
        assert config.adapters is not None
        assert "claude" in config.adapters
        assert config.cli_tools is None

    def test_load_config_with_cli_tools_emits_warning(self, tmp_path):
        """Test that cli_tools section triggers deprecation warning."""
        config_data = {
            "version": "1.0",
            "cli_tools": {
                "claude": {
                    "command": "claude",
                    "args": ["--model", "{model}"],
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

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(str(config_file))

            # Check warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "cli_tools" in str(w[0].message).lower()
            assert "deprecated" in str(w[0].message).lower()

    def test_load_config_fails_without_adapter_section(self, tmp_path):
        """Test config without adapters or cli_tools raises error."""
        config_data = {
            "version": "1.0",
            # Missing both adapters and cli_tools
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
            yaml.dump(config_data, f)

        with pytest.raises(ValueError) as exc_info:
            load_config(str(config_file))

        assert (
            "adapters" in str(exc_info.value).lower()
            or "cli_tools" in str(exc_info.value).lower()
        )


class TestDecisionGraphConfig:
    """Tests for DecisionGraphConfig path resolution."""

    @pytest.fixture
    def project_root(self):
        """
        Get the actual project root directory.

        The project root is where config.yaml is located, which is two levels
        up from models/config.py where DecisionGraphConfig is defined.
        """
        # This mirrors the logic in DecisionGraphConfig.resolve_db_path
        config_module_path = Path(__file__).parent.parent.parent / "models" / "config.py"
        return config_module_path.parent.parent

    def test_db_path_relative_to_project_root(self, project_root):
        """
        Test that relative path is resolved relative to project root.

        Verifies that "decision_graph.db" resolves to project_root/decision_graph.db,
        not the current working directory. This prevents breakage when running
        the server from different directories.
        """
        from models.config import DecisionGraphConfig

        config = DecisionGraphConfig(enabled=True, db_path="decision_graph.db")

        # Path should be absolute
        resolved_path = Path(config.db_path)
        assert resolved_path.is_absolute(), "Resolved path should be absolute"

        # Path should be at project root
        expected_path = (project_root / "decision_graph.db").resolve()
        assert config.db_path == str(expected_path), (
            f"Expected {expected_path}, got {config.db_path}"
        )

        # Verify it's a string, not a Path object
        assert isinstance(config.db_path, str), "db_path should be returned as string"

    def test_db_path_absolute_unchanged(self, project_root):
        """
        Test that absolute paths are kept unchanged.

        Verifies that absolute paths like "/tmp/graph.db" are not modified
        and remain absolute after validation. Note: symlinks are NOT resolved
        for absolute paths (only relative paths get .resolve() called).
        """
        from models.config import DecisionGraphConfig

        absolute_path = "/tmp/test_graph.db"
        config = DecisionGraphConfig(enabled=True, db_path=absolute_path)

        # Should still be absolute
        resolved_path = Path(config.db_path)
        assert resolved_path.is_absolute(), "Absolute path should remain absolute"

        # Should be unchanged (no symlink resolution for absolute paths)
        assert config.db_path == absolute_path, (
            f"Absolute path should be preserved unchanged"
        )

    def test_db_path_with_env_var(self, project_root, monkeypatch):
        """
        Test that environment variables are resolved before path resolution.

        Verifies that "${DATA_DIR}/graph.db" first resolves the env var,
        then converts the path to absolute if needed. Absolute paths after
        env var resolution are NOT further resolved (no symlink resolution).
        """
        from models.config import DecisionGraphConfig

        # Set up test environment variable with absolute path
        test_data_dir = "/var/data"
        monkeypatch.setenv("TEST_DATA_DIR", test_data_dir)

        config = DecisionGraphConfig(
            enabled=True,
            db_path="${TEST_DATA_DIR}/graph.db"
        )

        # Should resolve env var and path is already absolute (no further resolution)
        expected_path = "/var/data/graph.db"
        assert config.db_path == expected_path, (
            f"Expected {expected_path}, got {config.db_path}"
        )

        # Path should be absolute
        assert Path(config.db_path).is_absolute(), (
            "Path with resolved env var should be absolute"
        )

    def test_db_path_with_relative_env_var(self, project_root, monkeypatch):
        """
        Test that relative paths in env vars are resolved relative to project root.

        Verifies that if DATA_DIR="data" (relative), then "${DATA_DIR}/graph.db"
        resolves to project_root/data/graph.db.
        """
        from models.config import DecisionGraphConfig

        # Set up relative path in environment variable
        monkeypatch.setenv("TEST_DATA_DIR", "data")

        config = DecisionGraphConfig(
            enabled=True,
            db_path="${TEST_DATA_DIR}/graph.db"
        )

        # Should resolve env var, then make absolute relative to project root
        expected_path = (project_root / "data" / "graph.db").resolve()
        assert config.db_path == str(expected_path), (
            f"Expected {expected_path}, got {config.db_path}"
        )

    def test_db_path_parent_directory(self, project_root):
        """
        Test that parent directory references are resolved correctly.

        Verifies that "../shared/graph.db" resolves to the correct absolute
        path, navigating up from project root.
        """
        from models.config import DecisionGraphConfig

        config = DecisionGraphConfig(enabled=True, db_path="../shared/graph.db")

        # Should resolve .. relative to project root
        expected_path = (project_root / ".." / "shared" / "graph.db").resolve()
        assert config.db_path == str(expected_path), (
            f"Expected {expected_path}, got {config.db_path}"
        )

        # Path should be absolute
        assert Path(config.db_path).is_absolute(), (
            "Path with parent directory should be absolute"
        )

    def test_db_path_subdirectory(self, project_root):
        """
        Test that subdirectory paths preserve structure under project root.

        Verifies that "data/graphs/db.db" resolves to
        project_root/data/graphs/db.db with directory structure preserved.
        """
        from models.config import DecisionGraphConfig

        config = DecisionGraphConfig(
            enabled=True,
            db_path="data/graphs/decision_graph.db"
        )

        # Should preserve subdirectory structure under project root
        expected_path = (project_root / "data" / "graphs" / "decision_graph.db").resolve()
        assert config.db_path == str(expected_path), (
            f"Expected {expected_path}, got {config.db_path}"
        )

        # Path should be absolute
        assert Path(config.db_path).is_absolute(), (
            "Subdirectory path should be absolute"
        )

    def test_db_path_missing_env_var(self):
        """
        Test that missing environment variables raise clear error.

        Verifies that referencing an undefined env var like "${MISSING_VAR}/db.db"
        raises a ValueError with a helpful message mentioning the variable name.
        """
        from models.config import DecisionGraphConfig

        # Ensure the env var doesn't exist
        if "NONEXISTENT_TEST_VAR" in os.environ:
            del os.environ["NONEXISTENT_TEST_VAR"]

        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(
                enabled=True,
                db_path="${NONEXISTENT_TEST_VAR}/graph.db"
            )

        # Error message should mention the missing variable
        error_message = str(exc_info.value)
        assert "NONEXISTENT_TEST_VAR" in error_message, (
            "Error should mention the missing environment variable"
        )
        assert "not set" in error_message.lower(), (
            "Error should indicate variable is not set"
        )

    def test_db_path_multiple_env_vars(self, monkeypatch):
        """
        Test that multiple environment variable references are resolved.

        Verifies that paths like "${BASE_DIR}/${DB_NAME}.db" resolve both
        environment variables correctly.
        """
        from models.config import DecisionGraphConfig

        monkeypatch.setenv("TEST_BASE_DIR", "/opt/app")
        monkeypatch.setenv("TEST_DB_NAME", "decisions")

        config = DecisionGraphConfig(
            enabled=True,
            db_path="${TEST_BASE_DIR}/${TEST_DB_NAME}.db"
        )

        # Both env vars should be resolved
        expected_path = Path("/opt/app/decisions.db").resolve()
        assert config.db_path == str(expected_path), (
            f"Expected {expected_path}, got {config.db_path}"
        )

    def test_db_path_default_value(self, project_root):
        """
        Test that default db_path value is set correctly.

        Verifies that when db_path is not specified, the default value
        "decision_graph.db" is used. Note: Pydantic field validators only
        run on explicitly provided values, not on Field defaults, so the
        default remains as the literal string.
        """
        from models.config import DecisionGraphConfig

        # Use default value (don't specify db_path)
        config = DecisionGraphConfig(enabled=True)

        # Default is the literal string (validator doesn't run on Field defaults)
        assert config.db_path == "decision_graph.db", (
            f"Expected default 'decision_graph.db', got {config.db_path}"
        )

    def test_db_path_cwd_independence(self, project_root, tmp_path, monkeypatch):
        """
        Test that db_path resolution is independent of current working directory.

        Verifies that relative paths are always resolved relative to project root,
        not the current working directory. This is critical for reliability when
        running the server from different directories.
        """
        from models.config import DecisionGraphConfig

        # Change to a temporary directory
        monkeypatch.chdir(tmp_path)

        # Verify we're in a different directory
        assert Path.cwd() != project_root, "Should be in different directory"

        # Create config with relative path
        config = DecisionGraphConfig(enabled=True, db_path="decision_graph.db")

        # Path should still resolve relative to project root, not cwd
        expected_path = (project_root / "decision_graph.db").resolve()
        assert config.db_path == str(expected_path), (
            f"Path should be relative to project root, not cwd"
        )

        # Should NOT be in tmp_path
        assert not config.db_path.startswith(str(tmp_path)), (
            "Path should not be relative to current working directory"
        )

    def test_db_path_home_directory_expansion(self, project_root):
        """
        Test that home directory (~) references are treated as relative paths.

        Note: The current implementation treats "~/data/graph.db" as a relative
        path (since Path("~/data/graph.db").is_absolute() returns False), so it
        gets resolved relative to project root. This is a known limitation.
        If you need home directory expansion, use an absolute path or env var.
        """
        from models.config import DecisionGraphConfig

        config = DecisionGraphConfig(enabled=True, db_path="~/data/graph.db")

        # Current behavior: ~ is treated as relative path, resolved from project root
        # This is because Path("~/data").is_absolute() returns False
        expected_path = (project_root / "~" / "data" / "graph.db").resolve()
        assert config.db_path == str(expected_path), (
            f"Expected {expected_path}, got {config.db_path}"
        )

        # Should be absolute (resolved from project root)
        assert Path(config.db_path).is_absolute(), (
            "Path should be absolute after resolution"
        )

    def test_db_path_validation_fields(self):
        """
        Test that other DecisionGraphConfig fields validate correctly alongside db_path.

        Verifies that db_path validation doesn't interfere with validation
        of other fields like similarity_threshold and max_context_decisions.
        """
        from models.config import DecisionGraphConfig

        config = DecisionGraphConfig(
            enabled=True,
            db_path="test.db",
            similarity_threshold=0.8,
            max_context_decisions=5,
            compute_similarities=False,
        )

        # All fields should be validated correctly
        assert config.enabled is True
        assert Path(config.db_path).is_absolute()
        assert config.similarity_threshold == 0.8
        assert config.max_context_decisions == 5
        assert config.compute_similarities is False

    def test_db_path_invalid_similarity_threshold_still_validates_path(self, project_root):
        """
        Test that db_path is validated even if other field validation fails.

        Verifies that the db_path validator runs before other field validators
        fail, ensuring consistent error messages.
        """
        from models.config import DecisionGraphConfig

        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(
                enabled=True,
                db_path="test.db",  # Valid, should be processed
                similarity_threshold=1.5,  # Invalid, exceeds max
            )

        # Should fail on similarity_threshold, not db_path
        error_message = str(exc_info.value)
        assert "similarity_threshold" in error_message.lower(), (
            "Should report similarity_threshold validation error"
        )


class TestDecisionGraphBudgetAwareConfig:
    """Tests for budget-aware context injection configuration (Task 1)."""

    def test_decision_graph_config_budget_fields(self):
        """Budget fields exist with sensible defaults."""
        from models.config import DecisionGraphConfig

        config = DecisionGraphConfig(enabled=True)

        # Verify new fields exist
        assert hasattr(config, 'context_token_budget'), "Missing context_token_budget field"
        assert hasattr(config, 'tier_boundaries'), "Missing tier_boundaries field"
        assert hasattr(config, 'query_window'), "Missing query_window field"

        # Verify defaults
        assert config.context_token_budget == 1500, "Default context_token_budget should be 1500"
        assert config.tier_boundaries == {"strong": 0.75, "moderate": 0.60}, \
            "Default tier_boundaries should be {strong: 0.75, moderate: 0.60}"
        assert config.query_window == 1000, "Default query_window should be 1000"

    def test_decision_graph_config_tier_boundaries_validation(self):
        """Tier boundaries must be in order: strong > moderate > 0."""
        from models.config import DecisionGraphConfig

        # Valid: 0.75 > 0.60
        config = DecisionGraphConfig(
            enabled=True,
            tier_boundaries={"strong": 0.75, "moderate": 0.60}
        )
        assert config.tier_boundaries["strong"] > config.tier_boundaries["moderate"], \
            "Strong threshold should be greater than moderate"
        assert config.tier_boundaries["moderate"] > 0.0, \
            "Moderate threshold should be greater than 0"

        # Invalid: strong <= moderate should raise
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(
                enabled=True,
                tier_boundaries={"strong": 0.60, "moderate": 0.60}
            )
        assert "tier_boundaries" in str(exc_info.value).lower(), \
            "Error should mention tier_boundaries"

        # Invalid: strong < moderate (reversed order)
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(
                enabled=True,
                tier_boundaries={"strong": 0.50, "moderate": 0.70}
            )
        assert "tier_boundaries" in str(exc_info.value).lower(), \
            "Error should mention tier_boundaries"

        # Invalid: moderate <= 0
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(
                enabled=True,
                tier_boundaries={"strong": 0.75, "moderate": 0.0}
            )
        assert "tier_boundaries" in str(exc_info.value).lower(), \
            "Error should mention tier_boundaries"

        # Invalid: missing keys
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(
                enabled=True,
                tier_boundaries={"strong": 0.75}  # Missing 'moderate'
            )
        assert "tier_boundaries" in str(exc_info.value).lower(), \
            "Error should mention tier_boundaries"

        # Invalid: strong > 1.0
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(
                enabled=True,
                tier_boundaries={"strong": 1.5, "moderate": 0.60}
            )
        assert "tier_boundaries" in str(exc_info.value).lower(), \
            "Error should mention tier_boundaries"

    def test_decision_graph_config_query_window_validation(self):
        """Query window must be >= 50 and <= 10000."""
        from models.config import DecisionGraphConfig

        # Valid: within range
        config = DecisionGraphConfig(enabled=True, query_window=500)
        assert config.query_window == 500

        # Valid: at lower boundary
        config = DecisionGraphConfig(enabled=True, query_window=50)
        assert config.query_window == 50

        # Valid: at upper boundary
        config = DecisionGraphConfig(enabled=True, query_window=10000)
        assert config.query_window == 10000

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(enabled=True, query_window=49)
        assert "query_window" in str(exc_info.value).lower(), \
            "Error should mention query_window"

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(enabled=True, query_window=10001)
        assert "query_window" in str(exc_info.value).lower(), \
            "Error should mention query_window"

        # Invalid: negative value
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(enabled=True, query_window=-100)
        assert "query_window" in str(exc_info.value).lower(), \
            "Error should mention query_window"

    def test_decision_graph_config_context_token_budget_validation(self):
        """Context token budget must be >= 500 and <= 10000."""
        from models.config import DecisionGraphConfig

        # Valid: within range
        config = DecisionGraphConfig(enabled=True, context_token_budget=1500)
        assert config.context_token_budget == 1500

        # Valid: at lower boundary
        config = DecisionGraphConfig(enabled=True, context_token_budget=500)
        assert config.context_token_budget == 500

        # Valid: at upper boundary
        config = DecisionGraphConfig(enabled=True, context_token_budget=10000)
        assert config.context_token_budget == 10000

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(enabled=True, context_token_budget=499)
        assert "context_token_budget" in str(exc_info.value).lower(), \
            "Error should mention context_token_budget"

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            DecisionGraphConfig(enabled=True, context_token_budget=10001)
        assert "context_token_budget" in str(exc_info.value).lower(), \
            "Error should mention context_token_budget"

    def test_decision_graph_config_backward_compatibility(self):
        """Old config (without new fields) still loads with defaults."""
        from models.config import DecisionGraphConfig

        # Create config with only old fields (no new budget-aware fields)
        config = DecisionGraphConfig(
            enabled=True,
            db_path="test.db",
            similarity_threshold=0.7,
            max_context_decisions=3,
            compute_similarities=True
        )

        # Should still work and have default values for new fields
        assert config.enabled is True
        assert config.similarity_threshold == 0.7
        assert config.max_context_decisions == 3

        # New fields should have defaults
        assert config.context_token_budget == 1500
        assert config.tier_boundaries == {"strong": 0.75, "moderate": 0.60}
        assert config.query_window == 1000

    def test_decision_graph_config_deprecated_threshold(self):
        """similarity_threshold still accepted for backward compatibility."""
        from models.config import DecisionGraphConfig

        # Old style: using similarity_threshold
        config = DecisionGraphConfig(
            enabled=True,
            similarity_threshold=0.8
        )

        # Should still accept and store the value
        assert config.similarity_threshold == 0.8

        # Should also have new fields with defaults
        assert config.context_token_budget == 1500
        assert config.tier_boundaries == {"strong": 0.75, "moderate": 0.60}

        # Can override new fields explicitly
        config2 = DecisionGraphConfig(
            enabled=True,
            similarity_threshold=0.8,  # Old field
            context_token_budget=2000,  # New field
            tier_boundaries={"strong": 0.80, "moderate": 0.65}
        )

        assert config2.similarity_threshold == 0.8
        assert config2.context_token_budget == 2000
        assert config2.tier_boundaries == {"strong": 0.80, "moderate": 0.65}

    def test_config_yaml_loads_new_parameters(self):
        """Load config.yaml successfully with new budget-aware parameters."""
        # Load actual config.yaml from project root
        config = load_config()

        # Verify decision_graph section exists
        assert config.decision_graph is not None, "decision_graph section should exist"

        # Verify new budget-aware parameters are loaded
        assert hasattr(config.decision_graph, 'context_token_budget'), \
            "config.yaml should define context_token_budget"
        assert hasattr(config.decision_graph, 'tier_boundaries'), \
            "config.yaml should define tier_boundaries"
        assert hasattr(config.decision_graph, 'query_window'), \
            "config.yaml should define query_window"

        # Verify expected values from config.yaml
        assert config.decision_graph.context_token_budget == 1500, \
            "context_token_budget should be 1500 in config.yaml"
        assert config.decision_graph.tier_boundaries == {"strong": 0.75, "moderate": 0.60}, \
            "tier_boundaries should be {strong: 0.75, moderate: 0.60} in config.yaml"
        assert config.decision_graph.query_window == 1000, \
            "query_window should be 1000 in config.yaml"

        # Verify deprecated field is still present (backward compatibility)
        assert hasattr(config.decision_graph, 'similarity_threshold'), \
            "similarity_threshold should still exist for backward compatibility"


class TestFileTreeConfig:
    """Tests for FileTreeConfig validation."""

    def test_file_tree_config_defaults(self):
        """Test FileTreeConfig default values."""
        from models.config import FileTreeConfig

        config = FileTreeConfig()
        assert config.max_depth == 3
        assert config.max_files == 100
        assert config.enabled is True

    def test_file_tree_config_custom_values(self):
        """Test FileTreeConfig with custom values."""
        from models.config import FileTreeConfig

        config = FileTreeConfig(max_depth=5, max_files=50, enabled=False)
        assert config.max_depth == 5
        assert config.max_files == 50
        assert config.enabled is False

    def test_file_tree_config_max_depth_validation(self):
        """Test FileTreeConfig validates max_depth range (1-10)."""
        from models.config import FileTreeConfig

        # Valid values
        FileTreeConfig(max_depth=1)  # Minimum
        FileTreeConfig(max_depth=5)  # Middle
        FileTreeConfig(max_depth=10)  # Maximum

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            FileTreeConfig(max_depth=0)
        assert "max_depth" in str(exc_info.value).lower()

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            FileTreeConfig(max_depth=11)
        assert "max_depth" in str(exc_info.value).lower()

        # Invalid: negative value
        with pytest.raises(ValidationError) as exc_info:
            FileTreeConfig(max_depth=-1)
        assert "max_depth" in str(exc_info.value).lower()

    def test_file_tree_config_max_files_validation(self):
        """Test FileTreeConfig validates max_files range (10-1000)."""
        from models.config import FileTreeConfig

        # Valid values
        FileTreeConfig(max_files=10)  # Minimum
        FileTreeConfig(max_files=100)  # Middle
        FileTreeConfig(max_files=1000)  # Maximum

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            FileTreeConfig(max_files=5)
        assert "max_files" in str(exc_info.value).lower()

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            FileTreeConfig(max_files=1001)
        assert "max_files" in str(exc_info.value).lower()

        # Invalid: negative value
        with pytest.raises(ValidationError) as exc_info:
            FileTreeConfig(max_files=-10)
        assert "max_files" in str(exc_info.value).lower()

    def test_file_tree_config_enabled_field(self):
        """Test FileTreeConfig enabled field accepts booleans."""
        from models.config import FileTreeConfig

        # Valid boolean values
        config_true = FileTreeConfig(enabled=True)
        assert config_true.enabled is True

        config_false = FileTreeConfig(enabled=False)
        assert config_false.enabled is False

    def test_deliberation_config_has_file_tree(self):
        """Test DeliberationConfig includes file_tree field."""
        from models.config import DeliberationConfig, FileTreeConfig, ConvergenceDetectionConfig, EarlyStoppingConfig

        config = DeliberationConfig(
            convergence_detection=ConvergenceDetectionConfig(
                enabled=True,
                semantic_similarity_threshold=0.85,
                divergence_threshold=0.40,
                min_rounds_before_check=1,
                consecutive_stable_rounds=2,
                stance_stability_threshold=0.80,
                response_length_drop_threshold=0.40,
            ),
            early_stopping=EarlyStoppingConfig(
                enabled=True,
                threshold=0.66,
                respect_min_rounds=True,
            ),
            convergence_threshold=0.8,
            enable_convergence_detection=True,
        )

        # Should have file_tree field with defaults
        assert hasattr(config, 'file_tree')
        assert isinstance(config.file_tree, FileTreeConfig)
        assert config.file_tree.max_depth == 3
        assert config.file_tree.max_files == 100
        assert config.file_tree.enabled is True

    def test_deliberation_config_custom_file_tree(self):
        """Test DeliberationConfig with custom file_tree values."""
        from models.config import DeliberationConfig, FileTreeConfig, ConvergenceDetectionConfig, EarlyStoppingConfig

        custom_file_tree = FileTreeConfig(max_depth=5, max_files=200, enabled=False)

        config = DeliberationConfig(
            convergence_detection=ConvergenceDetectionConfig(
                enabled=True,
                semantic_similarity_threshold=0.85,
                divergence_threshold=0.40,
                min_rounds_before_check=1,
                consecutive_stable_rounds=2,
                stance_stability_threshold=0.80,
                response_length_drop_threshold=0.40,
            ),
            early_stopping=EarlyStoppingConfig(
                enabled=True,
                threshold=0.66,
                respect_min_rounds=True,
            ),
            convergence_threshold=0.8,
            enable_convergence_detection=True,
            file_tree=custom_file_tree,
        )

        # Should have custom values
        assert config.file_tree.max_depth == 5
        assert config.file_tree.max_files == 200
        assert config.file_tree.enabled is False

    def test_config_yaml_loads_file_tree(self):
        """Test config.yaml loads file_tree section successfully."""
        # Load actual config.yaml from project root
        config = load_config()

        # Verify deliberation section exists
        assert config.deliberation is not None

        # Verify file_tree field exists
        assert hasattr(config.deliberation, 'file_tree')

        # Verify expected values from config.yaml
        assert config.deliberation.file_tree.enabled is True
        assert config.deliberation.file_tree.max_depth == 3
        assert config.deliberation.file_tree.max_files == 100
