# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Counsel is an MCP (Model Context Protocol) server that enables true deliberative consensus between AI models. Unlike parallel opinion gathering, models see each other's responses and refine positions across multiple rounds of debate.

**Key differentiation**: Models engage in actual debate with cross-pollination (not just parallel aggregation).

**Production Ready**: 113+ passing tests, type-safe validation, graceful error handling, structured logging, convergence detection, AI-powered summaries, evidence-based deliberation with secure tool execution.

## Architecture

### Core Components

**MCP Server Layer** (`server.py`)
- Entry point for MCP protocol communication via stdio
- Exposes 2 MCP tools: `deliberate` and `query_decisions` (when decision graph enabled)
- Handles JSON serialization and response truncation for token limits
- Logs to `mcp_server.log` (not stdout/stderr to avoid stdio interference)

**Deliberation Engine** (`deliberation/engine.py`)
- Orchestrates multi-round debates between models
- Manages context building from previous responses
- Coordinates convergence detection and early stopping
- Initializes AI summarizer with fallback chain: Claude Sonnet → GPT-5 Codex → Droid → Gemini
- Integrates tool execution system for evidence-based deliberation

**Tool Execution System** (`deliberation/tools.py`, `models/tool_schema.py`)
- Base: `BaseTool` with `execute()` method and security controls
- Tools: `ReadFileTool` (configurable size limit), `SearchCodeTool`, `ListFilesTool`, `RunCommandTool` (whitelist: ls, grep, find, cat, head, tail), `GetFileTreeTool` (ASCII output for clean JSON)
- Orchestrator: `ToolExecutor` parses TOOL_REQUEST markers, validates, routes to tools
- Security: Whitelisted commands, file size limits, timeout protection (10s default), path exclusion patterns (prevents context contamination)
- Path Exclusions: Configurable patterns to block access to sensitive directories (e.g., `transcripts/`, `.git/`, `node_modules/`)
- File Tree Rendering: Uses ASCII characters (`|--`) in tool responses for clean JSON serialization; Unicode box-drawing (`├──`) in Round 1 prompts for better readability
- Context injection: Tool results visible to all participants in subsequent rounds

