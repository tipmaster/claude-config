"""Configuration loading and validation."""
import os
import re
import warnings
from pathlib import Path
from typing import Annotated, List, Literal, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class CLIAdapterConfig(BaseModel):
    """Configuration for CLI-based adapter."""

    type: Literal["cli"] = "cli"
    command: str
    args: list[str]
    timeout: int = 60


class HTTPAdapterConfig(BaseModel):
    """Configuration for HTTP-based adapter."""

    type: Literal["http"] = "http"
    base_url: str
    api_key: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    timeout: int = 60
    max_retries: int = 3

    @field_validator("api_key", "base_url")
    @classmethod
    def resolve_env_vars(cls, v: Optional[str], info) -> Optional[str]:
        """Resolve ${ENV_VAR} references in string fields.

        For optional fields like api_key:
        - If env var is missing, returns None (allows graceful degradation)

        For required fields like base_url:
        - If env var is missing, raises ValueError
        """
        if v is None:
            return v

        # Pattern: ${VAR_NAME}
        pattern = r"\$\{([^}]+)\}"
        is_api_key = info.field_name == "api_key"

        def replacer(match):
            env_var = match.group(1)
            value = os.getenv(env_var)
            if value is None:
                # For optional fields like api_key, use a sentinel marker
                if is_api_key:
                    return "__MISSING_API_KEY__"  # Sentinel to detect later
                # For required fields, raise error
                raise ValueError(
                    f"Environment variable '{env_var}' is not set. "
                    f"Required for configuration."
                )
            return value

        result = re.sub(pattern, replacer, v)
        # If api_key has sentinel marker, return None (graceful degradation)
        if is_api_key and "__MISSING_API_KEY__" in result:
            return None
        return result


# Discriminated union - Pydantic uses 'type' field to determine which model to use
AdapterConfig = Annotated[
    Union[CLIAdapterConfig, HTTPAdapterConfig], Field(discriminator="type")
]


class CLIToolConfig(BaseModel):
    """Configuration for a single CLI tool (legacy, deprecated)."""

    command: str
    args: list[str]
    timeout: int


class DefaultsConfig(BaseModel):
    """Default settings."""

    mode: str
    rounds: int
    max_rounds: int
    timeout_per_round: int


class ModelDefinition(BaseModel):
    """Single model entry in the registry."""

    id: str = Field(..., description="Model identifier used by the adapter")
    label: Optional[str] = Field(
        None, description="Human-friendly label for the model"
    )
    tier: Optional[str] = Field(None, description="Cost/quality tier hint")
    default: bool = Field(
        False, description="Whether this model should be used as the default"
    )
    note: Optional[str] = Field(
        None, description="Optional additional guidance about the model"
    )


class StorageConfig(BaseModel):
    """Storage configuration."""

    transcripts_dir: str
    format: str
    auto_export: bool


class ConvergenceDetectionConfig(BaseModel):
    """Convergence detection configuration."""

    enabled: bool
    semantic_similarity_threshold: float
    divergence_threshold: float
    min_rounds_before_check: int
    consecutive_stable_rounds: int
    stance_stability_threshold: float
    response_length_drop_threshold: float


class EarlyStoppingConfig(BaseModel):
    """Model-controlled early stopping configuration."""

    enabled: bool
    threshold: float  # Fraction of models that must want to stop (e.g., 0.66 = 2/3)
    respect_min_rounds: bool  # Whether to respect defaults.rounds before stopping


class FileTreeConfig(BaseModel):
    """Configuration for file tree generation in Round 1 prompts."""

    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum directory depth to scan"
    )
    max_files: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum number of files to include"
    )
    enabled: bool = Field(
        default=True,
        description="Enable auto-injection of file tree in Round 1"
    )


class ToolSecurityConfig(BaseModel):
    """Security configuration for evidence-based deliberation tools."""

    exclude_patterns: List[str] = Field(
        default=[
            "transcripts/",
            "transcripts/**",
            ".git/",
            ".git/**",
            "node_modules/",
            "node_modules/**",
            ".venv/",
            "venv/",
            "__pycache__/",
        ],
        description="Patterns to exclude from tool access (prevents context contamination)"
    )
    max_file_size_bytes: int = Field(
        default=1_048_576,  # 1MB
        ge=1024,
        le=10_485_760,  # 10MB
        description="Maximum file size for read_file tool"
    )


class DeliberationConfig(BaseModel):
    """Deliberation engine configuration."""

    convergence_detection: ConvergenceDetectionConfig
    early_stopping: EarlyStoppingConfig
    convergence_threshold: float
    enable_convergence_detection: bool
    tool_context_max_rounds: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum number of recent rounds to include tool results from"
    )
    tool_output_max_chars: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum characters to include from tool outputs"
    )
    file_tree: FileTreeConfig = Field(
        default_factory=FileTreeConfig,
        description="File tree injection settings"
    )
    tool_security: ToolSecurityConfig = Field(
        default_factory=ToolSecurityConfig,
        description="Security settings for deliberation tools"
    )


