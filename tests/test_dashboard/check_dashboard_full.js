import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 3000 } // Tall viewport to capture everything
  });
  const page = await context.newPage();

  try {
    console.log('Navigating to main dashboard...');
    await page.goto('http://127.0.0.1:9244/', { waitUntil: 'networkidle', timeout: 10000 });

    await page.waitForTimeout(1000);

    console.log('Clicking on Diagnostics menu item...');
    await page.click('.sidebar-item[data-page="diagnostics"]');

    // Wait for diagnostics to load
    await page.waitForTimeout(3000);

    // Check if there's content that extends beyond the viewport
    const hasScrollableContent = await page.evaluate(() => {
      const diagnosticsPage = document.getElementById('page-diagnostics');
      if (diagnosticsPage) {
        console.log('Page height:', diagnosticsPage.scrollHeight);
        console.log('Page content:', diagnosticsPage.innerHTML.substring(0, 500));
        return diagnosticsPage.scrollHeight;
      }
      return 0;
    });

    console.log('Diagnostics page height:', hasScrollableContent);

    // Get all HTML content of the diagnostics page
    const fullHTML = await page.evaluate(() => {
      const diagnosticsPage = document.getElementById('page-diagnostics');
      return diagnosticsPage ? diagnosticsPage.innerHTML : 'Not found';
    });

    console.log('\n=== FULL DIAGNOSTICS HTML ===\n');
    console.log(fullHTML.substring(0, 5000)); // First 5000 chars

    // Take full page screenshot
    await page.screenshot({
      path: '/Users/robert/Code/spec-kitty/diagnostics_full_screenshot.png',
      fullPage: true
    });
    console.log('Full page screenshot saved');

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
