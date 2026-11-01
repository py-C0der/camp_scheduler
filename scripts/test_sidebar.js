const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const consoleLogs = [];
  const pageErrors = [];

  page.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => pageErrors.push(err.message));

  console.log('Navigating to http://127.0.0.1:8000/workspace...');
  await page.goto('http://127.0.0.1:8000/workspace', { waitUntil: 'networkidle' });

  const navs = ['dashboard', 'timetable', 'examinations', 'bookings', 'disruptions', 'validations', 'notifications', 'ai-assistant'];

  for (const n of navs) {
    try {
      console.log(`\nTesting switchNav('${n}')...`);
      await page.evaluate(name => switchNav(name), n);
      await page.waitForTimeout(500);

      const activePanels = await page.$$eval('.view-panel.active', els => els.map(e => e.id));
      console.log(`Active panels after switchNav('${n}'):`, activePanels);
    } catch(e) {
      console.error(`Error in switchNav('${n}'):`, e.message);
    }
  }

  // Also test clicking each <a> in the sidebar
  console.log('\n--- TESTING CLICKING SIDEBAR ITEMS ---');
  const items = await page.$$('.sidebar .nav-item');
  console.log(`Found ${items.length} nav items in sidebar.`);
  for (let i = 0; i < items.length; i++) {
    try {
      const text = await items[i].textContent();
      const onclick = await items[i].getAttribute('onclick');
      console.log(`Nav item ${i}: "${text.trim().replace(/\s+/g, ' ')}" -> onclick: ${onclick}`);
      await items[i].click();
      await page.waitForTimeout(300);
    } catch(e) {
      console.warn(`Click error on item ${i}:`, e.message);
    }
  }

  console.log('\n--- PAGE ERRORS ---');
  console.log(pageErrors.length ? pageErrors.join('\n') : 'None');

  await browser.close();
})();