class DecisionGraphConfig(BaseModel):
    """Configuration for decision graph memory."""

    enabled: bool = Field(False, description="Enable decision graph memory")
    db_path: str = Field("decision_graph.db", description="Path to SQLite database")

    # DEPRECATED: Use tier_boundaries instead. Kept for backward compatibility.
    similarity_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="DEPRECATED: Minimum similarity score for context injection. Use tier_boundaries instead.",
    )

    max_context_decisions: int = Field(
        3,
        ge=1,
        le=10,
        description="Maximum number of past decisions to inject as context",
    )
    compute_similarities: bool = Field(
        True, description="Compute similarities after storing a deliberation"
    )

    # NEW: Budget-aware context injection parameters
    context_token_budget: int = Field(
        1500,
        ge=500,
        le=10000,
        description="Maximum tokens allowed for context injection (prevents token bloat)"
    )

    tier_boundaries: dict[str, float] = Field(
        default_factory=lambda: {"strong": 0.75, "moderate": 0.60},
        description="Similarity score boundaries for tiered injection (strong > moderate > 0)"
    )

    query_window: int = Field(
        1000,
        ge=50,
        le=10000,
        description="Number of recent decisions to query for scalability"
    )

    # Cache configuration
    query_cache_size: int = Field(
        200,
        ge=10,
        le=10000,
        description="LRU cache size for query results (L1 cache)"
    )
    embedding_cache_size: int = Field(
        500,
        ge=10,
        le=10000,
        description="LRU cache size for embeddings (L2 cache)"
    )
    query_ttl: int = Field(
        300,
        ge=60,
        le=3600,
        description="Time-to-live for cached query results in seconds (default: 5 minutes)"
    )

    # Adaptive K configuration
    adaptive_k_small_threshold: int = Field(
        100,
        ge=10,
        le=1000,
        description="Database size threshold for small DB (returns small_k)"
    )
    adaptive_k_medium_threshold: int = Field(
        1000,
        ge=100,
        le=10000,
        description="Database size threshold for medium DB (returns medium_k)"
    )
    adaptive_k_small: int = Field(
        5,
        ge=1,
        le=20,
        description="Number of candidates to retrieve for small databases"
    )
    adaptive_k_medium: int = Field(
        3,
        ge=1,
        le=20,
        description="Number of candidates to retrieve for medium databases"
    )
    adaptive_k_large: int = Field(
        2,
        ge=1,
        le=20,
        description="Number of candidates to retrieve for large databases"
    )

    # Similarity filtering
    noise_floor: float = Field(
        0.40,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score to consider (filter out noise below this threshold)"
    )

    @field_validator("tier_boundaries")
    @classmethod
    def validate_tier_boundaries(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate tier boundaries: strong > moderate > 0."""
        if not isinstance(v, dict) or "strong" not in v or "moderate" not in v:
            raise ValueError("tier_boundaries must have 'strong' and 'moderate' keys")

        if not (0.0 < v["moderate"] < v["strong"] <= 1.0):
            raise ValueError(
                f"tier_boundaries must satisfy: 0 < moderate ({v['moderate']}) "
                f"< strong ({v['strong']}) <= 1"
            )

        return v

    @field_validator("db_path")
    @classmethod
    def resolve_db_path(cls, v: str) -> str:
        """
        Resolve db_path to absolute path relative to project root.

        This validator ensures that relative database paths are always resolved
        relative to the project root directory (where config.yaml is located),
        not the current working directory. This prevents breakage when running
        the server from different directories.

        Processing steps:
        1. Resolve ${ENV_VAR} environment variable references
        2. Convert relative paths to absolute paths relative to project root
        3. Keep absolute paths unchanged
        4. Return normalized absolute path as string

        Examples:
            "decision_graph.db" → "/path/to/project/decision_graph.db"
            "/tmp/foo.db" → "/tmp/foo.db" (unchanged)
            "${DATA_DIR}/graph.db" → "/var/data/graph.db" (if DATA_DIR=/var/data)
            "../shared/graph.db" → "/path/to/shared/graph.db"

        Args:
            v: Database path from configuration (may contain env vars)

        Returns:
            Absolute path as string

        Raises:
            ValueError: If environment variable is referenced but not set
        """
        # Step 1: Resolve environment variables using ${VAR_NAME} pattern
        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            env_var = match.group(1)
            value = os.getenv(env_var)
            if value is None:
                raise ValueError(
                    f"Environment variable '{env_var}' is not set. "
                    f"Required for db_path configuration."
                )
            return value

        resolved = re.sub(pattern, replacer, v)

        # Step 2: Convert to Path object
        path = Path(resolved)

        # Step 3: If relative, make it relative to project root
        if not path.is_absolute():
            # This file is at: project_root/models/config.py
            # Project root is two levels up from this file
            project_root = Path(__file__).parent.parent
            path = (project_root / path).resolve()

        # Step 4: Return as string (normalized, absolute)
        return str(path)


class Config(BaseModel):
    """Root configuration model."""

    version: str

    # New adapters section (preferred)
    adapters: Optional[dict[str, AdapterConfig]] = None

    # Legacy cli_tools section (deprecated)
    cli_tools: Optional[dict[str, CLIToolConfig]] = None

    defaults: DefaultsConfig
    model_registry: Optional[dict[str, list[ModelDefinition]]] = Field(
        default=None,
        description="Allowlisted models per adapter to surface in MCP clients",
    )
    storage: StorageConfig
    deliberation: DeliberationConfig
    decision_graph: Optional[DecisionGraphConfig] = None

    def model_post_init(self, __context):
        """Post-initialization validation."""
        if self.adapters is None and self.cli_tools is None:
            raise ValueError(
                "Configuration must include either 'adapters' or 'cli_tools' section"
            )

        # If cli_tools is used, emit deprecation warning
        if self.cli_tools is not None and self.adapters is None:
            warnings.warn(
                "The 'cli_tools' configuration section is deprecated. "
                "Please migrate to 'adapters' section with explicit 'type' field. "
                "See migration guide: docs/migration/cli_tools_to_adapters.md",
                DeprecationWarning,
                stacklevel=2,
            )


def load_config(path: str = "config.yaml") -> Config:
    """
    Load configuration from YAML file.

    Args:
        path: Path to config file (default: config.yaml)

    Returns:
        Validated Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValidationError: If config is invalid
    """
    # Load environment variables from .env file (if it exists)
    load_dotenv()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    return Config(**data)
