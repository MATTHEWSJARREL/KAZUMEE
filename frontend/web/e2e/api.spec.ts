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
    `Backend is not reachable at ${BACKEND_URL}. Start API server to run backend e2e tests.`,
  );
}

const makeEmail = (prefix: string) =>
  `${prefix}.${Date.now()}@example.com`;

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
  expect(res.ok()).toBeTruthy();
  return res.json();
}

test('auth register + login returns token', async ({ request }) => {
  await requireBackend(request);
  const password = 'TestPass123!';
  const email = makeEmail('api');

  const register = await request.post(`${BACKEND_URL}/auth/register`, {
    data: { email, password, role: 'viewer' },
  });
  expect(register.ok()).toBeTruthy();
  const regJson = await register.json();
  expect(regJson.token).toBeTruthy();

  const login = await request.post(`${BACKEND_URL}/auth/login`, {
    data: { email, password },
  });
  expect(login.ok()).toBeTruthy();
  const loginJson = await login.json();
  expect(loginJson.token).toBeTruthy();
});

test('auth me returns user with valid token', async ({ request }) => {
  await requireBackend(request);
  const password = 'TestPass123!';
  const email = makeEmail('api');

  const register = await request.post(`${BACKEND_URL}/auth/register`, {
    data: { email, password, role: 'viewer' },
  });
  const regJson = await register.json();

  const me = await request.get(`${BACKEND_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${regJson.token}` },
  });
  expect(me.ok()).toBeTruthy();
  const meJson = await me.json();
  expect(meJson.user?.email).toBe(email.toLowerCase());
});

test('viewer dashboard returns data', async ({ request }) => {
  await requireBackend(request);
  const password = 'TestPass123!';
  const streamerEmail = makeEmail('dashstreamer');
  const viewerEmail = makeEmail('dashviewer');

  const streamerReg = await registerUser(request, {
    email: streamerEmail,
    password,
    role: 'streamer',
  });
  const viewerReg = await registerUser(request, {
    email: viewerEmail,
    password,
    role: 'viewer',
  });

  const setStreamerRes = await request.post(`${BACKEND_URL}/auth/active-streamer`, {
    data: { streamer_id: streamerReg.streamer_id || 1 },
    headers: { Authorization: `Bearer ${viewerReg.token}` },
  });
  expect(setStreamerRes.ok()).toBeTruthy();

  const res = await request.get(`${BACKEND_URL}/api/viewer/dashboard`, {
    headers: { Authorization: `Bearer ${viewerReg.token}` },
  });
  expect(res.ok()).toBeTruthy();
  const data = await res.json();
  expect(data.viewer).toBeTruthy();
  expect(data.active_streamer_id).toBeTruthy();
});

test('commands process returns 200', async ({ request }) => {
  await requireBackend(request);
  const password = 'TestPass123!';
  const streamerEmail = makeEmail('cmdstreamer');
  const streamerReg = await registerUser(request, {
    email: streamerEmail,
    password,
    role: 'streamer',
  });

  const res = await request.post(`${BACKEND_URL}/api/commands/process`, {
    data: { command: 'switch to gameplay', role: 'streamer' },
    headers: {
      Authorization: `Bearer ${streamerReg.token}`,
      'X-Streamer-Id': String(streamerReg.streamer_id || 1),
    },
  });
  expect(res.ok()).toBeTruthy();
});

test('clips list endpoints respond (may be empty)', async ({ request }) => {
  await requireBackend(request);
  const recent = await request.get(`${BACKEND_URL}/clips/recent?limit=5`);
  expect([200, 404]).toContain(recent.status());
  const pending = await request.get(`${BACKEND_URL}/clips/pending`);
  // Pending clips require streamer auth; unauth can return 401/403.
  expect([200, 401, 403, 404]).toContain(pending.status());
});
