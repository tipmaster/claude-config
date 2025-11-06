---
name: error-handling-patterns
description: Use when adding error handling, designing APIs, or debugging failures - guides selection of fail-fast vs graceful degradation, error boundaries, retry strategies, and user-facing messages to build resilient systems
---

# Error Handling Patterns

## Overview

Systematic approach to error handling that balances resilience with debuggability through appropriate strategies for different error types and contexts.

## When to Use

Use this skill when:
- Adding error handling to new code
- Designing API error responses
- Implementing retry logic
- Debugging production errors
- Reviewing error handling in code
- Deciding between fail-fast and graceful degradation

**Symptoms that trigger this skill:**
- "Add error handling for..."
- "Handle this failure..."
- "Retry when X fails..."
- try/catch blocks, error objects
- Production errors in logs
- Discussing failure modes

**Don't use when:**
- Validation errors (straightforward)
- Expected control flow (not errors)

## Quick Reference: Error Handling Decision Tree

Use TodoWrite for ALL items below when handling errors:

```
Is this error recoverable?
├─ No → Fail fast (crash, log, alert)
└─ Yes → Can user take action?
    ├─ Yes → Return actionable error message
    └─ No → Should we retry automatically?
        ├─ Yes → Retry with backoff
        └─ No → Graceful degradation or fail
```

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Classify error type (recoverable vs unrecoverable)
☐ Choose strategy (fail-fast, retry, graceful degradation)
☐ Implement error boundary if needed
☐ Add user-facing error message (actionable)
☐ Add technical error details (for logging)
☐ Add request/trace ID for debugging
☐ Log error with context (stack trace, input, state)
☐ Set up monitoring/alerting if critical
☐ Test error scenarios (unit tests, integration tests)
☐ Document error behavior in API docs
```

### Step 2: Error Classification

**Unrecoverable errors (fail fast):**
- Programmer errors (bugs)
- Missing required config
- Invalid state (corrupted data)
- Out of memory
- Missing dependencies

**Recoverable errors (handle gracefully):**
- Network timeouts
- Rate limits
- User input validation
- Resource temporarily unavailable
- Third-party API failures

**Decision:**
```javascript
// Unrecoverable → Let it crash
if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is required');
}

// Recoverable → Handle gracefully
try {
  const data = await fetchFromAPI();
} catch (error) {
  if (error.code === 'TIMEOUT') {
    return fallbackData;
  }
  throw error; // Re-throw if unexpected
}
```

### Step 3: Fail-Fast Pattern

**When to use:**
- Configuration errors on startup
- Programmer errors (bugs)
- Invalid state that can't be recovered
- Security violations

**How:**
```javascript
// Example: Fail fast on startup
function validateConfig() {
  if (!process.env.DATABASE_URL) {
    console.error('FATAL: DATABASE_URL not set');
    process.exit(1);
  }
  if (!process.env.API_KEY) {
    console.error('FATAL: API_KEY not set');
    process.exit(1);
  }
}

validateConfig(); // Run before starting server

// Example: Fail fast on invalid state
function processOrder(order) {
  if (!order || !order.id) {
    throw new Error('Invalid order: missing id');
  }
  // Process order
}
```

**Why fail fast:**
- Bugs surface immediately (not hidden)
- Clear error messages (not mysterious failures)
- Prevents cascading failures
- Easier to debug (fails at root cause)

### Step 4: Retry Pattern

**When to use:**
- Transient network failures
- Rate limiting (with backoff)
- Temporary resource unavailability
- Idempotent operations

**When NOT to use:**
- Non-idempotent operations (e.g., charging credit card)
- Permanent failures (404, 401, validation errors)
- Operations with side effects

**Exponential backoff with jitter:**

```javascript
async function retryWithBackoff(fn, options = {}) {
  const {
    maxRetries = 3,
    initialDelayMs = 1000,
    maxDelayMs = 10000,
    factor = 2,
  } = options;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      // Don't retry on permanent errors
      if (error.statusCode === 404 || error.statusCode === 400) {
        throw error;
      }

      // Last attempt, give up
      if (attempt === maxRetries) {
        throw new Error(`Failed after ${maxRetries} retries: ${error.message}`);
      }

      // Calculate delay with exponential backoff and jitter
      const delay = Math.min(
        initialDelayMs * Math.pow(factor, attempt),
        maxDelayMs
      );
      const jitter = delay * 0.1 * Math.random();
      const totalDelay = delay + jitter;

      console.warn(`Retry attempt ${attempt + 1} after ${totalDelay}ms`);
      await sleep(totalDelay);
    }
  }
}

