# AI Counsel

True deliberative consensus MCP server where AI models debate and refine positions across multiple rounds.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)
![MCP](https://img.shields.io/badge/MCP-Server-green.svg)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

## 🎬 See It In Action

**Cloud Models Debate** (Claude Sonnet, GPT-5 Codex, Gemini):
```javascript
mcp__ai-counsel__deliberate({
  question: "Should we use REST or GraphQL for our new API?",
  participants: [
    {cli: "claude", model: "claude-sonnet-4-5-20250929"},
    {cli: "codex", model: "gpt-5-codex"},
    {cli: "gemini", model: "gemini-2.5-pro"}
  ],
  mode: "conference",
  rounds: 3
})
```
**Result**: Converged on hybrid architecture (0.82-0.95 confidence) • [View full transcript](transcripts/20251030_153509_Should_we_use_REST_or_GraphQL_for_our_new_API_Con.md)

**Local Models Debate** (100% private, zero API costs):
```javascript
mcp__ai-counsel__deliberate({
  question: "Should we prioritize code quality or delivery speed?",
  participants: [
    {cli: "ollama", model: "llama3.1:8b"},
    {cli: "ollama", model: "mistral:7b"},
    {cli: "ollama", model: "deepseek-r1:8b"}
  ],
  mode: "conference",
  rounds: 2
})
```
**Result**: 2 models switched positions after Round 1 debate • [View full transcript](transcripts/20251030_153834_Should_we_prioritize_code_quality_or_delivery_spee.md)

---

## What Makes This Different

**AI Counsel enables TRUE deliberative consensus** where models see each other's responses and refine positions across multiple rounds:

- Models engage in actual debate (see and respond to each other)
- Multi-round convergence with voting and confidence levels
- Full audit trail with AI-generated summaries
- Automatic early stopping when consensus reaches (saves API costs)

## Features

- 🎯 **Two Modes**: `quick` (single-round) or `conference` (multi-round debate)
- 🤖 **Mixed Adapters**: CLI tools (claude, codex, droid, gemini) + HTTP services (ollama, lmstudio, openrouter)
- ⚡ **Auto-Convergence**: Stops when opinions stabilize (saves API costs)
- 🗳️ **Structured Voting**: Models cast votes with confidence levels and rationale
- 🧮 **Semantic Grouping**: Similar vote options automatically merged (0.70+ similarity)
- 🎛️ **Model-Controlled Stopping**: Models decide when to stop deliberating
- 🔬 **Evidence-Based Deliberation**: Models can read files, search code, list files, and run commands to ground decisions in reality
- 💰 **Local Model Support**: Zero API costs with Ollama, LM Studio, llamacpp
- 🔐 **Data Privacy**: Keep all data on-premises with self-hosted models
- 🧠 **Context Injection**: Automatically finds similar past debates and injects context for faster convergence
- 🔍 **Semantic Search**: Query past decisions with `query_decisions` tool (finds contradictions, traces evolution, analyzes patterns)
- 🛡️ **Fault Tolerant**: Individual adapter failures don't halt deliberation
- 📝 **Full Transcripts**: Markdown exports with AI-generated summaries

## Quick Start

Get up and running in minutes:

1. **Install** – follow the commands in [Installation](#installation) to clone the repo, create a virtualenv, and install requirements.
2. **Configure** – set up your MCP client using the `.mcp.json` example in [Configure in Claude Code](#configure-in-claude-code).
3. **Run** – start the server with `python server.py` and trigger the `deliberate` tool using the examples in [Usage](#usage).

**Try a Deliberation:**

```javascript
// Mix local + cloud models, zero API costs for local models
mcp__ai-counsel__deliberate({
  question: "Should we add unit tests to new features?",
  participants: [
    {cli: "ollama", model: "llama2"},           // Local
    {cli: "lmstudio", model: "mistral"},        // Local
    {cli: "claude", model: "sonnet"}            // Cloud
  ],
  mode: "quick"
})
```

> **⚠️ Model Size Matters for Deliberations**
>
> **Recommended**: Use 7B-8B+ parameter models (Llama-3-8B, Mistral-7B, Qwen-2.5-7B) for reliable structured output and vote formatting.
>
> **Not Recommended**: Models under 3B parameters (e.g., Llama-3.2-1B) may struggle with complex instructions and produce invalid votes.

**Available Models**: `claude` (sonnet, opus, haiku), `codex` (gpt-5-codex), `droid`, `gemini`, HTTP adapters (ollama, lmstudio, openrouter).
See [CLI Model Reference](docs/CLI_MODEL_REFERENCE.md) for complete details.

For model choices and picker workflow, see [Model Registry & Picker](docs/model-registry-and-picker.md).

## Installation

### Prerequisites

1. **Python 3.11+**: `python3 --version`
2. **At least one AI tool** (optional - HTTP adapters work without CLI):
   - **Claude CLI**: https://docs.claude.com/en/docs/claude-code/setup
   - **Codex CLI**: https://github.com/openai/codex
   - **Droid CLI**: https://github.com/Factory-AI/factory
   - **Gemini CLI**: https://github.com/google-gemini/gemini-cli

### Setup

```bash
git clone https://github.com/blueman82/ai-counsel.git
cd ai-counsel
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux; Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 -m pytest tests/unit -v  # Verify installation
```

✅ Ready to use! Server includes core dependencies plus optional convergence backends (scikit-learn, sentence-transformers) for best accuracy.

## Configuration

Edit `config.yaml` to configure adapters and settings:

```yaml
adapters:
  claude:
    type: cli
    command: "claude"
    args: ["-p", "--model", "{model}", "--settings", "{\"disableAllHooks\": true}", "{prompt}"]
    timeout: 300

  ollama:
    type: http
    base_url: "http://localhost:11434"
    timeout: 120
    max_retries: 3

defaults:
  mode: "quick"
  rounds: 2
  max_rounds: 5
```

**Note:** Use `type: cli` for CLI tools and `type: http` for HTTP adapters (Ollama, LM Studio, OpenRouter).

## Core Features Deep Dive

### Convergence Detection & Auto-Stop
Models automatically converge and stop deliberating when opinions stabilize, saving time and API costs. Status: Converged (≥85% similarity), Refining (40-85%), Diverging (<40%), or Impasse (stable disagreement). Voting takes precedence: when models cast votes, convergence reflects voting outcome.

→ **[Complete Guide](docs/convergence-detection.md)** - Thresholds, backends, configuration

### Structured Voting
Models cast votes with confidence levels (0.0-1.0), rationale, and continue_debate signals. Votes determine consensus: Unanimous (3-0), Majority (2-1), or Tie. Similar options automatically merged at 0.70+ similarity threshold.

→ **[Complete Guide](docs/structured-voting.md)** - Vote structure, examples, integration

### HTTP Adapters & Local Models
Run Ollama, LM Studio, or OpenRouter locally for zero API costs and complete data privacy. Mix with cloud models (Claude, GPT-4) in single deliberation.

→ **[Setup Guides](docs/http-adapters/intro.md)** - Ollama, LM Studio, OpenRouter, cost analysis

### Extending AI Counsel
Add new CLI tools or HTTP adapters to fit your infrastructure. Simple 3-5 step process with examples and testing patterns.

→ **[Developer Guide](docs/adding-adapters.md)** - Step-by-step tutorials, real-world examples

## Evidence-Based Deliberation

Ground design decisions in reality by querying actual code, files, and data:

```javascript
// MCP client example (e.g., Claude Code)
mcp__ai_counsel__deliberate({
  question: "Should we migrate from SQLite to PostgreSQL?",
  participants: [
    {cli: "claude", model: "sonnet"},
    {cli: "codex", model: "gpt-4"}
  ],
  rounds: 3,
  working_directory: process.cwd()  // Required - enables tools to access your files
})
```

**During deliberation, models can:**
- 📄 Read files: `TOOL_REQUEST: {"name": "read_file", "arguments": {"path": "config.yaml"}}`
- 🔍 Search code: `TOOL_REQUEST: {"name": "search_code", "arguments": {"pattern": "database.*connect"}}`
- 📋 List files: `TOOL_REQUEST: {"name": "list_files", "arguments": {"pattern": "*.sql"}}`
- ⚙️ Run commands: `TOOL_REQUEST: {"name": "run_command", "arguments": {"command": "git", "args": ["log", "--oneline"]}}`

**Example workflow:**
1. Model A proposes PostgreSQL based on assumptions
2. Model B requests: `read_file` to check current config
3. Tool returns: `database: sqlite, max_connections: 10`
4. Model B searches: `search_code` for database queries
5. Tool returns: 50+ queries with complex JOINs
6. Models converge: "PostgreSQL needed for query complexity and scale"
7. Decision backed by evidence, not opinion

**Benefits:**
- Decisions rooted in current state, not assumptions
- Applies to code reviews, architecture choices, testing strategy
- Full audit trail of evidence in transcripts

**Supported Tools:**
- `read_file` - Read file contents (max 1MB)
- `search_code` - Search regex patterns (ripgrep or Python fallback)
- `list_files` - List files matching glob patterns
- `run_command` - Execute safe read-only commands (ls, git, grep, etc.)

### Configuration

Control tool behavior in `config.yaml`:

**Working Directory** (Required):
- Set `working_directory` parameter when calling `deliberate` tool
- Tools resolve relative paths from this directory
- Example: `working_directory: process.cwd()` in JavaScript MCP clients

**Tool Security** (`deliberation.tool_security`):
- `exclude_patterns`: Block access to sensitive directories (default: `transcripts/`, `.git/`, `node_modules/`)
- `max_file_size_bytes`: File size limit for `read_file` (default: 1MB)
- `command_whitelist`: Safe commands for `run_command` (ls, grep, find, cat, head, tail)

**File Tree** (`deliberation.file_tree`):
- `enabled`: Inject repository structure into Round 1 prompts (default: true)
- `max_depth`: Directory depth limit (default: 3)
- `max_files`: Maximum files to include (default: 100)

**Adapter-Specific Requirements:**

| Adapter | Working Directory Behavior | Configuration |
|---------|---------------------------|---------------|
| **Claude** | Automatic isolation via subprocess `{working_directory}` | No special config needed |
| **Codex** | No true isolation - can access any file | Security consideration: models can read outside `{working_directory}` |
| **Droid** | Automatic isolation via subprocess `{working_directory}` | No special config needed |
| **Gemini** | Enforces workspace boundaries | **Required**: `--include-directories {working_directory}` flag |
| **Ollama/LMStudio** | N/A - HTTP adapters | No file system access restrictions |

**Learn More:**
- [Complete Configuration Reference](CLAUDE.md#configuration-notes) - All config.yaml settings explained
- [Working Directory Isolation](CLAUDE.md#core-components) - How adapters handle file paths
- [Tool Security Model](CLAUDE.md#evidence-based-deliberation) - Whitelists, limits, and exclusions
- [Adding Custom Tools](docs/adding-tool.md) - Developer guide for extending the tool system

### Troubleshooting

**"File not found" errors:**
- Ensure `working_directory` is set correctly in your MCP client call
- Use discovery pattern: `list_files` → `read_file`
- Check file paths are relative to working directory

**"Access denied: Path matches exclusion pattern":**
- Tools block `transcripts/`, `.git/`, `node_modules/` by default
- Customize via `deliberation.tool_security.exclude_patterns` in config.yaml

**Gemini "File path must be within workspace" errors:**
- Verify Gemini's `--include-directories` flag uses `{working_directory}` placeholder
- See adapter-specific setup above

**Tool timeout errors:**
- Increase `deliberation.tool_security.tool_timeout` for slow operations
- Default: 10 seconds for file operations, 30 seconds for commands

**Learn More:**
- [Adding Custom Tools](docs/adding-tool.md) - Developer guide for extending tool system
- [Architecture & Security](CLAUDE.md#evidence-based-deliberation) - How tools work under the hood
- [Common Gotchas](CLAUDE.md#common-gotchas) - Advanced settings and known issues

## Decision Graph Memory

AI Counsel learns from past deliberations to accelerate future decisions. Two core capabilities:

### 1. Automatic Context Injection
When starting a new deliberation, the system:
- Searches past debates for similar questions (semantic similarity)
- Finds the top-k most relevant decisions (configurable, default: 3)
- Injects context into Round 1 prompts automatically
- Result: Models start with institutional knowledge, converge faster

### 2. Semantic Search with `query_decisions`
Query past deliberations programmatically:
- **Search similar**: Find decisions related to a question
- **Find contradictions**: Detect conflicting past decisions
- **Trace evolution**: See how opinions changed over time
- **Analyze patterns**: Identify recurring themes

**Configuration** (optional - defaults work out-of-box):
```yaml
decision_graph:
  enabled: true                       # Auto-injection on by default
  db_path: "decision_graph.db"        # Resolves to project root (works for any user/folder)
  similarity_threshold: 0.6           # Adjust to control context relevance
  max_context_decisions: 3            # How many past decisions to inject
```

**Works for any user from any directory** - database path is resolved relative to project root.

→ **[Quickstart](docs/decision-graph/quickstart.md)** | **[Configuration](docs/decision-graph/configuration.md)** | **[Context Injection](docs/decision-graph/using-context-injection.md)**

## Usage

### Start the Server

```bash
python server.py
```

### Configure in Claude Code

**Option A: Project Config (Recommended)** - Create `.mcp.json`:

```json
{
  "mcpServers": {
    "ai-counsel": {
      "type": "stdio",
      "command": ".venv/bin/python",
      "args": ["server.py"],
      "env": {}
    }
  }
}
```

**Option B: User Config** - Add to `~/.claude.json` with absolute paths.

After configuration, restart Claude Code.

### Model Selection & Session Defaults

- Discover the allowlisted models for each adapter by running the MCP tool `list_models`.
- Set per-session defaults with `set_session_models`; leave `model` blank in `deliberate` to use those defaults.
- Full instructions and request examples live in [Model Registry & Picker](docs/model-registry-and-picker.md).

### Examples

**Quick Mode:**
```javascript
mcp__ai-counsel__deliberate({
  question: "Should we migrate to TypeScript?",
  participants: [{cli: "claude", model: "sonnet"}, {cli: "codex", model: "gpt-5-codex"}],
  mode: "quick"
})
```

**Conference Mode (multi-round):**
```javascript
mcp__ai-counsel__deliberate({
  question: "JWT vs session-based auth?",
  participants: [
    {cli: "claude", model: "sonnet"},
    {cli: "codex", model: "gpt-5-codex"}
  ],
  rounds: 3,
  mode: "conference"
})
```

**Search Past Decisions:**
```javascript
mcp__ai-counsel__query_decisions({
  query: "database choice",
  operation: "search_similar",
  limit: 5
})
// Returns: Similar past deliberations with consensus and similarity scores

// Find contradictions
mcp__ai-counsel__query_decisions({
  operation: "find_contradictions"
})
// Returns: Decisions where consensus conflicts

// Trace evolution
mcp__ai-counsel__query_decisions({
  query: "microservices architecture",
  operation: "trace_evolution"
})
// Returns: How opinions evolved over time on this topic
```

### Transcripts

All deliberations saved to `transcripts/` with AI-generated summaries and full debate history.

## Architecture

```
ai-counsel/
├── server.py                # MCP server entry point
├── config.yaml              # Configuration
├── adapters/                # CLI/HTTP adapters
│   ├── base.py             # Abstract base
│   ├── base_http.py        # HTTP base
│   └── [adapter implementations]
├── deliberation/            # Core engine
│   ├── engine.py           # Orchestration
│   ├── convergence.py      # Similarity detection
│   └── transcript.py       # Markdown generation
├── models/                  # Data models (Pydantic)
├── tests/                   # Unit/integration/e2e tests
└── decision_graph/         # Optional memory system
```

## Documentation Hub

### Getting Started
- **[Quick Start](README.md#quick-start)** - 5-minute setup
- **[Installation](README.md#installation)** - Detailed prerequisites and setup
- **[Usage Examples](README.md#usage)** - Quick and conference modes

### Core Concepts
- **[Convergence Detection](docs/convergence-detection.md)** - Auto-stop, thresholds, backends
- **[Structured Voting](docs/structured-voting.md)** - Vote structure, consensus types, vote grouping
- **[Evidence-Based Deliberation](README.md#evidence-based-deliberation)** - Ground decisions in reality with read_file, search_code, list_files, run_command
- **[Decision Graph Memory](docs/decision-graph/quickstart.md)** - Learning from past decisions

### Setup & Configuration
- **[HTTP Adapters](docs/http-adapters/intro.md)** - Ollama, LM Studio, OpenRouter setup
- **[Configuration Reference](docs/convergence-detection.md#configuration)** - All YAML options
- **[Migration Guide](docs/migration/cli_tools_to_adapters.md)** - From cli_tools to adapters

### Development
- **[Adding Adapters](docs/adding-adapters.md)** - CLI and HTTP adapter development
- **[CLAUDE.md](CLAUDE.md)** - Architecture, development workflow, gotchas
- **[Model Registry & Picker](docs/model-registry-and-picker.md)** - Managing allowlisted models and MCP picker tools

### Reference
- **[Troubleshooting](docs/troubleshooting/http-adapters.md)** - HTTP adapter issues
- **[Decision Graph Docs](docs/decision-graph/)** - Advanced memory features

## Development

### Running Tests

```bash
pytest tests/unit -v                    # Unit tests (fast)
pytest tests/integration -v -m integration  # Integration tests
pytest --cov=. --cov-report=html       # Coverage report
```

See [CLAUDE.md](CLAUDE.md) for development workflow and architecture notes.

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Write tests first (TDD workflow)
4. Implement feature
5. Ensure all tests pass
6. Submit PR with clear description

## License

MIT License - see LICENSE file

## Credits

Built with:
- [MCP SDK](https://modelcontextprotocol.io/) - Model Context Protocol
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [pytest](https://pytest.org/) - Testing framework

Inspired by the need for true deliberative AI consensus beyond parallel opinion gathering.

---

## Status

![GitHub stars](https://img.shields.io/github/stars/blueman82/ai-counsel)
![GitHub forks](https://img.shields.io/github/forks/blueman82/ai-counsel)
![GitHub last commit](https://img.shields.io/github/last-commit/blueman82/ai-counsel)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Tests](https://img.shields.io/badge/tests-130%2B%20passing-green)
![Version](https://img.shields.io/badge/version-1.2.1-blue)

**Production Ready** - Multi-model deliberative consensus with cross-user decision graph memory, structured voting, and adaptive early stopping for critical technical decisions!
