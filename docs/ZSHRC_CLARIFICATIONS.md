# .zshrc AI CLI Configuration Clarifications

This document explains the AI CLI aliases and startup parameters configured in your `~/.zshrc`.

## Current AI CLI Aliases

### Claude Code Aliases (Lines 43-49)

**Primary Alias (Default):**
```bash
alias cc="claude --dangerously-skip-permissions --allowedTools ... --verbose --continue"
```
- `--dangerously-skip-permissions`: ⚠️  **DANGEROUS** - Bypasses all permission checks
- `--allowedTools`: Whitelist of tools Claude can use without approval
- `--verbose`: Show detailed output
- `--continue`: Continue previous conversation if available

**Variant Aliases:**
| Alias | Model | Flags | Use Case |
|-------|-------|-------|----------|
| `cc` | Sonnet (default) | verbose, continue, skip-perms | Daily work (default) |
| `ccn` | Sonnet | verbose, skip-perms | New conversation |
| `cco` | Opus | verbose, continue, skip-perms | Complex tasks (opus model) |
| `cch` | Sonnet | print, skip-perms | Quick questions (print mode) |
| `ccf` | Sonnet | verbose, skip-perms | Fresh start, verbose |
| `ccq` | Sonnet | continue, skip-perms | Quick continue |
| `ccs` | Sonnet | max-turns 10, continue, skip-perms | Short sessions (10 turns) |

**Helper Functions:**
```bash
ask() { claude --print ... "$*" }      # Quick questions without quotes
askclip() { pbpaste | claude ... }     # Ask about clipboard content
```

### Gemini CLI Aliases (Lines 97-98)

**⚠️  IMPORTANT SAFETY NOTE:**

```bash
alias gemini-auto="gemini --approval-mode auto_edit"  # Line 97: SAFER option
alias gemini="gemini --yolo"                           # Line 98: DANGEROUS default!
```

**Issue:** Your default `gemini` alias uses `--yolo` mode which auto-approves EVERYTHING.

**Recommendation:** Consider reversing these:
```bash
# RECOMMENDED: Make auto-edit the default
alias gemini="gemini --approval-mode auto_edit"
alias gemini-yolo="gemini --yolo"
```

### Codex CLI Aliases (Lines 95, 99)

```bash
alias ccodex="codex --sandbox danger-full-access --ask-for-approval never --enable web_search_request"
alias codex="codex --full-auto"
```

- `ccodex`: ⚠️  **EXTREMELY DANGEROUS** - Full access, no approvals, no sandbox
- `codex`: Balanced - Full-auto mode with workspace-write sandbox (recommended)

### Copilot Alias (Line 96)

```bash
alias copilot-yolo="copilot --allow-all-tools --allow-all-paths"
```

- ⚠️  **DANGEROUS** - Auto-approves all tools + unrestricted file access
- No safe `copilot` alias defined (uses interactive mode by default)

---

## Safety Analysis

### 🔴 Dangerous Defaults (Need Attention)

1. **`gemini` uses `--yolo`** (Line 98)
   - Auto-approves: Everything
   - Recommendation: Change to `--approval-mode auto_edit`

2. **`cc` uses `--dangerously-skip-permissions`** (Lines 43-49)
   - Bypasses: All permission checks
   - Consideration: This is your primary workflow, understand the risks

3. **`ccodex` has no sandbox** (Line 95)
   - Full system access without restrictions
   - Recommendation: Use `codex` (full-auto) instead for most work

### 🟡 Balanced Options (Recommended for Daily Use)

1. **`gemini-auto`** (Line 97)
   - Auto-approves: Edits only
   - Asks for: Tool executions, MCP calls
   - ✅ Recommended as default

2. **`codex`** (Line 99)
   - Model decides when to ask
   - Sandboxed workspace access
   - ✅ Good balance of safety and productivity

3. **`copilot`** (no alias, uses defaults)
   - Interactive mode
   - Trusted folders configured
   - ✅ Safe for all scenarios

### 🟢 Safe Options

1. **`cch` / `ask()` / `askclip()`**
   - Print mode (read-only responses)
   - No file modifications
   - ✅ Perfect for quick questions

---

## Recommended Changes

### Priority 1: Fix Gemini Default

**Current (DANGEROUS):**
```bash
alias gemini-auto="gemini --approval-mode auto_edit"
alias gemini="gemini --yolo"
```

**Recommended (SAFER):**
```bash
# Safe default for daily use
alias gemini="gemini --approval-mode auto_edit"

# Explicit YOLO mode when you need it
alias gemini-yolo="gemini --yolo"
```

### Priority 2: Add Missing Aliases

Add these for consistency:

```bash
# Droid CLI
alias droid-low="droid --auto low"          # File operations only
alias droid-medium="droid --auto medium"    # Development work
alias droid-high="droid --auto high"        # Production changes

# Qwen CLI
alias qwen="qwen --approval-mode auto-edit" # Safe default
alias qwen-yolo="qwen --yolo"               # Dangerous mode
alias qwen-plan="qwen --approval-mode plan" # Planning mode

# Copilot (add safe version)
alias copilot="copilot"                     # Interactive (safe)
alias copilot-auto="copilot --allow-all-tools"  # Auto-approve tools
# copilot-yolo already exists (line 96)
```

### Priority 3: Add Interactive Launcher

Add to .zshrc:
```bash
# Interactive AI CLI launcher (new script)
alias ai="~/dev/tfwg/claude-config/scripts/ai-launcher.sh"
```

