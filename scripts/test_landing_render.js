const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  console.log('Opening http://127.0.0.1:8000/ ...');
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const screenshotPath = path.resolve('scripts/landing_view.png');
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log('Saved screenshot of root to:', screenshotPath);

  console.log('Title:', await page.title());

  await browser.close();
})();
