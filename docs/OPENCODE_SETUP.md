# OpenCode Setup Guide

Complete guide for using OpenCode with this Claude Code configuration repository.

## What is OpenCode?

**OpenCode** is an open-source, terminal-based AI coding agent built in Go that:
- Runs in your terminal with a TUI (Text User Interface)
- Supports multiple AI providers: Claude, OpenAI, Gemini, AWS Bedrock, Groq
- Has full MCP (Model Context Protocol) server support
- Integrates with VS Code/Cursor via terminal split (Cmd+Esc / Ctrl+Esc)
- Uses LSP (Language Server Protocol) for codebase understanding

## Why Use OpenCode Alongside Claude Code?

| Advantage | Details |
|-----------|---------|
| **Multi-Model** | Use different AI providers (Claude + Gemini + OpenAI) for different tasks |
| **Lightweight** | Lower resource usage than full IDE integration |
| **Terminal-First** | Perfect for server work, SSH sessions, quick iterations |
| **Same MCP Servers** | Leverage your existing MCP infrastructure |
| **Open Source** | Community-driven, customizable |

## Installation

### macOS (Homebrew)
```bash
brew install opencode
```

### npm (Cross-platform)
```bash
npm install -g opencode
```

### Verify Installation
```bash
opencode --version
```

## Configuration Overview

This repository includes a complete OpenCode configuration that mirrors your Claude Code setup:

```
/Users/administrator/dev/tfwg/claude-config/
├── config/
│   ├── opencode.json              # OpenCode MCP servers (version controlled)
│   └── settings-laptop.json        # Claude Code settings
├── agents/                         # Shared agents (19 total)
├── rules/                          # OpenCode rules (5 total)
├── .claude/commands/              # Claude Code slash commands (5 total)
└── mcp-servers/                    # Custom MCP implementations

Symlinks created:
~/.config/opencode/opencode.json   → config/opencode.json
~/.config/opencode/agent/          → repo-agents/ → agents/
~/.config/opencode/rule/           → repo-rules/ → rules/
```

## MCP Servers (10 Total)

All configured and ready to use:

### Core Infrastructure
1. **filesystem** - File operations (scoped to `/Users/administrator/dev`)
2. **memory** - Persistent knowledge graph
3. **sqlite** - Database operations

### Development Tools
4. **serena** - IDE assistant with semantic code tools
5. **headless-terminal** - Terminal operations

### Web & Search
6. **brave-search** - Web search capability
7. **chrome-bridge** - Browser automation

### Custom/Specialized
8. **dataforseo** - SEO tools (local implementation)
9. **zen** - Multi-model AI orchestration
10. **promos** - Custom promo server

## Usage

### Basic Usage

Launch OpenCode from your project directory:
```bash
cd /Users/administrator/dev/tfwg/claude-config
opencode
```

### IDE Integration

In VS Code or Cursor:
- **macOS**: Cmd+Esc
- **Windows/Linux**: Ctrl+Esc

### Agent Modes

**Build Mode** (default):
```bash
opencode
```
Full access agent for development work.

**Plan Mode** (read-only):
```bash
opencode --mode plan
```
For analysis and code exploration without making changes.

### Accessing Agents

Your 19 custom agents are available through the symlinked `repo-agents/` directory:

**Example agents:**
- backend-architect
- code-reviewer
- debugger
- frontend-developer
- database-architect
- security-auditor
- test-runner
- refactoring-specialist
- And 11 more...

### Accessing Rules (Commands)

Your 5 slash commands are available as rules through `repo-rules/`:

- feature-plan
- debug-loop
- test-suite
- api-spec
- doc-generate

## Testing Your Setup

### 1. Verify MCP Servers Load

```bash
opencode
# In OpenCode, check that MCP servers are connected
# Look for filesystem, memory, brave-search, etc.
```

### 2. Test Basic MCP Tool

Try using the filesystem or memory MCP server:
```
Use the filesystem MCP to list files in this directory
```

