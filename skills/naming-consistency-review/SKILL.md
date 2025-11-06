---
name: naming-consistency-review
description: Use when writing/reviewing code, renaming identifiers, or establishing codebase conventions - validates naming consistency, terminology alignment, and convention adherence to improve readability and maintainability
---

# Naming Consistency Review

## Overview

Systematic validation of naming conventions and terminology to ensure codebase readability, consistency, and maintainability through clear, predictable naming patterns.

## When to Use

Use this skill when:
- Writing new code (functions, classes, variables)
- Renaming existing identifiers
- Reviewing pull requests
- Establishing coding standards
- Onboarding new team members
- Refactoring modules

**Symptoms that trigger this skill:**
- "Add function/class/variable..."
- "Rename X to Y..."
- Code review time
- Inconsistent naming noticed
- Before committing new code

**Don't use when:**
- Third-party code you don't control
- Generated code (protobuf, GraphQL schemas)
- Temporary/throwaway code

## Quick Reference: Naming Conventions

Use TodoWrite for ALL items below when reviewing naming:

| Element | Convention | Good Examples | Bad Examples |
|---------|-----------|---------------|--------------|
| **Functions** | camelCase, verb + noun | `getUserById`, `calculateTotal` | `get_user`, `user`, `do_thing` |
| **Classes** | PascalCase, noun | `UserService`, `OrderProcessor` | `userService`, `processOrder` |
| **Variables** | camelCase, noun | `userId`, `totalAmount` | `user_id`, `x`, `temp` |
| **Constants** | UPPER_SNAKE_CASE | `MAX_RETRIES`, `API_KEY` | `maxRetries`, `apiKey` |
| **Files** | kebab-case or camelCase | `user-service.ts`, `userService.ts` | `UserService.ts`, `user_service.ts` |
| **Booleans** | is/has/can prefix | `isActive`, `hasPermission`, `canEdit` | `active`, `permission`, `edit` |

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Check function names (verb + noun, camelCase)
☐ Check class names (PascalCase, noun)
☐ Check variable names (camelCase, descriptive)
☐ Check constant names (UPPER_SNAKE_CASE)
☐ Check boolean names (is/has/can prefix)
☐ Check terminology consistency (same concept = same word)
☐ Check abbreviation usage (avoid unless standard)
☐ Check file naming consistency
☐ Search for similar names in codebase (grep/search)
☐ Update naming dictionary if new terms introduced
```

### Step 2: Function Naming

**Pattern: verb + noun**

```javascript
// Good: Clear action and target
✅ getUserById(id)
✅ calculateTotalPrice(items)
✅ sendEmailNotification(user)
✅ validateUserInput(input)
✅ formatDateString(date)

// Bad: Missing verb or noun
❌ user(id)           // Missing verb
❌ get(id)            // Missing noun (get what?)
❌ do_calculation()   // Wrong case, vague
❌ handleStuff()      // Vague noun
❌ x()                // Meaningless
```

**Common verbs:**
- Data access: `get`, `fetch`, `find`, `load`
- Data modification: `create`, `update`, `delete`, `save`
- Validation: `validate`, `check`, `verify`, `ensure`
- Transformation: `format`, `transform`, `convert`, `parse`
- Computation: `calculate`, `compute`, `generate`, `build`
- Communication: `send`, `receive`, `request`, `notify`

### Step 3: Class Naming

**Pattern: PascalCase noun (singular)**

```typescript
// Good: Clear responsibility
✅ class UserService { }
✅ class OrderProcessor { }
✅ class EmailValidator { }
✅ class DatabaseConnection { }
✅ class PaymentGateway { }

// Bad: Wrong case, plural, vague
❌ class userService { }        // Wrong case
❌ class Users { }              // Plural (unless collection)
❌ class Process { }            // Too vague
❌ class Helper { }             // Meaningless suffix
❌ class Manager { }            // Vague suffix
```

**Common suffixes (use sparingly):**
- `-Service`: Business logic layer
- `-Controller`: Request handling
- `-Repository`: Data access
- `-Factory`: Object creation
- `-Validator`: Input validation
- `-Processor`: Data processing

**Avoid meaningless suffixes:**
- ❌ `-Helper`, `-Manager`, `-Handler`, `-Utils` (too vague)

### Step 4: Variable Naming

**Pattern: camelCase noun (descriptive)**

```javascript
// Good: Clear purpose
✅ const userId = user.id;
✅ const totalAmount = items.reduce(...);
✅ const isAuthenticated = checkAuth();
✅ const errorMessage = "Invalid input";
✅ const maxRetryCount = 3;

