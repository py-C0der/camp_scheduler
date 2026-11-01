const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => consoleErrors.push(err.message));

  const startTime = Date.now();
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  const loadTime = Date.now() - startTime;
  console.log(`Page loaded directly at / in ${loadTime}ms`);
  console.log(`Page title: ${await page.title()}`);

  // Test 8 sidebar navigation tabs
  const tabs = [
    { id: '#navItemDashboard', view: '#view-dashboard' },
    { id: '#navItemTimetable', view: '#view-timetable' },
    { id: '#navItemExaminations', view: '#view-examinations' },
    { id: '#navItemBookings', view: '#view-bookings' },
    { id: '#navItemDisruptions', view: '#view-disruptions' },
    { id: '#navItemValidations', view: '#view-validations' },
    { id: '#navItemNotifications', view: '#view-notifications' },
    { id: '#navItemAiAssistant', view: '#view-ai-assistant' }
  ];

  let passed = 0;
  for (const t of tabs) {
    await page.click(t.id);
    await page.waitForTimeout(100);
    const active = await page.$eval(t.view, el => el.classList.contains('active'));
    if (active) passed++;
  }
  console.log(`Sidebar tabs passed: ${passed} / ${tabs.length}`);

  // Check badges count
  const badgeCount = await page.locator('.nav-badge').count();
  console.log(`Remaining .nav-badge count in DOM: ${badgeCount}`);

  console.log(`Total console/page errors: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.log('Errors:', consoleErrors);
  }

  await page.screenshot({ path: 'clean_root_workspace.png' });
  console.log('Saved clean_root_workspace.png');

  await browser.close();
})();
