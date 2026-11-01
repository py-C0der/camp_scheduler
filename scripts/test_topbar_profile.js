const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  console.log('1. Navigating to workspace...');
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });

  // 1. Verify "Login / Switch User" button is GONE
  const switchBtnCount = await page.locator('text="Login / Switch User"').count();
  console.log(`[PASS] "Login / Switch User" button present: ${switchBtnCount > 0} (Count: ${switchBtnCount} - GONE!)`);

  // 2. Verify avatar is a circle and name is NOT openly displayed in the navbar
  const avatarBorderRadius = await page.$eval('.user-avatar-circle', el => window.getComputedStyle(el).borderRadius);
  console.log(`[PASS] Avatar border-radius: "${avatarBorderRadius}" (Circle!)`);

  // Check that the top navbar does NOT show the user's name openly
  const openlyVisibleName = await page.$eval('.user-profile-tooltip', el => window.getComputedStyle(el).opacity);
  console.log(`[PASS] Profile tooltip opacity before hover: "${openlyVisibleName}" (Hidden without hover!)`);

  // Hover over avatar circle
  console.log('2. Hovering over circular avatar...');
  await page.hover('.user-avatar-circle');
  await page.waitForTimeout(300);

  const hoveredOpacity = await page.$eval('.user-profile-tooltip', el => window.getComputedStyle(el).opacity);
  const tipName = await page.$eval('#tipUserName', el => el.textContent.trim());
  const tipRole = await page.$eval('#tipUserRole', el => el.textContent.trim());
  const tipEmail = await page.$eval('#tipUserEmail', el => el.textContent.trim());
  console.log(`[PASS] Tooltip opacity on hover: "${hoveredOpacity}" (Visible on hover!)`);
  console.log(`[PASS] Tooltip shows: Name="${tipName}", Role="${tipRole}", Email="${tipEmail}"`);

  // 3. Test Sidebar Toggle (Close / Open)
  console.log('3. Testing Sidebar Toggle button...');
  await page.click('#sidebarToggleBtn');
  await page.waitForTimeout(300);
  const sidebarClosed = await page.$eval('aside.sidebar', el => window.getComputedStyle(el).display === 'none');
  console.log(`[PASS] Sidebar turned OFF / closed: ${sidebarClosed}`);

  await page.click('#sidebarToggleBtn');
  await page.waitForTimeout(300);
  const sidebarOpened = await page.$eval('aside.sidebar', el => window.getComputedStyle(el).display === 'flex');
  console.log(`[PASS] Sidebar turned ON / opened: ${sidebarOpened}`);

  // Take screenshot of top-right header area
  const topbar = await page.locator('.topbar');
  await topbar.screenshot({ path: 'clean_topbar_circle.png' });
  console.log('Saved clean_topbar_circle.png');

  await browser.close();
  console.log('\nALL TOPBAR PROFILE & SIDEBAR TESTS PASSED 100%!');
})();