Then you can just type `ai` and select from a menu with arrow keys!

---

## Understanding the Flags

### Claude Code Flags

| Flag | What It Does | Safety Level |
|------|--------------|--------------|
| `--dangerously-skip-permissions` | Bypass all permission checks | 🔴 Dangerous |
| `--allowedTools <list>` | Whitelist tools (no approval needed) | 🟡 Depends on tools |
| `--verbose` | Show detailed output | 🟢 Safe (output only) |
| `--continue` | Continue previous conversation | 🟢 Safe |
| `--print` | Read-only mode (no actions) | 🟢 Very Safe |
| `--model opus` | Use Opus model instead of Sonnet | 🟢 Safe (model choice) |
| `--max-turns N` | Limit conversation length | 🟢 Safe |

### Gemini Flags

| Flag | What It Does | Safety Level |
|------|--------------|--------------|
| `--approval-mode auto_edit` | Auto-approve edits only | 🟡 Balanced |
| `--yolo` or `-y` | Auto-approve EVERYTHING | 🔴 Dangerous |
| `--allowed-mcp-server-names <list>` | Whitelist MCP servers | 🟡 Depends on servers |

### Codex Flags

| Flag | What It Does | Safety Level |
|------|--------------|--------------|
| `--full-auto` | Model decides + workspace sandbox | 🟡 Balanced |
| `--sandbox workspace-write` | Allow writes in workspace only | 🟡 Balanced |
| `--sandbox danger-full-access` | Full system access | 🔴 Extremely Dangerous |
| `--ask-for-approval never` | Never ask for approval | 🔴 Dangerous |
| `-a on-request` | Model decides when to ask | 🟡 Balanced |

### Copilot Flags

| Flag | What It Does | Safety Level |
|------|--------------|--------------|
| `--allow-all-tools` | Auto-approve all tool executions | 🟡 Medium Risk |
| `--allow-all-paths` | Disable path restrictions | 🔴 Dangerous |
| `--agent <name>` | Use specific agent role | 🟢 Safe |

### Droid Flags

| Flag | What It Does | Safety Level |
|------|--------------|--------------|
| (none) | Read-only mode | 🟢 Very Safe |
| `--auto low` | Basic file operations | 🟡 Low Risk |
| `--auto medium` | Dev operations (git, builds) | 🟡 Medium Risk |
| `--auto high` | Production operations | 🟠 High Risk |
| `--skip-permissions-unsafe` | Bypass all permissions | 🔴 Extremely Dangerous |

### Qwen Flags

| Flag | What It Does | Safety Level |
|------|--------------|--------------|
| `--approval-mode auto-edit` | Auto-approve edits only | 🟡 Balanced |
| `--approval-mode plan` | Plan only, no execution | 🟢 Very Safe |
| `--approval-mode default` | Interactive (ask for all) | 🟢 Safe |
| `--yolo` or `-y` | Auto-approve everything | 🔴 Dangerous |

---

## Quick Reference: Which Alias Should I Use?

### For Daily Coding Work
- **Claude Code:** `cc` (if you trust your setup) or `ccf` for fresh start
- **Gemini:** `gemini-auto` (current) → Should be renamed to `gemini`
- **Codex:** `codex` (balanced and safe)
- **Copilot:** `copilot` (interactive, safe)
- **Droid:** `droid-medium` (add this alias)
- **Qwen:** `qwen` with auto-edit (add this alias)

### For Quick Questions
- **Claude Code:** `ask "your question"` or `cch`
- **Claude Code:** `askclip` (for clipboard content)

### For Trusted Projects Only
- **Gemini:** `gemini` (current - uses YOLO!)
- **Codex:** `ccodex` (full danger mode)
- **Copilot:** `copilot-yolo`
- **Qwen:** `qwen-yolo` (add this alias)

### For Complex Tasks
- **Claude Code:** `cco` (uses Opus model)
- **Claude Code:** `ccs` (short session with 10 turns)

### For Clipboard Operations
- **Claude Code:** `askclip` (ask about clipboard content)

---

## Action Items

### Immediate (Safety)
1. ✅ Review the `gemini` alias using `--yolo` by default
2. ✅ Consider renaming for safety:
   - `gemini` → `gemini-yolo`
   - `gemini-auto` → `gemini`

### Recommended (Completeness)
1. ✅ Add Droid aliases (`droid-low`, `droid-medium`, `droid-high`)
2. ✅ Add Qwen aliases (`qwen`, `qwen-yolo`, `qwen-plan`)
3. ✅ Add Copilot safe alias if desired
4. ✅ Add interactive launcher alias: `alias ai="~/dev/tfwg/claude-config/scripts/ai-launcher.sh"`

### Optional (Organization)
1. ✅ Group all AI CLI aliases together in .zshrc
2. ✅ Add comments explaining safety levels
3. ✅ Consider moving AI aliases to separate `~/.ai_aliases` file and sourcing it

---

## Summary

Your .zshrc is well-configured with extensive AI CLI support. The main concern is the **`gemini` alias defaulting to `--yolo` mode**, which auto-approves everything without asking. Consider making `--approval-mode auto_edit` the default for safer daily use.

The new **interactive launcher** (`ai`) provides a menu-driven interface where:
- Press Enter for Claude Code (default)
- Type number 1-9 to select other agents
- Each option shows safety level (🟢 Safe, 🟡 Balanced, 🔴 Dangerous)

**Last Updated:** 2025-11-22
**Config Version:** 1.0
