# Claude Code Hooks

This directory contains hook scripts that can be integrated into `.claude/settings.json` to automate workflows.

## Available Hooks

### check-protected-files.sh

Warns when modifying critical project files.

**Protected Files:**
- CLAUDE.md, SHARED_INSTRUCTIONS.MD (project instructions)
- .env files (environment configuration)
- requirements.txt, pyproject.toml (dependencies)
- .claude/settings.json files (Claude Code configuration)

**Testing:**
```bash
# Simulate hook with file path
ARGUMENTS='{"file_path":"CLAUDE.md"}' .claude/hooks/check-protected-files.sh
```

### skill-suggester.py

Analyzes user prompts and suggests relevant Superpowers skills based on pattern matching.

**Features:**
- Matches prompts against skill patterns from `skill-rules.json`
- Prioritizes suggestions (critical, high, medium, low)
- Exempts informational queries
- Works standalone or as a hook

**Usage:**
```bash
# Command line
.claude/hooks/skill-suggester.py "fix the authentication bug"

# Test mode (show all rules)
.claude/hooks/skill-suggester.py --test

# Via environment variable (hook mode)
ARGUMENTS='{"prompt":"implement new feature"}' .claude/hooks/skill-suggester.py
```

**Output Example:**
```
📋 Relevant Skills Detected:

🟡 superpowers:systematic-debugging
   Priority: HIGH
   Systematic investigation before proposing fixes
```

## Hooks Integration (Optional)

To integrate hooks into `.claude/settings.json`, add a `hooks` section. This is optional - hooks can also be run manually.

### Protected Files Hook

Warn when modifying critical files:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/check-protected-files.sh"
          }
        ]
      },
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/check-protected-files.sh"
          }
        ]
      }
    ]
  }
}
```

### Skill Suggestion Hook (Advanced)

Suggest skills based on user prompts (note: Superpowers already includes skill checking):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/skill-suggester.py"
          }
        ]
      }
    ]
  }
}
```

## Hook Development

Hooks receive JSON input via the `$ARGUMENTS` environment variable. Common fields:
- `file_path` - For Edit/Write/Read tools
- `command` - For Bash tools
- `pattern` - For Grep tools
- `prompt` / `message` / `content` - User input

Exit codes:
- `0` - Success (continues execution)
- `non-zero` - Blocks execution with error message

## Configuration Files

- **skill-rules.json** - Defines patterns for skill suggestions
- **settings.json** - Hooks configuration (optional)

## Manual Usage

All hooks can be run manually without integration:
```bash
# Check if a file is protected
ARGUMENTS='{"file_path":"requirements.txt"}' .claude/hooks/check-protected-files.sh

# Get skill suggestions for a task
.claude/hooks/skill-suggester.py "refactor the database layer"
```
