"""Test Gemini adapter with long prompts to reproduce API errors."""
import pytest

from adapters.gemini import GeminiAdapter


class TestGeminiLongPrompts:
    """Tests for Gemini adapter handling of long prompts."""

    @pytest.fixture
    def gemini_adapter(self):
        """Create a Gemini adapter instance."""
        return GeminiAdapter(
            command="gemini", args=["-m", "{model}", "-p", "{prompt}"], timeout=180
        )

    def test_long_prompt_with_markdown_formatting(self, gemini_adapter):
        """
        Test that Gemini adapter validates prompt length before invocation.

        This reproduces the "invalid argument" error seen in production logs
        when prompts exceed Gemini API limits (~30k tokens or ~120k characters).

        Expected behavior: Should validate and truncate/reject long prompts
        Current behavior (RED): No validation, relies on API error
        """
        # This is a realistic long prompt similar to what caused the error
        long_prompt = """We need to rescue valuable metrics work (24 commits implementing flexible time period support for /ketchup metrics command) that's trapped in a feature branch containing legacy DI infrastructure we've deleted. Which rescue strategy should we use?

**Option 1: Selective Cherry-Pick (24 commits)**
- Cherry-pick exact 24 metrics commits in phase order
- Preserves full commit history and progression
- ~45-60 minutes with conflict resolution
- Conflicts likely in legacy DI imports (resolve to TypedDI)

**Option 2: File-by-File Port**
- Copy 6 new files, manually merge 5 modified files
- No git conflicts, full control over what's ported
- ~30-45 minutes
- Loses commit history but cleaner implementation

**Option 3: Full Rebase**
- Rebase entire 46-commit branch onto current work
- Most complete, preserves everything
- ~2-3 hours, 143 file conflicts
- High risk of accidentally restoring deleted legacy DI

**Context:**
- Current branch: TypedDI migration complete (v2.360.321 deployed)
- Metrics branch: Contains Phase 1-5 work PLUS legacy DI we deleted
- User has exact commit list (24 core metrics + 21 infrastructure/docs)
- Goal: Get working flexible time periods without restoring legacy DI"""

        # Add context to make it even longer (simulates round 2+ with previous responses)
        context = """Previous discussion:

Round 1 - claude@cli (for): I recommend Option 2 (File-by-File Port) because it provides the safest path forward with minimal risk. Here's my reasoning:

1. **Safety First**: The TypedDI migration is already deployed to production (v2.360.321). We cannot risk accidentally restoring legacy DI infrastructure through a complex rebase or cherry-pick operation.

2. **Time Efficiency**: 30-45 minutes is reasonable and manageable. While cherry-picking preserves history, the 45-60 minute estimate doesn't account for potential complications or additional conflicts beyond the legacy DI imports.

3. **Complete Control**: Manual file copying gives us explicit control over what gets ported. We can verify each change incrementally and test as we go, reducing the chance of introducing bugs or unwanted code.

Round 1 - codex@cli (neutral): Both Option 1 and Option 2 have merit depending on priorities. If commit history and git blame are important for future debugging and understanding the evolution of the metrics feature, Option 1 (Cherry-Pick) is worth the extra 15-30 minutes. However, if the primary goal is speed and safety, Option 2 is the clear winner."""

        # Simulate 50+ rounds of context (each round adds ~2k chars)
        # This creates a prompt exceeding 100k characters
        very_long_context = context * 100  # Repeat context 100 times = ~118k chars
        full_prompt_with_context = f"{very_long_context}\n\n{long_prompt}"

        # Test that adapter has a method to validate prompt length
        # Expected: Should have validate_prompt_length() method that returns False for long prompts
        assert hasattr(
            gemini_adapter, "validate_prompt_length"
        ), "Adapter should have validate_prompt_length() method"
        assert not gemini_adapter.validate_prompt_length(
            full_prompt_with_context
        ), f"Long prompts ({len(full_prompt_with_context)} chars) should be flagged as invalid"

    def test_prompt_length_validation(self, gemini_adapter):
        """
        Test that adapter validates prompt length before sending to API.

        Expected: Should check prompt length and handle appropriately
        Current (RED): No validation, sends directly to API
        """
        # Gemini API typically has token limits around 30k-100k tokens
        # A rough estimate is ~4 chars per token, so 200k chars = ~50k tokens
        very_long_prompt = "A" * 200000  # 200k characters

        # Should have a validation method
        assert hasattr(
            gemini_adapter, "validate_prompt_length"
        ), "Adapter should have validate_prompt_length() method"
        assert not gemini_adapter.validate_prompt_length(
            very_long_prompt
        ), "Extremely long prompts should be flagged as invalid"

    def test_markdown_formatting_in_prompt(self, gemini_adapter):
        """
        Test that markdown formatting doesn't cause API errors.

        The Gemini API might be sensitive to certain markdown patterns
        or special characters that need escaping.
        """
        markdown_prompt = """
# Heading 1
## Heading 2

**Bold text** and *italic text*

- Bullet point 1
- Bullet point 2
  - Nested bullet

1. Numbered list
2. Second item

`code snippet`

```python
def example():
    return "test"
```

> Blockquote

[Link](https://example.com)
"""

        # Should handle markdown without errors
        result = gemini_adapter.parse_output(markdown_prompt)
        assert result == markdown_prompt.strip()
