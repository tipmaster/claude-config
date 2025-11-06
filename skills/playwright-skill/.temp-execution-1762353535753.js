const { chromium } = require('playwright');

const TARGET_URL = 'file:///Users/administrator/dev/tfwg/emd/sites/hesgoal.group/html/basketball-live-stream.html';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage();

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(TARGET_URL);

  console.log('Page loaded:', await page.title());

  // Take full page screenshot
  await page.screenshot({
    path: '/tmp/basketball-full-page.png',
    fullPage: true
  });
  console.log('📸 Full page screenshot saved to /tmp/basketball-full-page.png');

  // Find all content links (not nav/footer)
  const contentLinks = await page.locator('main a, article a, .content a').all();
  console.log(`\nFound ${contentLinks.length} links in content area`);

  // Get link details
  for (let i = 0; i < contentLinks.length; i++) {
    const link = contentLinks[i];
    const text = await link.textContent();
    const href = await link.getAttribute('href');
    const color = await link.evaluate(el => window.getComputedStyle(el).color);

    console.log(`\nLink ${i + 1}:`);
    console.log(`  Text: "${text}"`);
    console.log(`  Href: ${href}`);
    console.log(`  Color: ${color}`);
    console.log(`  Text length: ${text.length} chars`);
  }

  // Take screenshot of first content section with links
  const firstSection = await page.locator('main, article').first();
  if (firstSection) {
    await firstSection.screenshot({
      path: '/tmp/basketball-content-section.png'
    });
    console.log('\n📸 Content section screenshot saved to /tmp/basketball-content-section.png');
  }

  // Wait a bit before closing so user can see
  await page.waitForTimeout(3000);

  await browser.close();
})();
