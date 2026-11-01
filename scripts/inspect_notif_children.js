const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  await page.click('#navItemNotifications');

  const report = await page.$eval('#view-notifications', el => {
    const res = [];
    for (let i = 0; i < el.children.length; i++) {
      const c = el.children[i];
      const style = window.getComputedStyle(c);
      res.push({
        tag: c.tagName,
        id: c.id,
        className: c.className,
        display: style.display,
        visibility: style.visibility,
        height: style.height,
        offsetHeight: c.offsetHeight
      });
    }
    return {
      panelDisplay: window.getComputedStyle(el).display,
      panelParent: el.parentElement ? el.parentElement.tagName + '.' + el.parentElement.className : 'null',
      children: res
    };
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
