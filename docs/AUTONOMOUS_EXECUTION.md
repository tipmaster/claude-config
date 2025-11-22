# Autonomous Execution Guide

Quick reference for launching AI CLIs with reduced friction and fewer approval prompts.

## Quick Commands

### Recommended (Safe + Productive)

```bash
# Gemini - Auto-approve edits only
gemini --approval-mode auto_edit

# Codex - Model decides when to ask, sandboxed
codex --full-auto

# Or use the convenience launcher:
./scripts/launch-ai-cli.sh gemini auto-edit
./scripts/launch-ai-cli.sh codex full-auto
```

### Maximum Autonomy (Use with Caution)

```bash
# Gemini - Auto-approve EVERYTHING
gemini --yolo
gemini -y

# Codex - NO SANDBOX, NO APPROVALS (DANGEROUS)
codex --dangerously-bypass-approvals-and-sandbox
```

---

## Tool-by-Tool Configuration

### Claude Code

**Built-in Config:** `~/.claude/settings.json`

```json
{
  "globalShellCommand": {
    "allowedDirectories": ["/Users/administrator/dev"],
    "restrictedCommands": []
  }
}
```

**Per-Project Trust:**
Claude Code uses hooks and trust levels per project. No CLI flags for autonomous mode.

**Best Practice:**
- Configure trusted directories in settings
- Use hooks for project-specific approvals
- No YOLO mode available (by design)

---

### Gemini CLI

**Config:** `~/.gemini/settings.json` (symlinked to repo config)

**Default Config:**
```json
{
  "approvalMode": "auto_edit",
  "allowedMcpServerNames": [
    "serena", "headless-terminal", "dataforseo",
    "chrome-bridge", "zen", "brave-search",
    "filesystem", "memory", "promos"
  ]
}
```

**Launch Flags:**

| Flag | Mode | What It Does |
|------|------|--------------|
| (none) | `auto_edit` | Auto-approve edits only (from config) |
| `--approval-mode auto_edit` | Auto-Edit | Same as above (explicit) |
| `--yolo` or `-y` | YOLO | Auto-approve ALL tools & actions |
| `--approval-mode yolo` | YOLO | Same as above (explicit) |
| `--allowed-tools <list>` | Custom | Whitelist specific tools |

**Examples:**
```bash
# Default (auto-edit from config)
gemini

# Explicit auto-edit
gemini --approval-mode auto_edit

# YOLO mode
gemini --yolo

# Whitelist specific MCP servers
gemini --allowed-mcp-server-names serena filesystem brave-search
```

**Recommendations:**
- **Daily work:** `auto_edit` mode (default in our config)
- **Trusted projects:** `--yolo` for maximum productivity
- **Production:** Remove `approvalMode` from config, use interactive

---

### Codex CLI

**Config:** `~/.codex/config.toml`

**Default Config:**
```toml
approval_mode = "on-request"  # Model decides when to ask
sandbox = "workspace-write"   # Allow file writes
trust_level = "trusted"       # Trusted by default
sandbox_permissions = ["disk-full-read-access"]

[shell_environment_policy]
inherit = "all"  # Inherit all environment variables

[projects."/Users/administrator/dev/tfwg/claude-config"]
trust_level = "trusted"  # Per-project trust
```

**Launch Flags:**

| Flag | Mode | What It Does |
|------|------|--------------|
| (none) | Config defaults | Uses approval_mode from config |
| `--full-auto` | Full-Auto | `-a on-request` + `--sandbox workspace-write` |
| `-a on-request` | On-Request | Model decides when to ask |
| `-a on-failure` | On-Failure | Only asks if command fails |
| `-a never` | Never | Never asks (execution failures returned to model) |
| `-s workspace-write` | Workspace Write | Allow writes in workspace |
| `-s danger-full-access` | Full Access | NO RESTRICTIONS (dangerous) |
| `--dangerously-bypass-approvals-and-sandbox` | YOLO | NO SANDBOX + NO APPROVALS |

**Examples:**
```bash
# Default (uses config settings)
codex

# Full-auto (recommended for trusted projects)
codex --full-auto

# Maximum autonomy (DANGEROUS)
codex --dangerously-bypass-approvals-and-sandbox

# Custom approval + sandbox
codex -a on-failure -s workspace-write

# Override config
codex -c approval_mode=never -c sandbox=workspace-write
```

