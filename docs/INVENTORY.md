# Claude Config Repository - Inventory Report

**Date:** November 6, 2025
**Source Machine:** macOS (administrator@laptop)

---

## Summary

This document tracks all resources copied into the claude-config repository for centralization and version control.

### Total Resources Copied

| Category | Count | Size | Status |
|----------|-------|------|--------|
| Agents | 17 files | ~148KB | ✅ Copied |
| Commands | 6 files | ~30KB | ✅ Copied |
| Skills | 9 directories | ~13MB | ✅ Copied |
| MCP Servers | 2 servers | ~321MB | ✅ Copied |
| Config Files | 2 files | ~10KB | ✅ Copied |

---

## Detailed Inventory

### 1. Agents (from `~/.claude/agents/`)

**Location in repo:** `agents/`
**Source:** `/Users/administrator/.claude/agents/`

| File | Size | Purpose |
|------|------|---------|
| backend-architect.md | 1.5KB | Backend architecture design agent |
| command-expert.md | 1.1KB | CLI command creation agent |
| context-fetcher.md | 2.2KB | Documentation fetching agent |
| database-architect.md | 6.1KB | Database design and optimization agent |
| database-optimizer.md | 1.9KB | Query optimization agent |
| date-checker.md | 2.7KB | Date/time checking agent |
| debugger.md | 1.9KB | Debugging assistance agent |
| file-creator.md | 6.6KB | File creation automation agent |
| frontend-developer.md | 2.1KB | Frontend development agent |
| git-workflow.md | 3.6KB | Git operations agent |
| prompt-engineer.md | 4.9KB | Prompt optimization agent |
| python-expert.md | 2.0KB | Python expertise agent |
| seo-strategist.md | 6.2KB | SEO analysis agent |
| sitemap-builder.md | 25KB | Sitemap generation agent |
| test-runner.md | 1.7KB | Test execution agent |
| website-builder.md | 32KB | Website building agent |
| website-reviewer.md | 15KB | Website review agent |

**Total:** 17 agents, ~148KB

---

### 2. Commands (from `~/.claude/commands/`)

**Location in repo:** `commands/`
**Source:** `/Users/administrator/.claude/commands/`

| File | Purpose |
|------|---------|
| analyze-product.md | Product analysis workflow |
| create-spec.md | Specification creation workflow |
| execute-tasks.md | Task execution workflow |
| plan-product.md | Product planning workflow |
| serverDeploy.md | Server deployment workflow |
| testOnServer.md | Server testing workflow |

**Total:** 6 commands, ~30KB

---

### 3. Skills (from `~/.claude/skills/`)

**Location in repo:** `skills/`
**Source:** `/Users/administrator/.claude/skills/`

| Skill Directory | Has Dependencies | Size | Purpose |
|----------------|------------------|------|---------|
| api-design-review/ | No | ~5KB | API contract validation |
| caching-strategy-review/ | No | ~5KB | Cache design patterns |
| configuration-management/ | No | ~5KB | Config and secrets validation |
| documentation-completeness/ | No | ~5KB | Documentation standards |
| error-handling-patterns/ | No | ~5KB | Error handling design |
| naming-consistency-review/ | No | ~5KB | Naming conventions |
| playwright-skill/ | Yes (npm) | ~13MB | Browser automation with Playwright |
| refactoring-safety/ | No | ~5KB | Safe refactoring practices |
| seo-content-validation/ | No | ~5KB | SEO validation |

**Dependencies noted:**
- `playwright-skill/` has `node_modules/` (~13MB) - **excluded by .gitignore**
- `playwright-skill/package.json` lists: `playwright@^1.48.0`

**Total:** 9 skills, ~13MB (mostly node_modules)

---

### 4. MCP Servers

#### 4.1 ai-counsel (from `~/dev/3p/mcp/ai-counsel/`)

**Location in repo:** `mcp-servers/ai-counsel/`
**Source:** `/Users/administrator/dev/3p/mcp/ai-counsel/`
**Size:** ~266MB (including .venv)

