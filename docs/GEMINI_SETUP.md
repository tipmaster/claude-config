# Gemini CLI Setup Guide

Complete guide for using Google's Gemini CLI with this Claude Code configuration repository.

## What is Gemini CLI?

**Gemini CLI** is Google's official terminal-based AI coding agent that:
- Runs in your terminal with autonomous agent capabilities
- Uses Google's Gemini models (2.0 Flash, 1.5 Pro, etc.)
- Has excellent MCP (Model Context Protocol) support
- Features 1M token context window for large codebases
- Uses TOML files for custom slash commands
- Integrates with IDE workflows

## Why Use Gemini CLI Alongside Claude Code?

| Advantage | Details |
|-----------|---------|
| **Google's Models** | Access Gemini 2.0 Flash (fast), 1.5 Pro (deep reasoning) |
| **Huge Context** | 1M token window - perfect for large codebases |
| **Free Tier** | Generous free quota for experimentation |
| **Same MCP Servers** | Leverage your existing MCP infrastructure |
| **Shared Agents** | All 19 custom agents work seamlessly |
| **TOML Commands** | Structured command syntax |

## Installation

### Install Gemini CLI

```bash
# Install via npm
npm install -g @google/generative-ai-cli

# Or via pip
pip install google-generativeai-cli

# Verify installation
gemini --version
```

### Get API Key

1. Visit https://aistudio.google.com/app/apikey
2. Create a new API key
3. Add to your `.env` file:

```bash
GEMINI_API_KEY=AIzaSy...your-key-here
```

## Configuration Overview

This repository includes a complete Gemini CLI configuration that minimizes redundancy:

```
/Users/administrator/dev/tfwg/claude-config/
├── config/
│   ├── shared/
│   │   └── mcp-servers.json      # Shared MCP definitions (10 servers)
│   ├── gemini-settings.json       # Gemini CLI config (version controlled)
│   ├── opencode.json              # OpenCode config
│   └── settings-laptop.json       # Claude Code config
├── agents/                         # Shared agents (19 total)
├── commands/
│   └── gemini/                    # Gemini TOML commands (5 total)
└── .gemini/                       # Symlinked config directory

Symlinks created:
~/.gemini/gemini-settings.json   → config/gemini-settings.json
~/.gemini/agents/                → agents/
~/.gemini/commands/repo-commands → commands/gemini/
```

## Shared Configuration Strategy

To minimize redundancy across tools (Claude Code, OpenCode, Gemini CLI):

### 1. Shared MCP Servers

All MCP server definitions live in `config/shared/mcp-servers.json`. Each tool references these with tool-specific syntax:

- **Claude Code**: Uses `${VAR}` syntax
- **OpenCode**: Uses `{env:VAR}` syntax
- **Gemini CLI**: Uses `${VAR}` syntax

### 2. Shared Agents

All 19 agents are stored once in `agents/` and symlinked to each tool's config directory.

### 3. Shared Environment Variables

All tools use the same `.env` file for secrets.

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

Launch Gemini CLI from your project directory:

```bash
cd /Users/administrator/dev/tfwg/your-project
gemini
```

### Custom Commands

Your 5 custom commands are available as TOML files:

```bash
# In Gemini CLI:
/feature-plan "Add user authentication"
/debug-loop "Error connecting to database"
/test-suite "src/auth/login.ts"
/api-spec "src/api/users.ts"
/doc-generate "src/lib/utils.ts"
```

### Accessing Agents

Your 19 custom agents are available through the symlinked `agents/` directory:

**Example usage in Gemini CLI:**
```
I need help with backend architecture
```

Gemini will use the `backend-architect` agent context.

**Available agents:**
- backend-architect
- code-reviewer
- debugger
- frontend-developer
- database-architect
- security-auditor
- test-runner
- refactoring-specialist
- And 11 more...

## Testing Your Setup

### 1. Verify Configuration

```bash
# Check symlink
ls -la ~/.gemini/gemini-settings.json
# Should point to: /Users/administrator/dev/tfwg/claude-config/config/gemini-settings.json

# Validate JSON
cat ~/.gemini/gemini-settings.json | jq .
```

### 2. Test API Key

```bash
export GEMINI_API_KEY="your-key-here"
gemini "Hello, can you see my MCP servers?"
```

### 3. Test MCP Server

Try using the filesystem MCP server:
```
Use the filesystem MCP to list files in the current directory
```

### 4. Test Custom Command

```
/feature-plan "Add email notifications"
```

### 5. Test Custom Agent

```
I need backend architecture help for a REST API
```

## Troubleshooting

### MCP Server Not Starting

