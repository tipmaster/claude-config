# Claude Code Subagent Quick Reference

**Last Updated**: November 22, 2025
**Total Agents**: 21

---

## 🚀 New Critical Agents (Nov 2025)

### @code-reviewer ⭐ **USE BEFORE EVERY COMMIT**
**Purpose**: Systematic code review for quality, security, performance
**When**: Before commits, PRs, after significant changes
**Example**: `@code-reviewer review the authentication module for security issues`

### @security-auditor 🔒 **PROACTIVE SECURITY**
**Purpose**: Security vulnerability scanning, OWASP Top 10, secret detection
**When**: Sensitive code, API endpoints, auth logic, before deployment
**Example**: `@security-auditor audit the payment processing code`

### @api-designer 🎯 **CONTRACT-FIRST APIs**
**Purpose**: RESTful/GraphQL API design, OpenAPI specs, versioning
**When**: Designing new APIs, evolving existing endpoints
**Example**: `@api-designer create an OpenAPI spec for the user management API`

### @refactoring-specialist ♻️ **SAFE REFACTORING**
**Purpose**: Code smell detection, safe transformation, technical debt reduction
**When**: Legacy code modernization, simplification, pattern application
**Example**: `@refactoring-specialist refactor the OrderProcessor class to reduce complexity`

---

## 📋 Development Workflow Agents

### @frontend-developer
**Purpose**: React, Next.js, shadcn/ui, Tailwind CSS development
**When**: UI components, SSR/SSG, app router, frontend architecture

### @backend-architect
**Purpose**: Microservices, database schemas, API boundaries, scalability
**When**: System design, service boundaries, architectural decisions

### @python-expert
**Purpose**: Idiomatic Python, decorators, generators, async/await, optimization
**When**: Python refactoring, complex features, design patterns

### @debugger
**Purpose**: Root cause analysis, systematic debugging, issue investigation
**When**: Mysterious bugs, race conditions, memory leaks

### @test-runner
**Purpose**: Run tests, analyze failures without making fixes
**When**: Verifying test suite, understanding test failures

---

## 🗄️ Data & Infrastructure Agents

### @database-architect
**Purpose**: Multi-database expertise (MongoDB, Redis, MySQL, PostgreSQL, SQLite)
**When**: Schema design, database selection, migrations, optimization

### @database-optimizer
**Purpose**: Query optimization, indexing, N+1 problems, caching
**When**: Performance issues, slow queries, database tuning

---

## 🌐 Specialized Agents

### @seo-strategist
**Purpose**: SEO analysis, competitor research, keyword strategy, ranking improvements
**When**: SEO audits, content optimization, technical SEO

### @website-builder
**Purpose**: Static website generation, sports streaming, HTML/CSS/JS
**When**: Building high-performance static sites

### @website-reviewer
**Purpose**: QA validation, SEO standards, performance, accessibility
**When**: Website quality assurance before launch

### @sitemap-builder
**Purpose**: Data-driven sitemaps, keyword research, GSC analysis
**When**: Content planning, sitemap generation

### @prompt-engineer
**Purpose**: LLM prompt creation, optimization, cross-model compatibility
**When**: Writing/improving prompts for AI models

---

## 🛠️ Utility Agents

### @command-expert
**Purpose**: CLI command design, argument parsing, task automation
**When**: Building command-line interfaces

### @git-workflow
**Purpose**: Git operations, branch management, commits, PR creation
**When**: Complex git operations, automated workflows

### @file-creator
**Purpose**: Batch file creation, directory structures, templates
**When**: Scaffolding projects, creating boilerplate

### @context-fetcher
**Purpose**: Retrieve Agent OS documentation, check existing context
**When**: Accessing Agent OS docs

### @date-checker
**Purpose**: Determine current date (year, month, day)
**When**: Need current date information

---

## 📖 Common Workflow Patterns

### Pre-Commit Workflow
```
1. @code-reviewer → Review for issues
2. @security-auditor → Security scan
3. @test-runner → Verify tests pass
4. Git commit
```

### Feature Development
```
1. @api-designer → Design API contract
2. @backend-architect → System architecture
3. @frontend-developer → Implement UI
4. @test-runner → Generate/run tests
5. @code-reviewer → Final review
```

### Legacy Code Modernization
```
1. @refactoring-specialist → Analyze & plan
2. @database-optimizer → Update queries
3. @security-auditor → Check vulnerabilities
4. @test-runner → Verify behavior preserved
```

### Security-Focused Development
```
1. @security-auditor → Initial security design
2. @api-designer → Secure API design
3. @backend-architect → Security architecture
4. @security-auditor → Final security audit
```

---

## 💡 Best Practices

**Proactive Delegation:**
- Use subagents EARLY for complex problems
- Delegate well-scoped tasks (tests, docs, single-module refactors)
- Keep architecture decisions in main conversation

**Context Preservation:**
- Subagents have independent context windows
- Use them to preserve main conversation context
- Parallel execution for independent tasks

**Tool Permissions:**
- code-reviewer, security-auditor: Read, Grep, Glob (no writes)
- refactoring-specialist, api-designer: Read, Write, Edit
- Always review changes before applying

---

## 🔗 Agent Sources

**Built-in**: Installed with Claude Code
**VoltAgent**: https://github.com/VoltAgent/awesome-claude-code-subagents (4.9k ⭐, MIT)

To add more agents:
```bash
cd ~/.claude/agents
curl -O https://raw.githubusercontent.com/VoltAgent/awesome-claude-code-subagents/main/categories/<category>/<agent-name>.md
```

**Categories**: 01-core-development, 02-language-specialists, 03-infrastructure, 04-quality-security, 05-data-ai, 06-developer-experience, 07-specialized-domains, 08-business-product, 09-meta-orchestration, 10-research-analysis

---

## 📊 Usage Analytics

To see available agents: `/agents`
To invoke: `@agent-name <task>`
To let Claude choose: Describe task, Claude auto-invokes if appropriate

**Note**: Agents marked "PROACTIVE" should be used automatically by Claude when appropriate without explicit user request.
