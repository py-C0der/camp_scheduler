const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });

  const tabs = [
    { name: 'timetable', btn: '#navItemTimetable', view: '#view-timetable' },
    { name: 'examinations', btn: '#navItemExaminations', view: '#view-examinations' },
    { name: 'bookings', btn: '#navItemBookings', view: '#view-bookings' },
    { name: 'disruptions', btn: '#navItemDisruptions', view: '#view-disruptions' },
    { name: 'validations', btn: '#navItemValidations', view: '#view-validations' },
    { name: 'notifications', btn: '#navItemNotifications', view: '#view-notifications' },
    { name: 'ai-assistant', btn: '#navItemAiAssistant', view: '#view-ai-assistant' }
  ];

  for (const t of tabs) {
    await page.click(t.btn);
    await page.waitForTimeout(300);
    const dims = await page.$eval(t.view, el => ({
      display: window.getComputedStyle(el).display,
      height: el.offsetHeight,
      width: el.offsetWidth
    }));
    console.log(`Tab ${t.name}: display=${dims.display}, height=${dims.height}px, width=${dims.width}px`);
  }

  await browser.close();
})();