**Key Files:**
- `server.py` - Main MCP server
- `requirements.txt` - Python dependencies
- `.venv/` - Python virtual environment (**excluded by .gitignore**)
- `decision_graph.db` - Decision history database (56KB)
- `mcp_server.log` - Runtime logs (276KB, **excluded by .gitignore**)
- `tests/` - Test suite
- `docs/` - Documentation

**Dependencies:**
- Python 3.9+
- Multiple Python packages (installed in .venv)

#### 4.2 chrome-mcp (from `~/dev/chrome-mcp/`)

**Location in repo:** `mcp-servers/chrome-mcp/`
**Source:** `/Users/administrator/dev/chrome-mcp/`
**Size:** ~55MB (including node_modules)

**Key Files:**
- `run-server.js` - Main entry point
- `package.json` - NPM dependencies
- `node_modules/` - NPM packages (**excluded by .gitignore**)
- `src/` - Source code
- `dist/` - Built files (**excluded by .gitignore**)
- `launch-chrome-cdp.sh` - Chrome launcher script
- `README.md` - Documentation

**Dependencies:**
- Node.js 14+
- Multiple NPM packages (installed in node_modules)

**Total:** 2 MCP servers, ~321MB (mostly dependencies)

---

### 5. Configuration Files

#### 5.1 statusline Script (from `~/.claude/statusline-opus.sh`)

**Location in repo:** `config/base/statusline.sh`
**Source:** `/Users/administrator/.claude/statusline-opus.sh`
**Size:** ~4KB

**Purpose:** Custom status line for Claude Code showing:
- Username and hostname
- Current directory
- Git branch
- Model name
- Usage statistics

#### 5.2 MCP Overrides (from `~/.claude/config/mcp.json`)

**Location in repo:** `config/mcp-overrides.json`
**Source:** `/Users/administrator/.claude/config/mcp.json`
**Size:** ~600 bytes

**Purpose:** MCP server configuration overrides

**Contains:**
- chrome-bridge SSE configuration
- ai-counsel configuration with environment variable substitution

**✅ Good pattern:** Uses `${VARIABLE}` substitution for API keys instead of hardcoded values

---

### 6. Context Engineering (from `../context-engineering/`)

**Location in repo:** `context-engineering/`
**Source:** `/Users/administrator/dev/tfwg/context-engineering/`

| File | Size | Purpose |
|------|------|---------|
| CLAUDE.MD | 5.5KB | Main project instructions |
| SHARED_INSTRUCTIONS.MD | 2.3KB | Core AI behavior rules |
| AGENTS.MD → CLAUDE.MD | symlink | Alias for CLAUDE.MD |
| GEMINI.MD → CLAUDE.MD | symlink | Alias for CLAUDE.MD |
| set-soft-links.txt | 221B | Documentation of symlink pattern |

**Total:** 4 files (2 real, 2 symlinks), ~8KB

---

## What Was NOT Copied (Intentionally)

### From `~/.claude/`
- `session-env/` - Session-specific data (73 directories)
- `file-history/` - File history cache (93 directories, 9.7MB)
- `shell-snapshots/` - Shell history (226 files, 1.2MB)
- `todos/` - Todo tracking data (485 files, 1.9MB)
- `debug/` - Debug logs (47MB)
- `history.jsonl` - Command history (268KB)
- `projects/` - Per-project settings (110MB)
- `statsig/` - Analytics data (144KB)
- `plugins/` - Plugin system (managed separately, 31MB)

**Reason:** These are ephemeral, session-specific, or managed by the plugin system

### From `~/dev/3p/mcp/`
- `dataforseo-mcp-server/` - Not used in current Claude Code config (runs on remote server via SSH)
- `mcp-seo/` - Not configured in settings.json
- `mcp-server-typescript/` - Remote server component (dataforseo)
- `transcripts/` - Not an MCP server

**Reason:** Not actively configured in the current Claude Code setup

---

## Dependencies Summary

### Node.js Dependencies (npm)
- **playwright-skill:** `playwright@^1.48.0`
- **chrome-mcp:** Multiple packages (see package.json)

**Installation:** `npm install` in each directory

