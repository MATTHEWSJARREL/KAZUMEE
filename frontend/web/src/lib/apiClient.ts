const resolveApiBase = () => {
  // Try React App env var first (for Vercel)
  if (import.meta.env.REACT_APP_API_URL) return import.meta.env.REACT_APP_API_URL;
  // Then try Next.js env vars
  if (import.meta.env.NEXT_PUBLIC_API_URL) return import.meta.env.NEXT_PUBLIC_API_URL;
  if (typeof window === "undefined") return "http://127.0.0.1:8000";

  const host = window.location.hostname || "127.0.0.1";
  const protocol = window.location.protocol === "https:" ? "https" : "http";
  const port = import.meta.env.NEXT_PUBLIC_API_PORT || "8000";
  return `${protocol}://${host}:${port}`;
};

const resolveWsBase = () => {
  // Try React App env var first (for Vercel)
  if (import.meta.env.REACT_APP_API_URL) {
    const apiUrl = import.meta.env.REACT_APP_API_URL;
    const protocol = apiUrl.startsWith("https") ? "wss" : "ws";
    const host = apiUrl.replace("https://", "").replace("http://", "");
    return `${protocol}://${host}`;
  }
  // Then try Next.js env vars
  if (import.meta.env.NEXT_PUBLIC_WS_URL) return import.meta.env.NEXT_PUBLIC_WS_URL;
  if (typeof window === "undefined") return "ws://127.0.0.1:8000";

  const host = window.location.hostname || "127.0.0.1";
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const port = import.meta.env.NEXT_PUBLIC_API_PORT || "8000";
  return `${protocol}://${host}:${port}`;
};

export const apiBase = resolveApiBase();
export const wsBase = resolveWsBase();

export const buildApiUrl = (path: string) => {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (!path.startsWith("/")) return `${apiBase}/${path}`;
  return `${apiBase}${path}`;
};

const tokenKey = "kazumi_auth_token";
const tokenKeySession = "kazumi_auth_token_session";
const persistKey = "kazumi_auth_persist";
const streamerKey = "kazumi_active_streamer_id";
const bypassKey = "kazumi_auth_bypass";
const authMeCacheKey = "kazumi_auth_me_cache";

export const isAuthBypassEnabled = () => {
  if (typeof window === "undefined") return false;
  const envEnabled = process.env.NEXT_PUBLIC_AUTH_BYPASS === "true";
  const stored = localStorage.getItem(bypassKey) === "true";
  return envEnabled || stored;
};

export const setAuthBypassEnabled = (enabled: boolean) => {
  if (typeof window === "undefined") return;
  localStorage.setItem(bypassKey, enabled ? "true" : "false");
};

export const setAuthToken = (token: string, persist: boolean = false) => {
  if (typeof window === "undefined") return;
  clearApiResponseCaches();
  if (persist) {
    localStorage.setItem(tokenKey, token);
    sessionStorage.removeItem(tokenKeySession);
    localStorage.setItem(persistKey, "true");
  } else {
    sessionStorage.setItem(tokenKeySession, token);
    localStorage.removeItem(tokenKey);
    localStorage.setItem(persistKey, "false");
  }
  window.dispatchEvent(new Event("kazumi:auth"));
};

export const clearAuthToken = () => {
  if (typeof window === "undefined") return;
  clearApiResponseCaches();
  localStorage.removeItem(tokenKey);
  sessionStorage.removeItem(tokenKeySession);
  localStorage.removeItem(persistKey);
};

export const clearActiveStreamerId = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem(streamerKey);
};

export const clearAuthBypass = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem(bypassKey);
};

export const getAuthToken = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(tokenKey) || sessionStorage.getItem(tokenKeySession);
};

export const getAuthPersist = () => {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(persistKey) === "true";
};

export const setActiveStreamerId = (streamerId: number) => {
  if (typeof window === "undefined") return;
  streamTokenCache.clear();
  localStorage.setItem(streamerKey, String(streamerId));
  window.dispatchEvent(new Event("kazumi:auth"));
};

export const getActiveStreamerId = () => {
  if (typeof window === "undefined") return null;
  const value = localStorage.getItem(streamerKey);
  return value ? Number(value) : null;
};

const sleep = (ms: number) => new Promise((res) => setTimeout(res, ms));

type CachedApiResponse = {
  body: string;
  expiresAt: number;
  headers: [string, string][];
  status: number;
  statusText: string;
};

const streamTokenCache = new Map<string, CachedApiResponse | Promise<CachedApiResponse>>();
let authMeCache: CachedApiResponse | Promise<CachedApiResponse> | null = null;

function clearApiResponseCaches() {
  authMeCache = null;
  streamTokenCache.clear();
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(authMeCacheKey);
  }
}

const readStoredAuthMe = () => {
  if (typeof window === "undefined") return null;
  try {
    const stored = sessionStorage.getItem(authMeCacheKey);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as CachedApiResponse;
    if (parsed.expiresAt <= Date.now()) {
      sessionStorage.removeItem(authMeCacheKey);
      return null;
    }
    return parsed;
  } catch {
    sessionStorage.removeItem(authMeCacheKey);
    return null;
  }
};

const writeStoredAuthMe = (cached: CachedApiResponse) => {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(authMeCacheKey, JSON.stringify(cached));
  } catch {
    // Ignore storage pressure; the in-memory cache still dedupes this tab.
  }
};

