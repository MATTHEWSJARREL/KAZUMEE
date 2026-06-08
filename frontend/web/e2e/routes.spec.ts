import { test, expect } from '@playwright/test';

const enableAuthBypass = async (page: import('@playwright/test').Page) => {
  await page.addInitScript(() => {
    localStorage.setItem('kazumi_auth_bypass', 'true');
    localStorage.setItem('kazumi_active_streamer_id', '1');
  });
};

const routes = [
  '/',
  '/viewer',
  '/stream-health',
  '/clips',
  '/moderation',
  '/commands',
  '/analytics',
  '/ml-training',
  '/voice',
  '/settings',
];

for (const route of routes) {
  test(`route loads: ${route}`, async ({ page }) => {
    await enableAuthBypass(page);
    const response = await page.goto(route);
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(400);
    await expect(page.locator('body')).toBeVisible();
  });
}
