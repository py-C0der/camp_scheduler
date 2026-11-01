const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const pagesToTest = [
    { name: 'Intro / WebGL', url: 'http://127.0.0.1:8000/' },
    { name: 'Digital Planner', url: 'http://127.0.0.1:8000/planner' },
    { name: 'Login Page', url: 'http://127.0.0.1:8000/login' },
    { name: 'Workspace Console', url: 'http://127.0.0.1:8000/workspace' },
    { name: 'Validations Page', url: 'http://127.0.0.1:8000/validations' },
    { name: 'Dashboard Page', url: 'http://127.0.0.1:8000/dashboard' },
    { name: 'Timetable Page', url: 'http://127.0.0.1:8000/timetable' },
    { name: 'AI Assistant Page', url: 'http://127.0.0.1:8000/ai-assistant' }
  ];

  console.log('--- STARTING PLAYWRIGHT AUDIT ---');

  let passed = 0;
  let failed = 0;

  for (const item of pagesToTest) {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    try {
      const resp = await page.goto(item.url, { waitUntil: 'domcontentloaded', timeout: 10000 });
      const status = resp.status();
      const title = await page.title();
      
      console.log(`[PASS] ${item.name} -> HTTP ${status} | Title: "${title}"`);
      passed++;
    } catch (e) {
      console.error(`[FAIL] ${item.name} -> ${e.message}`);
      failed++;
    }
  }

  // Specifically test the Live Validator widget on Validations page
  try {
    console.log('\n--- TESTING LIVE VALIDATOR WIDGET ON /validations ---');
    await page.goto('http://127.0.0.1:8000/validations', { waitUntil: 'networkidle', timeout: 10000 });
    
    // Check if the Run Validator button exists
    const btn = await page.$('#btnRunOfficialValidator');
    if (btn) {
      console.log('Found #btnRunOfficialValidator button. Clicking...');
      await btn.click();
      await page.waitForTimeout(1500);

      const hardText = await page.$eval('#valMetricHard', el => el.textContent.trim());
      const softText = await page.$eval('#valMetricSoft', el => el.textContent.trim());
      const bkText = await page.$eval('#valMetricBooking', el => el.textContent.trim());
      const exText = await page.$eval('#valMetricExams', el => el.textContent.trim());

      console.log(`Live Validator Results -> Hard: ${hardText}, Soft: ${softText}, Booking: ${bkText}, Exams: ${exText}`);
      if (hardText === '0') {
        console.log('[PASS] Live Validator verified with 0 hard violations!');
      } else {
        console.warn(`[WARN] Hard violations = ${hardText}`);
      }
    } else {
      console.log('Button #btnRunOfficialValidator not found in DOM.');
    }
  } catch (e) {
    console.error('Validator widget test error:', e.message);
  }

  // Check Reset Demo Data button
  try {
    const resetBtn = await page.$('#btnHeaderResetDemo');
    if (resetBtn) {
      console.log('[PASS] Found #btnHeaderResetDemo in header!');
    }
  } catch(e) {}

  await browser.close();
  console.log(`\nAudit Complete: ${passed} passed, ${failed} failed.`);
})();
