const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('http://127.0.0.1:8000/workspace', { waitUntil: 'networkidle' });

  const buttons = [
    { id: '#navItemDashboard', expected: 'view-dashboard' },
    { id: '#navItemTimetable', expected: 'view-timetable' },
    { id: '#navItemExaminations', expected: 'view-examinations' },
    { id: '#navItemBookings', expected: 'view-bookings' },
    { id: '#navItemDisruptions', expected: 'view-disruptions' },
    { id: '#navItemValidations', expected: 'view-validations' },
    { id: '#navItemNotifications', expected: 'view-notifications' },
    { id: '#navItemAiAssistant', expected: 'view-ai-assistant' }
  ];

  let passed = 0;
  for (const b of buttons) {
    const el = await page.$(b.id);
    if (!el) {
      console.error(`Button ${b.id} not found in DOM!`);
      continue;
    }
    await el.click();
    await page.waitForTimeout(200);

    const isActive = await page.$eval(`#${b.expected}`, el => el.classList.contains('active'));
    if (isActive) {
      console.log(`[PASS] Clicked ${b.id} -> ${b.expected} is active!`);
      passed++;
    } else {
      console.error(`[FAIL] Clicked ${b.id} -> ${b.expected} is NOT active!`);
    }
  }

  console.log(`\nSidebar verification: ${passed}/${buttons.length} passed.`);
  await browser.close();
})();
