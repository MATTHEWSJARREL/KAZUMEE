import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.KAZUMI_BACKEND_URL || 'http://127.0.0.1:8000';
let backendReachable: boolean | null = null;

async function hasBackend(
  request: import('@playwright/test').APIRequestContext,
) {
  if (backendReachable !== null) return backendReachable;
  try {
    const res = await request.get(`${BACKEND_URL}/api/health`, { timeout: 2500 });
    backendReachable = res.ok();
  } catch {
    backendReachable = false;
  }
  return backendReachable;
}

async function requireBackend(
  request: import('@playwright/test').APIRequestContext,
) {
  const reachable = await hasBackend(request);
  test.skip(
    !reachable,
    `Backend is not reachable at ${BACKEND_URL}. Start API server to run auth e2e tests.`,
  );
}

const makeEmail = (prefix: string) =>
  `${prefix}.${Date.now()}@example.com`;

const disableAuthBypass = async (page: import('@playwright/test').Page) => {
  await page.addInitScript(() => {
    localStorage.setItem('kazumi_auth_bypass', 'false');
    localStorage.removeItem('kazumi_auth_token');
    localStorage.removeItem('kazumi_active_streamer_id');
  });
};

async function registerUser(
  request: import('@playwright/test').APIRequestContext,
  {
    email,
    password,
    role,
  }: { email: string; password: string; role: 'viewer' | 'streamer' },
) {
  const res = await request.post(`${BACKEND_URL}/auth/register`, {
    data: { email, password, role },
  });
  if (!res.ok()) {
    const body = await res.text();
    throw new Error(`Failed to register ${role}: ${res.status()} ${body}`);
  }
  return res.json();
}

async function loginUser(
  request: import('@playwright/test').APIRequestContext,
  {
    email,
    password,
  }: { email: string; password: string },
) {
  const res = await request.post(`${BACKEND_URL}/auth/login`, {
    data: { email, password },
  });
  if (!res.ok()) {
    const body = await res.text();
    throw new Error(`Failed to login: ${res.status()} ${body}`);
  }
  return res.json();
}

test('streamer can register and access dashboard', async ({ page, request }) => {
  await requireBackend(request);
  const password = 'TestPass123!';
  const streamerEmail = makeEmail('streamer');

  await registerUser(request, { email: streamerEmail, password, role: 'streamer' });

  await disableAuthBypass(page);
  const loginData = await loginUser(request, { email: streamerEmail, password });
  await page.addInitScript((token: string) => {
    localStorage.setItem('kazumi_auth_token', token);
  }, loginData.token);
  await page.goto('about:blank');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Main Dashboard' })).toBeVisible();
});

test('viewer can login and access viewer mode after selecting streamer', async ({ page, request }) => {
  await requireBackend(request);
  const password = 'TestPass123!';
  const streamerEmail = makeEmail('streamer');
  const viewerEmail = makeEmail('viewer');

  const streamerReg = await registerUser(request, { email: streamerEmail, password, role: 'streamer' });
  await registerUser(request, { email: viewerEmail, password, role: 'viewer' });

  await disableAuthBypass(page);
  const loginData = await loginUser(request, { email: viewerEmail, password });
  await page.addInitScript((token: string) => {
    localStorage.setItem('kazumi_auth_token', token);
  }, loginData.token);

  const setStreamerRes = await request.post(`${BACKEND_URL}/auth/active-streamer`, {
    data: { streamer_id: streamerReg.streamer_id || 1 },
    headers: { Authorization: `Bearer ${loginData.token}` },
  });
  if (!setStreamerRes.ok()) {
    const body = await setStreamerRes.text();
    throw new Error(`Failed to set active streamer: ${setStreamerRes.status()} ${body}`);
  }

  await page.goto('/viewer');
  await expect(page.getByRole('heading', { name: 'Viewer Mode' })).toBeVisible();
});