// Bad: Abbreviations, single letters, vague
❌ const uid = user.id;           // Unclear abbreviation
❌ const x = user.id;             // Meaningless
❌ const temp = calculate();      // Vague
❌ const data = fetch();          // Too generic
❌ const result = process();      // Vague
```

**Length guidelines:**
- Scope < 10 lines: 1-2 words OK (`user`, `item`)
- Scope > 10 lines: 2-3 words (`userProfile`, `orderItems`)
- Loop variables: `i`, `j`, `k` acceptable for simple loops
- Iterator variables: descriptive (`user`, `order`, not `u`, `o`)

### Step 5: Boolean Naming

**Pattern: is/has/can/should prefix**

```javascript
// Good: Clear boolean intent
✅ const isActive = user.status === 'active';
✅ const hasPermission = checkPermission(user);
✅ const canEdit = user.role === 'editor';
✅ const shouldRetry = errorCode === 'TIMEOUT';
✅ const wasSuccessful = response.ok;

// Bad: Ambiguous or negative
❌ const active = user.status === 'active';     // Could be string
❌ const permission = check();                  // Could be object
❌ const notActive = !user.isActive;           // Double negative
❌ const disabled = !enabled;                   // Use isEnabled instead
```

**Avoid negative booleans:**
```javascript
// Bad: Confusing
❌ if (!isNotActive) { ... }   // Double negative

// Good: Positive booleans
✅ if (isActive) { ... }
```

### Step 6: Terminology Consistency

**Same concept = Same word everywhere**

**Example: User identification**

```javascript
// Bad: Inconsistent terms for same concept
❌ getUserById(userId)
❌ findUserByIdentifier(identifier)
❌ loadUserByID(id)
❌ fetchUserByUid(uid)

// Good: Consistent term
✅ getUserById(userId)
✅ findUserById(userId)
✅ loadUserById(userId)
✅ updateUserById(userId)
```

**Create terminology dictionary:**

| Concept | Standard Term | Avoid |
|---------|--------------|-------|
| User identifier | `userId` | `uid`, `id`, `user_id`, `identifier` |
| Order identifier | `orderId` | `orderNumber`, `order_id`, `orderRef` |
| Email address | `email` | `emailAddress`, `mail`, `e_mail` |
| Authentication | `auth`, `authenticate` | `login`, `signin`, `logon` |
| Authorization | `authorize`, `permission` | `access`, `rights`, `auth` |
| Create | `create` | `add`, `insert`, `new` |
| Retrieve | `get`, `find` | `load`, `fetch`, `retrieve` |
| Update | `update` | `modify`, `change`, `edit` |
| Delete | `delete` | `remove`, `destroy`, `drop` |

### Step 7: Abbreviations

**Avoid abbreviations unless standard**

```javascript
// Bad: Unclear abbreviations
❌ const usr = getUsr();
❌ const msg = "Hello";
❌ const btn = document.querySelector('button');
❌ const qty = item.quantity;
❌ const amt = calculateAmt();

// Good: Full words or standard abbreviations
✅ const user = getUser();
✅ const message = "Hello";
✅ const button = document.querySelector('button');
✅ const quantity = item.quantity;
✅ const amount = calculateAmount();

