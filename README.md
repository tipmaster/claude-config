# Claude Code Configuration Repository

**Centralized, versioned Claude Code configuration for laptop and server environments.**

---

## 🎯 Purpose

This repository centralizes all Claude Code configurations (agents, commands, skills, MCP servers, hooks) into a single versioned source that syncs between your laptop and AlmaLinux 9 server via GitHub.

## 🔗 How It Works

### The Symlink Mechanism

**Claude Code always reads from:** `~/.claude/`

**Our solution:** Make `~/.claude/` point to this versioned repo via symlinks.

```
┌─────────────────────────────────────────────┐
│ THIS REPOSITORY (versioned in git)         │
│                                             │
│ ~/dev/tfwg/claude-config/                  │
│   ├── agents/          ← Real files here   │
│   ├── commands/        ← Real files here   │
│   ├── skills/          ← Real files here   │
│   └── mcp-servers/     ← Real files here   │
└─────────────────────────────────────────────┘
                     ▲
                     │
                 symlinks
                     │
                     │
┌─────────────────────────────────────────────┐
│ CLAUDE CODE READS FROM                      │
│                                             │
│ ~/.claude/                                  │
│   ├── agents/      → symlink to repo       │
│   ├── commands/    → symlink to repo       │
│   ├── skills/      → symlink to repo       │
│   └── settings.json  (generated)           │
└─────────────────────────────────────────────┘
```

**Key Benefits:**
- ✅ Edit files in repo, changes are immediately active (symlinks are live)
- ✅ Commit and push changes, server pulls to get updates
- ✅ No manual copying needed
- ✅ Full git history of configuration changes

---

## 📁 Repository Structure

```
claude-config/
├── .env.example                # Template for secrets
├── .gitignore                  # Comprehensive exclusions
├── README.md                   # This file
│
├── agents/                     # Claude Code agents (17 files)
├── commands/                   # Slash commands (6 files)
├── skills/                     # User-defined skills (9 skills)
│
├── mcp-servers/                # MCP servers
│   ├── ai-counsel/            # Multi-AI deliberation server
│   └── chrome-mcp/            # Chrome browser automation
│
├── config/
│   ├── base/
│   │   ├── settings.base.json    # Base settings (no secrets)
│   │   └── statusline.sh         # Status line script
│   ├── profiles/
│   │   ├── laptop.json          # Laptop-specific (Chrome enabled)
│   │   └── server.json          # Server-specific (headless only)
│   └── mcp-overrides.json       # MCP configuration overrides
│
├── context-engineering/         # Shared project instructions
│   ├── CLAUDE.MD               # Main instructions
│   └── SHARED_INSTRUCTIONS.MD  # AI behavior rules
│
├── scripts/
│   ├── generate-config.sh      # Generate settings.json
│   ├── install-laptop.sh       # Laptop installation
│   ├── install-server.sh       # Server installation (TODO)
│   └── init-new-project.sh     # New project setup (TODO)
│
└── docs/
    ├── INVENTORY.md            # What was copied from where
    ├── SOP-NEW-PROJECT.md      # How to init new projects (TODO)
    ├── SOP-UPDATE-AGENT-OS.md  # How to update agent-os (TODO)
    └── SOP-SYNC.md             # Laptop ↔ Server sync workflow (TODO)
```

---

## 🚀 Quick Start

### Prerequisites

**macOS (Laptop):**
```bash
brew install jq node python3
```

**AlmaLinux 9 (Server):**
```bash
sudo dnf install jq nodejs python3
```

### Installation (Laptop)

```bash
# 1. Clone this repository
cd ~/dev/tfwg/
git clone git@github.com:yourusername/claude-config.git
cd claude-config

# 2. Create .env with your API keys
cp .env.example .env
vim .env  # Add your API keys

# 3. Run installation script
./scripts/install-laptop.sh

# 4. Test Claude Code
claude --version
claude  # Start a session
```

**What the install script does:**
1. ✅ Backs up current `~/.claude/` directory
2. ✅ Removes `~/.claude/agents`, `commands`, `skills` (originals)
3. ✅ Creates symlinks from `~/.claude/` to this repo
4. ✅ Installs dependencies (npm, pip packages)
5. ✅ Generates `settings.json` from templates + `.env`

---

## 🔧 Configuration System

### How Configuration Works

**Base + Profile = Final Config**

1. **Base** (`config/base/settings.base.json`) - Common settings, no secrets
2. **Profile** (`config/profiles/laptop.json` or `server.json`) - Platform-specific MCP servers
3. **Environment** (`.env`) - API keys and secrets
4. **Generate** → `~/.claude/settings.json`

```bash
# Regenerate configuration
./scripts/generate-config.sh laptop

# Or for server:
./scripts/generate-config.sh server
```

### Environment Variables

All secrets go in `.env` (never committed):

```bash
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
REPO_ROOT=/Users/username/dev/tfwg/claude-config
CLAUDE_PLATFORM=laptop
```

### Platform Differences

| Feature | Laptop (macOS) | Server (AlmaLinux 9) |
|---------|----------------|----------------------|
| Chrome MCP | ✅ Enabled | ❌ Disabled (no GUI) |
| Playwright | ✅ Full | ⚠️ Headless only |
| Paths | `~/dev/tfwg/` | `/opt/` or `/root/` |

---

## 📝 Daily Workflow

### Editing Configurations