### 3. Test Custom Agent

Reference one of your custom agents:
```
I need help with backend architecture
```

### 4. Test Rule/Command

Try one of your rules:
```
Help me plan a new feature for user authentication
```

## Troubleshooting

### MCP Server Not Starting

**Check environment variables:**
```bash
echo $DATAFORSEO_USERNAME
echo $BRAVE_API_KEY
echo $GEMINI_API_KEY
```

**Test server command directly:**
```bash
node /Users/administrator/dev/tfwg/claude-config/mcp-servers/mcp-seo/build/main/main/cli.js
```

**Verify paths:**
```bash
ls -la /Users/administrator/dev/tfwg/claude-config/mcp-servers/
```

### Agents Not Appearing

**Check symlinks:**
```bash
ls -la ~/.config/opencode/agent/
cat ~/.config/opencode/agent/repo-agents/backend-architect.md
```

**Verify symlink targets:**
```bash
readlink ~/.config/opencode/agent/repo-agents
# Should point to: /Users/administrator/dev/tfwg/claude-config/agents
```

### Environment Variables Not Working

**Export in shell before launching:**
```bash
export BRAVE_API_KEY="your-key-here"
export DATAFORSEO_USERNAME="your-username"
export DATAFORSEO_PASSWORD="your-password"
opencode
```

**Or use a .env file:**
```bash
# Create ~/.opencode/.env
BRAVE_API_KEY=xxx
DATAFORSEO_USERNAME=xxx
DATAFORSEO_PASSWORD=xxx
```

### Config File Not Loading

**Verify symlink:**
```bash
ls -la ~/.config/opencode/opencode.json
# Should point to: /Users/administrator/dev/tfwg/claude-config/config/opencode.json
```

**Validate JSON:**
```bash
cat ~/.config/opencode/opencode.json | jq .
```

## Dual-Tool Workflow

Use both Claude Code and OpenCode simultaneously:

### Recommended Pattern

**Terminal 1: Claude Code** (IDE integration)
```bash
cd /Users/administrator/dev/tfwg/my-project
claude
```

**Terminal 2: OpenCode** (quick iterations)
```bash
cd /Users/administrator/dev/tfwg/my-project
opencode
```

**Terminal 3: VS Code with OpenCode split**
```
Cmd+Esc to toggle OpenCode panel
```

### When to Use Each

**Claude Code:**
- Full IDE integration
- Complex multi-file edits
- Visual diffs and reviews
- Git operations
- Familiar workflow

**OpenCode:**
- Quick terminal tasks
- Server/SSH sessions
- Multi-model experimentation
- Lightweight operations
- Fast iterations

## Advanced Configuration

### Enable Only Specific MCP Servers

Edit `config/opencode.json`:
```json
"mcp": {
  "serena": {
    "enabled": false  // Disable heavy servers when not needed
  }
}
```

### Add New MCP Server

1. Add to `config/opencode.json`:
```json
"my-custom-server": {
  "type": "local",
  "command": ["node", "/path/to/server.js"],
  "enabled": true
}
```

2. Commit to version control:
```bash
git add config/opencode.json
git commit -m "Add my-custom-server MCP configuration"
```

3. Changes are immediately available through symlink

### Project-Specific Overrides

Create `.opencode/opencode.json` in any project:
```json
{
  "mcp": {
    "project-specific-tool": {
      "type": "local",
      "command": ["node", "./tools/custom-mcp.js"],
      "enabled": true
    }
  }
}
```

## Environment Variables

OpenCode respects these environment variables:

### API Keys
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
```

### MCP Server Variables
```bash
export BRAVE_API_KEY="..."
export DATAFORSEO_USERNAME="..."
export DATAFORSEO_PASSWORD="..."
export DISABLED_TOOLS="..."  # For zen server
export DEFAULT_MODEL="..."   # For zen server
```

### Paths
```bash
export REPO_ROOT="/Users/administrator/dev/tfwg/claude-config"
```

## Comparison with Claude Code

| Feature | Claude Code | OpenCode |
|---------|-------------|----------|
| **Interface** | CLI + IDE integration | TUI (Terminal UI) |
| **AI Models** | Claude only | Claude, OpenAI, Gemini, Bedrock, Groq |
| **MCP Support** | Yes (.claude.json, settings.json) | Yes (opencode.json) |
| **Custom Agents** | Yes (.claude/agents/) | Yes (~/.config/opencode/agent/) |
| **Commands** | Slash commands | Rules |
| **IDE Integration** | Native VS Code/Cursor | Terminal split in VS Code/Cursor |
| **Configuration** | settings.json | opencode.json |
| **Open Source** | Proprietary (Anthropic) | Open source (SST) |
| **Resource Usage** | Medium | Low |
| **Best For** | Full IDE workflows | Terminal-first workflows |

## Maintaining Configuration

### Syncing Changes

Since agents and rules are symlinked, changes in the repo automatically sync:

**Add new agent:**
```bash
# In repo
vim agents/my-new-agent.md

# Immediately available in OpenCode (through symlink)
```

**Add new rule:**
```bash
# In repo
vim rules/my-new-command.md

# Immediately available in OpenCode (through symlink)
```

**Update MCP config:**
```bash
# Edit in repo
vim config/opencode.json

# Immediately available (through symlink)
```

### Version Control

Commit your changes to keep everything in sync:
```bash
git add config/opencode.json
git add agents/my-new-agent.md
git add rules/my-new-command.md
git commit -m "Add new agent and rule for OpenCode"
git push
```

### Team Collaboration

Share OpenCode configuration with your team:

1. Team members clone the repo:
```bash
git clone <repo-url>
cd claude-config
```

2. Run setup script (create one):
```bash
./scripts/setup-opencode.sh
```

3. Script creates symlinks:
```bash
#!/bin/bash
mkdir -p ~/.config/opencode/agent ~/.config/opencode/rule
ln -sf "$(pwd)/config/opencode.json" ~/.config/opencode/opencode.json
ln -sf "$(pwd)/agents" ~/.config/opencode/agent/repo-agents
ln -sf "$(pwd)/rules" ~/.config/opencode/rule/repo-rules
```

## Resources

- **OpenCode Documentation**: https://opencode.ai/docs/
- **OpenCode GitHub**: https://github.com/sst/opencode
- **MCP Documentation**: https://modelcontextprotocol.io/
- **Claude Code Docs**: https://code.claude.com/docs/

## Support

### OpenCode Issues
- GitHub Issues: https://github.com/sst/opencode/issues
- Discord: https://discord.gg/sst

### Claude Code Issues
- GitHub Issues: https://github.com/anthropics/claude-code/issues

## Quick Reference Card

```
OPENCODE QUICK REFERENCE

Launch:
  opencode                    # Start in build mode
  opencode --mode plan        # Start in plan mode (read-only)

IDE Integration:
  Cmd+Esc (Mac)              # Toggle OpenCode in VS Code/Cursor
  Ctrl+Esc (Win/Linux)       # Toggle OpenCode in VS Code/Cursor

Configuration:
  ~/.config/opencode/opencode.json    # Main config (symlinked)
  ~/.config/opencode/agent/           # Agents directory (symlinked)
  ~/.config/opencode/rule/            # Rules directory (symlinked)

MCP Servers (10):
  serena, headless-terminal, dataforseo, chrome-bridge, zen,
  brave-search, filesystem, memory, sqlite, promos

Agents (19):
  backend-architect, code-reviewer, debugger, frontend-developer,
  database-architect, security-auditor, test-runner, and 12 more

Rules (5):
  feature-plan, debug-loop, test-suite, api-spec, doc-generate

Troubleshooting:
  opencode --help            # Show help
  cat ~/.config/opencode/opencode.json | jq .  # Validate config
  ls -la ~/.config/opencode/  # Check symlinks
```
