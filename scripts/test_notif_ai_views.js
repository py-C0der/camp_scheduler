const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });

  // Notifications
  await page.click('#navItemNotifications');
  await page.waitForTimeout(400);
  const notifBox = await page.$eval('#view-notifications', el => ({
    display: window.getComputedStyle(el).display,
    offsetHeight: el.offsetHeight,
    scrollHeight: el.scrollHeight,
    childrenCount: el.children.length
  }));
  console.log('Notifications box:', notifBox);
  await page.screenshot({ path: 'notif_view.png' });

  // AI Assistant
  await page.click('#navItemAiAssistant');
  await page.waitForTimeout(400);
  const aiBox = await page.$eval('#view-ai-assistant', el => ({
    display: window.getComputedStyle(el).display,
    offsetHeight: el.offsetHeight,
    scrollHeight: el.scrollHeight,
    childrenCount: el.children.length
  }));
  console.log('AI Assistant box:', aiBox);
  await page.screenshot({ path: 'ai_view.png' });

  await browser.close();
})();