```bash
# Edit any file in the repo
cd ~/dev/tfwg/claude-config
vim agents/backend-architect.md

# Changes are immediately active (via symlinks)
# Test in Claude Code - no restart needed

# Commit and push
git add agents/backend-architect.md
git commit -m "Update backend architect agent"
git push
```

### Syncing to Server

```bash
# On server:
cd /opt/claude-config
git pull

# Changes are immediately active on server too
```

### Adding a New Skill

```bash
# Create skill directory
mkdir -p skills/my-new-skill

# Create SKILL.md
vim skills/my-new-skill/SKILL.md

# Skill is immediately available in Claude Code
# Commit when ready
git add skills/my-new-skill/
git commit -m "Add new skill: my-new-skill"
git push
```

---

## 🔒 Security

### What's Protected

- ✅ `.env` files (never committed - in .gitignore)
- ✅ API keys (only in .env, templates use `${VARIABLES}`)
- ✅ Dependencies (node_modules, .venv - excluded)
- ✅ Logs and cache files (excluded)

### Verification

```bash
# Check no secrets in repo
git grep -i "api.*key" | grep -v ".example" | grep -v ".gitignore"
# Should return nothing

# Verify .gitignore working
git status --ignored | grep node_modules
# Should show "!! node_modules/" (ignored)
```

### Rotating Keys

If API keys are exposed:

```bash
# 1. Get new keys from providers
# 2. Update .env file
vim .env

# 3. Regenerate config
./scripts/generate-config.sh laptop

# 4. Restart Claude Code
```

---

## 🛠️ Maintenance

### Installing Dependencies

```bash
# After pulling updates, reinstall if package.json changed:

# Playwright skill:
cd skills/playwright-skill && npm install

# AI Counsel:
cd mcp-servers/ai-counsel
.venv/bin/pip install -r requirements.txt

# Chrome MCP:
cd mcp-servers/chrome-mcp && npm install
```

### Updating Agent OS (TODO - see docs/SOP-UPDATE-AGENT-OS.md)

```bash
# Update base installation
curl -sSL "https://raw.githubusercontent.com/buildermethods/agent-os/main/scripts/base-install.sh" | bash

# Update projects
./scripts/update-agent-os.sh
```

---

## 🐛 Troubleshooting

### Claude Code doesn't see changes

```bash
# Verify symlinks exist
ls -la ~/.claude/agents  # Should show: agents -> /path/to/claude-config/agents

# If broken, reinstall
./scripts/install-laptop.sh
```

### MCP servers not loading

```bash
# Check configuration
cat ~/.claude/settings.json | jq '.mcpServers'

# Verify paths
ls -la ~/dev/tfwg/claude-config/mcp-servers/

# Regenerate config
./scripts/generate-config.sh laptop
```

### Dependencies missing

```bash
# Reinstall all dependencies
cd ~/dev/tfwg/claude-config

# Playwright
cd skills/playwright-skill && npm install

# AI Counsel
cd ../../mcp-servers/ai-counsel
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Chrome MCP
cd ../chrome-mcp && npm install
```

### Restore from backup

```bash
# Find backup
ls -d ~/.claude.backup.*

# Restore
rm -rf ~/.claude
mv ~/.claude.backup.YYYYMMDD_HHMMSS ~/.claude
```

---

## 📚 Documentation

- [`docs/INVENTORY.md`](docs/INVENTORY.md) - Complete inventory of copied resources
- [`docs/SOP-NEW-PROJECT.md`](docs/SOP-NEW-PROJECT.md) - Setting up new projects (TODO)
- [`docs/SOP-UPDATE-AGENT-OS.md`](docs/SOP-UPDATE-AGENT-OS.md) - Updating Agent OS (TODO)
- [`docs/SOP-SYNC.md`](docs/SOP-SYNC.md) - Sync workflow (TODO)

---

## 🤝 Contributing

**This is a personal configuration repository.** However, if you want to adapt it:

1. Fork this repo
2. Update paths in `.env.example`
3. Adjust `config/profiles/` for your needs
4. Run `install-laptop.sh`

---

## 📋 What's Included

### Agents (17)
- backend-architect, command-expert, context-fetcher, database-architect, database-optimizer, date-checker, debugger, file-creator, frontend-developer, git-workflow, prompt-engineer, python-expert, seo-strategist, sitemap-builder, test-runner, website-builder, website-reviewer

### Commands (6)
- analyze-product, create-spec, execute-tasks, plan-product, serverDeploy, testOnServer

### Skills (9)
- api-design-review, caching-strategy-review, configuration-management, documentation-completeness, error-handling-patterns, naming-consistency-review, playwright-skill, refactoring-safety, seo-content-validation

### MCP Servers (2 + 5 external)
- **ai-counsel** - Multi-AI deliberation and consensus building
- **chrome-mcp** - Chrome browser automation
- **serena** - IDE assistant (external, via uvx)
- **headless-terminal** - Terminal operations (external, via binary)
- **dataforseo** - SEO tools (external, via SSH to server)
- **chrome-bridge** - Chrome bridge (external, via npm global)
- **zen** - Multi-model AI orchestration (external, via uvx)

---

## 📄 License

Personal configuration repository. Adapt as needed for your own use.

---

## 🔗 Related

- [Agent OS](https://github.com/buildermethods/agent-os) - Development standards system
- [Claude Code](https://claude.com/claude-code) - Official Claude CLI

---

**Last Updated:** November 6, 2025
**Version:** 1.0.0
**Platform:** macOS + AlmaLinux 9