// Usage
const data = await retryWithBackoff(() => fetchFromAPI(), {
  maxRetries: 5,
  initialDelayMs: 1000,
});
```

**Retry rules:**
- ✅ Exponential backoff (1s, 2s, 4s, 8s, ...)
- ✅ Add jitter (prevent thundering herd)
- ✅ Max delay cap (don't wait hours)
- ✅ Max retry count (eventually give up)
- ❌ Don't retry non-idempotent operations
- ❌ Don't retry permanent errors (400, 404)

### Step 5: Graceful Degradation

**When to use:**
- Non-critical features
- Optional enhancements
- Features with acceptable fallbacks

**Patterns:**

**Pattern 1: Fallback value**
```javascript
async function getUserPreferences(userId) {
  try {
    return await db.getUserPreferences(userId);
  } catch (error) {
    console.warn(`Failed to load preferences: ${error.message}`);
    return DEFAULT_PREFERENCES; // Fallback
  }
}
```

**Pattern 2: Feature flag fallback**
```javascript
async function enhanceWithAI(text) {
  if (!AI_FEATURE_ENABLED) {
    return text; // Gracefully degrade
  }

  try {
    return await aiService.enhance(text);
  } catch (error) {
    console.warn(`AI enhancement failed: ${error.message}`);
    return text; // Fallback to original
  }
}
```

**Pattern 3: Partial failure**
```javascript
async function fetchDashboardData() {
  const [users, orders, analytics] = await Promise.allSettled([
    fetchUsers(),
    fetchOrders(),
    fetchAnalytics(),
  ]);

  return {
    users: users.status === 'fulfilled' ? users.value : [],
    orders: orders.status === 'fulfilled' ? orders.value : [],
    analytics: analytics.status === 'fulfilled' ? analytics.value : null,
  };
}
```

### Step 6: Error Boundaries (React Example)

**Component-level error isolation:**

```typescript
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Caught error:', error, errorInfo);
    // Send to error tracking (Sentry, etc.)
    trackError(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <button onClick={() => this.setState({ hasError: false })}>
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Usage: Wrap risky components
<ErrorBoundary>
  <RiskyComponent />
</ErrorBoundary>
```

### Step 7: User-Facing Error Messages

**Good error messages:**
- ✅ Explain what went wrong
- ✅ Tell user what to do next
- ✅ Avoid technical jargon
- ✅ Include request ID for support

**Bad error messages:**
- ❌ Generic: "An error occurred"
- ❌ Technical: "500 Internal Server Error"
- ❌ No action: "Failed"

**Examples:**

```javascript
// Bad
throw new Error('Invalid input');

// Good
throw new Error('Email address is invalid. Please use format: user@example.com');

// Bad
return { error: 'Database error' };

// Good
return {
  error: {
    message: 'We couldn\'t save your changes. Please try again in a moment.',
    code: 'DATABASE_UNAVAILABLE',
    retryAfter: 5, // seconds
    requestId: 'req_abc123',
  }
};

// Bad
console.error('Error');

// Good
console.error({
  message: 'Failed to fetch user data',
  userId: userId,
  endpoint: '/api/users',
  statusCode: response.status,
  requestId: response.headers.get('X-Request-ID'),
  timestamp: new Date().toISOString(),
  stack: error.stack,
});
```

### Step 8: Logging with Context

**Always log errors with context:**

```javascript
try {
  await processOrder(order);
} catch (error) {
  console.error({
    message: 'Order processing failed',
    error: error.message,
    stack: error.stack,
    orderId: order.id,
    userId: order.userId,
    orderTotal: order.total,
    timestamp: new Date().toISOString(),
    requestId: req.id,
  });

  // Re-throw or handle
  throw error;
}
```

**Context to include:**
- Input parameters
- Current state
- Request/trace ID
- Timestamp
- Stack trace
- Error type/code

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Swallowing errors | Silent failures, hard to debug | Log errors, re-throw if needed |
| Generic error messages | User can't take action | Specific, actionable messages |
| Retrying non-idempotent ops | Duplicate charges, double emails | Only retry safe operations |
| Infinite retries | Never gives up, wastes resources | Max retry count and timeout |
| No exponential backoff | Thundering herd, overwhelms server | Exponential backoff with jitter |
| Catching all errors blindly | Masks bugs, hides real issues | Only catch expected errors |
| No logging context | Can't reproduce or debug | Log inputs, state, request ID |
| Failing entire request on partial failure | All-or-nothing, poor UX | Graceful degradation, partial success |

## Rationalization Counters

**"I'll add error handling later"** → Later never comes. Errors happen in production immediately. Handle them now.

**"Just catch and log, it's fine"** → Catching and logging isn't handling. Decide: retry, degrade, or fail. Logging alone helps no one.

**"Users don't need details"** → Generic errors frustrate users. "Something went wrong" is useless. Tell them what and how to fix.

**"Retry everything, it'll work eventually"** → Non-idempotent retries cause duplicates. Permanent errors never succeed. Be selective.

**"Error handling adds too much code"** → Unhandled errors add outages, angry users, and 3am debugging. Error handling is core logic, not optional.

**"This won't fail in production"** → Famous last words. Everything fails in production. Plan for failure.

## Decision Guide: Which Pattern to Use?

**Startup/Configuration errors:**
- ✅ Fail fast (exit immediately)

**Network requests (idempotent):**
- ✅ Retry with exponential backoff

**Network requests (non-idempotent):**
- ❌ Don't auto-retry
- ✅ Return error, let user retry

**Non-critical features:**
- ✅ Graceful degradation with fallback

**Critical operations (payment, data integrity):**
- ✅ Fail fast, alert, require manual intervention

**User input validation:**
- ✅ Return specific error message
- ❌ Don't retry or degrade

**Third-party API failures:**
- ✅ Retry if transient (503, timeout)
- ✅ Degrade if optional feature
- ✅ Fail if critical dependency

## Error Handling by Layer

### API Layer (Express example)
```javascript
// Global error handler
app.use((error, req, res, next) => {
  // Log with context
  console.error({
    error: error.message,
    stack: error.stack,
    path: req.path,
    method: req.method,
    userId: req.user?.id,
    requestId: req.id,
  });

  // User-facing response
  res.status(error.statusCode || 500).json({
    error: {
      message: error.userMessage || 'An unexpected error occurred',
      code: error.code || 'INTERNAL_ERROR',
      requestId: req.id,
    },
  });
});
```

### Service Layer
```javascript
class UserService {
  async getUser(userId) {
    try {
      return await this.db.users.findById(userId);
    } catch (error) {
      if (error.code === 'NOT_FOUND') {
        throw new NotFoundError(`User ${userId} not found`);
      }
      throw new ServiceError('Failed to fetch user', { cause: error });
    }
  }
}
```

### Database Layer
```javascript
async function queryWithRetry(query, params) {
  return retryWithBackoff(
    () => db.query(query, params),
    {
      maxRetries: 3,
      shouldRetry: (error) => error.code === 'CONNECTION_ERROR',
    }
  );
}
```

## Integration with Existing Workflows

**With TDD:**
- Write tests for error scenarios
- Test retry logic
- Test graceful degradation fallbacks

**With monitoring:**
- Send errors to error tracking (Sentry, Rollbar)
- Set up alerts for critical errors
- Track error rates in metrics

**With APIs:**
- Document error responses in OpenAPI
- Include error codes and messages
- Provide retry guidance

## Real-World Impact

**Without this skill:**
- Silent failures (errors swallowed)
- Mysterious production issues (no context logged)
- Thundering herd (no backoff on retries)
- Duplicate charges (retrying non-idempotent ops)
- Frustrated users ("An error occurred")

**With this skill:**
- Fast failure on bugs (easy debugging)
- Resilient systems (smart retries)
- Graceful degradation (partial failures OK)
- Clear error messages (users know what to do)
- Rich logs (easy debugging with context)

## Required Background

None. This skill is self-contained.

## Cross-References

- Use `superpowers:systematic-debugging` when debugging error scenarios
- Use `superpowers:test-driven-development` to test error paths
- Use `superpowers:api-design-review` for API error design