**Recommendations:**
- **Daily work:** Default config (`on-request` + `workspace-write`)
- **Trusted projects:** `--full-auto` flag
- **Rapid iteration:** `-a on-failure` (less interruptions)
- **Production:** `-a untrusted` (asks for non-trusted commands)

---

### GitHub Copilot CLI

**Config:** `~/.copilot/config.json`
**MCP Config:** `~/.copilot/mcp-config.json` (symlinked to repo config)

**Default Config:**
```json
{
  "model": "gpt-5.1",
  "trusted_folders": [
    "/Users/administrator/dev/tfwg/claude-config",
    "/Users/administrator/dev/tfwg/lt"
  ]
}
```

**Launch Flags:**

| Flag | Mode | What It Does |
|------|------|--------------|
| (none) | Interactive | Default interactive mode |
| `--allow-all-tools` | Auto-Tool | Auto-approve all tool executions |
| `--allow-all-paths` | Path Access | Disable path verification |
| `--agent <agent>` | Custom Agent | Use specific agent from `~/.copilot/agents/` |
| `--no-custom-instructions` | No AGENTS.md | Disable loading custom instructions |

**Examples:**
```bash
# Default (interactive)
copilot

# Auto-approve all tools (autonomous)
copilot --allow-all-tools

# Use specific agent
copilot --agent backend-architect

# Full autonomous mode
copilot --allow-all-tools --allow-all-paths
```

**Recommendations:**
- **Daily work:** Default interactive mode (safe)
- **Trusted projects:** `--allow-all-tools` for productivity
- **Specific tasks:** `--agent <name>` for domain expertise
- **Production:** No flags (interactive only)

---

### Droid CLI

**Config:** Command-line based (no config file)
**MCP Setup:** `./scripts/setup-droid-mcp.sh` (registers all 9 MCP servers)

**Default Behavior:**
Droid uses command-line based MCP server registration instead of config files. MCP servers persist across sessions once registered.

**MCP Server Registration:**
```bash
# Run setup script to register all 9 MCP servers
./scripts/setup-droid-mcp.sh

# Verify registration
droid mcp
```

**Launch Flags:**

| Flag | Mode | What It Does |
|------|------|--------------|
| (none) | Read-Only | Default safe mode - read files, no modifications |
| `--auto low` | Low Autonomy | Basic file operations (create, edit, delete files) |
| `--auto medium` | Medium Autonomy | Development operations (git, package managers, builds) |
| `--auto high` | High Autonomy | Production changes (deployments, system configs) |
| `--skip-permissions-unsafe` | YOLO | Bypass ALL permission checks (DANGEROUS) |

**Examples:**
```bash
# Default (read-only mode)
droid

# Low autonomy (basic file operations)
droid --auto low

# Medium autonomy (development work)
droid --auto medium

# High autonomy (production changes)
droid --auto high

# Maximum autonomy (DANGEROUS - bypass all permissions)
droid --skip-permissions-unsafe
```

**Recommendations:**
- **Daily work:** `--auto low` for file editing tasks
- **Development:** `--auto medium` for git, builds, and package management
- **Trusted projects:** `--auto high` for deployment operations
- **Production:** Default read-only mode (interactive approvals)
- **NEVER use `--skip-permissions-unsafe` in production**

**MCP Server Management:**
```bash
# List registered MCP servers
droid mcp

# Remove a server
droid mcp remove <server-name>

# Re-run setup script to restore all servers
./scripts/setup-droid-mcp.sh
```

---

### Qwen CLI

**Config:** `~/.qwen/settings.json`
**MCP Setup:** `./scripts/setup-qwen-mcp.sh` (registers all 9 MCP servers)

**Default Config:**
```json
{
  "approvalMode": "auto-edit",
  "security": {
    "auth": {
      "selectedType": "qwen-oauth"
    }
  }
}
```

**Default Behavior:**
Qwen uses project-scoped MCP server registration. MCP servers persist across sessions once registered.

**MCP Server Registration:**
```bash
# Run setup script to register all 9 MCP servers
./scripts/setup-qwen-mcp.sh

# Verify registration
qwen mcp list
```

**Launch Flags:**

