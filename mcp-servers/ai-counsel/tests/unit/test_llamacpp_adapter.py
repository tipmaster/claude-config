"""Unit tests for LlamaCppAdapter.

llama.cpp is a CLI tool for running LLMs locally with unique output format.
Unlike other adapters, llama.cpp outputs include:
- Model loading information
- Sampling parameters
- Token generation stats (tokens/s, timing)
- Perplexity information
- The actual response text mixed with metadata

Test cases cover:
1. Initialization with proper defaults
2. Output parsing to extract response from verbose output
3. Handling various llama.cpp output formats
4. Error handling for malformed output
5. Context and prompt integration
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from adapters.llamacpp import LlamaCppAdapter


class TestLlamaCppAdapter:
    """Tests for LlamaCppAdapter."""

    def test_should_initialize_with_correct_defaults_when_created(self):
        """Test adapter initializes with correct command and timeout."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"], timeout=120)
        assert adapter.command == "llama-cli"
        assert adapter.timeout == 120
        assert adapter.args == ["-m", "{model}", "-p", "{prompt}"]

    def test_should_require_args_when_initializing(self):
        """Test adapter requires args parameter from config."""
        with pytest.raises(ValueError) as exc_info:
            LlamaCppAdapter()

        assert "args must be provided" in str(exc_info.value)

    def test_should_extract_response_when_parsing_verbose_output(self):
        """Test parsing extracts model response from verbose llama.cpp output."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        # Typical llama.cpp output includes metadata before/after response
        raw_output = """
llama_model_loader: loaded meta data with 20 key-value pairs and 291 tensors
llm_load_print_meta: model type = 7B
llm_load_print_meta: BOS token = 1 '<s>'
llm_load_print_meta: EOS token = 2 '</s>'
llama_new_context_with_model: n_ctx = 512

sampling: repeat_last_n = 64, repeat_penalty = 1.100
generate: n_ctx = 512, n_batch = 512, n_predict = 128, n_keep = 0

The answer to your question is 42. This is based on mathematical reasoning and logical deduction.

llama_print_timings:        load time =   234.56 ms
llama_print_timings:      sample time =    12.34 ms /   128 runs
llama_print_timings: prompt eval time =    45.67 ms /    10 tokens
llama_print_timings:        eval time =   890.12 ms /   128 tokens
llama_print_timings:       total time =  1234.56 ms
        """

        result = adapter.parse_output(raw_output)

        # Should extract only the actual response
        assert "The answer to your question is 42" in result
        assert "mathematical reasoning" in result
        # Should NOT include metadata
        assert "llama_model_loader" not in result
        assert "llm_load_print_meta" not in result
        assert "llama_print_timings" not in result
        assert "sampling:" not in result

    def test_should_handle_multiline_response_when_parsing_output(self):
        """Test parsing preserves multiline responses."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_new_context_with_model: n_ctx = 512
sampling: repeat_last_n = 64

Here is my detailed answer:

1. First point with explanation
2. Second point with more details
3. Third point concluding the argument

This covers all aspects of your question.

llama_print_timings:        load time =   123.45 ms
        """

        result = adapter.parse_output(raw_output)

        # Should preserve multiline structure
        assert "Here is my detailed answer:" in result
        assert "1. First point" in result
        assert "2. Second point" in result
        assert "3. Third point" in result
        assert "This covers all aspects" in result
        # No metadata
        assert "llama_new_context" not in result
        assert "llama_print_timings" not in result

    def test_should_extract_response_when_output_has_no_timings(self):
        """Test parsing works when llama.cpp output lacks timing info."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_model_loader: loaded meta data
sampling: repeat_last_n = 64

This is a simple response without timing information at the end.
        """

        result = adapter.parse_output(raw_output)

        assert "This is a simple response" in result
        assert "llama_model_loader" not in result
        assert "sampling:" not in result

    def test_should_handle_empty_lines_when_parsing_output(self):
        """Test parsing handles empty lines gracefully."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_new_context_with_model: n_ctx = 512


Response with empty lines above and below.


llama_print_timings: total time = 100 ms
        """

        result = adapter.parse_output(raw_output)

        assert "Response with empty lines" in result
        # Should preserve internal empty lines but strip leading/trailing
        assert result.strip() == "Response with empty lines above and below."

    def test_should_strip_whitespace_when_parsing_output(self):
        """Test parsing strips leading and trailing whitespace."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_new_context_with_model: n_ctx = 512

    Response with indentation and trailing spaces.

