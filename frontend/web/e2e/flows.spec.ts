import { test, expect } from '@playwright/test';

const enableAuthBypass = async (page: import('@playwright/test').Page) => {
  await page.addInitScript(() => {
    localStorage.setItem('kazumi_auth_bypass', 'true');
    localStorage.setItem('kazumi_active_streamer_id', '1');
    localStorage.removeItem('kazumi_auth_token');
  });
};

const disableAuthBypass = async (page: import('@playwright/test').Page) => {
  await page.addInitScript(() => {
    localStorage.setItem('kazumi_auth_bypass', 'false');
    localStorage.removeItem('kazumi_auth_token');
    localStorage.removeItem('kazumi_active_streamer_id');
  });
};

test('unauthenticated viewer route redirects to auth', async ({ page }) => {
  await disableAuthBypass(page);
  await page.goto('/viewer');
  await expect(page).toHaveURL(/\/auth/);
});

test('viewer shell loads in bypass mode', async ({ page }) => {
  await enableAuthBypass(page);
  await page.goto('/viewer');

  await expect(page.getByPlaceholder('Ask Kazumi anything...')).toBeVisible();
});

test('streamer routes load in bypass mode', async ({ page }) => {
  await enableAuthBypass(page);
  await page.goto('/');
  await expect(page.locator('body')).toBeVisible();

  await page.goto('/stream-health');
  await expect(page.getByPlaceholder('Ask Kazumi anything...')).toBeVisible();
});
