"""Unit tests for CLI adapters."""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from adapters import create_adapter
from adapters.base import BaseCLIAdapter
from adapters.claude import ClaudeAdapter
from adapters.codex import CodexAdapter
from adapters.droid import DroidAdapter
from adapters.gemini import GeminiAdapter
from models.config import CLIAdapterConfig, CLIToolConfig, HTTPAdapterConfig


class TestBaseCLIAdapter:
    """Tests for BaseCLIAdapter."""

    def test_cannot_instantiate_base_adapter(self):
        """Test that base adapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCLIAdapter(command="test", args=[], timeout=60)

    def test_subclass_must_implement_parse_output(self):
        """Test that subclasses must implement parse_output."""

        class IncompleteAdapter(BaseCLIAdapter):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter(command="test", args=[], timeout=60)


class TestClaudeAdapter:
    """Tests for ClaudeAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct values."""
        adapter = ClaudeAdapter(
            args=[
                "-p",
                "--model",
                "{model}",
                "--settings",
                '{{"disableAllHooks": true}}',
                "{prompt}",
            ],
            timeout=90,
        )
        assert adapter.command == "claude"
        assert adapter.timeout == 90

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_success(self, mock_subprocess):
        """Test successful CLI invocation."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Claude Code output\n\nActual model response here", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = ClaudeAdapter(
            args=[
                "-p",
                "--model",
                "{model}",
                "--settings",
                '{{"disableAllHooks": true}}',
                "{prompt}",
            ]
        )
        result = await adapter.invoke(
            prompt="What is 2+2?", model="claude-3-5-sonnet-20241022"
        )

        assert result == "Actual model response here"
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_timeout(self, mock_subprocess):
        """Test timeout handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process

        adapter = ClaudeAdapter(
            args=[
                "-p",
                "--model",
                "{model}",
                "--settings",
                '{{"disableAllHooks": true}}',
                "{prompt}",
            ],
            timeout=1,
        )

        with pytest.raises(TimeoutError) as exc_info:
            await adapter.invoke("test", "model")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_process_error(self, mock_subprocess):
        """Test process error handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: Model not found")
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        adapter = ClaudeAdapter(
            args=[
                "-p",
                "--model",
                "{model}",
                "--settings",
                '{{"disableAllHooks": true}}',
                "{prompt}",
            ]
        )

        with pytest.raises(RuntimeError) as exc_info:
            await adapter.invoke("test", "model")

        assert "failed" in str(exc_info.value).lower()

    def test_parse_output_extracts_response(self):
        """Test output parsing extracts model response."""
        adapter = ClaudeAdapter(
            args=[
                "-p",
                "--model",
                "{model}",
                "--settings",
                '{{"disableAllHooks": true}}',
                "{prompt}",
            ]
        )

        raw_output = """
        Claude Code v1.0
        Loading model...

        Here is the actual response from the model.
        This is what we want to extract.
        """

        result = adapter.parse_output(raw_output)
        assert "actual response" in result
        assert "Claude Code v1.0" not in result
        assert "Loading model" not in result