### Python Dependencies (pip)
- **ai-counsel:** Multiple packages (see requirements.txt)

**Installation:** `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

---

## Security Audit

### ✅ Secrets Properly Excluded

**API Keys found in source files (before sanitization):**
- ~~GEMINI_API_KEY: `AIzaSy...REDACTED...V18`~~ (in `~/.claude/settings.json`)
- ~~OPENAI_API_KEY: `sk-proj-...REDACTED...`~~ (in `~/.claude/settings.json`)

**Status:** ✅ These were in source files, NOT copied into repo
**Action needed:** These API keys MUST be rotated immediately (they were exposed in git history)

### Files Containing Secrets (Excluded by .gitignore)
- `.env` - ✅ Excluded
- `settings.json` (generated) - ✅ Excluded
- Any `*.key`, `*.pem` files - ✅ Excluded

### Files Using Good Secret Patterns (Included)
- `config/mcp-overrides.json` - ✅ Uses `${VARIABLE}` substitution

---

## Path Analysis

### Hardcoded Paths Requiring Template Variables

From `~/.claude/settings.json` (NOT copied as-is):

| Hardcoded Path | Should Be | Used In |
|----------------|-----------|---------|
| `/Users/administrator/` | `${HOME}/` | All configs |
| `/Users/administrator/dev/tfwg/claude-config/` | `${REPO_ROOT}/` | MCP servers |
| `/Users/administrator/dev/chrome-mcp/` | `${REPO_ROOT}/mcp-servers/chrome-mcp/` | chrome-mcp MCP |
| `/Users/administrator/dev/3p/mcp/ai-counsel/` | `${REPO_ROOT}/mcp-servers/ai-counsel/` | ai-counsel MCP |
| `/Users/administrator/.npm-global/bin/` | `$(which mcp-chrome-stdio)` | chrome-bridge |
| `/opt/homebrew/bin/uvx` | `$(which uvx)` | zen MCP |

**Action needed:** Create settings.base.json template with variable substitution

---

## Git Status

### Files Ready to Commit

```bash
# Ready to commit (source files only, no dependencies):
agents/                    # 17 .md files
commands/                  # 6 .md files
skills/                    # 9 directories with SKILL.md files
mcp-servers/ai-counsel/    # Source files only (.venv excluded)
mcp-servers/chrome-mcp/    # Source files only (node_modules excluded)
config/base/statusline.sh
config/mcp-overrides.json
context-engineering/       # 4 files
.gitignore
```

### Files Excluded by .gitignore

```bash
# Excluded (will be reinstalled):
skills/playwright-skill/node_modules/        # ~13MB
mcp-servers/ai-counsel/.venv/                # ~260MB
mcp-servers/chrome-mcp/node_modules/         # ~54MB
mcp-servers/chrome-mcp/dist/                 # Build artifacts
mcp-servers/ai-counsel/*.log                 # Logs
mcp-servers/ai-counsel/*.db                  # Runtime databases
```

---

## Next Steps

1. ✅ **Inventory complete**
2. ⏳ **Review with user**
3. 📝 **Create settings.base.json template** (sanitize secrets, template paths)
4. 📝 **Create .env.example** (document required secrets)
5. 📝 **Create platform profiles** (laptop.json, server.json)
6. 🔧 **Write installation scripts**
7. 📚 **Write documentation** (SETUP.md, SOPs)
8. ✅ **Initial git commit**

---

## Verification Commands

```bash
# Count files
find agents -name "*.md" | wc -l           # Should be 17
find commands -name "*.md" | wc -l         # Should be 6
find skills -type d -maxdepth 1 | wc -l    # Should be 10 (9 + skills/ itself)

# Check for secrets
git grep -i "api.*key" | grep -v ".example" | grep -v ".gitignore"  # Should be empty

# Check .gitignore working
git status --porcelain | grep node_modules  # Should be empty
git status --porcelain | grep .venv         # Should be empty
```

---

**Inventory Report Generated:** 2025-11-06
**Repository:** `~/dev/tfwg/claude-config/`
**Machine:** macOS laptop (administrator)