const responseFromCache = (cached: CachedApiResponse) =>
  new Response(cached.body, {
    status: cached.status,
    statusText: cached.statusText,
    headers: cached.headers,
  });

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = 2,
): Promise<Response> {
  const method = (options.method || "GET").toUpperCase();
  const canRetry = method === "GET" || method === "HEAD";

  try {
    return await fetch(url, options);
  } catch (err: any) {
    // If an AbortController intentionally cancelled the request (unmount, new recap, etc),
    // do not retry. Retrying would just re-emit AbortError and create noise.
    if (err?.name === "AbortError") throw err;

    if (canRetry && retries > 0) {
      await sleep(300 * (3 - retries));
      return fetchWithRetry(url, options, retries - 1);
    }

    throw err;
  }
}


export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  if (isAuthBypassEnabled()) {
    if (path === "/auth/me") {
      const body = JSON.stringify({
        user: { email: "demo@kazumi.ai", role: "streamer" },
        streamer_id: getActiveStreamerId() || 1,
      });
      return new Response(body, { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (path === "/auth/streamers") {
      const body = JSON.stringify({
        streamers: [
          { id: 1, display_name: "Demo Streamer", platform: "twitch" },
        ],
      });
      return new Response(body, { status: 200, headers: { "Content-Type": "application/json" } });
    }
  }
  const headers = new Headers(options.headers || {});
  const token = getAuthToken();
  const streamerId = getActiveStreamerId();
  const isAuthBootstrapPath =
    path === "/auth/login" || path === "/auth/register";
  const method = (options.method || "GET").toUpperCase();

  // Keep login/register requests as clean as possible.
  if (!isAuthBootstrapPath) {
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (streamerId) headers.set("X-Streamer-Id", String(streamerId));
  }

  const hasExternalSignal = Boolean(options.signal);
  const shouldApplyTimeout = !hasExternalSignal && method !== "OPTIONS";
  const controller = shouldApplyTimeout ? new AbortController() : null;
  const timeoutMs = isAuthBootstrapPath ? 30000 : 45000;
  const timeoutId = controller
    ? setTimeout(() => controller.abort(`${method} ${path} timeout after ${timeoutMs}ms`), timeoutMs)
    : null;

  const shouldCacheStreamToken = path === "/auth/stream-token" && method === "POST";
  const shouldCacheAuthMe = path === "/auth/me" && method === "GET";
  const streamTokenCacheKey = shouldCacheStreamToken
    ? `${token || "cookie"}:${streamerId || ""}:${String(options.body || "")}`
    : "";

  try {
    // Auth endpoints need include credentials to handle session cookies
    const defaultCredentials = shouldCacheAuthMe ? "include" : "same-origin";
    const finalOptions: RequestInit = {
      ...options,
      // Use include for /auth/me to ensure session cookies are sent
      // Otherwise default to same-origin for consistency
      credentials: options.credentials || defaultCredentials,
      headers,
      signal: options.signal || controller?.signal,
    };


    if (shouldCacheAuthMe) {
      const cached = authMeCache || readStoredAuthMe();
      if (cached) {
        const resolved = await cached;
        if (resolved.expiresAt > Date.now()) return responseFromCache(resolved);
        authMeCache = null;
      }

      const pending = fetchWithRetry(buildApiUrl(path), finalOptions).then(async (res) => {
        const body = await res.text();
        const storedFallback = readStoredAuthMe();
        if (res.status === 429 && storedFallback) {
          authMeCache = storedFallback;
          return storedFallback;
        }

        const cachedResponse = {
          body,
          expiresAt: Date.now() + (res.ok ? 30_000 : 0),
          headers: Array.from(res.headers.entries()),
          status: res.status,
          statusText: res.statusText,
        };
        if (res.ok) {
          authMeCache = cachedResponse;
          writeStoredAuthMe(cachedResponse);
        } else {
          authMeCache = null;
        }
        return cachedResponse;
      }).catch((error) => {
        authMeCache = null;
        throw error;
      });
      authMeCache = pending;
      return responseFromCache(await pending);
    }

    if (shouldCacheStreamToken) {
      const cached = streamTokenCache.get(streamTokenCacheKey);
      if (cached) {
        const resolved = await cached;
        if (resolved.expiresAt > Date.now()) return responseFromCache(resolved);
        streamTokenCache.delete(streamTokenCacheKey);
      }

      const pending = fetchWithRetry(buildApiUrl(path), finalOptions).then(async (res) => {
        const body = await res.text();
        let expiresIn = 30;
        try {
          expiresIn = Number(JSON.parse(body)?.expires_in || expiresIn);
        } catch {
          // Keep a short cache for non-JSON responses too, mostly to dedupe bursts.
        }
        const cachedResponse = {
          body,
          expiresAt: Date.now() + Math.max(5, Math.min(expiresIn, 60)) * 1000,
          headers: Array.from(res.headers.entries()),
          status: res.status,
          statusText: res.statusText,
        };
        if (!res.ok) {
          streamTokenCache.delete(streamTokenCacheKey);
          return cachedResponse;
        }
        streamTokenCache.set(streamTokenCacheKey, cachedResponse);
        return cachedResponse;
      });
      streamTokenCache.set(streamTokenCacheKey, pending);
      return responseFromCache(await pending);
    }

    return await fetchWithRetry(buildApiUrl(path), finalOptions);
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}