| Flag | Mode | What It Does |
|------|------|--------------|
| (none) | Auto-Edit | Default from config - auto-approve edits only |
| `--approval-mode auto-edit` | Auto-Edit | Same as default (explicit) |
| `--approval-mode yolo` | YOLO | Auto-approve ALL tools & actions |
| `--yolo` or `-y` | YOLO | Same as above (shorthand) |
| `--approval-mode plan` | Plan Only | Generate plans without executing |
| `--approval-mode default` | Interactive | Prompt for all approvals |
| `--allowed-mcp-server-names <list>` | Whitelist | Only allow specific MCP servers |
| `--allowed-tools <list>` | Whitelist | Only allow specific tools |

**Examples:**
```bash
# Default (auto-edit from config)
qwen

# Explicit auto-edit
qwen --approval-mode auto-edit

# YOLO mode
qwen --yolo
qwen --approval-mode yolo

# Plan only (no execution)
qwen --approval-mode plan

# Interactive mode (ask for everything)
qwen --approval-mode default

# Whitelist specific MCP servers
qwen --allowed-mcp-server-names serena filesystem brave-search

# Whitelist specific tools
qwen --allowed-tools read_file write_file bash
```

**Recommendations:**
- **Daily work:** Default `auto-edit` mode (from config)
- **Trusted projects:** `--yolo` for maximum productivity
- **Planning sessions:** `--approval-mode plan` to review before executing
- **Production:** `--approval-mode default` (interactive mode)

**MCP Server Management:**
```bash
# List registered MCP servers
qwen mcp list

# Remove a server
qwen mcp remove <server-name>

# Add a server manually
qwen mcp add <name> <command> -t stdio -e "KEY=value"

# Re-run setup script to restore all servers
./scripts/setup-qwen-mcp.sh
```

---

### OpenCode

**Config:** `~/.config/opencode/opencode.json`

**Launch Flags:**
See OpenCode documentation for model-specific approval settings.

---

## Safety Matrix

| Tool | Mode | Safety | Productivity | Use Case |
|------|------|--------|-------------|----------|
| Claude | Interactive | 🟢 High | 🟡 Medium | All scenarios |
| Gemini | `auto_edit` | 🟢 High | 🟢 High | Daily work (recommended) |
| Gemini | `--yolo` | 🔴 Low | 🟢 Very High | Trusted projects only |
| Codex | Default config | 🟢 High | 🟢 High | Daily work (recommended) |
| Codex | `--full-auto` | 🟢 High | 🟢 Very High | Trusted projects |
| Codex | `--dangerously-bypass...` | 🔴 None | 🟢 Maximum | Dev containers only |
| Copilot | Interactive | 🟢 High | 🟡 Medium | All scenarios |
| Copilot | `--allow-all-tools` | 🟡 Medium | 🟢 High | Trusted projects |
| Copilot | `--allow-all-tools --allow-all-paths` | 🔴 Low | 🟢 Very High | Dev containers recommended |
| Droid | Read-Only (default) | 🟢 High | 🟡 Low | All scenarios (safe exploration) |
| Droid | `--auto low` | 🟢 High | 🟢 High | Daily work (file editing) |
| Droid | `--auto medium` | 🟢 High | 🟢 Very High | Development (git, builds) |
| Droid | `--auto high` | 🟡 Medium | 🟢 Very High | Production deployments |
| Droid | `--skip-permissions-unsafe` | 🔴 None | 🟢 Maximum | Dev containers only |
| Qwen | `auto-edit` (default) | 🟢 High | 🟢 High | Daily work (recommended) |
| Qwen | `--yolo` | 🔴 Low | 🟢 Very High | Trusted projects only |
| Qwen | `--approval-mode plan` | 🟢 High | 🟡 Medium | Planning/review only |

---

## Environment-Based Recommendations

### Development Laptop (Trusted Environment)