llama_print_timings: total time = 100 ms
        """

        result = adapter.parse_output(raw_output)

        # Should strip outer whitespace but preserve sentence structure
        assert result.strip() == "Response with indentation and trailing spaces."

    def test_should_handle_response_only_output_when_parsing(self):
        """Test parsing handles output with minimal metadata."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        # Some llama.cpp builds may have minimal output
        raw_output = "Just the response text without metadata."

        result = adapter.parse_output(raw_output)

        assert result == "Just the response text without metadata."

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_should_invoke_successfully_when_process_succeeds(
        self, mock_subprocess, tmp_path
    ):
        """Test successful CLI invocation."""
        # Create a temporary model file
        model_file = tmp_path / "model.gguf"
        model_file.touch()

        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(
                b"""
llama_model_loader: loaded meta data
sampling: repeat_last_n = 64

The answer is 42.

llama_print_timings: total time = 100 ms
            """,
                b"",
            )
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])
        result = await adapter.invoke(
            prompt="What is the answer?", model=str(model_file)
        )

        assert result == "The answer is 42."
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_should_raise_timeout_error_when_process_times_out(
        self, mock_subprocess, tmp_path
    ):
        """Test timeout handling."""
        # Create a temporary model file
        model_file = tmp_path / "model.gguf"
        model_file.touch()

        mock_process = Mock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process

        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"], timeout=1)

        with pytest.raises(TimeoutError) as exc_info:
            await adapter.invoke("test prompt", str(model_file))

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_should_raise_runtime_error_when_process_fails(self, mock_subprocess, tmp_path):
        """Test process error handling."""
        # Create a temporary model file
        model_file = tmp_path / "model.gguf"
        model_file.touch()

        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"error: failed to load model")
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        with pytest.raises(RuntimeError) as exc_info:
            await adapter.invoke("test prompt", str(model_file))

        assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_should_include_context_when_provided(self, mock_subprocess, tmp_path):
        """Test context is prepended to prompt."""
        # Create a temporary model file
        model_file = tmp_path / "model.gguf"
        model_file.touch()

        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Response with context.", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])
        result = await adapter.invoke(
            prompt="Answer this:",
            model=str(model_file),
            context="Previous context here.",
        )

        # Verify subprocess was called with combined prompt
        call_args = mock_subprocess.call_args
        combined_prompt = None
        for arg in call_args[0]:
            if "Previous context" in arg and "Answer this:" in arg:
                combined_prompt = arg
                break

        assert combined_prompt is not None
        assert "Previous context here." in combined_prompt
        assert "Answer this:" in combined_prompt
        assert result == "Response with context."

    def test_should_handle_response_with_code_blocks_when_parsing(self):
        """Test parsing preserves code blocks in response."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_new_context_with_model: n_ctx = 512

Here's a code example:

```python
def hello():
    print("Hello, world!")
```

This demonstrates the concept.

llama_print_timings: total time = 200 ms
        """

        result = adapter.parse_output(raw_output)

        assert "Here's a code example:" in result
        assert "```python" in result
        assert "def hello():" in result
        assert "This demonstrates the concept." in result
        assert "llama_print_timings" not in result

    def test_should_handle_special_characters_when_parsing_output(self):
        """Test parsing preserves special characters in response."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_new_context_with_model: n_ctx = 512

Response with special chars: @#$%^&*()
Also includes: "quotes" and 'apostrophes'
Mathematical symbols: ∑ ∫ √ π

llama_print_timings: total time = 100 ms
        """

        result = adapter.parse_output(raw_output)

        assert "@#$%^&*()" in result
        assert '"quotes"' in result
        assert "'apostrophes'" in result
        assert "∑ ∫ √ π" in result
        assert "llama_print_timings" not in result

    def test_should_filter_eof_marker_when_parsing_output(self):
        """Test parsing filters out EOF marker from truncated responses."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_new_context_with_model: n_ctx = 512
sampling: repeat_last_n = 64

This is a response that got truncated.
VOTE: {"option": "LFU", "confidence":
> EOF by user

llama_print_timings: total time = 100 ms
        """

        result = adapter.parse_output(raw_output)

        assert "This is a response that got truncated" in result
        assert "VOTE:" in result
        # Should NOT include EOF marker
        assert "> EOF by user" not in result
        assert "EOF" not in result
        # Should NOT include metadata
        assert "llama_new_context" not in result
        assert "llama_print_timings" not in result

    def test_should_filter_ggml_messages_when_parsing_output(self):
        """Test parsing filters out ggml/gguf library messages."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
ggml_metal_init: using Metal library
gguf_init_from_file: loading model
llama_model_loader: loaded meta data

This is the actual response text.

llama_print_timings: total time = 100 ms
        """

        result = adapter.parse_output(raw_output)

        assert "This is the actual response text" in result
        # Should NOT include ggml/gguf messages
        assert "ggml_" not in result
        assert "gguf_" not in result
        assert "llama_model_loader" not in result

    def test_should_filter_standalone_prompt_markers_when_parsing(self):
        """Test parsing filters out standalone prompt markers."""
        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = """
llama_new_context_with_model: n_ctx = 512

First line of response
>
Second line of response

llama_print_timings: total time = 100 ms
        """

        result = adapter.parse_output(raw_output)

        assert "First line of response" in result
        assert "Second line of response" in result
        # Should NOT include standalone '>' prompt marker
        lines = result.split("\n")
        assert ">" not in [line.strip() for line in lines]


