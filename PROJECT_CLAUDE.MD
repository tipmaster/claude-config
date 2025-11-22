# Project-Specific Configuration

## Project Overview

This is the Claude Code configuration repository that centralizes settings, agents, and slash commands for all development projects.

**📚 For comprehensive tool documentation, see [TOOLS.MD](./TOOLS.MD)** - Complete guide to MCP servers, AI models, agents, and slash commands.

## Agent Usage Guide

### Available Agents

Use the right agent for the right task to get optimal results:

**Backend & API Development:**
- `@backend-architect` - Use for:
  - Designing RESTful APIs or GraphQL schemas
  - Creating API specifications (OpenAPI 3.1)
  - System architecture and microservices design
  - Service boundary definition
  - Technology stack selection
  - Backend system design and patterns

**Database:**
- `@database-architect` - Use for:
  - Database selection and architecture
  - Schema design and optimization
  - Query performance optimization and N+1 query detection
  - Index strategy and EXPLAIN ANALYZE
  - Database migrations and scaling strategies
  - Caching strategies (Redis/Memcached)
  - Covers: MongoDB, Redis, SQLite, MariaDB, MySQL, PostgreSQL

**Code Quality:**
- `@code-reviewer` - General code review (quality, security, best practices)
- `@security-auditor` - Deep security audits and compliance validation
- `@refactoring-specialist` - Systematic code refactoring and complexity reduction

**Development:**
- `@frontend-developer` - Next.js, React, shadcn/ui, Tailwind CSS
- `@python-expert` - Python-specific optimization and patterns
- `@command-expert` - CLI commands and automation

**SEO & Content:**
- `@seo-strategist` - SEO analysis and strategy
- `@sitemap-builder` - Content planning and sitemap generation
- `@prompt-engineer` - LLM prompt optimization

**Specialized:**
- `@debugger` - Systematic debugging and root cause analysis
- `@test-runner` - Test execution and failure analysis
- `@git-workflow` - Git operations and PR management

### Custom Slash Commands

Project includes these workflow commands in `.claude/commands/`:

- `/debug-loop` - Systematic debugging (analyze → hypothesis → test → repeat)
- `/feature-plan` - Comprehensive feature planning (requirements → design → implementation)
- `/test-suite` - Generate comprehensive test coverage
- `/doc-generate` - Auto-generate documentation from code
- `/api-spec` - Generate OpenAPI 3.1 specifications

**Usage:** Type `/` in Claude Code to see all available commands.

## Environment

**Server Access:**
- Server: <server-name>
- SSH: <user>@<server>:<port>
- Project location: `/path/to/project`

**Database:**
- Type: <database-type>
- Connection: <connection-details>

## Deployment

**Server Deployment Process:**
1. SSH to server: `ssh <user>@<server> -p <port>`
2. Navigate to project: `cd /path/to/project`
3. Pull latest code: `git pull`
4. Update environment variables if needed (e.g., .env file)
5. Restart service:
   - Linux (systemd): `systemctl restart <service-name>`
   - Docker: `docker-compose restart` or `docker restart <container>`
   - PM2: `pm2 restart <app-name>`
   - Custom: See project-specific restart procedure
6. Verify: Check logs and health endpoints

**Cron Job Management:**
If this project uses cron jobs:

1. **Version Control:**
   - Cron configuration file location in repo: `deploy/<project-name>.cron`
   - Server cron file location: `/etc/cron.d/<project-name>`

2. **Deployment Process:**
   ```bash
   # Deploy cron configuration to server
   sudo cp /path/to/project/deploy/<project-name>.cron /etc/cron.d/<project-name>
   sudo chmod 644 /etc/cron.d/<project-name>

   # Verify deployment
   cat /etc/cron.d/<project-name>

   # Monitor cron execution (update log path as needed)
   tail -f /var/log/<project-name>/cron.log
   ```

3. **Important Rules:**
   - Never use `crontab -e` on the server
   - Never edit `/etc/cron.d/<project-name>` directly
   - Always version changes in git first
   - Deploy by copying from repo to server

**Health Checks & Monitoring:**
- Health endpoint: `http://<server>/api/health` (replace with actual endpoint)
- Log locations: `/var/log/<project-name>/` or project-specific log directory
- Service status check:
  - Linux (systemd): `systemctl status <service-name>`
  - Docker: `docker ps` or `docker-compose ps`
  - PM2: `pm2 status` or `pm2 logs <app-name>`