// Acceptable standard abbreviations:
✅ const id = getId();       // Standard
✅ const url = getUrl();     // Standard
✅ const html = render();    // Standard
✅ const api = callApi();    // Standard
✅ const db = connect();     // Standard in context
```

**Standard abbreviations (generally acceptable):**
- `id`, `url`, `uri`, `html`, `css`, `js`
- `api`, `sdk`, `cli`, `ui`, `ux`
- `db`, `sql`, `orm`
- `http`, `https`, `tcp`, `udp`
- `max`, `min`, `avg` (in math contexts)

### Step 8: File Naming

**Be consistent across codebase:**

**Option 1: kebab-case (recommended for web)**
```
✅ user-service.ts
✅ order-processor.ts
✅ email-validator.ts
```

**Option 2: camelCase**
```
✅ userService.ts
✅ orderProcessor.ts
✅ emailValidator.ts
```

**Option 3: PascalCase (for classes)**
```
✅ UserService.ts
✅ OrderProcessor.ts
✅ EmailValidator.ts
```

**Pick ONE convention and stick to it.**

**Avoid:**
```
❌ user_service.ts    // snake_case (unless Python)
❌ UserService.js     // Mixing conventions
❌ userservice.ts     // No separation
```

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Single-letter variables outside loops | Meaningless, hard to search | Use descriptive names |
| Inconsistent terminology | Confusing, hard to understand | Pick one term per concept |
| Abbreviations everywhere | Hard to read, ambiguous | Use full words |
| Generic names (`data`, `temp`, `result`) | Too vague, no context | Be specific |
| Negative booleans (`isNotActive`) | Double negatives confuse | Use positive (`isActive`) |
| Class names with verbs (`ProcessUser`) | Classes are nouns | Use noun (`UserProcessor`) |
| Functions without verbs (`user(id)`) | Unclear action | Add verb (`getUser(id)`) |
| Mixed naming conventions | Inconsistent, hard to predict | Pick one convention |

## Rationalization Counters

**"Abbreviations save typing"** → You type code once, read it 100 times. Optimize for reading, not typing. IDEs autocomplete anyway.

**"This name is obvious in context"** → Context is lost when searching, reviewing, or debugging. Names should be clear in isolation.

**"I'll rename it later"** → Later never comes. Name it right now or it stays wrong forever.

**"Terminology consistency doesn't matter"** → Inconsistent terms waste mental energy. Is `userId` the same as `uid`? Readers shouldn't guess.

**"Single letters are fine for simple variables"** → `x`, `temp`, `data` are never descriptive. What does `x` mean in 6 months? Name it properly.

**"This is just a draft"** → Draft code becomes production code. Name it right from the start.

## Naming Patterns by Language

### JavaScript/TypeScript
```javascript
// Functions: camelCase
function getUserById(id) { }

// Classes: PascalCase
class UserService { }

// Variables: camelCase
const userId = 123;

// Constants: UPPER_SNAKE_CASE
const MAX_RETRIES = 3;

// Files: kebab-case or camelCase
// user-service.ts or userService.ts
```

### Python
```python
# Functions: snake_case
def get_user_by_id(id):
    pass

# Classes: PascalCase
class UserService:
    pass

# Variables: snake_case
user_id = 123

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3

# Files: snake_case
# user_service.py
```

### Go
```go
// Functions: camelCase (PascalCase if exported)
func getUserByID(id int) { }
func GetUserByID(id int) { } // Exported

// Types: PascalCase
type UserService struct { }

// Variables: camelCase
var userId = 123

// Constants: camelCase or UPPER_SNAKE_CASE
const MaxRetries = 3

// Files: snake_case
// user_service.go
```

## Integration with Existing Workflows

**When writing code:**
1. Check naming conventions before committing
2. Search codebase for similar concepts
3. Use consistent terminology

**When reviewing code:**
1. Check naming consistency
2. Flag unclear abbreviations
3. Suggest better names if needed

**When refactoring:**
1. Rename inconsistent identifiers
2. Update terminology dictionary
3. Use refactoring-safety skill for systematic renaming

## Real-World Impact

**Without this skill:**
- Codebase has `userId`, `user_id`, `uid`, `userIdentifier`
- Functions named `get()`, `fetch()`, `load()`, `retrieve()` for same action
- Variables named `x`, `temp`, `data` with no meaning
- Readers waste time deciphering abbreviations
- Searching is difficult (what term was used here?)

**With this skill:**
- Consistent terminology (`userId` everywhere)
- Predictable patterns (easy to guess names)
- Self-documenting code (names explain purpose)
- Easy searching (one term per concept)
- Fast onboarding (clear patterns)

## Required Background

None. This skill is self-contained.

## Cross-References

- Use `superpowers:refactoring-safety` when renaming identifiers
- Use `superpowers:requesting-code-review` to validate naming choices
