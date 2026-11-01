const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  await page.goto('http://127.0.0.1:8000/workspace', { waitUntil: 'networkidle' });
  
  // Locate the sidebar element
  const sidebar = await page.$('.sidebar');
  if (sidebar) {
    const screenshotPath = path.resolve('scripts/sidebar_no_badges.png');
    await sidebar.screenshot({ path: screenshotPath });
    console.log('Sidebar screenshot saved at:', screenshotPath);
  } else {
    console.log('Sidebar not found');
  }

  // Verify that no .nav-badge elements are visible
  const visibleBadges = await page.$$eval('.nav-badge', els => els.filter(el => {
    const style = window.getComputedStyle(el);
    return style && style.display !== 'none' && style.visibility !== 'hidden';
  }).length);

  console.log('Visible .nav-badge count:', visibleBadges);
  await browser.close();
})();
