import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Collect console messages
  const consoleMessages = [];
  page.on('console', msg => {
    consoleMessages.push({
      type: msg.type(),
      text: msg.text()
    });
  });

  // Collect errors
  const errors = [];
  page.on('pageerror', error => {
    errors.push(error.message);
  });

  try {
    console.log('Navigating to main dashboard...');
    await page.goto('http://127.0.0.1:9244/', { waitUntil: 'networkidle', timeout: 10000 });

    // Wait for page to load
    await page.waitForTimeout(1000);

    console.log('Clicking on Diagnostics menu item...');
    // Click on diagnostics in the sidebar
    await page.click('.sidebar-item[data-page="diagnostics"]');

    // Wait for diagnostics to load
    await page.waitForTimeout(3000);

    // Take screenshot
    await page.screenshot({ path: '/Users/robert/Code/spec-kitty/diagnostics_screenshot.png', fullPage: true });
    console.log('Screenshot saved to diagnostics_screenshot.png');

    // Get page title
    const title = await page.title();
    console.log('Page title:', title);

    // Get diagnostics page content
    const diagnosticsContent = await page.evaluate(() => {
      const diagnosticsPage = document.getElementById('page-diagnostics');
      if (diagnosticsPage) {
        return diagnosticsPage.innerText;
      }
      return 'Diagnostics page not found';
    });

    console.log('\n=== DIAGNOSTICS PAGE CONTENT ===\n');
    console.log(diagnosticsContent);

    // Get diagnostics data from API
    console.log('\n=== DIAGNOSTICS API DATA ===\n');
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/diagnostics');
        return await response.json();
      } catch (e) {
        return { error: e.toString() };
      }
    });
    console.log(JSON.stringify(apiResponse, null, 2));

    // Print console messages
    console.log('\n=== CONSOLE MESSAGES ===\n');
    if (consoleMessages.length > 0) {
      consoleMessages.forEach(msg => {
        console.log(`[${msg.type}] ${msg.text}`);
      });
    } else {
      console.log('No console messages');
    }

    // Print errors
    console.log('\n=== JAVASCRIPT ERRORS ===\n');
    if (errors.length > 0) {
      errors.forEach(err => {
        console.log(`ERROR: ${err}`);
      });
    } else {
      console.log('No JavaScript errors');
    }

  } catch (error) {
    console.error('Error accessing page:', error.message);
    // Take screenshot even on error
    try {
      await page.screenshot({ path: '/Users/robert/Code/spec-kitty/diagnostics_error_screenshot.png', fullPage: true });
      console.log('Error screenshot saved');
    } catch (e) {
      console.error('Could not save error screenshot:', e.message);
    }
  } finally {
    await browser.close();
  }
})();