class TestCodexAdapter:
    """Tests for CodexAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct values."""
        adapter = CodexAdapter(
            args=["exec", "--model", "{model}", "{prompt}"], timeout=90
        )
        assert adapter.command == "codex"
        assert adapter.timeout == 90

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_success(self, mock_subprocess):
        """Test successful CLI invocation."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"This is the codex model response.", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = CodexAdapter(args=["exec", "--model", "{model}", "{prompt}"])
        result = await adapter.invoke(prompt="What is 2+2?", model="gpt-4")

        assert result == "This is the codex model response."
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_timeout(self, mock_subprocess):
        """Test timeout handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process

        adapter = CodexAdapter(
            args=["exec", "--model", "{model}", "{prompt}"], timeout=1
        )

        with pytest.raises(TimeoutError) as exc_info:
            await adapter.invoke("test", "model")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_process_error(self, mock_subprocess):
        """Test process error handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: Model not available")
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        adapter = CodexAdapter(args=["exec", "--model", "{model}", "{prompt}"])

        with pytest.raises(RuntimeError) as exc_info:
            await adapter.invoke("test", "model")

        assert "failed" in str(exc_info.value).lower()

    def test_parse_output_returns_cleaned_text(self):
        """Test output parsing returns cleaned text."""
        adapter = CodexAdapter(args=["exec", "--model", "{model}", "{prompt}"])

        raw_output = "  Response with extra whitespace.  \n\n"
        result = adapter.parse_output(raw_output)

        assert result == "Response with extra whitespace."
        assert not result.startswith(" ")
        assert not result.endswith(" ")


class TestGeminiAdapter:
    """Tests for GeminiAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct values."""
        adapter = GeminiAdapter(args=["-m", "{model}", "-p", "{prompt}"], timeout=90)
        assert adapter.command == "gemini"
        assert adapter.timeout == 90

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_success(self, mock_subprocess):
        """Test successful CLI invocation."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"This is the gemini model response.", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = GeminiAdapter(args=["-m", "{model}", "-p", "{prompt}"])
        result = await adapter.invoke(prompt="What is 2+2?", model="gemini-pro")

        assert result == "This is the gemini model response."
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_timeout(self, mock_subprocess):
        """Test timeout handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process

        adapter = GeminiAdapter(args=["-m", "{model}", "-p", "{prompt}"], timeout=1)

        with pytest.raises(TimeoutError) as exc_info:
            await adapter.invoke("test", "model")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_process_error(self, mock_subprocess):
        """Test process error handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: Model not available")
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        adapter = GeminiAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        with pytest.raises(RuntimeError) as exc_info:
            await adapter.invoke("test", "model")

        assert "failed" in str(exc_info.value).lower()

    def test_parse_output_returns_cleaned_text(self):
        """Test output parsing returns cleaned text."""
        adapter = GeminiAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        raw_output = "  Response with extra whitespace.  \n\n"
        result = adapter.parse_output(raw_output)

        assert result == "Response with extra whitespace."
        assert not result.startswith(" ")
        assert not result.endswith(" ")


class TestDroidAdapter:
    """Tests for DroidAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct values."""
        adapter = DroidAdapter(args=["exec", "{prompt}"], timeout=90)
        assert adapter.command == "droid"
        assert adapter.timeout == 90

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_success(self, mock_subprocess):
        """Test successful CLI invocation."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"This is the droid model response.", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = DroidAdapter(args=["exec", "{prompt}"])
        result = await adapter.invoke(prompt="What is 2+2?", model="factory-1")

        assert result == "This is the droid model response."
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_timeout(self, mock_subprocess):
        """Test timeout handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process

        adapter = DroidAdapter(args=["exec", "{prompt}"], timeout=1)

        with pytest.raises(TimeoutError) as exc_info:
            await adapter.invoke("test", "model")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_process_error(self, mock_subprocess):
        """Test process error handling."""
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: Model not available")
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        adapter = DroidAdapter(args=["exec", "{prompt}"])

        with pytest.raises(RuntimeError) as exc_info:
            await adapter.invoke("test", "model")

        assert "failed" in str(exc_info.value).lower()

    def test_parse_output_returns_cleaned_text(self):
        """Test output parsing returns cleaned text."""
        adapter = DroidAdapter(args=["exec", "{prompt}"])

        raw_output = "  Response with extra whitespace.  \n\n"
        result = adapter.parse_output(raw_output)

        assert result == "Response with extra whitespace."
        assert not result.startswith(" ")
        assert not result.endswith(" ")


