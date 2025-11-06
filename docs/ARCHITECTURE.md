# Architecture - Centralized Claude Code Configuration

## Overview

This repository centralizes all Claude Code configuration for syncing between laptop (macOS) and server (AlmaLinux 9).

## Two Separate Systems

This repo contains **two distinct but complementary systems**:

### 1. Claude Code Configuration (Global)
**Purpose:** System-wide Claude Code setup
**Scope:** Applies to ALL projects
**Location:** `~/.claude/` (via symlinks to this repo)
**Contains:**
- Agents (AI subagents)
- Commands (slash commands)
- Skills (Superpowers)
- MCP Servers configuration
- Settings and permissions

### 2. Agent-OS Framework (Per-Project)
**Purpose:** Project-specific development standards
**Scope:** Applies to individual projects
**Location:** Copied/symlinked into each project directory
**Contains:**
- `CLAUDE.MD` - Project instructions
- `SHARED_INSTRUCTIONS.MD` - Development standards
- `agent-os/` - Coding style, tech stack rules

**Key Difference:**
- Claude Code config = installed ONCE system-wide
- Agent-OS framework = initialized PER PROJECT

See [Agent-OS Integration](#agent-os-integration) below for details.

## Key Principle: Selective Symlinking

Claude Code reads from `~/.claude/`, so we symlink specific directories from this repo:

```
~/.claude/agents/       → ~/dev/tfwg/claude-config/agents/
~/.claude/commands/     → ~/dev/tfwg/claude-config/commands/
~/.claude/skills/       → ~/dev/tfwg/claude-config/skills/
~/.claude/settings.json → ~/dev/tfwg/claude-config/config/settings-laptop.json
```

## Environment Variables Strategy

### Discovery: Claude Code Supports ${VAR} Expansion

Testing confirmed that Claude Code natively supports `${VARIABLE}` syntax in settings.json. This means:

✅ **No config generation needed** - Just use ${VAR} directly
✅ **Secrets stay in .env** - Never committed to git
✅ **Cross-platform paths** - Use ${REPO_ROOT} and ${HOME}

### Loading .env

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Load Claude Config environment variables
if [ -f ~/dev/tfwg/claude-config/.env ]; then
    set -a
    source ~/dev/tfwg/claude-config/.env
    set +a
fi
```

## Platform Differences

### Laptop (macOS)
- Uses: `config/settings-laptop.json`
- Includes: Chrome MCPs (chrome-bridge, chrome-mcp)
- All agents and skills enabled

### Server (AlmaLinux 9)
- Uses: `config/settings-server.json`
- Excludes: Chrome MCPs (headless environment)
- Same agents and skills

## Directory Structure

```
~/dev/tfwg/claude-config/
├── .env                      # Secrets (NOT versioned)
├── .env.example              # Template with all variables
├── .gitignore                # Excludes .env, node_modules, .venv, etc.
│
├── agents/                   # ✅ Versioned, symlinked
│   ├── backend-architect.md
│   ├── database-architect.md
│   └── ... (17 total)
│
├── commands/                 # ✅ Versioned, symlinked
│   ├── serverDeploy.md
│   ├── testOnServer.md
│   └── ... (6 total)
│
├── skills/                   # ✅ Versioned, symlinked
│   ├── playwright-skill/     # (node_modules excluded)
│   └── ... (9 total)
│
├── mcp-servers/              # ✅ Source code versioned
│   ├── ai-counsel/           # (.venv excluded)
│   └── chrome-mcp/           # (node_modules excluded)
│
├── config/
│   ├── settings-laptop.json  # ✅ Laptop config (with Chrome)
│   ├── settings-server.json  # ✅ Server config (no Chrome)
│   └── statusline.sh         # ✅ Shared statusline script
│
├── scripts/
│   ├── install-laptop.sh     # Automated laptop setup
│   └── install-server.sh     # Automated server setup
│
└── docs/
    ├── ARCHITECTURE.md       # This file
    ├── INVENTORY.md          # Complete resource inventory
    └── SECURITY.md           # Security notes and key rotation
```

## What's Versioned vs Excluded

### ✅ Versioned (in git)
- Configuration files (settings-*.json)
- Agents, commands, skills (source code)
- MCP server source code
- Documentation
- Scripts

### ❌ Excluded (.gitignore)
- `.env` - Secrets and API keys
- `node_modules/` - npm dependencies
- `.venv/` - Python virtual environments
- `.ck/` - CK search cache
- `*.log` - Log files
- Nested `.git/` directories

## Security Model

### API Keys and Secrets
- Stored in: `.env` (root of repo)
- Referenced as: `${OPENAI_API_KEY}` in settings files
- Never hardcoded in configuration files
- Never committed to git

### Current Security Issue
⚠️ **Exposed keys found in ~/.claude/settings.json** (hardcoded values):
- GEMINI_API_KEY: `AIzaSyA3WT_0b6b3PNScoQ-F1mJFxvIaLmL-V18`
- OPENAI_API_KEY: `sk-proj-yuWEO...`

**Action required:** Rotate these keys after migration complete.

See `docs/SECURITY.md` for rotation instructions.

## Installation Flow

### Laptop
```bash
cd ~/dev/tfwg/claude-config
./scripts/install-laptop.sh
```

This will:
1. Backup existing ~/.claude/
2. Create symlinks for agents, commands, skills
3. Symlink settings-laptop.json → ~/.claude/settings.json
4. Install MCP dependencies (npm/pip)
5. Verify .env exists

### Server
```bash
cd /opt/claude-config
./scripts/install-server.sh
```

Same process but uses `settings-server.json` (no Chrome).

## Testing Verification

After installation:

```bash
# 1. Basic functionality
claude --version

# 2. Start session
claude

# 3. In session, verify:
# - Agents load (type a message, check skills)
# - MCP servers connect (use MCP-powered commands)
# - Skills work (test playwright-skill)
# - Commands work (test slash commands)
```

## Cross-Platform Sync Workflow

### Making Changes
1. Edit files in `~/dev/tfwg/claude-config/`
2. Changes immediately reflected via symlinks
3. Commit and push to git

### Syncing to Server
```bash
# On server
cd /opt/claude-config
git pull
# Changes automatically active via symlinks
```

## Why This Works

1. **Symlinks** - Claude Code reads from ~/.claude/, symlinks point to repo
2. **${VAR} Expansion** - Claude Code substitutes environment variables natively
3. **Platform Profiles** - Separate settings files for laptop vs server
4. **Dependency Exclusion** - Only source code versioned, dependencies installed locally

## Migration from Old System

Old approach (abandoned):
- ❌ Config generation scripts
- ❌ Base + profile merging
- ❌ Bash variable substitution
- ❌ Override system with mcp.json

New approach (current):
- ✅ Direct settings files with ${VAR}
- ✅ Simple symlinking
- ✅ Native Claude Code features
- ✅ Minimal complexity

## Agent-OS Integration

### What is Agent-OS?

Agent-OS is a **per-project framework** for standardized development practices. It provides:
- Project-level instructions (CLAUDE.MD)
- Common development standards (SHARED_INSTRUCTIONS.MD)
- Coding style guides
- Technology stack rules
- Testing standards

### Files in context-engineering/

```
context-engineering/
├── CLAUDE.MD               # Main project instructions
├── AGENTS.MD              # Symlink → CLAUDE.MD
├── GEMINI.MD              # Symlink → CLAUDE.MD
├── SHARED_INSTRUCTIONS.MD # Common development standards
└── set-soft-links.txt     # Historical reference
```

### How to Use Agent-OS

**For new projects:**
```bash
# Initialize agent-os in a new project
cd ~/dev/tfwg/claude-config
./scripts/init-project.sh /path/to/your-new-project
```

This creates symlinks in your project:
```
your-project/
├── CLAUDE.MD              → ~/dev/tfwg/claude-config/context-engineering/CLAUDE.MD
├── AGENTS.MD              → ~/dev/tfwg/claude-config/context-engineering/CLAUDE.MD
├── GEMINI.MD              → ~/dev/tfwg/claude-config/context-engineering/CLAUDE.MD
└── SHARED_INSTRUCTIONS.MD → ~/dev/tfwg/claude-config/context-engineering/SHARED_INSTRUCTIONS.MD
```

**For existing projects:**
If you already have CLAUDE.MD in your project, you can:
1. Keep it as-is (project-specific)
2. Replace with symlink to centralized version
3. Hybrid: Keep project-specific CLAUDE.MD, symlink SHARED_INSTRUCTIONS.MD

### Relationship Between Systems

```
┌─────────────────────────────────────────┐
│ Claude Code (Global - System-wide)     │
│                                         │
│ ~/.claude/                              │
│   ├── agents/      ← Repo symlink      │
│   ├── commands/    ← Repo symlink      │
│   ├── skills/      ← Repo symlink      │
│   └── settings.json ← Repo symlink     │
│                                         │
│ Applies to: ALL projects                │
└─────────────────────────────────────────┘
              ↓
        When Claude runs
              ↓
┌─────────────────────────────────────────┐
│ Agent-OS (Per-Project)                  │
│                                         │
│ /path/to/your-project/                 │
│   ├── CLAUDE.MD                         │
│   ├── SHARED_INSTRUCTIONS.MD            │
│   └── agent-os/standards/               │
│                                         │
│ Applies to: THIS project only           │
└─────────────────────────────────────────┘
```

**Example workflow:**
1. Install claude-config ONCE: `./scripts/install-laptop.sh`
2. For each new project: `./scripts/init-project.sh ~/dev/my-app`
3. Work on project: `cd ~/dev/my-app && claude`
4. Claude reads:
   - Global agents/skills from ~/.claude/
   - Project instructions from ./CLAUDE.MD

## Next Steps

### Laptop Setup
1. ✅ Backup created: `~/.claude.backup.20251106_194511`
2. ⏳ Create `.env` from `.env.example` and add API keys
3. ⏳ Run `./scripts/install-laptop.sh` to create symlinks
4. ⏳ Test Claude Code functionality
5. ⏳ Rotate exposed API keys (see SECURITY.md)

### Server Setup
6. ⏳ Deploy to server (/opt/claude-config)
7. ⏳ Run `./scripts/install-server.sh`

### Project Initialization
8. ⏳ Run `./scripts/init-project.sh` for existing projects
9. ⏳ Test agent-os integration
