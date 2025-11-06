Always read ./SHARED_INSTRUCTIONS.MD before doing any work.

This project follows standardized development practices in the `agent-os` directory.

## Development Standards

**Core Guidelines:**
- `agent-os/standards/global/` - Core principles and dependency management
- `agent-os/standards/global/tech-stack.md` - Technology stack and infrastructure
- `agent-os/standards/coding-style.md` - Formatting and naming conventions

**Layer-Specific Rules:**
- `agent-os/standards/frontend/` - Frontend and UI rules
- `agent-os/standards/backend/` - Backend and API rules
- `agent-os/standards/testing/` - Testing-specific rules

## Workflow Commands

**Slash Commands:**

Core Workflow:
- `/init` - Initialize session context, load project instructions and current task focus
- `/dev-docs <task-name>` - Create structured development documentation for complex tasks
  - Generates `dev/active/<task-name>/` with plan.md, context.md, tasks.md
  - Use templates from `dev/templates/` as starting point
  - Archive to `dev/completed/` when task is finished

Documentation & Planning:
- `/explain <component>` - Deep explanation of code, architecture, or system behavior
- `/refactor-plan <component>` - Create detailed refactoring plan with safety analysis
- `/api-docs <endpoint>` - Generate or update API documentation from code analysis

Quality Assurance:
- `/review` - Comprehensive code review (architecture, security, performance, quality)
- `/test` - Generate tests for modified code or run existing test suite
- `/build-check` - Quick build and test validation before commits (syntax, linting, fast tests)

Deployment:
- `/deploy-check` - Pre-deployment validation checklist
- `/compact-with-docs` - Preserve context to dev docs before compacting conversation

**Development Documentation Workflow:**

For complex features or significant changes:
1. Run `/dev-docs <task-name>` to create documentation structure
2. Review and refine plan.md before implementation
3. Update context.md with architectural decisions and key files
4. Use tasks.md checklist to track implementation progress
5. Run `/review` before finalizing changes
6. Run `/deploy-check` before deployment
7. Archive completed work to `dev/completed/<task-name>/`

**Utilities:**

Available in `.claude/hooks/` for manual execution:
- `skill-suggester.py <prompt>` - Suggest relevant Superpowers skills based on task description
- `pre-deploy-validator.py [--branch main] [--require-tests]` - Comprehensive pre-deployment validation
- `check-protected-files.sh` - Warn when modifying critical project files

Usage examples:
```bash
# Get skill suggestions for a task
.claude/hooks/skill-suggester.py "implement user authentication"

# Validate before deployment
.claude/hooks/pre-deploy-validator.py --branch main --require-tests

# Check if file is protected
ARGUMENTS='{"file_path":"requirements.txt"}' .claude/hooks/check-protected-files.sh
```

**Protected Files:**

These files are critical and require extra care when modifying:
- CLAUDE.md, SHARED_INSTRUCTIONS.MD (project instructions)
- .env files (environment configuration)
- requirements.txt, pyproject.toml (dependencies)
- .claude/settings.json files (Claude Code configuration)

## Requirements

**Code Management:**
- Always version code in git
- Use git to move code between local and server (except .env files and security keys)
- Maintain CHANGELOG.MD with proper timestamps for significant changes

**Documentation:**
- Update README.md when adding features, changing dependencies, or modifying setup
- Comment non-obvious code for mid-level developer understanding
- Add `# Reason:` comments for complex logic

## Environment

**Server Access:**
- Server: nue
- SSH: root@nue:55000 (no credentials required)
- Project location: `/opt/<project-folder>` or `/<project-folder>`

**Database:**
- ClickHouse available: `/opt/clickhouse/clickhouse --client --port 9002`

## Deployment

**IMPORTANT - Server Cronjobs:**
- **NEVER modify cronjob files directly on the server**
- Document any required cronjob changes in comments or separate notes
- User must manually update server cronjobs after reviewing changes
- Current cronjobs run existing updater scripts - no changes needed for predictions/top scorers feature
- New features are controlled via `.env` file settings, not cronjob modifications

**Server Deployment Process:**
1. Commit and push code changes to git repository
2. SSH to server: `ssh root@nue -p 55000`
3. Navigate to project: `cd /opt/sportmonks-embed`
4. Pull latest code: `git pull`
5. Update .env if needed (feature flags, settings)
6. Restart service: `systemctl restart sportmonks-api`
7. Verify: Check logs and `/api/health` endpoint

## Tools

**Browser Testing:**
- Playwright (v1.54.0 global, v1.55.0 local)
- Create `.js` scripts, run with `node script_name.js`
- Use directly (not MCP) for all browser testing

**Code Search (Priority Order):**

1. **Semgrep** (Primary) - Structure-aware pattern matching
   - Quick pattern: `semgrep -e "<pattern>" --lang <lang> <path> --json --quiet`
   - Rule pack: `semgrep --config p/<pack> <path> --json --quiet`
   - Local rules: `semgrep --config semgrep-rules/ <path> --json --quiet`
   - Diff review: `semgrep --config semgrep-rules/ --baseline-ref origin/main --json --quiet`
   - Always use `--json --quiet`, default to 50 results

2. **CK Search** (Supplemental) - Semantic and traditional search
   - Semantic: `ck --sem "error handling" src/`
   - Traditional: `ck -n "TODO" *.rs`
   - Hybrid: `ck --hybrid "connection timeout" src/`