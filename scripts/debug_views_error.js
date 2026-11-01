const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  page.on('console', msg => console.log('BROWSER LOG:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message, err.stack));

  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });

  console.log('--- Switching to notifications ---');
  await page.click('#navItemNotifications');
  await page.waitForTimeout(500);

  console.log('--- Switching to ai-assistant ---');
  await page.click('#navItemAiAssistant');
  await page.waitForTimeout(500);

  await browser.close();
})();
