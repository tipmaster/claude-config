#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract basic info
model=$(echo "$input" | jq -r '.model.display_name')
cwd=$(echo "$input" | jq -r '.workspace.current_dir')
branch=$(git -C "$cwd" branch --show-current 2>/dev/null || echo '')

# Get username and hostname (shell-style)
username=$(whoami)
hostname=$(hostname -s)

# Get current directory basename
current_dir=$(basename "$cwd")

# Create git branch info if available
git_info=""
if [[ -n "$branch" ]]; then
    git_info=" (${branch})"
fi

# Get Claude Code usage information
usage_info=""
if command -v claude >/dev/null 2>&1; then
    # Try to get usage info from claude command
    usage_output=$(claude usage 2>/dev/null || true)
    if [[ -n "$usage_output" ]]; then
        # Parse daily and weekly limits
        # Look for patterns like "X of Y remaining" or "X remaining"
        daily_used=""
        daily_limit=""
        weekly_used=""
        weekly_limit=""

        # Try to extract daily usage (for current model)
        daily_line=$(echo "$usage_output" | grep -i "daily" | head -1)
        if [[ -n "$daily_line" ]]; then
            # Extract used/limit from formats like "45 of 50 remaining" or "5 remaining"
            if echo "$daily_line" | grep -q "of"; then
                daily_used=$(echo "$daily_line" | grep -o "[0-9]\+\s*of" | grep -o "[0-9]\+")
                daily_limit=$(echo "$daily_line" | grep -o "of\s*[0-9]\+" | grep -o "[0-9]\+")
            else
                daily_remaining=$(echo "$daily_line" | grep -o "[0-9]\+\s*remaining" | grep -o "[0-9]\+")
                if [[ -n "$daily_remaining" ]]; then
                    daily_used="?"
                    daily_limit="?"
                fi
            fi
        fi

        # Try to extract weekly usage
        weekly_line=$(echo "$usage_output" | grep -i "weekly" | head -1)
        if [[ -n "$weekly_line" ]]; then
            if echo "$weekly_line" | grep -q "of"; then
                weekly_used=$(echo "$weekly_line" | grep -o "[0-9]\+\s*of" | grep -o "[0-9]\+")
                weekly_limit=$(echo "$weekly_line" | grep -o "of\s*[0-9]\+" | grep -o "[0-9]\+")
            else
                weekly_remaining=$(echo "$weekly_line" | grep -o "[0-9]\+\s*remaining" | grep -o "[0-9]\+")
                if [[ -n "$weekly_remaining" ]]; then
                    weekly_used="?"
                    weekly_limit="?"
                fi
            fi
        fi

        # Build usage info string
        if [[ -n "$daily_used" ]] || [[ -n "$weekly_used" ]]; then
            usage_parts=""

            if [[ -n "$daily_used" ]] && [[ -n "$daily_limit" ]]; then
                usage_parts="D:${daily_used}/${daily_limit}"
            fi

            if [[ -n "$weekly_used" ]] && [[ -n "$weekly_limit" ]]; then
                if [[ -n "$usage_parts" ]]; then
                    usage_parts="${usage_parts} W:${weekly_used}/${weekly_limit}"
                else
                    usage_parts="W:${weekly_used}/${weekly_limit}"
                fi
            fi

            if [[ -n "$usage_parts" ]]; then
                usage_info=" [${usage_parts}]"
            fi
        fi
    fi
fi

# Display shell-style status line with dimmed colors
printf "\033[2m%s@%s %s%s %s%s\033[0m" "$username" "$hostname" "$current_dir" "$git_info" "$model" "$usage_info"