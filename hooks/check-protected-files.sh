#!/bin/bash
# Protected files validation hook
# Warns when attempting to modify critical project files
# Usage: Called via PostToolUse hook or manually

# Protected files patterns
PROTECTED_FILES=(
  "CLAUDE.md"
  "SHARED_INSTRUCTIONS.MD"
  ".env"
  ".env.*"
  "requirements.txt"
  "pyproject.toml"
  ".claude/settings.json"
  ".claude/settings.local.json"
)

# Parse hook input JSON to get file path
# Expects $ARGUMENTS environment variable with JSON like: {"file_path": "..."}
if [ -n "$ARGUMENTS" ]; then
  FILE_PATH=$(echo "$ARGUMENTS" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

  if [ -n "$FILE_PATH" ]; then
    # Check if file matches any protected pattern
    for pattern in "${PROTECTED_FILES[@]}"; do
      # Convert glob pattern to regex for matching
      regex=$(echo "$pattern" | sed 's/\./\\./g' | sed 's/\*/.*/')

      if echo "$FILE_PATH" | grep -qE "^${regex}$"; then
        echo "⚠️  WARNING: Modifying protected file: $FILE_PATH"
        echo "This file is critical to project configuration."
        echo "Ensure changes are intentional and tested."
        exit 0
      fi
    done
  fi
fi

exit 0
