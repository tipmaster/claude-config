"""Tests for the model registry utility."""
import pytest

from models.config import load_config
from models.model_registry import ModelRegistry


@pytest.fixture(scope="module")
def registry() -> ModelRegistry:
    config = load_config()
    return ModelRegistry(config)


def test_registry_lists_models(registry: ModelRegistry):
    claude_entries = registry.list_for_adapter("claude")
    assert claude_entries, "Expected allowlisted Claude models"
    assert claude_entries[0].id == "claude-sonnet-4-5-20250929"
    assert registry.get_default("claude") == "claude-sonnet-4-5-20250929"


def test_registry_enforces_allowlist(registry: ModelRegistry):
    assert registry.is_allowed("claude", "claude-haiku-4-5-20251001") is True
    assert registry.is_allowed("claude", "non-existent-model") is False


def test_registry_is_permissive_for_unmanaged_adapters(registry: ModelRegistry):
    # Adapters with no registry (e.g., llamacpp) accept any model name
    assert registry.is_allowed("llamacpp", "/path/to/model.gguf") is True
