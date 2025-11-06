---
name: refactoring-safety
description: Use when restructuring code without changing behavior - ensures test coverage baseline, incremental steps, behavior preservation, and separation of refactoring from feature work to prevent regressions
---

# Refactoring Safety

## Overview

Systematic approach to code restructuring that preserves behavior through disciplined incremental steps, comprehensive testing, and verification at each stage.

## When to Use

Use this skill when:
- Restructuring code for better design
- Renaming classes, functions, or variables
- Extracting functions or classes
- Moving code between files or modules
- Simplifying complex logic
- Removing duplication

**Symptoms that trigger this skill:**
- "Refactor the..."
- "Clean up this code..."
- "Rename X to Y..."
- "Extract this into..."
- "Simplify this..."
- "Remove duplication..."

**Don't use when:**
- Adding new features (use TDD)
- Fixing bugs (use systematic-debugging)
- Making behavior changes (not refactoring)

## Core Principle

**Refactoring ≠ Rewriting. Refactoring = Same behavior, better structure.**

If behavior changes, it's not refactoring—it's a feature or bug fix. Keep them separate.

## Quick Reference: Refactoring Safety Checklist

Use TodoWrite for ALL items below when refactoring:

| Phase | Action | Verification |
|-------|--------|--------------|
| **Before** | Run tests, establish baseline coverage | All tests pass, coverage measured |
| **Extract** | Extract small chunks (1 function/class at a time) | Tests still pass |
| **Rename** | Rename after extraction settled | Tests still pass |
| **Verify** | Run full test suite after EACH step | Tests pass, behavior unchanged |
| **Commit** | Commit after each successful step | Small, focused commits |

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Run full test suite - establish baseline (all tests must pass)
☐ Measure test coverage for code being refactored (target: >80%)
☐ If coverage <80%, add characterization tests first
☐ Plan refactoring steps (1 change per step)
☐ For each step:
  ☐ Make ONE small change
  ☐ Run full test suite
  ☐ Verify behavior unchanged
  ☐ Commit with descriptive message
☐ Final verification: Run full test suite + manual smoke test
☐ Update documentation if needed
```

### Step 2: Establish Safety Baseline

**Before touching ANY code:**

```bash
# 1. Run tests - ALL must pass
npm test              # or pytest, go test, etc.

# 2. Measure coverage
npm run coverage      # Should be >80% for refactoring target

# 3. If coverage too low, add tests FIRST
# Use characterization tests to capture current behavior
```

**Red flag:** If tests are failing or coverage <80%, STOP. Fix tests first, then refactor.

**Why:** Refactoring without tests = flying blind. You can't detect regressions.

### Step 3: Incremental Refactoring Steps

**The safe refactoring cycle:**

```
1. Make ONE small change
2. Run tests
3. If tests pass → commit
4. If tests fail → revert, investigate
5. Repeat
```

**What counts as "one small change":**
- ✅ Extract one function
- ✅ Rename one variable
- ✅ Move one function to different file
- ✅ Inline one variable
- ✅ Extract one class

**Too big (split into smaller steps):**
- ❌ Extract multiple functions at once
- ❌ Extract + rename in same step
- ❌ Move + modify logic in same step
- ❌ Refactor entire module at once

### Step 4: Extract First, Rename Second

**Pattern for safe refactoring:**

**Step 1: Extract with ugly name**
```javascript
// Before
function processUser(user) {
  // 50 lines of mixed concerns
  if (user.isActive) {
    // 15 lines of validation
  }
  // 20 lines of database logic
  // 15 lines of notification logic
}

// After Step 1: Extract with descriptive name
function processUser(user) {
  validateActiveUser(user);
  saveUserToDatabase(user);
  sendNotifications(user);
}
```

**✅ Run tests → commit "Extract validation, DB, notifications into separate functions"**

**Step 2: Rename if needed**
```javascript
// After Step 2: Better names if needed
function processUser(user) {
  validateUserIsActive(user);      // Renamed for clarity
  persistUser(user);               // Renamed for consistency
  notifyUserActivation(user);      // Renamed for specificity
}
```

**✅ Run tests → commit "Rename extracted functions for clarity"**

**Why separate:** If renaming breaks something, you know it was the rename, not the extraction.

### Step 5: Behavior Preservation Verification

**After EVERY change, verify:**

```bash
# Run full test suite
npm test

# Check specific test coverage
npm run coverage -- path/to/refactored/file.ts

# Manual smoke test if critical path
# (Don't rely only on automated tests for critical business logic)
```

**Red flags that behavior changed:**
- Tests that were passing now fail
- Tests that were failing now pass
- Code coverage decreased
- Different output for same input

**If behavior changed accidentally:**
1. Revert the change immediately
2. Investigate what went wrong
3. Make smaller change
4. Try again

### Step 6: Commit Strategy

**Commit after each successful step:**

```bash
# Good commits (atomic, focused)
git commit -m "Extract user validation into separate function"
git commit -m "Extract database save logic"
git commit -m "Extract notification logic"
git commit -m "Rename extracted functions for clarity"

