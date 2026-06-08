import { test, expect } from '@playwright/test';

test('home loads', async ({ page }) => {
  const response = await page.goto('/');
  expect(response).not.toBeNull();
  expect(response!.status()).toBeLessThan(400);
  await expect(page.locator('body')).toBeVisible();
});
