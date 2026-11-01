const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  
  const defaultTitle = await page.$eval('#pageTitle', el => el.textContent);
  console.log('Default title:', defaultTitle);
  const dashboardVisible = await page.$eval('#view-dashboard', el => ({
    display: window.getComputedStyle(el).display,
    height: el.offsetHeight,
    width: el.offsetWidth
  }));
  console.log('Dashboard dimensions:', dashboardVisible);
  await page.screenshot({ path: 'dashboard_view.png' });
  console.log('Saved dashboard_view.png');

  await browser.close();
})();
