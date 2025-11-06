---
name: api-design-review
description: Use when designing/modifying REST APIs, GraphQL schemas, or service contracts - validates versioning, auth, error handling, pagination, rate limits, and breaking changes to prevent costly post-deployment fixes
---

# API Design Review

## Overview

Systematic validation of API contracts before implementation to catch design issues that are expensive or impossible to fix after client integration.

## When to Use

Use this skill when:
- Designing new API endpoints or services
- Modifying existing API contracts
- Reviewing pull requests with API changes
- Planning API versioning or deprecation
- Adding authentication or authorization
- Integrating third-party APIs

**Symptoms that trigger this skill:**
- "Add endpoint for..."
- "Modify API response..."
- "Change authentication..."
- Code in `routes/`, `controllers/`, `api/`, `graphql/` directories
- Files named `*api*.{ts,js,py,go}`, `routes.*`, `schema.graphql`

**Don't use when:**
- Internal function signatures (not exposed to clients)
- Database schema changes (use different pattern)
- UI components

## Quick Reference: API Design Checklist

Use TodoWrite for ALL items below when reviewing APIs:

| Category | Validation | Critical Issues |
|----------|-----------|-----------------|
| **REST Principles** | Nouns not verbs, HTTP methods correctly, status codes | Verbs in URLs, wrong methods, generic 200s |
| **Versioning** | Strategy defined, in URL or header, documented | No version, breaking changes without version |
| **Authentication** | Scheme chosen (JWT/OAuth/API key), applied consistently | Unprotected sensitive endpoints |
| **Authorization** | Role/permission checks, resource ownership validation | Missing authz checks, privilege escalation |
| **Error Handling** | Consistent format, error codes, helpful messages | Generic errors, stack traces exposed |
| **Pagination** | Cursor or offset, page size limits, total count | No pagination on large collections |
| **Rate Limiting** | Limits defined, headers included, documented | No rate limits, DOS vulnerability |
| **Breaking Changes** | Detected, versioned, migration path documented | Breaking changes in same version |

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Validate REST principles (resource naming, HTTP methods, status codes)
☐ Validate versioning strategy (URL/header, documented, consistent)
☐ Validate authentication (scheme chosen, consistently applied)
☐ Validate authorization (role checks, resource ownership, least privilege)
☐ Validate error responses (consistent format, codes, no stack traces)
☐ Validate pagination (cursor/offset, limits, metadata)
☐ Validate rate limiting (limits defined, headers, documented)
☐ Validate request validation (schema, required fields, types)
☐ Validate response schema (consistent, documented, versioned)
☐ Detect breaking changes (compare to previous version, document migration)
```

### Step 2: REST Principles Validation

**Resource naming:**
```
✅ GET    /api/v1/users              # Plural nouns
✅ GET    /api/v1/users/{id}         # Specific resource
✅ POST   /api/v1/users              # Create
✅ PUT    /api/v1/users/{id}         # Full update
✅ PATCH  /api/v1/users/{id}         # Partial update
✅ DELETE /api/v1/users/{id}         # Delete

❌ GET    /api/v1/getUsers           # No verbs
❌ POST   /api/v1/createUser         # No verbs
❌ GET    /api/v1/user/{id}          # Use plural
```

**HTTP status codes:**
```
✅ 200 OK - Successful GET, PUT, PATCH
✅ 201 Created - Successful POST
✅ 204 No Content - Successful DELETE
✅ 400 Bad Request - Client error (validation)
✅ 401 Unauthorized - Not authenticated
✅ 403 Forbidden - Not authorized
✅ 404 Not Found - Resource doesn't exist
✅ 429 Too Many Requests - Rate limit
✅ 500 Internal Server Error - Server error

❌ 200 for errors with {"error": "..."}
❌ 500 for validation errors
❌ 200 for not found
```

### Step 3: Versioning Strategy

**Choose one strategy consistently:**

**URL versioning (recommended for simplicity):**
```
✅ /api/v1/users
✅ /api/v2/users
```

**Header versioning (recommended for cleanliness):**
```
✅ Accept: application/vnd.api+json; version=1
✅ X-API-Version: 2
```

**Rules:**
- Version ALL endpoints from day 1
- Increment version for breaking changes only
- Support N-1 version minimum (v2 and v1 simultaneously)
- Document deprecation timeline (e.g., 6 months notice)

**Breaking changes that require new version:**
- Removing fields from response
- Renaming fields
- Changing field types
- Removing endpoints
- Changing authentication mechanism
- Changing required request fields

**Non-breaking changes (same version OK):**
- Adding optional fields to response
- Adding new endpoints
- Adding optional request parameters
- Relaxing validation rules

### Step 4: Authentication & Authorization

**Authentication (who are you?):**

```typescript
// Choose one consistently:
✅ JWT Bearer tokens (stateless, scalable)
   Authorization: Bearer <token>

✅ API Keys (simple, for machine clients)
   X-API-Key: <key>

✅ OAuth 2.0 (delegated access, third-party)
   Authorization: Bearer <oauth-token>