**Check environment variables:**
```bash
echo $GEMINI_API_KEY
echo $DATAFORSEO_USERNAME
echo $BRAVE_API_KEY
```

**Test server command directly:**
```bash
node /Users/administrator/dev/tfwg/claude-config/mcp-servers/mcp-seo/build/main/main/cli.js
```

**Verify paths in config:**
```bash
cat ~/.gemini/gemini-settings.json | jq '.mcp'
```

### Agents Not Appearing

**Check symlinks:**
```bash
ls -la ~/.gemini/agents/
# Should show symlink to repo agents

readlink ~/.gemini/agents
# Should point to: /Users/administrator/dev/tfwg/claude-config/agents
```

### Commands Not Working

**Verify TOML files:**
```bash
ls -la ~/.gemini/commands/repo-commands/
# Should list: feature-plan.toml, debug-loop.toml, test-suite.toml, api-spec.toml, doc-generate.toml
```

**Check TOML syntax:**
```bash
cat ~/.gemini/commands/repo-commands/feature-plan.toml
```

### Environment Variables Not Working

**Export before launching:**
```bash
export GEMINI_API_KEY="your-key-here"
export BRAVE_API_KEY="your-key-here"
export DATAFORSEO_USERNAME="your-username"
export DATAFORSEO_PASSWORD="your-password"
gemini
```

### Config File Not Loading

**Verify symlink:**
```bash
ls -la ~/.gemini/gemini-settings.json
# Should be a symlink, not a regular file
```

**Check JSON validity:**
```bash
cat ~/.gemini/gemini-settings.json | jq . | head -20
```

## Multi-Tool Workflow

Use Claude Code, OpenCode, and Gemini CLI together:

### Recommended Pattern

**Terminal 1: Claude Code** (IDE integration)
```bash
cd /Users/administrator/dev/tfwg/my-project
claude
```

**Terminal 2: Gemini CLI** (fast iterations, deep reasoning)
```bash
cd /Users/administrator/dev/tfwg/my-project
gemini
```

**Terminal 3: OpenCode** (terminal tasks, multi-model)
```bash
cd /Users/administrator/dev/tfwg/my-project
opencode
```

### When to Use Each

**Claude Code:**
- Full IDE integration
- Complex multi-file edits
- Visual diffs and reviews
- Git operations

**Gemini CLI:**
- Large codebase understanding (1M token context)
- Deep reasoning tasks
- Free tier experimentation
- Google model strengths (code completion, analysis)

**OpenCode:**
- Multi-model comparisons
- Quick terminal tasks
- Server/SSH sessions
- Lightweight operations

## Advanced Configuration

### Enable Only Specific MCP Servers

Edit `config/gemini-settings.json`:
```json
"mcp": {
  "serena": {
    "enabled": false  // Disable heavy servers when not needed
  }
}
```

### Add New MCP Server

1. Add to `config/shared/mcp-servers.json`:
```json
"my-custom-server": {
  "description": "My custom MCP server",
  "command": ["node", "/path/to/server.js"],
  "env": {}
}
```

2. Add to `config/gemini-settings.json`:
```json
"my-custom-server": {
  "type": "local",
  "command": ["node", "/path/to/server.js"],
  "enabled": true
}
```

3. Commit to version control:
```bash
git add config/shared/mcp-servers.json config/gemini-settings.json
git commit -m "Add my-custom-server MCP configuration"
```

### Project-Specific Overrides

Create `.gemini/gemini-settings.json` in any project:
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

### Add New Custom Command

Create a new TOML file in `commands/gemini/`:

```toml
# commands/gemini/my-command.toml
name = "my-command"
description = "My custom command"
argument_hint = "<input>"

[prompt]
content = """
You are doing something custom.

## Input

{{.Arguments}}

## Process

1. Step one
2. Step two
3. Step three

Start now.
"""
```

Commit and it's immediately available:
```bash
git add commands/gemini/my-command.toml
git commit -m "Add custom command: my-command"
```

## Environment Variables

Gemini CLI respects these environment variables:

### API Keys
```bash
export GEMINI_API_KEY="AIzaSy..."
export OPENAI_API_KEY="sk-..."  # For zen server
export ANTHROPIC_API_KEY="sk-ant-..."  # For other tools
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

## Comparison with Other Tools

| Feature | Claude Code | OpenCode | Gemini CLI |
|---------|-------------|----------|------------|
| **Interface** | CLI + IDE | TUI | CLI |
| **AI Models** | Claude only | Multi-provider | Gemini only |
| **Context Window** | 200K tokens | Varies | 1M tokens |
| **MCP Support** | Yes | Yes | Yes |
| **Custom Agents** | Yes | Yes | Yes |
| **Commands Format** | Markdown | Markdown | TOML |
| **Free Tier** | Limited | Varies | Generous |
| **Best For** | IDE workflows | Multi-model | Large codebases |

## Maintaining Configuration

### Syncing Changes

Since agents and commands are symlinked, changes in the repo automatically sync:

**Add new agent:**
```bash
# In repo
vim agents/my-new-agent.md

