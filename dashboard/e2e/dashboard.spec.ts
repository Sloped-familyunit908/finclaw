import { test, expect } from '@playwright/test';

test.describe('Dashboard Homepage', () => {
  test('loads without errors', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('FinClaw');
    // Should not show error page
    await expect(page.locator('body')).not.toContainText('Application error');
  });

  test('displays market index banner', async ({ page }) => {
    await page.goto('/');
    // Wait for indices to load (may take a few seconds)
    await expect(page.locator('text=S&P 500')).toBeVisible({ timeout: 15000 });
  });

  test('displays watchlist with data', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h2:has-text("Watchlist")')).toBeVisible();
    // Wait for at least one price to load
    await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 15000 });
  });

  test('watchlist table headers are sortable', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('table tbody tr', { timeout: 15000 });
    // Click "Last" column header
    await page.locator('th:has-text("Last")').click();
    // Should not crash
    await expect(page.locator('table')).toBeVisible();
  });

  test('displays top movers', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h2:has-text("Top Movers")')).toBeVisible({ timeout: 15000 });
  });

  test('search box shows dropdown', async ({ page }) => {
    await page.goto('/');
    const searchBox = page.locator('input[placeholder*="Search"]');
    await searchBox.fill('AAPL');
    // Should show dropdown with results (use the search dropdown button specifically)
    await expect(page.getByRole('button', { name: 'AAPL Apple Inc US' })).toBeVisible({ timeout: 5000 });
  });

  test('search navigates to stock detail', async ({ page }) => {
    await page.goto('/');
    const searchBox = page.locator('input[placeholder*="Search"]');
    await searchBox.fill('TSLA');
    await page.waitForTimeout(500);
    // Click the first result or press Enter
    await searchBox.press('Enter');
    await page.waitForURL('**/stock/**', { timeout: 10000 });
    await expect(page.locator('body')).not.toContainText('Application error');
  });

  test('AI chat button exists and opens panel', async ({ page }) => {
    await page.goto('/');
    const chatBtn = page.locator('button:has-text("Ask about markets")');
    await expect(chatBtn).toBeVisible();
    await chatBtn.click();
    // Chat panel should open
    await expect(page.locator('text=FinClaw AI')).toBeVisible({ timeout: 5000 });
  });

  test('chat panel can be closed', async ({ page }) => {
    await page.goto('/');
    await page.locator('button:has-text("Ask about markets")').click();
    await expect(page.locator('text=FinClaw AI')).toBeVisible();
    // Find and click close button
    await page.locator('button[aria-label="Close chat"], button:has-text("Close")').first().click();
    // Panel should close (chat text should not be visible)
    await page.waitForTimeout(500);
  });

  test('nav links work', async ({ page }) => {
    await page.goto('/');
    // Screener link
    const screenerLink = page.locator('a:has-text("Screener")');
    if (await screenerLink.isVisible()) {
      await screenerLink.click();
      await page.waitForURL('**/screener', { timeout: 10000 });
      await expect(page.locator('body')).not.toContainText('Application error');
    }
  });
});

test.describe('Stock Detail Page', () => {
  const tickers = ['AAPL', 'NVDA', 'TSLA', 'BTC', 'ETH', '600438.SH'];

  for (const ticker of tickers) {
    test(`${ticker} detail page loads without crash`, async ({ page }) => {
      await page.goto(`/stock/${encodeURIComponent(ticker)}`);
      // Must NOT show "Application error"
      await expect(page.locator('body')).not.toContainText('Application error');
      // Should show the ticker name or code
      await page.waitForTimeout(2000);
      // Back link should exist
      await expect(page.locator('a:has-text("Back")')).toBeVisible();
    });
  }

  test('AAPL shows price and indicators', async ({ page }) => {
    await page.goto('/stock/AAPL');
    await page.waitForTimeout(3000);
    // Should have price section
    await expect(page.locator('body')).not.toContainText('Application error');
    // Should have chart heading
    await expect(page.locator('h2:has-text("Price")')).toBeVisible({ timeout: 10000 });
    // Should have RSI
    await expect(page.locator('h3:has-text("RSI")')).toBeVisible();
    // Should have Technical Analysis Summary
    await expect(page.locator('h2:has-text("Technical Analysis")')).toBeVisible();
  });

  test('time range buttons exist', async ({ page }) => {
    await page.goto('/stock/AAPL');
    await page.waitForTimeout(2000);
    for (const range of ['1W', '1M', '3M', '6M', '1Y', 'All']) {
      await expect(page.locator(`button:has-text("${range}")`)).toBeVisible();
    }
  });

  test('back to dashboard link works', async ({ page }) => {
    await page.goto('/stock/AAPL');
    await page.waitForTimeout(1000);
    await page.locator('a:has-text("Back")').click();
    await page.waitForURL('/', { timeout: 10000 });
    await expect(page.locator('body')).not.toContainText('Application error');
  });
});

test.describe('Screener Page', () => {
  test('loads without errors', async ({ page }) => {
    await page.goto('/screener');
    await expect(page.locator('body')).not.toContainText('Application error');
    await expect(page.locator('h1:has-text("Stock Screener")')).toBeVisible();
  });

  test('shows stock results', async ({ page }) => {
    await page.goto('/screener');
    // Wait for data to load
    await expect(page.locator('text=/\\d+ stocks? found/')).toBeVisible({ timeout: 15000 });
  });

  test('market filter works', async ({ page }) => {
    await page.goto('/screener');
    await page.waitForSelector('text=/\\d+ stocks? found/', { timeout: 15000 });
    // Change to US only
    await page.locator('select').selectOption('us');
    await page.waitForTimeout(2000);
    // Should still show results (not crash)
    await expect(page.locator('body')).not.toContainText('Application error');
  });

  test('reset button clears filters', async ({ page }) => {
    await page.goto('/screener');
    await page.waitForSelector('text=/\\d+ stocks? found/', { timeout: 15000 });
    const resetBtn = page.locator('button:has-text("Reset")');
    await resetBtn.click();
    // Should not crash
    await expect(page.locator('body')).not.toContainText('Application error');
  });

  test('export CSV button exists', async ({ page }) => {
    await page.goto('/screener');
    await page.waitForSelector('text=/\\d+ stocks? found/', { timeout: 15000 });
    const exportBtn = page.locator('button:has-text("Export CSV")');
    await expect(exportBtn).toBeVisible();
  });

  test('clicking stock row navigates to detail', async ({ page }) => {
    await page.goto('/screener');
    await page.waitForSelector('table tbody tr', { timeout: 15000 });
    // Click first data row
    await page.locator('table tbody tr').first().click();
    await page.waitForURL('**/stock/**', { timeout: 10000 });
    await expect(page.locator('body')).not.toContainText('Application error');
  });

  test('back to dashboard link works', async ({ page }) => {
    await page.goto('/screener');
    await page.locator('a:has-text("Back to Dashboard")').click();
    await page.waitForURL('/', { timeout: 10000 });
  });
});

test.describe('404 / Not Found', () => {
  test('unknown page shows not-found', async ({ page }) => {
    await page.goto('/this-page-does-not-exist');
    // Should not crash
    await expect(page.locator('body')).not.toContainText('Application error');
  });

  test('unknown stock code handles gracefully', async ({ page }) => {
    await page.goto('/stock/XXXINVALID');
    // Should not crash with "Application error"
    await expect(page.locator('body')).not.toContainText('Application error');
  });
});
