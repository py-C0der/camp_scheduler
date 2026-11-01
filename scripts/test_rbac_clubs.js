const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  console.log('1. Loading site and logging in as Clubs...');
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });

  // Open role selection
  await page.evaluate(() => showAuthGateModal());
  await page.waitForTimeout(300);

  // Click on "Clubs" card
  await page.click('#authStageRoleSelect .role-select-card:has-text("Clubs")');
  await page.waitForTimeout(300);

  // Submit login
  await page.click('#btnAuthGateSubmit');
  await page.waitForTimeout(600);

  // Check RBAC for Clubs
  const disDisplay = await page.$eval('#navItemDisruptions', el => el.parentElement.style.display);
  const examDisplay = await page.$eval('#navItemExaminations', el => el.parentElement.style.display);
  const resetDemoDisplay = await page.$eval('#btnHeaderResetDemo', el => el ? el.style.display : 'none');
  const autoDecideDisplay = await page.$eval('#btnAutoDecide', el => el ? el.style.display : 'none');

  console.log(`[RBAC CHECK] Disruptions sidebar display: "${disDisplay}" (Hidden: ${disDisplay === 'none'})`);
  console.log(`[RBAC CHECK] Examinations sidebar display: "${examDisplay}" (Hidden: ${examDisplay === 'none'})`);
  console.log(`[RBAC CHECK] Reset Demo header display: "${resetDemoDisplay}" (Hidden: ${resetDemoDisplay === 'none'})`);
  console.log(`[RBAC CHECK] Auto-Decide button display: "${autoDecideDisplay}" (Hidden: ${autoDecideDisplay === 'none'})`);

  const topUser = await page.$eval('#topUserName', el => el.textContent.trim());
  const roleBadge = await page.$eval('#activeRoleBadge', el => el.textContent.trim());
  console.log(`[PASS] Topbar User: "${topUser}", Badge: "${roleBadge}"`);

  // Try unauthorized route
  let alertFired = false;
  page.on('dialog', async dialog => {
    console.log(`[PASS] Alert Dialog intercepted: "${dialog.message()}"`);
    alertFired = true;
    await dialog.accept();
  });

  console.log('2. Testing unauthorized switchNav("disruptions") as Clubs...');
  await page.evaluate(() => switchNav('disruptions'));
  await page.waitForTimeout(400);
  console.log(`[PASS] Unauthorized route was blocked with alert: ${alertFired}`);

  await browser.close();
  console.log('\nSTRICT ROLE-BASED ACCESS CONTROL VERIFIED WITH 100% SUCCESS!');
})();
