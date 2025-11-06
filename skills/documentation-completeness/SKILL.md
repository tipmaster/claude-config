---
name: documentation-completeness
description: Use when adding features, changing APIs, modifying setup, or updating dependencies - ensures README updates, code comments, API docs sync, and architecture decisions are documented to prevent knowledge loss and onboarding friction
---

# Documentation Completeness

## Overview

Systematic documentation validation to ensure code changes are accompanied by appropriate documentation updates, preventing knowledge silos and onboarding friction.

## When to Use

Use this skill when:
- Adding new features or functionality
- Modifying existing APIs or interfaces
- Changing setup or installation process
- Adding or updating dependencies
- Making architectural decisions
- Fixing complex bugs
- Before merging pull requests

**Symptoms that trigger this skill:**
- "Add feature..."
- "Change API..."
- "Update dependency..."
- "Refactor architecture..."
- Before running final verification
- Before creating PR

**Don't use when:**
- Trivial changes (typo fixes, formatting)
- Internal refactoring with no external impact
- WIP/draft commits

## Quick Reference: Documentation Checklist

Use TodoWrite for ALL items below when documenting changes:

| Documentation Type | When Required | What to Update |
|-------------------|---------------|----------------|
| **README.md** | Feature add, setup change, new dependency | Installation, usage, examples |
| **Code Comments** | Complex logic, non-obvious decisions | Why, not what; edge cases |
| **API Docs** | API changes (endpoints, params, responses) | OpenAPI/Swagger, inline docs |
| **CHANGELOG.md** | User-facing changes | Version, date, breaking changes |
| **Architecture Decision Record (ADR)** | Significant architectural choice | Context, decision, consequences |
| **Inline Examples** | Public APIs, complex usage | Working code examples |

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Check if README needs update (setup, usage, examples)
☐ Add code comments for complex/non-obvious logic
☐ Update API documentation if endpoints/schemas changed
☐ Update CHANGELOG.md with user-facing changes
☐ Create ADR if architectural decision made
☐ Add inline code examples for new public APIs
☐ Update dependency documentation if added/changed
☐ Verify all examples still work
☐ Check for outdated documentation that needs removal
```

### Step 2: README.md Updates

**README must be updated when:**

| Change Type | README Section to Update | Example |
|------------|-------------------------|---------|
| New feature | Usage, Examples | New CLI flag, new API endpoint |
| Setup change | Installation, Configuration | New env var, different build command |
| New dependency | Prerequisites, Installation | Node version, system packages |
| API change | Usage, API Reference | New parameters, changed response format |
| Breaking change | Migration Guide, Usage | Removed feature, changed behavior |

**README structure (minimum):**

```markdown
# Project Name

Brief description (1-2 sentences)

## Prerequisites

- Node.js >= 18
- PostgreSQL >= 14
- Redis >= 6

## Installation

\`\`\`bash
npm install
cp .env.example .env
# Edit .env with your values
npm run migrate
\`\`\`

## Usage

\`\`\`bash
npm start
\`\`\`

### Common Tasks

- Run tests: `npm test`
- Build: `npm run build`
- Deploy: `npm run deploy`

## Configuration

See `.env.example` for all available environment variables.

| Variable | Description | Default |
|----------|-------------|---------|
| PORT | Server port | 3000 |
| DATABASE_URL | PostgreSQL connection | - |

## API Documentation

See [API.md](API.md) or OpenAPI spec at `/api/docs`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
```

### Step 3: Code Comments (When and What)

**Comment when:**
- ✅ Logic is complex or non-obvious
- ✅ Explaining WHY, not WHAT
- ✅ Documenting edge cases or gotchas
- ✅ Warning about performance implications
- ✅ Referencing external resources (RFCs, Stack Overflow)

**Don't comment when:**
- ❌ Code is self-explanatory
- ❌ Repeating what code says
- ❌ Compensating for bad naming

**Good comments:**

```javascript
// Good: Explains WHY
// Use exponential backoff to avoid overwhelming the API
// during recovery from outage
await retryWithBackoff(apiCall, { maxRetries: 5 });

// Good: Documents edge case
// Edge case: When user has no email, fall back to username
// for notification delivery
const recipient = user.email || user.username;

// Good: Performance warning
// PERF: This query is O(n²). For large datasets (>10k items),
// use the batch processing endpoint instead
const results = items.map(item => processItem(item));

// Good: References external resource
// Implementation follows RFC 6749 Section 4.1
// https://tools.ietf.org/html/rfc6749#section-4.1
function authorizeUser() { ... }
```

**Bad comments:**

