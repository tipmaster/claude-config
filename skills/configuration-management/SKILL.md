---
name: configuration-management
description: Use when adding/modifying config files, environment variables, or secrets - validates secret detection, environment-specific configs, drift detection, and prevents credential leaks through systematic pre-commit validation
---

# Configuration Management

## Overview

Systematic validation of configuration and secrets to prevent credential leaks, environment mismatches, and configuration drift between development, staging, and production.

## When to Use

Use this skill when:
- Adding or modifying `.env` files
- Creating config files (JSON, YAML, TOML, etc.)
- Adding environment variables
- Storing API keys, tokens, or credentials
- Deploying to new environments
- Debugging environment-specific issues

**Symptoms that trigger this skill:**
- "Add API key..."
- "Configure database..."
- "Set up environment..."
- Files named `.env*`, `config.*`, `secrets.*`, `*.config.js`
- Working with process.env, os.environ, or config libraries
- Before committing any file that might contain secrets

**Don't use when:**
- Reading config (only for adding/modifying)
- Application code that uses config
- Non-sensitive config (UI themes, feature flags)

## Quick Reference: Config Safety Checklist

Use TodoWrite for ALL items below when managing config:

| Category | Validation | Critical Issues |
|----------|-----------|-----------------|
| **Secret Detection** | Scan for keys, tokens, passwords, certificates | Credentials in code/config |
| **Environment Separation** | Dev/staging/prod configs separate | Prod credentials in dev |
| **Config Drift** | Compare environments, detect missing vars | Different configs per env |
| **Documentation** | .env.example, README setup instructions | Missing setup docs |
| **Version Control** | .gitignore for secrets, committed examples | Secrets in git history |
| **Validation** | Required vars, type checking, ranges | Missing required config |

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Scan for secrets in staged files (API keys, tokens, passwords)
☐ Verify .gitignore includes secret files (.env, credentials.*, *.key, *.pem)
☐ Verify .env.example exists with placeholder values
☐ Document all required environment variables in README
☐ Validate environment-specific configs (dev/staging/prod separate)
☐ Check for hardcoded secrets in code (grep for common patterns)
☐ Validate config schema (required fields, types, ranges)
☐ Test config loading in isolation
☐ Verify feature flags have safe defaults
☐ Check for config drift between environments
```

### Step 2: Secret Detection (Pre-Commit)

**Run before EVERY commit:**

```bash
# Check staged files for secrets
git diff --cached --name-only | xargs grep -E "(api[_-]?key|password|secret|token|private[_-]?key|aws[_-]?access)" -i

# Check for common secret patterns
grep -r "sk-[a-zA-Z0-9]{32,}" .  # OpenAI keys
grep -r "ghp_[a-zA-Z0-9]{36}" .  # GitHub tokens
grep -r "AKIA[A-Z0-9]{16}" .     # AWS access keys
grep -r "\"password\":\s*\"[^{]" . # Hardcoded passwords
```

**Red flags:**
- ❌ `API_KEY=sk-abc123...` in code
- ❌ `const password = "mypassword"` in code
- ❌ `aws_access_key=AKIA...` in committed file
- ❌ Private keys (.pem, .key files) in git

**Fix:** Use environment variables or secret management service.

### Step 3: .gitignore for Secrets

**Required .gitignore entries:**

```gitignore
# Environment files
.env
.env.local
.env.*.local

# Secrets and credentials
secrets/
credentials.json
*.key
*.pem
*.p12
*.pfx

# Cloud provider credentials
.aws/credentials
.gcloud/
.azure/

# Database dumps (might contain sensitive data)
*.sql
*.dump
```

**Verify .gitignore:**
```bash
# Test that .env is ignored
echo "TEST_SECRET=abc123" >> .env
git status  # Should NOT show .env as changed
```

### Step 4: .env.example Pattern

**Always provide .env.example:**

```bash
# .env.example (committed to git)
# Copy to .env and fill in real values

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# API Keys
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_test_...

# Feature Flags
ENABLE_BETA_FEATURES=false

# Optional with defaults
LOG_LEVEL=info
PORT=3000
```

**Rules:**
- ✅ Commit .env.example (with placeholders)
- ✅ Never commit .env (with real values)
- ✅ Document format and examples
- ❌ Don't use real values in examples
- ❌ Don't commit .env files

### Step 5: Environment-Specific Configs

**Structure for multiple environments:**

```
config/
  default.js       # Defaults for all environments
  development.js   # Dev overrides
  staging.js       # Staging overrides
  production.js    # Production overrides
```

**Load based on NODE_ENV:**

```javascript
// config/index.js
const env = process.env.NODE_ENV || 'development';
const defaultConfig = require('./default');
const envConfig = require(`./${env}`);

module.exports = { ...defaultConfig, ...envConfig };
```

**Rules:**
- ✅ Separate config per environment
- ✅ Use environment variables for secrets
- ✅ Validate required vars on startup
- ❌ Don't mix dev and prod configs
- ❌ Don't use prod credentials in dev

### Step 6: Config Validation on Startup

**Validate config immediately on app start:**

```javascript
// validateConfig.js
function validateConfig() {
  const required = [
    'DATABASE_URL',
    'API_KEY',
    'JWT_SECRET'
  ];

  const missing = required.filter(key => !process.env[key]);

  if (missing.length > 0) {
    console.error(`Missing required environment variables: ${missing.join(', ')}`);
    console.error('Copy .env.example to .env and fill in values');
    process.exit(1);
  }

  // Type validation
  const port = parseInt(process.env.PORT);
  if (isNaN(port) || port < 1 || port > 65535) {
    console.error('PORT must be a valid port number (1-65535)');
    process.exit(1);
  }
}

