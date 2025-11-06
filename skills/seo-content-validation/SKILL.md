---
name: seo-content-validation
description: Use when creating/editing web pages, content templates, or sitemaps - validates SEO technical requirements including Schema.org markup, meta tags, internal links, and Core Web Vitals to prevent indexing and ranking issues
---

# SEO Content Validation

## Overview

Systematic validation of SEO requirements before content publication to prevent common issues that harm search rankings, indexability, and user experience.

## When to Use

Use this skill when:
- Creating new web pages or content templates
- Modifying existing page templates or layouts
- Generating sitemaps or content structures
- Adding affiliate content or monetization
- Changing URL structures or internal linking
- Updating meta tags or structured data

**Symptoms that trigger this skill:**
- "Add new page/template"
- "Generate sitemap"
- "Create content for X keyword"
- Working with files in `sites/*/` directories
- Modifying HTML templates or components

**Don't use when:**
- Writing backend API code unrelated to content
- Database migrations
- Server configuration changes

## Quick Reference: SEO Validation Checklist

Use TodoWrite for ALL items below when validating content:

| Category | Validation | Critical Issues |
|----------|-----------|-----------------|
| **Meta Tags** | Title (50-60 chars), Description (150-160 chars), Canonical URL | Duplicate titles, missing descriptions |
| **Structured Data** | Schema.org markup (Article/Organization/BreadcrumbList) | Invalid JSON-LD, missing required fields |
| **Internal Links** | 3-5 contextual links per page, proper anchor text | Orphaned pages, broken links |
| **Core Web Vitals** | LCP <2.5s, FID <100ms, CLS <0.1 | Heavy images, layout shifts |
| **Mobile** | Responsive design, tap targets ≥48px, readable text | Mobile-usability issues |
| **Content** | H1 unique per page, H2-H6 hierarchy, keyword placement | Duplicate H1s, missing headers |
| **URLs** | Hyphens not underscores, lowercase, descriptive slugs | Non-canonical URLs |

## Implementation

### Step 1: Create TodoWrite Checklist

```markdown
☐ Validate title tag (50-60 chars, unique, includes target keyword)
☐ Validate meta description (150-160 chars, compelling, includes keyword)
☐ Validate canonical URL (absolute, matches primary URL)
☐ Validate Schema.org markup (appropriate type, valid JSON-LD, required fields)
☐ Validate H1 tag (unique, includes primary keyword, <70 chars)
☐ Validate heading hierarchy (H2-H6 in logical order)
☐ Validate internal links (3-5 contextual, relevant anchor text, valid URLs)
☐ Validate image optimization (alt text, appropriate sizes, lazy loading)
☐ Validate mobile responsiveness (viewport meta, readable text, tap targets)
☐ Validate Core Web Vitals impact (image sizes, layout stability, interactivity)
```

### Step 2: Meta Tags Validation

**Required tags:**
```html
<title>Primary Keyword - Brand | 50-60 chars</title>
<meta name="description" content="150-160 chars compelling summary with keyword">
<link rel="canonical" href="https://example.com/page-url">
<meta name="viewport" content="width=device-width, initial-scale=1">
```

**Check for:**
- ❌ Title >60 chars or <30 chars
- ❌ Description >160 chars or <120 chars
- ❌ Missing canonical tag
- ❌ Duplicate titles/descriptions across pages

### Step 3: Structured Data Validation

**Minimum Schema.org types for content sites:**
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Title",
  "datePublished": "2025-01-01",
  "dateModified": "2025-01-01",
  "author": {"@type": "Organization", "name": "Brand"},
  "publisher": {
    "@type": "Organization",
    "name": "Brand",
    "logo": {"@type": "ImageObject", "url": "logo-url"}
  }
}
```

**Validation:**
- Use schema.org validator or Google Rich Results Test
- Ensure all required fields present
- Verify proper nesting and types

### Step 4: Internal Linking Validation

**Best practices:**
- 3-5 contextual internal links per page minimum
- Link to related content and pillar pages
- Use descriptive anchor text (not "click here")
- Ensure no orphaned pages (0 incoming links)

**Check for:**
- ❌ Pages with <3 internal links
- ❌ Orphaned pages in sitemap
- ❌ Broken internal links
- ❌ Generic anchor text ("here", "click here")

### Step 5: Core Web Vitals Impact

**Key metrics:**
- **LCP** (Largest Contentful Paint): <2.5s
  - Check image sizes, lazy loading, CDN usage
- **FID** (First Input Delay): <100ms
  - Check JavaScript execution time
- **CLS** (Cumulative Layout Shift): <0.1
  - Check image dimensions, font loading, dynamic content

**Quick checks:**
- All images have width/height attributes
- Lazy loading enabled for below-fold images
- Fonts use `font-display: swap` or `optional`

### Step 6: Mobile Validation

**Required:**
- Viewport meta tag present
- Text ≥16px font size
- Tap targets ≥48x48px
- No horizontal scrolling
- Responsive images

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Skipping Schema.org markup | Misses rich results in SERPs | Add Article/Organization schema minimum |
| Duplicate title tags | Confuses search engines on which to rank | Generate unique titles per page |
| Generic meta descriptions | Low CTR from SERPs | Write compelling, keyword-rich descriptions |
| Missing canonical tags | Duplicate content issues | Add canonical to every page |
| Images without alt text | Poor accessibility and image SEO | Add descriptive alt text to all images |
| Broken internal links | Wastes crawl budget, poor UX | Validate all URLs before publication |
| No mobile optimization | 60% of traffic is mobile | Use responsive design, test on mobile |
| Large image files | Slow LCP, poor Core Web Vitals | Optimize images, use WebP, lazy load |

## Rationalization Counters

**"I'll add SEO later"** → SEO must be built in from the start. Retrofitting is 10x harder and you'll miss launch window for indexing.

**"This is just a test page"** → Test pages often go live. Validate now or it will go live broken.

**"Schema.org is optional"** → It's optional like seatbelts are optional. You want the rich results visibility.

**"I checked the title tag, that's enough"** → Title is 1 of 10 critical items. Use the full checklist or you WILL miss issues.

**"Internal linking can wait"** → Orphaned pages don't get crawled. Add links during creation or the page won't rank.

## Integration with Existing Workflows

**When generating sitemaps:**
- Validate each URL entry has corresponding meta tags defined
- Check for duplicate URLs or canonical conflicts
- Ensure internal linking plan covers all pages

**When using affiliate content:**
- Schema.org markup must include disclosure
- Affiliate links need rel="sponsored" or rel="nofollow"
- Balance commercial content with value content (E-A-T)

**When building templates:**
- Make SEO fields required in template schema
- Include Schema.org markup in template
- Add internal linking component to template

## Real-World Impact

**Without this skill:**
- Pages published without meta descriptions (0% CTR)
- Missing Schema.org markup (no rich results)
- Orphaned pages (never indexed)
- Duplicate titles (confused rankings)
- Poor Core Web Vitals (ranking penalties)

**With this skill:**
- All pages indexed within 24-48 hours
- Rich results in SERPs increase CTR 20-30%
- Clean internal linking distributes authority
- No ranking penalties from technical issues
- Mobile traffic converts better

## Required Background

None. This skill is self-contained.

## Cross-References

- Use `superpowers:verification-before-completion` before publishing content
- Use `superpowers:brainstorming` when planning content strategy