**CLI Adapters** (`adapters/base.py`, `adapters/claude.py`, etc.)
- Base: `BaseCLIAdapter` handles subprocess execution, timeout, error handling
- Concrete: `ClaudeAdapter`, `CodexAdapter`, `DroidAdapter`, `GeminiAdapter`, `LlamaCppAdapter`
- Factory pattern in `adapters/__init__.py` creates adapters from config
- **Working Directory Isolation**: All adapters run subprocesses from `working_directory` parameter (client's current directory), preventing models from analyzing the wrong repository
- **LlamaCpp Auto-Discovery**: Resolves model names to file paths automatically, searches default paths, supports fuzzy matching
- **Model Size Recommendations**:
  - Minimum: 7B-8B parameters (Llama-3-8B, Mistral-7B, Qwen-2.5-7B)
  - Not recommended: <3B parameters (struggle with vote formatting, echo prompts)
  - Token limits: Use 2048+ tokens for complete responses

**Working Directory Isolation** (`adapters/base.py`)
- All CLI adapters run subprocesses from the `working_directory` passed by MCP clients
- Prevents models from analyzing the AI Counsel codebase when deliberating about user projects
- **Claude**: Default isolation via subprocess cwd - models only see files in working directory
- **Gemini**: Workspace boundaries via `--include-directories` flag + subprocess cwd - strict isolation
- **Codex**: **Known limitation** - can access any file regardless of working_directory (no true isolation)
- **Droid**: Subprocess cwd provides basic isolation (no additional flags needed)
- Flow: MCP client's cwd → `deliberate` tool's `working_directory` → adapter subprocess cwd → model sees correct repository
- Important: Without `working_directory`, adapters default to current directory (usually the AI Counsel directory)

**HTTP Adapter Layer** (`adapters/base_http.py`, `adapters/ollama.py`, etc.)
- Base: `BaseHTTPAdapter` handles HTTP mechanics, retry logic, error handling
- Concrete: `OllamaAdapter`, `LMStudioAdapter`
- Retry: exponential backoff on 5xx/429/network errors, fail-fast on 4xx
- Authentication: environment variable substitution `${VAR_NAME}` in config
- Uses `httpx` for async HTTP, `tenacity` for retry

**Config Schema** (`models/config.py`, `scripts/migrate_config.py`)
- `adapters` section with explicit `type` field: `cli` or `http`
- Type discrimination: `CLIAdapterConfig` vs `HTTPAdapterConfig`
- Backward compatible with legacy `cli_tools` section
- Migration: `python scripts/migrate_config.py config.yaml`

**Convergence Detection** (`deliberation/convergence.py`)
- Semantic similarity between consecutive rounds
- Backends: SentenceTransformer (best) → TF-IDF → Jaccard (zero deps)
- Statuses: converged (≥85%), refining (40-85%), diverging (<40%), impasse
- Voting-aware: overrides semantic status with voting outcomes

**Structured Voting** (`models/schema.py`)
- Vote: option, confidence (0.0-1.0), rationale, continue_debate flag
- Aggregates into VotingResult with tally and winning option
- Voting overrides semantic similarity: 2-1 vote → "majority_decision", 3-0 → "unanimous_consensus"

**Model-Controlled Early Stopping** (`deliberation/engine.py`)
- Models signal readiness via `continue_debate: false` in votes
- Engine checks threshold (default: 66%) after each round
- Respects min_rounds before allowing early stop
- Config: `deliberation.early_stopping.enabled`, `threshold`, `respect_min_rounds`

**Transcript Management** (`deliberation/transcript.py`)
- Generates markdown in `transcripts/` directory
- Format: `YYYYMMDD_HHMMSS_Question_truncated.md`
- Includes AI summary, full debate, voting section, tool executions

**Data Models** (`models/schema.py`)
- Pydantic validation: `Participant`, `DeliberateRequest`, `RoundResponse`, `Summary`, `ConvergenceInfo`, `DeliberationResult`
- Voting: `Vote`, `RoundVote`, `VotingResult`
- Type-safe throughout system

**Configuration** (`config.yaml`)
- See `config.yaml` for adapter configs, timeouts, convergence thresholds
- Per-CLI command templates with `{model}` and `{prompt}` placeholders
- Hook disabling for Claude: `--settings '{"disableAllHooks": true}'`

### Data Flow

1. MCP client invokes `deliberate` tool → `server.py::call_tool()` with `working_directory` set to client's current directory
2. Request validated against `DeliberateRequest` schema
3. `DeliberationEngine.execute()` orchestrates rounds
4. For each round:
   - `execute_round()` → prompts enhanced with voting instructions → adapters invoke CLIs with `working_directory`
   - **Adapter isolation**: Subprocess runs from `working_directory` (client's cwd), models analyze correct repository
   - Responses collected and votes parsed from "VOTE: {json}" markers
   - **Tool request parsing**: Extract TOOL_REQUEST markers from responses
   - **Tool execution**: Change to `working_directory`, validate, execute with timeout/error handling, restore original directory
   - **Context injection**: Tool results visible to all participants in next round
   - **Recording**: Track in `ToolExecutionRecord` for transcript
   - Check early stopping: if ≥66% want to stop → break
5. After round 2+: convergence detection compares current vs previous round
6. If converged/impasse/early-stop: stop early; else continue to max rounds
7. Aggregate voting results: determine winner, consensus status
8. AI summarizer generates structured summary
9. Override convergence status with voting outcome if available
10. `TranscriptManager` saves markdown with "Tool Executions" section
11. Result serialized and returned to MCP client

### MCP Tool Architecture

**MCP-Exposed Tools** (callable by MCP clients):
- `deliberate`: Orchestrate multi-round AI deliberation (requires `working_directory` parameter)
- `query_decisions`: Search decision graph memory (when enabled)

**Internal Tools** (callable by AI models via TOOL_REQUEST):
- `read_file`: Read file contents (max 1MB)
- `search_code`: Search codebase with regex patterns
- `list_files`: List files matching glob patterns
- `run_command`: Execute safe read-only commands

**Important**: Internal tools are NOT directly exposed via MCP. They are invoked by AI models during deliberation by including TOOL_REQUEST markers in responses. Engine parses markers, executes tools, makes results visible to all participants.

**Example**: `TOOL_REQUEST: {"name": "read_file", "arguments": {"path": "/path/to/file.py"}}`

**Why Two Tool Types?**
- MCP tools: Clients start deliberations and query results
- Internal tools: AI models gather evidence during deliberation
- Separation keeps MCP interface clean while empowering models with research capabilities

### Decision Graph Memory

The decision graph module (`decision_graph/`) enables persistent learning from deliberations.

**Module Structure**: `schema.py`, `storage.py`, `similarity.py`, `retrieval.py`, `integration.py`, `cache.py`, `workers.py`, `maintenance.py`, `query_engine.py`, `exporters.py`

**Core Components**:
- **Schema**: `DecisionNode`, `ParticipantStance`, `DecisionSimilarity`
- **Storage**: SQLite3 with CRUD operations, indexed by timestamp/question_hash/decision_id
- **Retrieval**: Uses convergence backend, configurable threshold (default: 0.7), max results (default: 3)
- **Integration**: `store_deliberation()`, `get_context_for_deliberation()`, async background workers
- **Performance**: LRU cache (200 query + 500 embedding entries), 10 jobs/sec, p95 <450ms latency
- **Query Engine**: Unified interface for search_similar(), find_contradictions(), trace_evolution()
- **Export**: JSON, GraphML, DOT, Markdown formats

**Data Flow**:
- **Write**: Extract from DeliberationResult → save to SQLite → queue async similarity computation
- **Read**: Query recent decisions → compute similarity → format as markdown → prepend to Round 1 prompt
- **Background**: Async worker computes similarities vs recent decisions, stores top-20

**Performance**:
- Store: <100ms (async background similarity)
- Query (cache hit): <2μs
- Query (cache miss): <100ms
- Background similarity: <10s per decision
- Memory: ~5KB per decision

**Configuration**: See `config.yaml` for `decision_graph.enabled`, `db_path`, `similarity_threshold`, `max_context_decisions`

### Evidence-Based Deliberation

Enables AI models to gather concrete evidence during debates by executing tools. Tool results visible to ALL participants in subsequent rounds.

**Tool Interface**: `BaseTool` with async `execute(**kwargs) -> ToolResult`, timeout protection, error isolation

**Available Tools**:
1. **ReadFileTool**: Max 1MB, path validation, descriptive errors
2. **SearchCodeTool**: Uses ripgrep (falls back to grep), output truncation
3. **ListFilesTool**: Glob patterns, recursive search, directory validation
4. **RunCommandTool**: Whitelist (ls, grep, find, cat, head, tail), no shell injection

**Security**:
- Input validation: Pydantic schema prevents malformed requests
- Resource limits: Configurable file size (default 1MB), 10s timeout, output truncation
- Path exclusions: Blocks access to configured patterns (`transcripts/`, `.git/`, `node_modules/`, etc.) to prevent context contamination
- Isolation: Tool failures don't halt deliberation
- Audit trail: All executions recorded with timestamps
- Known limitations: No sandboxing beyond path exclusions, no rate limiting

**Performance**:
- Parse: <1ms, Validate: <1ms
- read_file: <10ms, search_code: 50-200ms, list_files: <20ms, run_command: 10-100ms

## Development Commands

### Virtual Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
pip install -r requirements-optional.txt  # Optional: Enhanced convergence backends
```

### Testing
```bash
pytest tests/unit -v                      # Unit tests
pytest tests/integration -v -m integration # Integration tests
pytest tests/e2e -v -m e2e                # E2E tests
pytest --cov=. --cov-report=html          # Coverage report
```

### Code Quality
```bash
black .           # Format
ruff check .      # Lint
mypy .            # Type check (optional)
```

### Running the Server
**Development**: `python server.py` (logs to mcp_server.log and stderr)
**Production**: Configure in `~/.claude/config/mcp.json`, check `mcp_server.log` for debugging

## Configuration Notes

### Timeouts
- Default: 60s per invocation
- Reasoning models (Claude Sonnet 4.5, GPT-5-Codex): 180-300s recommended
- Configure per-CLI in `config.yaml::adapters::<name>::timeout`

### Convergence Detection
- Enabled by default: `deliberation.convergence_detection.enabled: true`
- Threshold: 0.85 (85% similarity = converged)
- Min rounds before checking: `min_rounds_before_check: 1` (checks from round 2)
- **Important**: Must be `<= rounds - 1` for convergence info. For 2-round deliberations, use `min_rounds_before_check: 1`
- Voting override: Voting outcomes override semantic similarity

### Model-Controlled Early Stopping
- Enabled: `deliberation.early_stopping.enabled: true`
- Threshold: 0.66 (66% must want to stop)
- Respects min rounds: `respect_min_rounds: true`
- Example: 3 models, 2 say `continue_debate: false` → stops (2/3 = 66%)

### Hook Management
Claude CLI: `--settings '{"disableAllHooks": true}'` prevents hooks from interfering. Critical for reliable execution.

### MCP Response Truncation
- `mcp.max_rounds_in_response: 3` limits rounds in MCP response (avoids token limits)
- Tool executions are summarized (count by round/type) in MCP response, not full output
- Full transcript with complete tool outputs always saved to file

## Extension Guides

For detailed step-by-step guides on extending the system, see:
- **[Adding a New CLI Adapter](docs/adding-cli-adapter.md)**: Subclass `BaseCLIAdapter`, implement `parse_output()`, register in factory
- **[Adding a New HTTP Adapter](docs/adding-http-adapter.md)**: Subclass `BaseHTTPAdapter`, implement `build_request()` and `parse_response()`, configure retry logic
- **[Adding a New Tool](docs/adding-tool.md)**: Subclass `BaseTool`, implement `execute()`, register in `ToolExecutor`, update schema, write tests

## Design Principles

- **DRY**: Common logic in base classes, specific parsing in subclasses
- **YAGNI**: Build only what's needed, no premature optimization
- **TDD**: Red-green-refactor cycle for all features
- **Simple**: Straightforward solutions over clever abstractions
- **Type Safety**: Pydantic validation throughout
- **Error Isolation**: Adapter failures don't halt entire deliberation
- **NO TODOs**: Never commit TODO comments. All configuration must be in `config.yaml` with Pydantic schemas in `models/config.py`. Hardcoded values are technical debt that violate the project's configuration architecture

## Common Gotchas

1. **Stdio Contamination**: Server uses stdio for MCP protocol. All logging MUST go to file or stderr, never stdout.
2. **Timeout Tuning**: Reasoning models can take 60-120+ seconds. Undersized timeouts cause spurious failures.
3. **Convergence Backend**: Optional backends (TF-IDF, SentenceTransformer) improve quality but add dependencies. Zero-dep Jaccard backend always available.
4. **Model ID Format**: Some CLIs (droid) require full model IDs like `claude-sonnet-4-5-20250929`, not aliases like `sonnet`.
5. **Context Building**: Previous responses passed as context to subsequent rounds. Large debates = large context. Monitor token usage.
6. **Async Execution**: Engine uses `asyncio` for subprocess management. All adapter invocations are async.
7. **Hook Interference**: Claude CLI hooks can break CLI invocations during deliberation. Always disable with `--settings` flag.
8. **Prompt Length Limits**: Gemini adapter validates prompts ≤100k chars (prevents "invalid argument" API errors). `BaseCLIAdapter.invoke()` checks `validate_prompt_length()` if adapter implements it and raises `ValueError` with helpful message before making API call. Other adapters can implement similar validation.
9. **Tool Execution Errors**: Tool failures are isolated - they don't halt deliberation. Models receive error messages in tool results and can adapt their reasoning. Always check `ToolResult.success` before using `output`.
10. **Working Directory Requirement**: The `deliberate` tool requires a `working_directory` parameter (client's current directory). Tools resolve relative paths from this directory. Without it, the request will fail validation. MCP clients should always pass their current working directory.
11. **Database Directory Creation**: `DecisionGraphStorage` automatically creates parent directories for the database file if they don't exist. This prevents "readonly database" errors for first-time users. If you get SQLite errors, check file/directory permissions, not just existence.
12. **Tool Path Exclusions**: Tools automatically exclude configured patterns (`transcripts/`, `.git/`, etc.) to prevent context contamination. When models read transcript files from previous deliberations about different codebases, they get confused and describe the wrong repository. File tree generation also excludes these directories.
13. **NO TODOs - Configuration Pattern Violation**: Never commit TODO comments or hardcoded configuration values. This violates the project's configuration architecture where ALL settings live in `config.yaml` and are validated via Pydantic schemas in `models/config.py`. If you find yourself writing `# TODO: Make configurable`, STOP immediately and implement proper configuration first. Example violation: `max_depth=3 # TODO: Make configurable`. Correct approach: Add `FileTreeConfig` to `models/config.py`, add section to `config.yaml`, read from `self.config.deliberation.file_tree.max_depth`. This pattern applies to ALL configurable values across the entire codebase.

## Common Development Patterns

### Accessing Decision Graph
```python
# From integration layer
integration = DecisionGraphIntegration()
context = await integration.get_context_for_deliberation(question)
await integration.store_deliberation(question, result)

# From query engine
engine = QueryEngine()
results = await engine.search_similar("question", limit=5)
```

### Tool Usage in Deliberations
```python
# Evidence gathering
"Let me check: TOOL_REQUEST: {\"name\": \"read_file\", \"arguments\": {\"path\": \"/file.py\"}}"

# Code search
"I'll search: TOOL_REQUEST: {\"name\": \"search_code\", \"arguments\": {\"pattern\": \"regex\", \"path\": \"/path\"}}"

# Evidence-based voting
"TOOL_REQUEST: {...}\nBased on evidence: VOTE: {\"option\": \"A\", \"confidence\": 0.9, ...}"
```

### File System Tool Validation
```python
# Validate paths
if not os.path.exists(path):
    return ToolResult(success=False, error=f"Path not found: {path}")

# Check file size
if os.path.getsize(path) > MAX_SIZE:
    return ToolResult(success=False, error=f"File too large (max {MAX_SIZE} bytes)")
```

### Command Whitelisting
```python
ALLOWED_COMMANDS = {"ls", "grep", "find", "cat", "head", "tail"}
command_name = command.split()[0]
if command_name not in ALLOWED_COMMANDS:
    return ToolResult(success=False, error=f"Command not allowed: {command_name}")
```

### Async Operations with Timeout
```python
try:
    result = await asyncio.wait_for(slow_operation(), timeout=self.timeout)
except asyncio.TimeoutError:
    return ToolResult(success=False, error="Operation timed out")
```

### Proper Configuration Pattern (NO TODOs)
```python
# WRONG - NEVER DO THIS
def my_function(self):
    max_depth = 3  # TODO: Make configurable
    max_files = 100  # TODO: Make configurable

# RIGHT - Configuration-First Approach
# 1. Add to models/config.py
class MyFeatureConfig(BaseModel):
    max_depth: int = Field(default=3, ge=1, le=10)
    max_files: int = Field(default=100, ge=10, le=1000)

class DeliberationConfig(BaseModel):
    my_feature: MyFeatureConfig = Field(default_factory=MyFeatureConfig)

# 2. Add to config.yaml
deliberation:
  my_feature:
    max_depth: 3
    max_files: 100

# 3. Use in code
def my_function(self):
    config = self.config.deliberation.my_feature
    max_depth = config.max_depth
    max_files = config.max_files
```

## Testing Strategy

- **Unit Tests**: Mock adapters, test engine logic, convergence detection, transcript generation, tool execution, schema validation
- **Integration Tests**: Real CLI invocations (requires tools installed), convergence with real adapters, context injection, concurrent writes, performance benchmarks
- **E2E Tests**: Full workflow with real API calls (slow, expensive, use sparingly)
- **Fixtures**: `tests/conftest.py` provides shared fixtures for adapter mocking
- **Coverage**: 113+ tests, comprehensive coverage across all modules

## Development Workflow

1. Write test first (TDD)
2. Implement feature
3. Run unit tests: `pytest tests/unit -v`
4. Format/lint: `black . && ruff check .`
5. Integration test if needed: `pytest tests/integration -v`
6. Update CLAUDE.md if architecture changes
7. Commit with clear message

## MCP Integration

This server implements MCP protocol for Claude Code integration:
- **Transport**: stdio (stdin/stdout)
- **Tools**: `deliberate` and `query_decisions` with structured JSON I/O
- **Initialization**: `mcp.server.stdio.stdio_server()`
- **Error Handling**: Errors serialized to JSON with `error_type` and `status` fields