```javascript
// Bad: Repeats what code says
// Increment counter
counter++;

// Bad: Obvious from code
// Get user by ID
const user = getUserById(id);

// Bad: Compensating for bad naming
// x is the user object
const x = getUser();
// Should be: const user = getUser();
```

**Comment format:**

```javascript
/**
 * Calculate order total including discounts and tax
 *
 * @param items - Array of order items
 * @param discountCode - Optional discount code
 * @returns Total price in cents
 *
 * @example
 * const total = calculateTotal([
 *   { price: 1000, quantity: 2 }
 * ], 'SAVE10');
 * // returns 1800 (20% discount applied)
 */
function calculateTotal(items, discountCode) { ... }
```

### Step 4: API Documentation

**When API changes, update:**

**For REST APIs (OpenAPI/Swagger):**

```yaml
paths:
  /api/users:
    post:
      summary: Create a new user
      description: |
        Creates a new user account. Email must be unique.
        Returns 409 if email already exists.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - password
              properties:
                email:
                  type: string
                  format: email
                  example: user@example.com
                password:
                  type: string
                  minLength: 8
                  example: SecurePass123!
      responses:
        201:
          description: User created successfully
        400:
          description: Validation error
        409:
          description: Email already exists
```

**For code libraries (JSDoc/TSDoc):**

```typescript
/**
 * Fetch user data from the API
 *
 * @param userId - The unique user identifier
 * @param options - Optional fetch configuration
 * @throws {NotFoundError} When user doesn't exist
 * @throws {UnauthorizedError} When auth token is invalid
 * @returns Promise resolving to user data
 *
 * @example
 * ```typescript
 * const user = await fetchUser('user_123');
 * console.log(user.email);
 * ```
 */
async function fetchUser(userId: string, options?: FetchOptions): Promise<User> {
  // Implementation
}
```

### Step 5: CHANGELOG.md

**Update CHANGELOG.md for all user-facing changes:**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New `/api/users/search` endpoint for searching users by email or username
- Support for OAuth2 authentication via Google and GitHub

### Changed
- `/api/users` endpoint now returns pagination metadata
- Error responses now include `requestId` field for support debugging

### Fixed
- Fixed race condition in session cleanup job
- Corrected timezone handling in date filters

### Breaking Changes
- Removed deprecated `/api/v1/user` endpoint (use `/api/v2/users` instead)
- `createdAt` field now returns ISO 8601 format instead of Unix timestamp

## [1.2.0] - 2025-01-15

### Added
- User profile avatars with automatic resizing
...
```

**CHANGELOG format:**
- ✅ Group by version
- ✅ Include date
- ✅ Categorize: Added, Changed, Fixed, Removed, Breaking Changes
- ✅ User-facing language (not technical jargon)
- ✅ Breaking changes prominently marked

### Step 6: Architecture Decision Records (ADRs)

**Create ADR when making significant architectural decisions:**

**When to create ADR:**
- Choosing database technology
- Choosing framework or library
- Deciding on API architecture (REST vs GraphQL)
- Selecting authentication strategy
- Choosing deployment architecture
- Making trade-offs with long-term impact

**ADR template:**

```markdown
# ADR 001: Use PostgreSQL for Primary Database

## Status
Accepted

## Context
We need a database for storing user data, orders, and analytics.
Requirements:
- ACID transactions
- Complex queries with joins
- JSON storage for flexible schemas
- Open source, well-supported
- Scalable to 1M+ users

Considered alternatives:
- MongoDB (NoSQL, flexible schema)
- MySQL (mature, widely used)
- PostgreSQL (powerful, feature-rich)

## Decision
We will use PostgreSQL as our primary database.

## Reasoning
- Strong ACID guarantees needed for financial data
- Native JSON support (JSONB) for flexible schemas
- Powerful query capabilities (CTEs, window functions)
- Excellent performance for our scale
- Large ecosystem and community support
- Better full-text search than MySQL
- MongoDB lacks ACID transactions (deal-breaker)

## Consequences

### Positive
- Strong consistency guarantees
- Powerful query language
- JSON support when needed
- Well-understood by team

### Negative
- Requires more schema planning than MongoDB
- Scaling writes harder than eventual-consistency NoSQL
- Learning curve for advanced features

### Mitigation
- Use read replicas for scaling reads
- Use connection pooling (PgBouncer)
- Consider sharding if needed at scale

## Alternatives Considered

### MongoDB
- **Pros:** Flexible schema, easy horizontal scaling
- **Cons:** No ACID transactions, eventual consistency issues
- **Rejected because:** Financial data requires ACID