class TestLlamaCppAutoDiscovery:
    """Tests for LlamaCppAdapter auto-discovery feature."""

    def test_should_resolve_absolute_path_when_model_exists(self, tmp_path):
        """Test that absolute paths are returned as-is when they exist."""
        model_file = tmp_path / "test-model.gguf"
        model_file.touch()

        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])
        resolved = adapter._resolve_model_path(str(model_file))

        assert resolved == str(model_file)

    def test_should_resolve_relative_path_when_model_exists(self, tmp_path, monkeypatch):
        """Test that relative paths are resolved to absolute paths."""
        model_file = tmp_path / "test-model.gguf"
        model_file.touch()

        # Change to tmp_path so relative path works
        monkeypatch.chdir(tmp_path)

        adapter = LlamaCppAdapter(args=["-m", "{model}", "-p", "{prompt}"])
        resolved = adapter._resolve_model_path("test-model.gguf")

        assert resolved == str(model_file.absolute())

    def test_should_find_model_by_exact_name_when_in_search_path(self, tmp_path):
        """Test finding model by exact name in search paths."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "llama-2-7b-chat.Q4_K_M.gguf"
        model_file.touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )
        resolved = adapter._resolve_model_path("llama-2-7b-chat")

        assert resolved == str(model_file)

    def test_should_find_model_by_fuzzy_name_when_partial_match(self, tmp_path):
        """Test finding model by partial/fuzzy name."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "llama-2-7b-chat.Q4_K_M.gguf"
        model_file.touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )
        # Should match with just "llama-2"
        resolved = adapter._resolve_model_path("llama-2")

        assert resolved == str(model_file)

    def test_should_search_recursively_when_model_in_subdirectory(self, tmp_path):
        """Test recursive search finds models in subdirectories."""
        models_dir = tmp_path / "models"
        sub_dir = models_dir / "llama" / "7b"
        sub_dir.mkdir(parents=True)
        model_file = sub_dir / "llama-2-7b.gguf"
        model_file.touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )
        resolved = adapter._resolve_model_path("llama-2-7b")

        assert resolved == str(model_file)

    def test_should_prefer_exact_match_when_multiple_models_found(self, tmp_path):
        """Test that exact name matches are preferred over partial matches."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create multiple models with similar names
        exact_match = models_dir / "llama-2.gguf"
        partial_match = models_dir / "llama-2-7b-chat.Q4_K_M.gguf"
        exact_match.touch()
        partial_match.touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )
        resolved = adapter._resolve_model_path("llama-2")

        # Should prefer exact stem match
        assert resolved == str(exact_match)

    def test_should_return_shortest_path_when_no_exact_match(self, tmp_path):
        """Test shortest path is returned when multiple fuzzy matches exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create models with similar names
        short_path = models_dir / "llama.gguf"
        long_path = models_dir / "llama-2-7b-chat.Q4_K_M.gguf"
        short_path.touch()
        long_path.touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )
        resolved = adapter._resolve_model_path("llama")

        # Both match "llama", but shortest path should win
        assert resolved == str(short_path)

    def test_should_raise_file_not_found_when_model_does_not_exist(self, tmp_path):
        """Test helpful error when model cannot be found."""
        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(tmp_path)],
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            adapter._resolve_model_path("nonexistent-model")

        error_msg = str(exc_info.value)
        assert "Model not found" in error_msg
        assert "nonexistent-model" in error_msg
        assert "Searched in:" in error_msg
        assert "Available models:" in error_msg
        assert "Tips:" in error_msg
        assert "huggingface.co" in error_msg

    def test_should_list_available_models_in_error_message(self, tmp_path):
        """Test error message lists available models."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create some models
        (models_dir / "model-a.gguf").touch()
        (models_dir / "model-b.gguf").touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            adapter._resolve_model_path("nonexistent")

        error_msg = str(exc_info.value)
        assert "model-a" in error_msg
        assert "model-b" in error_msg

    def test_should_expand_tilde_in_search_paths(self, tmp_path, monkeypatch):
        """Test that ~ in search paths is expanded to home directory."""
        # Mock home directory
        monkeypatch.setenv("HOME", str(tmp_path))

        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "test.gguf"
        model_file.touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=["~/models"],
        )

        expanded_paths = adapter._get_expanded_search_paths()
        assert any(str(p) == str(models_dir) for p in expanded_paths)

    def test_should_use_env_var_for_additional_search_paths(self, tmp_path, monkeypatch):
        """Test LLAMA_CPP_MODEL_PATH environment variable adds search paths."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "test.gguf"
        model_file.touch()

        monkeypatch.setenv("LLAMA_CPP_MODEL_PATH", str(models_dir))

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[],  # Empty default paths
        )

        resolved = adapter._resolve_model_path("test")
        assert resolved == str(model_file)

    def test_should_support_colon_separated_paths_in_env_var(self, tmp_path, monkeypatch):
        """Test LLAMA_CPP_MODEL_PATH supports colon-separated paths."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        model1 = dir1 / "model-a.gguf"
        model2 = dir2 / "model-b.gguf"
        model1.touch()
        model2.touch()

        monkeypatch.setenv("LLAMA_CPP_MODEL_PATH", f"{dir1}:{dir2}")

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[],
        )

        # Should find models in both directories
        resolved1 = adapter._resolve_model_path("model-a")
        resolved2 = adapter._resolve_model_path("model-b")

        assert resolved1 == str(model1)
        assert resolved2 == str(model2)

    def test_should_deduplicate_search_paths(self, tmp_path):
        """Test that duplicate search paths are deduplicated."""
        models_dir = tmp_path / "models"

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir), str(models_dir), str(models_dir)],
        )

        expanded_paths = adapter._get_expanded_search_paths()
        # Should only have one instance
        assert len([p for p in expanded_paths if str(p) == str(models_dir)]) == 1

    def test_should_handle_case_insensitive_matching(self, tmp_path):
        """Test fuzzy matching is case-insensitive."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "LLaMA-2-7B-Chat.gguf"
        model_file.touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )

        # Should find with lowercase query
        resolved = adapter._resolve_model_path("llama-2-7b")
        assert resolved == str(model_file)

    def test_should_limit_available_models_list_in_error(self, tmp_path):
        """Test error message limits model list to avoid overwhelming output."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create 15 models
        for i in range(15):
            (models_dir / f"model-{i}.gguf").touch()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )

        error_msg = adapter._format_available_models()

        # Should limit to 10 and show "... and N more"
        assert "... and 5 more" in error_msg

    def test_should_show_no_models_message_when_search_paths_empty(self, tmp_path):
        """Test error message when no models found in search paths."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(empty_dir)],
        )

        error_msg = adapter._format_available_models()
        assert "No .gguf models found" in error_msg

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_should_auto_resolve_model_path_when_invoking(
        self, mock_subprocess, tmp_path
    ):
        """Test invoke() automatically resolves model names to paths."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "llama-2-7b.gguf"
        model_file.touch()

        mock_process = Mock()
        mock_process.communicate = AsyncMock(return_value=(b"Response", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = LlamaCppAdapter(
            args=["-m", "{model}", "-p", "{prompt}"],
            search_paths=[str(models_dir)],
        )

        result = await adapter.invoke(
            prompt="Test prompt",
            model="llama-2-7b",  # Use name, not path
        )

        # Should have resolved to full path
        call_args = mock_subprocess.call_args[0]
        assert str(model_file) in " ".join(call_args)
        assert result == "Response"
