import { Hono } from 'hono';
import { createHonoServer } from 'react-router-hono-server/node';

const app = new Hono();

// Health check
app.get('/health', (c) => c.json({ ok: true }));

// TEMP: stub integrations so frontend doesn’t crash
app.all('/integrations/*', (c) =>
  c.json({ error: 'Integrations disabled in dev' }, 501)
);

app.post('/api/voice-command', async (c) => {
  const body = await c.req.json().catch(() => ({}));

  return c.json({
    success: true,
    response: `DEV MODE: received command "${body.command ?? 'unknown'}"`,
    command: body.command ?? null,
  });
});

export default await createHonoServer({
  app,
  defaultLogger: true,
});