### MySQL
- **Pros:** Mature, widely used, good performance
- **Cons:** Weaker JSON support, less powerful query features
- **Rejected because:** PostgreSQL more feature-rich with no downsides for our use case
```

**ADR location:** `/docs/adr/` or `/adr/`

### Step 7: Inline Code Examples

**Provide examples for:**
- Public APIs
- Complex configuration
- Common use cases

**Good example format:**

```typescript
/**
 * Rate limiter middleware
 *
 * @example Basic usage
 * ```typescript
 * app.use(rateLimit({
 *   windowMs: 15 * 60 * 1000, // 15 minutes
 *   max: 100 // limit each IP to 100 requests per window
 * }));
 * ```
 *
 * @example Custom key generator
 * ```typescript
 * app.use(rateLimit({
 *   windowMs: 15 * 60 * 1000,
 *   max: 100,
 *   keyGenerator: (req) => req.user.id // limit per user
 * }));
 * ```
 *
 * @example Skip certain routes
 * ```typescript
 * app.use(rateLimit({
 *   windowMs: 15 * 60 * 1000,
 *   max: 100,
 *   skip: (req) => req.path === '/health'
 * }));
 * ```
 */
```

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| No README update | New devs can't set up project | Update README for all setup changes |
| Comments explain WHAT | Wastes space, duplicates code | Comment WHY and edge cases only |
| Outdated examples | Misleads developers, wastes time | Verify examples work, remove outdated ones |
| No CHANGELOG | Users don't know what changed | Update CHANGELOG for user-facing changes |
| Generic API docs | Developers guess at usage | Specific examples, all params documented |
| No ADRs | Decisions forgotten, repeated debates | Document significant architectural choices |
| Docs separate from code | Docs become stale quickly | Keep docs close to code (inline, same PR) |
| Over-commenting | Noise, hard to find important comments | Comment judiciously, only when necessary |

## Rationalization Counters

**"Documentation can wait until later"** → Later never comes. Code without docs is write-only. Document as you go.

**"The code is self-documenting"** → Code explains WHAT, not WHY. Comments explain intent, edge cases, and decisions.

**"I'll remember to update README"** → You won't. Update docs in the same commit as code changes.

**"This is just internal code"** → Internal code still has users (your teammates). They need docs too.

**"Documentation is boring"** → Onboarding a new dev for 2 hours because docs are missing is more boring.

**"Examples are obvious"** → To you, today. Not to new devs or you in 6 months. Add examples.

**"I don't need CHANGELOG, we have git log"** → Git log is for developers. CHANGELOG is for users. They're different audiences.

## Documentation Checklist by Change Type

### Adding New Feature
- ☐ README usage section
- ☐ Code examples
- ☐ API docs if applicable
- ☐ CHANGELOG entry (Added section)
- ☐ Tests documented

### Modifying Existing Feature
- ☐ Update existing docs
- ☐ CHANGELOG entry (Changed section)
- ☐ Update examples if behavior changed
- ☐ Note breaking changes if applicable

### Fixing Bug
- ☐ CHANGELOG entry (Fixed section)
- ☐ Add comment explaining fix if complex
- ☐ Update docs if they were misleading

### Changing Setup/Configuration
- ☐ README installation section
- ☐ README configuration section
- ☐ .env.example if env vars added
- ☐ Migration guide if breaking

### Adding Dependency
- ☐ README prerequisites
- ☐ README installation instructions
- ☐ Document why dependency chosen (ADR if significant)

### Making Architectural Decision
- ☐ Create ADR
- ☐ Update high-level architecture docs
- ☐ Update README if affects setup/usage

## Integration with Existing Workflows

**With git workflow:**
- Update docs in same commit as code
- Docs changes in same PR as feature
- CI checks that examples still work

**With code review:**
- Reviewer checks docs updated
- Examples verified working
- README changes reviewed

**With release:**
- CHANGELOG reviewed
- API docs regenerated
- Migration guides published

## Real-World Impact

**Without this skill:**
- New devs struggle with setup (missing README)
- Code mysteries (no comments on complex logic)
- API usage guessed (no examples)
- Breaking changes surprise users (no CHANGELOG)
- Architectural decisions forgotten (repeated debates)

**With this skill:**
- Fast onboarding (complete README)
- Code understandable (appropriate comments)
- API usage clear (examples provided)
- Users informed (CHANGELOG maintained)
- Decisions documented (ADRs prevent re-litigation)

## Required Background

None. This skill is self-contained.

## Cross-References

- Use `superpowers:verification-before-completion` to verify docs before merge
- Use `superpowers:requesting-code-review` to get docs reviewed
