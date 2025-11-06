---
name: caching-strategy-review
description: Use when adding caching, optimizing performance, or debugging cache issues - validates invalidation strategies, TTL settings, key collision prevention, and memory management to prevent stale data and cache stampedes
---

# Caching Strategy Review

## Overview

Systematic validation of caching decisions to balance performance gains against complexity, ensuring cache correctness through proper invalidation, reasonable TTLs, and memory management.

## When to Use

Use this skill when:
- Adding caching to improve performance
- Debugging stale data issues
- Optimizing slow endpoints
- Reviewing cache-related code
- Planning cache architecture
- Experiencing cache-related bugs

**Symptoms that trigger this skill:**
- "Add caching for..."
- "Cache this data..."
- "Optimize performance..."
- Code using Redis, Memcached, in-memory caches
- Stale data reported by users
- High cache miss rates or memory issues

**Don't use when:**
- Simple memoization (pure functions)
- Caching already working correctly
- Performance isn't an issue

## Quick Reference: Caching Decision Tree

Use TodoWrite for ALL items below when implementing caching:

```
Should I cache this?
├─ Data changes rarely? → Yes, cache it
├─ Read-heavy workload? → Yes, cache it
├─ Expensive computation? → Yes, cache it
└─ Data changes frequently OR staleness unacceptable? → No, don't cache

If caching:
├─ Invalidation strategy defined? (TTL, event-based, manual)
├─ TTL reasonable? (not too short, not too long)
├─ Cache key collision prevented? (include version/context)
├─ Memory limits set? (prevent OOM)
└─ Cache stampede prevented? (locking, stale-while-revalidate)
```

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Validate caching is appropriate (read-heavy, expensive, rarely changes)
☐ Choose cache layer (application, CDN, database, browser)
☐ Define invalidation strategy (TTL, event-based, manual)
☐ Set reasonable TTL (balance staleness vs cache hits)
☐ Design cache keys (prevent collisions, include version)
☐ Implement cache stampede prevention (locking/stale-while-revalidate)
☐ Set memory limits (prevent OOM)
☐ Add cache hit/miss monitoring
☐ Test cache invalidation (verify staleness doesn't occur)
☐ Document caching behavior (TTLs, invalidation triggers)
```

### Step 2: Should You Cache?

**Cache when:**
- ✅ Data is read much more than written (90/10 read/write ratio)
- ✅ Data changes infrequently (hourly, daily, weekly)
- ✅ Computation is expensive (>100ms, complex queries, API calls)
- ✅ Staleness is acceptable (data doesn't need to be real-time)

**Don't cache when:**
- ❌ Data changes constantly (every request)
- ❌ Staleness is unacceptable (bank balances, inventory counts)
- ❌ Data is personalized per user (unless per-user cache)
- ❌ Memory overhead too high (data size × users)
- ❌ Operation is already fast (<10ms)

**Example analysis:**

```javascript
// Good candidate for caching:
// - Product catalog (changes hourly)
// - Read-heavy (thousands of views per product)
// - Expensive query (joins multiple tables)
async function getProductDetails(productId) {
  const cacheKey = `product:${productId}`;
  const cached = await cache.get(cacheKey);
  if (cached) return cached;

  const product = await db.products.findById(productId);
  await cache.set(cacheKey, product, { ttl: 3600 }); // 1 hour
  return product;
}

// Bad candidate for caching:
// - User's shopping cart (changes every add/remove)
// - Personalized per user
// - Staleness unacceptable
async function getShoppingCart(userId) {
  // Don't cache - query is fast, data changes frequently
  return await db.carts.findByUserId(userId);
}
```

### Step 3: Cache Invalidation Strategies

**Choose ONE strategy per cache:**

**1. Time-based (TTL) - Simplest**
```javascript
// Good for: Data with predictable staleness window
await cache.set(key, value, { ttl: 3600 }); // Expires after 1 hour
```

**Pros:**
- Simple to implement
- No invalidation logic needed
- Memory automatically cleaned up

**Cons:**
- Data can be stale for up to TTL duration
- No immediate invalidation on updates

**2. Event-based - Most accurate**
```javascript
// Invalidate when data changes
async function updateProduct(productId, updates) {
  await db.products.update(productId, updates);
  await cache.del(`product:${productId}`); // Invalidate immediately
}
```

**Pros:**
- Always fresh data after updates
- No unnecessary staleness

**Cons:**
- Must invalidate in every write path
- Easy to miss invalidation points
- Complex for multi-layer caches

**3. Write-through - Consistent**
```javascript
// Update cache and DB together
async function updateProduct(productId, updates) {
  await db.products.update(productId, updates);
  const updated = await db.products.findById(productId);
  await cache.set(`product:${productId}`, updated, { ttl: 3600 });
}
```

**Pros:**
- Cache always consistent with DB
- No stale reads after writes

**Cons:**
- Slower writes (update both)
- Cache might be evicted before TTL

**4. Lazy invalidation - Efficient**
```javascript
// Check version on read
async function getProduct(productId) {
  const cacheKey = `product:${productId}`;
  const cached = await cache.get(cacheKey);

  if (cached) {
    const currentVersion = await db.products.getVersion(productId);
    if (cached.version === currentVersion) {
      return cached.data;
    }
    // Version mismatch, cache is stale
  }

  // Fetch fresh data
  const product = await db.products.findById(productId);
  await cache.set(cacheKey, {
    version: product.version,
    data: product
  }, { ttl: 3600 });
  return product;
}
```

**Recommendation:** Start with TTL (simplest). Add event-based if staleness is a problem.

### Step 4: TTL Selection

**TTL too short:** Defeats purpose of caching (high miss rate)
**TTL too long:** Stale data for long periods

**Guidelines by data type:**

| Data Type | TTL Recommendation | Reasoning |
|-----------|-------------------|-----------|
| **Static assets** (CSS, JS, images) | 1 year (31536000s) | Version in URL, immutable |
| **Product catalog** | 1 hour (3600s) | Updated occasionally, not real-time |
| **User sessions** | 30 minutes (1800s) | Balance security vs UX |
| **API responses** (third-party) | 5-15 minutes (300-900s) | Fresh but reduce API calls |
| **Search results** | 5 minutes (300s) | Fresh, expensive computation |
| **Real-time data** | 30 seconds (30s) or don't cache | Near real-time, balance load |
| **Computed reports** | 1 day (86400s) | Expensive, infrequent updates |

**Dynamic TTL based on data age:**
```javascript
// Longer TTL for older content (less likely to change)
function calculateTTL(item) {
  const age = Date.now() - item.createdAt;
  const oneDayMs = 24 * 60 * 60 * 1000;

  if (age < oneDayMs) return 300;        // 5 minutes (new content)
  if (age < 7 * oneDayMs) return 1800;   // 30 minutes (week old)
  return 3600;                            // 1 hour (older content)
}
```

### Step 5: Cache Key Design

**Prevent key collisions:**

```javascript
// Bad: Ambiguous keys
❌ cache.set(`123`, user);              // What is 123? User? Order? Product?
❌ cache.set(`user`, user);             // Which user?
❌ cache.set(`${id}`, data);            // Namespace collision

// Good: Explicit, namespaced keys
✅ cache.set(`user:${userId}`, user);
✅ cache.set(`product:${productId}`, product);
✅ cache.set(`order:${orderId}`, order);
```

**Include relevant context:**

```javascript
// Bad: Missing version, missing query params
❌ cache.set(`products`, products);

// Good: Include version and query context
✅ cache.set(`products:v2:page:${page}:limit:${limit}`, products);
✅ cache.set(`user:${userId}:profile:v3`, profile);
```

**Cache key patterns:**

```javascript
// Entity caches
const userKey = `user:${userId}:v${USER_CACHE_VERSION}`;
const productKey = `product:${productId}:v${PRODUCT_CACHE_VERSION}`;

// Query caches
const searchKey = `search:${query}:page:${page}:sort:${sort}`;
const listKey = `users:page:${page}:limit:${limit}:filter:${filter}`;

// Computed caches
const statsKey = `stats:${userId}:date:${date}`;
const reportKey = `report:${type}:from:${from}:to:${to}`;
```

### Step 6: Cache Stampede Prevention

**Problem:** Cache expires, many requests hit DB simultaneously.

**Solution 1: Locking (ensure single recompute)**

```javascript
async function getWithLock(key, fetchFn, ttl = 3600) {
  const cached = await cache.get(key);
  if (cached) return cached;

  const lockKey = `lock:${key}`;
  const locked = await cache.set(lockKey, '1', { ttl: 10, nx: true });

  if (locked) {
    // We got the lock, fetch data
    try {
      const data = await fetchFn();
      await cache.set(key, data, { ttl });
      return data;
    } finally {
      await cache.del(lockKey);
    }
  } else {
    // Someone else is fetching, wait and retry
    await sleep(100);
    return getWithLock(key, fetchFn, ttl);
  }
}
```

**Solution 2: Stale-while-revalidate**

```javascript
async function getWithSWR(key, fetchFn, ttl = 3600) {
  const cached = await cache.get(key);

  if (cached) {
    // Return stale data immediately
    const age = Date.now() - cached.timestamp;

    // Async revalidate if stale (don't block)
    if (age > ttl * 1000 * 0.8) { // Revalidate at 80% of TTL
      fetchFn().then(fresh => {
        cache.set(key, {
          data: fresh,
          timestamp: Date.now()
        }, { ttl });
      });
    }

    return cached.data;
  }

  // Cache miss, fetch synchronously
  const data = await fetchFn();
  await cache.set(key, {
    data,
    timestamp: Date.now()
  }, { ttl });
  return data;
}
```

### Step 7: Memory Management

**Set max memory limits:**

```javascript
// Redis config
maxmemory 2gb
maxmemory-policy allkeys-lru  // Evict least recently used keys
```

**Eviction policies:**
- **allkeys-lru:** Evict least recently used (good default)
- **allkeys-lfu:** Evict least frequently used (better for hot data)
- **volatile-ttl:** Evict keys closest to expiration (only keys with TTL)
- **noeviction:** Fail writes when full (use for sessions)

**Estimate memory usage:**

```javascript
// Rough estimation
const itemSize = JSON.stringify(typicalItem).length;
const numItems = 1000000;
const estimatedMemory = itemSize * numItems * 1.5; // 1.5x for overhead

console.log(`Estimated cache memory: ${estimatedMemory / 1024 / 1024} MB`);
```

**Monitor memory usage:**
```javascript
setInterval(async () => {
  const info = await cache.info('memory');
  const usedMemory = parseInt(info.used_memory);
  const maxMemory = parseInt(info.maxmemory);
  const usage = (usedMemory / maxMemory * 100).toFixed(2);

  console.log(`Cache memory usage: ${usage}%`);

  if (usage > 80) {
    console.warn('Cache memory usage high, consider increasing limit');
  }
}, 60000); // Check every minute
```

### Step 8: Cache Monitoring

**Track cache performance:**

```javascript
async function getWithMetrics(key, fetchFn, ttl) {
  const start = Date.now();
  const cached = await cache.get(key);

  if (cached) {
    metrics.increment('cache.hits');
    metrics.histogram('cache.latency', Date.now() - start);
    return cached;
  }

  metrics.increment('cache.misses');
  const data = await fetchFn();
  await cache.set(key, data, { ttl });
  metrics.histogram('cache.latency', Date.now() - start);

  return data;
}
```

**Key metrics:**
- **Hit rate:** hits / (hits + misses) - Target: >80%
- **Miss rate:** misses / (hits + misses) - Target: <20%
- **Eviction rate:** evictions / sets - High = memory pressure
- **Latency:** p50, p95, p99 - Should be <10ms

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| No invalidation strategy | Stale data forever | Define TTL or event-based invalidation |
| TTL too long | Stale data for hours/days | Balance staleness vs cache hits |
| TTL too short | High miss rate, poor performance | Longer TTL, pre-warming |
| No cache key versioning | Can't invalidate all keys on schema change | Include version in keys |
| No stampede prevention | DB overwhelmed on cache miss | Locking or stale-while-revalidate |
| No memory limits | OOM crashes | Set maxmemory and eviction policy |
| Caching non-deterministic data | Inconsistent results | Only cache deterministic data |
| Caching personalized data globally | Data leaks, wrong user data | Per-user cache keys |
| No monitoring | Can't detect issues (low hit rate, high evictions) | Track hit rate, latency, memory |

## Rationalization Counters

**"Caching is always better"** → No. Caching adds complexity. Only cache if read-heavy and staleness is acceptable.

**"I'll add invalidation later"** → Later never comes. Stale data will haunt you. Define invalidation strategy now.

**"TTL doesn't matter, I'll just set it high"** → High TTL = stale data. Low TTL = low hit rate. Choose carefully.

**"Cache keys don't need structure"** → Unstructured keys cause collisions, impossible invalidation. Namespace everything.

**"Memory will be fine"** → Memory fills up fast. Set limits or wake up to OOM crashes at 3am.

**"I don't need monitoring"** → Without metrics, you don't know if caching is helping or hurting. Always monitor.

## Caching Layers

**1. Browser cache (HTTP caching)**
```http
Cache-Control: public, max-age=3600  # Cache in browser for 1 hour
ETag: "abc123"                        # Conditional requests
```

**2. CDN cache (edge caching)**
```javascript
// Cloudflare, Fastly, CloudFront
res.setHeader('Cache-Control', 'public, max-age=86400'); // 1 day
```

**3. Application cache (Redis, Memcached)**
```javascript
const data = await cache.get(key);
```

**4. Database cache (query cache)**
```sql
-- PostgreSQL shared buffers, query cache
SELECT * FROM products WHERE id = 123;  -- Cached by DB
```

**Choose the right layer:**
- **Static assets:** Browser + CDN
- **API responses:** Application cache
- **Database queries:** Application cache (not DB query cache)

## Integration with Existing Workflows

**With performance optimization:**
1. Measure baseline (before caching)
2. Add caching
3. Measure improvement
4. Monitor hit rate

**With testing:**
- Test cache hits (data returned correctly)
- Test cache misses (data fetched correctly)
- Test invalidation (stale data not returned)
- Test stampede prevention

**With monitoring:**
- Set up alerts for low hit rate (<50%)
- Set up alerts for high memory usage (>80%)
- Track cache latency

## Real-World Impact

**Without this skill:**
- Stale data shown to users (no invalidation)
- Cache stampedes (DB overwhelmed)
- OOM crashes (no memory limits)
- Poor cache hit rates (TTL too short)
- Data leaks (key collisions, wrong user data)

**With this skill:**
- Fast responses (high cache hit rate)
- Fresh data (proper invalidation)
- Stable system (stampede prevention)
- Predictable memory usage (limits set)
- Secure caching (proper key design)

## Required Background

None. This skill is self-contained.

## Cross-References

- Use `superpowers:systematic-debugging` for cache-related bugs
- Use `superpowers:test-driven-development` to test caching behavior
