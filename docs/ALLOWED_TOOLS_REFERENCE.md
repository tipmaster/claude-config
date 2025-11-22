# Allowed Tools Reference

This document lists the comprehensive set of tools approved for use with Claude Code Assistant across all launch configurations.

## Standard Allowed Tools List

The following tools are enabled with `--allowedTools` flag across all Claude configurations:

```bash
--allowedTools serena,npm,git,grep,ssh,curl,perl,python3,mysql,redis-cli,clickhouse-client,make,brew,rsync,tmux,source,/usr/local/bin/playwright
```

### Tool Categories

#### Development Tools
- `npm` - Node package manager
- `git` - Version control
- `make` - Build automation
- `brew` - macOS package manager

#### System Utilities
- `grep` - Text search
- `ssh` - Remote shell access
- `curl` - HTTP client
- `rsync` - File synchronization
- `tmux` - Terminal multiplexer
- `source` - Shell script execution

#### Programming Languages
- `perl` - Perl interpreter
- `python3` - Python 3 interpreter

#### Database Clients
- `mysql` - MySQL database client
- `redis-cli` - Redis client
- `clickhouse-client` - ClickHouse database client

#### MCP Servers & Custom Tools
- `serena` - Code intelligence MCP server
- `/usr/local/bin/playwright` - Browser automation (full path)

## Usage Across Launch Configurations

### In ai-launcher.sh
All Claude launches (options 1 & 2) use the complete allowedTools list above.

### In .zshrc Aliases
All Claude aliases (`cc`, `ccn`, `cco`, `cch`, `ccf`, `ccq`, `ccs`) use the same comprehensive list.

## Permission Mode

All configurations use `--dangerously-skip-permissions` (YOLO mode) to auto-approve tool usage without prompts.

### Safety Considerations

While YOLO mode is enabled, the following safety measures are in place:
- Tools are explicitly whitelisted (not all system tools are available)
- Claude Code has built-in safety guardrails
- Git version control tracks all changes
- Database operations are limited to specific clients
- No `rm`, `dd`, or other destructive commands are in the allowedTools list

## Adding New Tools

To add a new tool to the allowed list:

1. Add it to the list in `scripts/ai-launcher.sh` (lines 111-112 and 117-119)
2. Add it to all aliases in `~/.zshrc` (lines 43-58)
3. Update this reference document
4. Test the new tool with a Claude session
5. Commit changes to git

## Related Files

- `scripts/ai-launcher.sh` - Interactive launcher
- `~/.zshrc` - Shell configuration with Claude aliases
- `config/settings-laptop.json` - Claude Code settings (project-specific allowedTools)