// Run validation before starting app
validateConfig();
```

**Why:** Fail fast on missing/invalid config instead of mysterious runtime errors.

### Step 7: Config Drift Detection

**Check for drift between environments:**

```bash
# Compare staging and prod configs
diff config/staging.js config/production.js

# Check for missing env vars
# In staging:
echo $DATABASE_URL, $API_KEY

# In prod:
ssh prod "echo \$DATABASE_URL, \$API_KEY"
```

**Common drift issues:**
- Feature flag enabled in prod but not staging (can't test)
- Different database connection params (staging hits prod DB)
- Missing env vars in prod (runtime errors)
- Different API versions between environments

### Step 8: Document Required Config

**In README.md:**

```markdown
## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in required values:

| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://user:pass@localhost:5432/db |
| API_KEY | OpenAI API key | sk-... |
| JWT_SECRET | Secret for JWT signing (32+ random chars) | generate with `openssl rand -hex 32` |

3. Optional variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| PORT | 3000 | Server port |
| LOG_LEVEL | info | Log level (debug, info, warn, error) |
```

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Commit .env with secrets | Credentials exposed in git history | Add .env to .gitignore, use .env.example |
| Hardcode API keys in code | Secrets in version control | Use environment variables |
| Same config for dev and prod | Accidental prod data modification | Separate configs per environment |
| No config validation on startup | Runtime errors, hard to debug | Validate required vars immediately |
| Missing .env.example | New devs can't set up project | Provide example with placeholders |
| Prod credentials in dev | Security risk, accidental prod changes | Use test/fake credentials in dev |
| No documentation for config | Devs don't know what vars needed | Document all required vars in README |
| Config drift between environments | Staging doesn't match prod, surprises | Regularly audit configs, use IaC |

## Rationalization Counters

**"I'll add .gitignore later"** → Later is too late. Secrets in git history are permanent. Add .gitignore before first commit.

**"This is just a test API key"** → Test keys get copy-pasted into prod. Treat all keys as sensitive. Use proper env var management from day 1.

**"I'll remember to change it before deploy"** → You won't. Use environment-specific configs so you can't accidentally deploy dev config to prod.

**"Config validation is overkill"** → Missing env var = cryptic runtime error at 2am. Fail fast on startup is better.

**"Documentation slows me down"** → Undocumented config = every new dev asks you "what env vars do I need?" Document once, save hours.

**"Drift is fine, they're almost the same"** → "Almost" = surprises in prod. Staging should mirror prod exactly.

## Secret Management Best Practices

**For local development:**
- ✅ Use .env files (not committed)
- ✅ Use test/fake credentials when possible
- ✅ Provide .env.example with placeholders

**For CI/CD:**
- ✅ Use CI secret storage (GitHub Secrets, CircleCI, etc.)
- ✅ Inject secrets as env vars at runtime
- ❌ Don't commit secrets to CI config files

**For production:**
- ✅ Use secret management service (AWS Secrets Manager, HashiCorp Vault)
- ✅ Rotate secrets regularly
- ✅ Use least-privilege access (separate keys per service)
- ❌ Don't hardcode secrets anywhere

**For third-party services:**
- ✅ Use separate API keys per environment (dev/staging/prod)
- ✅ Use restricted keys (e.g., read-only for analytics)
- ✅ Document which services need which keys

## Feature Flag Configuration

**Safe feature flag defaults:**

```javascript
// config.js
module.exports = {
  features: {
    // New features: default OFF
    betaFeature: process.env.ENABLE_BETA === 'true',

    // Stable features: default ON
    stableFeature: process.env.DISABLE_STABLE !== 'true',

    // Dangerous features: require explicit enable
    dangerousFeature: process.env.ENABLE_DANGEROUS === 'true' && process.env.I_KNOW_WHAT_IM_DOING === 'true'
  }
};
```

**Rules:**
- ✅ New features default OFF
- ✅ Require explicit enable for dangerous features
- ✅ Document feature flags in .env.example
- ❌ Don't default new features ON in prod

## Integration with Existing Workflows

**With git workflow:**
- Run secret detection as pre-commit hook
- Verify .gitignore before first commit
- Review config changes carefully in PRs

**With deployment:**
- Validate config in CI before deploy
- Compare staging and prod configs
- Test with prod-like config in staging

**With onboarding:**
- New devs copy .env.example to .env
- README documents required setup
- Config validation fails fast with helpful error

## Real-World Impact

**Without this skill:**
- API keys committed to git (security breach)
- Prod credentials used in dev (accidental prod changes)
- Missing env vars cause runtime errors (hard to debug)
- Config drift causes prod-only bugs
- New devs struggle with setup

**With this skill:**
- Secrets never committed (secure by default)
- Environment separation (safe dev/staging/prod)
- Fast feedback on config issues (fail on startup)
- No surprises from config drift
- Easy onboarding (documented setup)

## Required Background

None. This skill is self-contained.

## Cross-References

- Use `superpowers:verification-before-completion` to verify config before commit
- Use `superpowers:systematic-debugging` for config-related bugs
