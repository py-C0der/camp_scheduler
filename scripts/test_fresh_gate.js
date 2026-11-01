const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  console.log('Visiting fresh root...');
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);

  await page.screenshot({ path: 'fresh_login_gate.png' });
  console.log('Saved fresh_login_gate.png');

  await browser.close();
})();