# Immediately available in Gemini CLI (through symlink)
```

**Add new command:**
```bash
# In repo
vim commands/gemini/my-new-command.toml

# Immediately available in Gemini CLI (through symlink)
```

**Update MCP config:**
```bash
# Edit shared config first
vim config/shared/mcp-servers.json

# Then update Gemini-specific config
vim config/gemini-settings.json

# Changes immediately available (through symlink)
```

### Version Control

Commit your changes to keep everything in sync:

```bash
git add config/gemini-settings.json
git add config/shared/mcp-servers.json
git add agents/my-new-agent.md
git add commands/gemini/my-new-command.toml
git commit -m "Add new agent and command for Gemini CLI"
git push
```

### Team Collaboration

Share Gemini CLI configuration with your team:

1. Team members clone the repo:
```bash
git clone <repo-url>
cd claude-config
```

2. Run setup script:
```bash
./scripts/setup-gemini.sh  # TODO: Create this script
```

3. Script creates symlinks:
```bash
#!/bin/bash
mkdir -p ~/.gemini/commands
ln -sf "$(pwd)/config/gemini-settings.json" ~/.gemini/gemini-settings.json
ln -sf "$(pwd)/agents" ~/.gemini/agents
ln -sf "$(pwd)/commands/gemini" ~/.gemini/commands/repo-commands
```

## Resources

- **Gemini AI Studio**: https://aistudio.google.com/
- **Gemini CLI Docs**: https://ai.google.dev/gemini-api/docs/cli
- **MCP Documentation**: https://modelcontextprotocol.io/
- **Claude Code Docs**: https://code.claude.com/docs/
- **OpenCode Docs**: https://opencode.ai/docs/

## Support

### Gemini CLI Issues
- Google AI Forum: https://discuss.ai.google.dev/
- GitHub Issues: https://github.com/google/generative-ai-cli/issues

### Configuration Issues
- Check symlinks: `ls -la ~/.gemini/`
- Validate JSON: `jq . < ~/.gemini/gemini-settings.json`
- Check environment: `env | grep -E 'GEMINI|BRAVE|DATAFORSEO'`

## Quick Reference Card

```
GEMINI CLI QUICK REFERENCE

Launch:
  gemini                          # Start interactive session
  gemini "your prompt"            # Single prompt execution
  gemini -m gemini-1.5-pro        # Use specific model

Environment:
  export GEMINI_API_KEY="..."    # Required API key
  export BRAVE_API_KEY="..."     # For brave-search MCP
  export DATAFORSEO_USERNAME="..."  # For dataforseo MCP

Configuration:
  ~/.gemini/gemini-settings.json  # Main config (symlinked)
  ~/.gemini/agents/               # Agents directory (symlinked)
  ~/.gemini/commands/             # Commands directory (symlinked)

MCP Servers (10):
  serena, headless-terminal, dataforseo, chrome-bridge, zen,
  brave-search, filesystem, memory, sqlite, promos

Agents (19):
  backend-architect, code-reviewer, debugger, frontend-developer,
  database-architect, security-auditor, test-runner, and 12 more

Commands (5):
  /feature-plan, /debug-loop, /test-suite, /api-spec, /doc-generate

Troubleshooting:
  gemini --help                   # Show help
  cat ~/.gemini/gemini-settings.json | jq .  # Validate config
  ls -la ~/.gemini/               # Check symlinks
  env | grep GEMINI               # Check API key
```

## Gemini-Specific Features

### Large Context Window

Gemini's 1M token context is perfect for:
- Analyzing entire large codebases
- Processing multiple files at once
- Understanding complex interdependencies
- Reviewing extensive documentation

### Multimodal Capabilities

Gemini can process:
- Code files
- Images (diagrams, screenshots)
- Documents
- Mixed content

### Specialized Models

Choose the right model for your task:
- **gemini-2.0-flash-exp**: Fast, efficient (default)
- **gemini-1.5-pro**: Deep reasoning, complex tasks
- **gemini-1.5-flash**: Balance of speed and quality

```bash
# Specify model in command
gemini -m gemini-1.5-pro "Analyze this complex architecture"
```