❌ Basic auth over HTTP (insecure)
❌ Custom auth schemes (reinventing the wheel)
```

**Authorization (what can you do?):**

```typescript
// Always check:
✅ User has required role/permission
✅ User owns the resource (user A can't edit user B's data)
✅ Resource is in allowed state (can't delete published content)

// Example checks:
✅ await checkPermission(user, 'user:update')
✅ if (resource.userId !== user.id) throw Forbidden
✅ if (resource.status === 'locked') throw Forbidden

❌ Checking authentication only (missing authorization)
❌ Assuming user owns resource without check
❌ No role/permission system
```

**Critical rule:** Every endpoint must explicitly declare if auth is required. Default to requiring auth.

### Step 5: Error Response Format

**Consistent error schema:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "User-friendly error message",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "requestId": "uuid-for-support"
  }
}
```

**Rules:**
- ✅ Use consistent schema across all endpoints
- ✅ Include machine-readable error code
- ✅ Include human-readable message
- ✅ Include request ID for debugging
- ✅ For validation errors, include field-level details
- ❌ Never expose stack traces to clients
- ❌ Never expose internal error messages
- ❌ Don't return HTML error pages for JSON APIs

### Step 6: Pagination

**For any collection endpoint (returning arrays):**

**Cursor-based (recommended for large datasets):**
```json
{
  "data": [...],
  "pagination": {
    "nextCursor": "opaque-cursor-string",
    "hasMore": true
  }
}
```

**Offset-based (simple, but slow for large datasets):**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 50,
    "totalCount": 1000,
    "totalPages": 20
  }
}
```

**Rules:**
- ✅ Paginate any endpoint that can return >100 items
- ✅ Set max page size (e.g., 100-500)
- ✅ Document default page size
- ✅ Return pagination metadata
- ❌ No pagination on collections
- ❌ No max page size (DOS risk)

### Step 7: Rate Limiting

**Define limits:**
```
✅ Per user: 100 req/min, 10,000 req/day
✅ Per IP (unauthenticated): 10 req/min, 1,000 req/day
```

**Return rate limit headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1609459200
```

**On rate limit exceeded:**
```
429 Too Many Requests
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "retryAfter": 45
  }
}
```

### Step 8: Detect Breaking Changes

**Compare new API contract with previous version:**

**Breaking change checklist:**
- ☐ Removed fields from response?
- ☐ Renamed fields?
- ☐ Changed field types?
- ☐ Made optional fields required?
- ☐ Removed endpoints?
- ☐ Changed authentication?
- ☐ Changed URL structure?
- ☐ Changed error response format?

**If ANY breaking changes → Increment version number**

**Document migration:**
```markdown
# Migration Guide: v1 → v2

## Breaking Changes
1. `userName` field renamed to `username`
   - v1: `{"userName": "john"}`
   - v2: `{"username": "john"}`

2. `POST /users` now requires `email` field
   - v1: email was optional
   - v2: email is required

## Migration Steps
1. Update client to use v2 endpoint
2. Update field names in code
3. Ensure email is provided on user creation

## Deprecation Timeline
- v1 will be deprecated on 2025-07-01
- v1 will be removed on 2026-01-01
```

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Verbs in URLs | Not RESTful, confusing | Use nouns + HTTP methods |
| No API versioning | Breaking changes break all clients | Version from day 1 |
| Same 200 for errors | Clients can't distinguish success/failure | Use proper status codes |
| Missing authorization | Security vulnerability | Check resource ownership + permissions |
| Generic error messages | Poor developer experience | Specific, actionable error messages |
| No pagination | Performance + DOS risk | Paginate collections, set max limits |
| No rate limiting | DOS vulnerability | Implement rate limits per user/IP |
| Breaking changes without version bump | Breaks existing clients | Increment version for breaking changes |
| Exposing stack traces | Security risk (info disclosure) | Return sanitized errors only |
| No auth on sensitive endpoints | Data breach risk | Default to requiring auth |

## Rationalization Counters

**"I'll add versioning later"** → Versioning is nearly impossible to retrofit. Clients are already using unversioned endpoints. Start with v1 or you'll be stuck forever.

**"This is an internal API"** → Internal APIs still have clients (your own frontend). They still need stability. Apply same standards.

**"We only have one client"** → Today. Tomorrow you'll have mobile app, third-party integrations, webhooks. Design for multiple clients from day 1.

**"Pagination can wait until we have data"** → Pagination is hard to add to existing clients. They expect full arrays. Build it in now.

**"Rate limiting is premature optimization"** → Rate limiting prevents abuse and DOS. It's security, not optimization. Add it before launch.

**"I checked the endpoint, it works"** → "Works" ≠ well-designed. Use full checklist or you'll have breaking changes, security holes, and poor DX.

## Integration with Existing Workflows

**Before writing implementation:**
1. Design API contract first (OpenAPI/Swagger)
2. Run this skill on the contract
3. Get peer review on contract
4. Then implement

**When modifying existing API:**
1. Document proposed changes
2. Run breaking change detection
3. If breaking → plan new version
4. If non-breaking → document additive changes

**When reviewing PR:**
1. Look for API changes
2. Run this skill
3. Request changes if checklist items fail
4. Verify migration docs for breaking changes

## Real-World Impact

**Without this skill:**
- Breaking changes ship without version bump (angry clients)
- Missing authorization checks (security breach)
- No pagination (performance issues + DOS)
- No rate limiting (abuse, DOS, high costs)
- Inconsistent error handling (poor DX, support burden)
- Can't deprecate old endpoints (technical debt forever)

**With this skill:**
- Clean API versioning strategy (smooth migrations)
- Consistent auth/authz (secure by default)
- Pagination built in (scalable from day 1)
- Rate limiting prevents abuse
- Consistent error handling (great DX)
- Can evolve API without breaking clients

## Required Background

None. This skill is self-contained.

## Cross-References

- Use `superpowers:brainstorming` when planning API architecture
- Use `superpowers:requesting-code-review` after API implementation
- Use `superpowers:verification-before-completion` before deploying API changes
