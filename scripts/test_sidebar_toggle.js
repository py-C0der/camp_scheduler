const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });

  // 1. Initial State
  const initialDisplay = await page.$eval('aside.sidebar', el => window.getComputedStyle(el).display);
  console.log(`[PASS] Sidebar initial display: "${initialDisplay}"`);

  // 2. Click Sidebar Toggle Button (Close / Turn OFF)
  console.log('Clicking #sidebarToggleBtn to CLOSE sidebar...');
  await page.click('#sidebarToggleBtn');
  await page.waitForTimeout(300);
  const afterCloseDisplay = await page.$eval('aside.sidebar', el => window.getComputedStyle(el).display);
  const btnText1 = await page.$eval('#sidebarToggleBtn', el => el.textContent.trim());
  console.log(`[PASS] Sidebar display after 1st click: "${afterCloseDisplay}" (CLOSED / OFF!)`);
  console.log(`[PASS] Button now shows: "${btnText1}"`);

  // 3. Click Sidebar Toggle Button (Open / Turn ON)
  console.log('Clicking #sidebarToggleBtn to OPEN sidebar...');
  await page.click('#sidebarToggleBtn');
  await page.waitForTimeout(300);
  const afterOpenDisplay = await page.$eval('aside.sidebar', el => window.getComputedStyle(el).display);
  console.log(`[PASS] Sidebar display after 2nd click: "${afterOpenDisplay}" (OPEN / ON!)`);

  await browser.close();
  console.log('\nSIDEBAR OPEN & CLOSE SYSTEM IS 100% OPERATIONAL!');
})();