class TestAdapterFactory:
    """Tests for create_adapter factory function."""

    def test_create_claude_code_adapter(self):
        """Test creating ClaudeAdapter via factory."""
        config = CLIToolConfig(
            command="claude",
            args=["--model", "{model}", "--prompt", "{prompt}"],
            timeout=90,
        )
        adapter = create_adapter("claude", config)
        assert isinstance(adapter, ClaudeAdapter)
        assert adapter.command == "claude"
        assert adapter.timeout == 90

    def test_create_codex_adapter(self):
        """Test creating CodexAdapter via factory."""
        config = CLIToolConfig(
            command="codex", args=["--model", "{model}", "{prompt}"], timeout=120
        )
        adapter = create_adapter("codex", config)
        assert isinstance(adapter, CodexAdapter)
        assert adapter.command == "codex"
        assert adapter.timeout == 120

    def test_create_gemini_adapter(self):
        """Test creating GeminiAdapter via factory."""
        config = CLIToolConfig(
            command="gemini", args=["-m", "{model}", "-p", "{prompt}"], timeout=180
        )
        adapter = create_adapter("gemini", config)
        assert isinstance(adapter, GeminiAdapter)
        assert adapter.command == "gemini"
        assert adapter.timeout == 180

    def test_create_droid_adapter(self):
        """Test creating DroidAdapter via factory."""
        config = CLIToolConfig(command="droid", args=["exec", "{prompt}"], timeout=180)
        adapter = create_adapter("droid", config)
        assert isinstance(adapter, DroidAdapter)
        assert adapter.command == "droid"
        assert adapter.timeout == 180

    def test_create_llamacpp_adapter(self):
        """Test creating LlamaCppAdapter via factory."""
        from adapters.llamacpp import LlamaCppAdapter

        config = CLIToolConfig(
            command="llama-cli", args=["-m", "{model}", "-p", "{prompt}"], timeout=120
        )
        adapter = create_adapter("llamacpp", config)
        assert isinstance(adapter, LlamaCppAdapter)
        assert adapter.command == "llama-cli"
        assert adapter.timeout == 120

    def test_create_llamacpp_adapter_with_cli_adapter_config(self):
        """Test creating LlamaCppAdapter with new CLIAdapterConfig."""
        from adapters.llamacpp import LlamaCppAdapter

        config = CLIAdapterConfig(
            type="cli",
            command="llama-cli",
            args=["-m", "{model}", "-p", "{prompt}", "-n", "512"],
            timeout=180,
        )
        adapter = create_adapter("llamacpp", config)
        assert isinstance(adapter, LlamaCppAdapter)
        assert adapter.command == "llama-cli"
        assert adapter.timeout == 180

    def test_create_lmstudio_adapter(self):
        """Test creating LMStudioAdapter via factory."""
        from adapters.lmstudio import LMStudioAdapter

        config = HTTPAdapterConfig(
            type="http", base_url="http://localhost:1234", timeout=60, max_retries=3
        )

        adapter = create_adapter("lmstudio", config)
        assert isinstance(adapter, LMStudioAdapter)
        assert adapter.base_url == "http://localhost:1234"
        assert adapter.timeout == 60
        assert adapter.max_retries == 3

    def test_factory_rejects_cli_config_for_lmstudio(self):
        """Test LM Studio with CLI config raises error."""
        config = CLIAdapterConfig(type="cli", command="lmstudio", args=[], timeout=60)

        with pytest.raises(ValueError) as exc_info:
            create_adapter("lmstudio", config)

        # Should fail because lmstudio is not in CLI adapters
        assert "lmstudio" in str(exc_info.value).lower()
        assert "unknown cli adapter" in str(exc_info.value).lower()

    def test_create_ollama_adapter(self):
        """Test creating OllamaAdapter via factory."""
        from adapters.ollama import OllamaAdapter

        config = HTTPAdapterConfig(
            type="http", base_url="http://localhost:11434", timeout=120, max_retries=3
        )

        adapter = create_adapter("ollama", config)
        assert isinstance(adapter, OllamaAdapter)
        assert adapter.base_url == "http://localhost:11434"
        assert adapter.timeout == 120
        assert adapter.max_retries == 3

    def test_factory_rejects_cli_config_for_ollama(self):
        """Test Ollama with CLI config raises error."""
        config = CLIAdapterConfig(type="cli", command="ollama", args=[], timeout=60)

        with pytest.raises(ValueError) as exc_info:
            create_adapter("ollama", config)

        # Should fail because ollama is not in CLI adapters
        assert "ollama" in str(exc_info.value).lower()
        assert "unknown cli adapter" in str(exc_info.value).lower()

    def test_create_openrouter_adapter(self):
        """Test creating OpenRouterAdapter via factory."""
        from adapters.openrouter import OpenRouterAdapter

        config = HTTPAdapterConfig(
            type="http",
            base_url="https://openrouter.ai/api/v1",
            api_key="sk-test-key",
            timeout=90,
            max_retries=3,
        )

        adapter = create_adapter("openrouter", config)
        assert isinstance(adapter, OpenRouterAdapter)
        assert adapter.base_url == "https://openrouter.ai/api/v1"
        assert adapter.api_key == "sk-test-key"
        assert adapter.timeout == 90
        assert adapter.max_retries == 3

    def test_factory_rejects_cli_config_for_openrouter(self):
        """Test OpenRouter with CLI config raises error."""
        config = CLIAdapterConfig(type="cli", command="openrouter", args=[], timeout=60)

        with pytest.raises(ValueError) as exc_info:
            create_adapter("openrouter", config)

        # Should fail because openrouter is not in CLI adapters
        assert "openrouter" in str(exc_info.value).lower()
        assert "unknown cli adapter" in str(exc_info.value).lower()

    def test_create_adapter_with_default_timeout(self):
        """Test factory uses timeout from config object."""
        config = CLIToolConfig(
            command="claude",
            args=["--model", "{model}", "--prompt", "{prompt}"],
            timeout=60,
        )
        adapter = create_adapter("claude", config)
        assert adapter.timeout == 60

    def test_create_adapter_invalid_cli(self):
        """Test factory raises error for invalid CLI tool name."""
        config = CLIToolConfig(
            command="invalid-cli", args=["--model", "{model}", "{prompt}"], timeout=60
        )
        with pytest.raises(ValueError) as exc_info:
            create_adapter("invalid-cli", config)

        assert "unsupported" in str(exc_info.value).lower()
        assert "invalid-cli" in str(exc_info.value)

    def test_create_adapter_with_cli_adapter_config(self):
        """Test creating adapter with new CLIAdapterConfig."""
        config = CLIAdapterConfig(
            type="cli", command="claude", args=["--model", "{model}"], timeout=60
        )
        adapter = create_adapter("claude", config)
        assert isinstance(adapter, ClaudeAdapter)
        assert adapter.command == "claude"
        assert adapter.timeout == 60

    def test_create_adapter_with_http_adapter_config_unknown_adapter(self):
        """Test HTTP adapter raises error for unknown adapter name."""
        config = HTTPAdapterConfig(
            type="http", base_url="http://localhost:9999", timeout=60
        )

        # Should raise because "unknown-http-adapter" is not registered
        with pytest.raises(ValueError) as exc_info:
            create_adapter("unknown-http-adapter", config)

        assert "unknown http adapter" in str(exc_info.value).lower()

    def test_factory_type_checking(self):
        """Test factory validates config type matches adapter expectations."""
        # This will be important when we add actual HTTP adapters
        # For now, just verify the factory can handle both config types
        cli_config = CLIAdapterConfig(
            type="cli", command="claude", args=["--model", "{model}"], timeout=60
        )
        adapter = create_adapter("claude", cli_config)
        assert isinstance(adapter, ClaudeAdapter)


