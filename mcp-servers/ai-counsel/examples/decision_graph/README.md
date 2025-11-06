# Decision Graph Memory Examples

Runnable examples demonstrating the decision graph memory feature of AI Counsel.

## Quick Start

**Prerequisites**:
- AI Counsel with decision graph enabled in `config.yaml`
- At least one AI CLI tool (claude, codex, droid, or gemini)
- Python 3.11+

## Examples

### 1. Basic Usage (`basic_usage.py`)

Demonstrates the core functionality: storing deliberations in the graph and using context from past decisions.

```bash
# Run from project root
python examples/decision_graph/basic_usage.py
```

**What it does:**
1. Runs a deliberation on architecture decisions
2. Stores the result in the decision graph
3. Runs a second deliberation on a related topic
4. Automatically retrieves and injects context from the first deliberation
5. Shows how the second deliberation can leverage past decisions

**Expected output:**
- Two deliberations with consensus results
- Graph context usage information
- Path to generated transcripts

### 2. Graph Inspection (`inspect_graph.py`)

Shows how to query the decision graph to find similar decisions, contradictions, and patterns.

```bash
# Requires at least 2-3 deliberations in the graph first
python examples/decision_graph/inspect_graph.py
```

**What it does:**
1. Connects to the decision graph database
2. Lists all stored decisions
3. Searches for similar deliberations
4. Identifies contradictions or disagreements
5. Analyzes decision patterns across deliberations

**Expected output:**
- Statistics on stored decisions
- Similar decisions to a sample query
- Any contradictions found
- Pattern analysis (convergence time, model agreement, etc.)

### 3. Transcript Migration (`migrate_transcripts.py`)

Back-fills existing deliberation transcripts into the decision graph. Useful if you have existing deliberations and want to enable the graph feature retroactively.

```bash
# Run from project root
python examples/decision_graph/migrate_transcripts.py
```

**What it does:**
1. Scans the `transcripts/` directory
2. Extracts metadata from each transcript
3. Shows what would be migrated (dry-run)
4. Prompts for confirmation
5. Migrates selected transcripts to the graph

**Expected output:**
- List of transcripts found
- Metadata extracted from each
- Confirmation prompt
- Success message with migration count

## Typical Workflow

### First Time Setup

1. **Enable the feature:**
   ```yaml
   # config.yaml
   decision_graph:
     enabled: true
     db_path: "decision_graph.db"
   ```

2. **Run basic usage to populate graph:**
   ```bash
   python examples/decision_graph/basic_usage.py
   ```

3. **Run more deliberations** through Claude Code or CLI to build history

### Working with Historical Data

4. **Migrate existing transcripts (optional):**
   ```bash
   python examples/decision_graph/migrate_transcripts.py
   ```

5. **Inspect the graph:**
   ```bash
   python examples/decision_graph/inspect_graph.py
   ```

## Querying the Graph via CLI

After populating the graph with examples or real deliberations, use the CLI:

```bash
# Find similar past decisions
ai-counsel graph similar --query "database scaling strategies"

# Find contradictions in decision history
ai-counsel graph contradictions

# Trace how a decision evolved
ai-counsel graph timeline --decision-id <decision-id>

# Export for visualization
ai-counsel graph export --format graphml > decisions.graphml
```

## Troubleshooting

**"Decision graph is disabled in config.yaml"**
- Enable it: Set `decision_graph.enabled: true` in `config.yaml`

**"Graph is empty"**
- The graph is populated by running deliberations
- Use `basic_usage.py` or run deliberations through Claude Code

**"No transcripts found"**
- Transcripts are saved in the `transcripts/` directory
- Ensure you have run at least one deliberation first

**"QueryEngine errors"**
- Ensure `decision_graph.db` file exists (created automatically on first use)
- Check that the database is not corrupted: `sqlite3 decision_graph.db ".schema"`

## Performance Notes

- First query may take a few seconds (similarity computation)
- Subsequent queries are cached and instant
- Large graphs (1000+ decisions) still maintain <100ms query latency
- Background similarity computation runs asynchronously (non-blocking)

## Advanced Usage

For custom queries or programmatic access:

```python
from decision_graph.query_engine import QueryEngine
from models.config import load_config

config = load_config()
engine = QueryEngine(config)

# Search similar
results = await engine.search_similar("your query", limit=5)

# Find contradictions
contradictions = await engine.find_contradictions()

# Analyze patterns
patterns = await engine.analyze_patterns()
```

## Documentation

For more information, see:
- [Decision Graph Quickstart](../../docs/decision-graph/quickstart.md)
- [Configuration Reference](../../docs/decision-graph/configuration.md)
- [Troubleshooting Guide](../../docs/decision-graph/troubleshooting.md)