```bash
# Add to ~/.zshrc or ~/.bash_profile:
alias gemini-auto="gemini --approval-mode auto_edit"
alias gemini-yolo="gemini --yolo"
alias codex-auto="codex --full-auto"
alias copilot-auto="copilot --allow-all-tools"
alias copilot-yolo="copilot --allow-all-tools --allow-all-paths"
alias droid-low="droid --auto low"
alias droid-medium="droid --auto medium"
alias droid-high="droid --auto high"
alias qwen-auto="qwen --approval-mode auto-edit"
alias qwen-yolo="qwen --yolo"
alias qwen-plan="qwen --approval-mode plan"

# For this config repo specifically:
alias ai-gemini="cd ~/dev/tfwg/claude-config && gemini --yolo"
alias ai-codex="cd ~/dev/tfwg/claude-config && codex --full-auto"
alias ai-copilot="cd ~/dev/tfwg/claude-config && copilot --allow-all-tools"
alias ai-droid="cd ~/dev/tfwg/claude-config && droid --auto medium"
alias ai-qwen="cd ~/dev/tfwg/claude-config && qwen --yolo"
```

### Production Server (Restricted)

```bash
# Remove autonomous configs, use interactive only
gemini   # No flags
codex    # No --full-auto flag
copilot  # No --allow-all-tools flag
droid    # No --auto flag (read-only mode)
qwen --approval-mode default  # Interactive mode
```

### Docker/Dev Containers (Externally Sandboxed)

```bash
# Maximum autonomy is safe here
codex --dangerously-bypass-approvals-and-sandbox
gemini --yolo
copilot --allow-all-tools --allow-all-paths
droid --skip-permissions-unsafe
qwen --yolo
```

---

## Convenience Launcher

Use the included launcher script for guided execution:

```bash
# From repo root:
./scripts/launch-ai-cli.sh <tool> [mode]

# Examples:
./scripts/launch-ai-cli.sh gemini auto-edit
./scripts/launch-ai-cli.sh codex full-auto
./scripts/launch-ai-cli.sh copilot auto-tool
./scripts/launch-ai-cli.sh droid low
./scripts/launch-ai-cli.sh qwen auto-edit
./scripts/launch-ai-cli.sh qwen yolo
```

**Launcher provides:**
- ✅ Clear mode descriptions
- ✅ Safety warnings
- ✅ Confirmation for dangerous modes
- ✅ Usage examples

---

## Per-Project Overrides

### Codex: Project-Specific Trust

```toml
# In ~/.codex/config.toml:
[projects."/Users/administrator/dev/my-project"]
trust_level = "trusted"  # or "untrusted"
```

### Gemini: Project-Specific Config

```bash
# Create .gemini/settings.json in project root:
{
  "approvalMode": "yolo",
  "allowedMcpServerNames": ["filesystem", "brave-search"]
}
```

---

## Troubleshooting

### "Too many approval prompts"

**Gemini:**
```bash
gemini --approval-mode auto_edit  # Or --yolo for max autonomy
```

**Codex:**
```bash
codex --full-auto  # Or -a on-failure
```

### "Command execution blocked"

**Check trust level:**
```bash
# Codex:
cat ~/.codex/config.toml | grep trust_level

# Add project to trusted list if needed
```

### "MCP server asking for permissions"

**Whitelist MCP servers in Gemini:**
```bash
gemini --allowed-mcp-server-names serena filesystem chrome-bridge
```

---

## Security Best Practices

1. ✅ **Use `auto_edit` for daily work** - Good balance of safety and productivity
2. ✅ **YOLO mode only in trusted projects** - Know your codebase
3. ✅ **Never YOLO in production** - Interactive mode only
4. ✅ **Review what the model proposes** - Even in autonomous modes
5. ⚠️ **`--dangerously-bypass-approvals-and-sandbox` = dev containers only**

---

## Summary Table

| Goal | Claude | Gemini | Codex | Copilot | Droid | Qwen |
|------|--------|--------|-------|---------|-------|------|
| Safe default | `claude` | `gemini` | `codex` | `copilot` | `droid` | `qwen` |
| Auto-approve edits | N/A | `gemini --approval-mode auto_edit` | `codex` (from config) | N/A | `droid --auto low` | `qwen` (from config) |
| Auto-approve tools | N/A | N/A | N/A | `copilot --allow-all-tools` | N/A | N/A |
| Maximum autonomy | N/A | `gemini --yolo` | `codex --full-auto` | `copilot --allow-all-tools` | `droid --auto high` | `qwen --yolo` |
| Ultra-dangerous | N/A | `gemini --yolo` | `codex --dangerously-bypass...` | `copilot --allow-all-tools --allow-all-paths` | `droid --skip-permissions-unsafe` | `qwen --yolo` |

---

**Last Updated:** 2025-11-22
**Config Version:** 1.0