class TestWorkingDirectoryIsolation:
    """Tests for working_directory isolation in CLI adapters."""

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_uses_working_directory_as_cwd(self, mock_subprocess):
        """Test that invoke() uses working_directory as subprocess cwd."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Response from working directory", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = ClaudeAdapter(
            args=[
                "-p",
                "--model",
                "{model}",
                "--settings",
                '{{"disableAllHooks": true}}',
                "{prompt}",
            ]
        )

        # Invoke with working_directory parameter
        working_dir = "/tmp/test-repo"
        result = await adapter.invoke(
            prompt="What is 2+2?",
            model="claude-3-5-sonnet-20241022",
            working_directory=working_dir
        )

        assert result == "Response from working directory"

        # Verify subprocess was called with correct cwd
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs["cwd"] == working_dir

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_invoke_without_working_directory_uses_current_dir(self, mock_subprocess):
        """Test that invoke() without working_directory uses current directory."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Response from current dir", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = CodexAdapter(args=["exec", "--model", "{model}", "{prompt}"])

        # Invoke without working_directory parameter
        result = await adapter.invoke(
            prompt="What is 2+2?",
            model="gpt-4"
        )

        assert result == "Response from current dir"

        # Verify subprocess was called with current directory as cwd
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        # Should use current directory (getcwd equivalent)
        import os
        assert call_kwargs["cwd"] == os.getcwd()

    @pytest.mark.asyncio
    @patch("adapters.base.asyncio.create_subprocess_exec")
    async def test_gemini_adapter_uses_working_directory(self, mock_subprocess):
        """Test that GeminiAdapter uses working_directory."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Gemini response from working dir", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        adapter = GeminiAdapter(args=["-m", "{model}", "-p", "{prompt}"])

        working_dir = "/tmp/gemini-test"
        result = await adapter.invoke(
            prompt="Analyze this code",
            model="gemini-2.5-pro",
            working_directory=working_dir
        )

        assert result == "Gemini response from working dir"

        # Verify subprocess was called with correct cwd
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs["cwd"] == working_dir
