import { test, expect } from '@playwright/test';

test('home loads', async ({ page }) => {
  await page.goto('http://localhost:5173/login');
  await expect(page.locator('input[name="email"]')).toBeVisible();
});