# Bad commits (too big, mixed concerns)
git commit -m "Refactor user processing"  # Too vague, too big
git commit -m "Extract and rename functions, fix bug"  # Mixed refactor + fix
```

**Why:** Small commits make it easy to revert specific changes if something breaks.

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Refactor without tests | Can't detect regressions | Add tests first, then refactor |
| Big-bang refactor | Too many changes, hard to debug failures | One small change at a time |
| Extract + rename simultaneously | Can't tell which change caused failure | Extract first, rename second |
| Refactor + add features | Mixed concerns, hard to review | Separate refactoring from features |
| Skip verification between steps | Regressions compound, harder to debug | Test after EVERY change |
| Commit too rarely | Hard to revert specific changes | Commit after each successful step |
| Refactor complex code with low coverage | Risky, likely to break | Add characterization tests first |
| Change behavior "while I'm here" | No longer refactoring | Keep refactoring pure, add features separately |

## Rationalization Counters

**"Tests slow me down"** → Tests are the only way to know you didn't break something. Without them, you're not refactoring—you're gambling.

**"I'll refactor everything at once, then test"** → When tests fail, you won't know which of 50 changes caused it. Incremental testing finds issues immediately.

**"This is just a rename, tests aren't needed"** → Renames break things all the time (dynamic calls, reflections, serialization). Run tests.

**"I'll add tests after refactoring"** → Then it's not refactoring, it's rewriting. You have no baseline to verify behavior preservation.

**"The change is small, I don't need to commit"** → Small changes compound. One breaks tests, you don't know which. Commit each step.

**"I'll fix this bug while refactoring"** → Now you can't tell if tests fail due to refactoring or the bug fix. Keep them separate.

**"Coverage is fine at 60%"** → 60% means 40% of code is untested. That 40% WILL break when refactored. Get to 80%+ first.

## Extract Patterns (Common Refactorings)

### Pattern 1: Extract Function

```javascript
// Before
function calculateOrder(items) {
  let total = 0;
  for (let item of items) {
    total += item.price * item.quantity;
  }

  let discount = 0;
  if (total > 100) {
    discount = total * 0.1;
  }

  let tax = (total - discount) * 0.08;

  return total - discount + tax;
}

// After (3 commits)
function calculateOrder(items) {
  const subtotal = calculateSubtotal(items);
  const discount = calculateDiscount(subtotal);
  const tax = calculateTax(subtotal, discount);
  return subtotal - discount + tax;
}

function calculateSubtotal(items) {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

function calculateDiscount(subtotal) {
  return subtotal > 100 ? subtotal * 0.1 : 0;
}

function calculateTax(subtotal, discount) {
  return (subtotal - discount) * 0.08;
}
```

### Pattern 2: Extract Class

```javascript
// Before
class Order {
  constructor(items, customerEmail) {
    this.items = items;
    this.customerEmail = customerEmail;
  }

  sendConfirmation() {
    // 30 lines of email logic
  }
}

// After (2 commits)
class Order {
  constructor(items, customerEmail) {
    this.items = items;
    this.emailService = new EmailService(customerEmail);
  }

  sendConfirmation() {
    this.emailService.sendOrderConfirmation(this.items);
  }
}

class EmailService {
  constructor(email) {
    this.email = email;
  }

  sendOrderConfirmation(items) {
    // 30 lines of email logic
  }
}
```

## Integration with Existing Workflows

**With TDD:**
- Tests already exist (from TDD)
- Refactor between RED and GREEN phases
- Or refactor after GREEN (REFACTOR phase)

**With code review:**
- Separate refactoring PRs from feature PRs
- Small, focused refactoring PRs are easy to review
- Verify tests pass in CI

**With debugging:**
- Don't refactor while debugging
- Fix bug first, commit
- Then refactor, commit separately

## Real-World Impact

**Without this skill:**
- Big-bang refactors break production
- Can't tell which change caused regression
- Refactoring + features mixed (hard to review)
- Regressions discovered weeks later
- Team fears refactoring ("if it works, don't touch it")

**With this skill:**
- Safe, incremental refactors
- Immediate feedback on regressions
- Clean separation of concerns
- Confidence to improve code regularly
- Codebase evolves without fear

## Required Background

**Recommended:**
- `superpowers:test-driven-development` - Ensures test coverage exists
- `superpowers:verification-before-completion` - Validates final state

## Cross-References

- Use `superpowers:test-driven-development` to ensure test coverage before refactoring
- Use `superpowers:verification-before-completion` after refactoring to verify
- Use `superpowers:systematic-debugging` if refactoring causes unexpected failures
