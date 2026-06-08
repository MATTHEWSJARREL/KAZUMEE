import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  useLocation,
} from 'react-router';

import {
  useEffect,
  useState,
  useRef,
  type ReactNode,
  Component,
} from 'react';

// Keep the Query Client setup here so it's global
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import './global.css';

import fetch from '@/__create/fetch';

import { Toaster, toast } from 'sonner';
import { Home } from 'lucide-react';
import { ClipSearchProvider } from '@/lib/ClipSearchContext';
import { SettingsProvider } from '@/lib/SettingsContext';
// @ts-ignore
import ClipSearchResults from '@/components/ClipSearchResults';
// @ts-ignore
import ObsStatus from '@/components/ObsStatus';
import KazumiSidePanel from '@/components/KazumiSidePanel';

import { useObsTruth } from '@/hooks/useObsTruth';
import KazumiChat from '@/components/KazumiChat';
import { apiFetch, isAuthBypassEnabled, clearAuthToken, clearActiveStreamerId, clearAuthBypass } from '@/lib/apiClient';

import type { Route } from './+types/root';

const checkSession = async () => {
  const res = await apiFetch("/auth/me");
  if (res.status === 401 || res.status === 403) {
    return { status: "unauthenticated" as const, user: null, streamerId: null };
  }
  if (!res.ok) {
    return { status: "error" as const, user: null, streamerId: null };
  }
  const data = await res.json();
  return {
    status: data?.user ? ("authenticated" as const) : ("unauthenticated" as const),
    user: data?.user || null,
    streamerId: data?.streamer_id || null,
  };
};

/* --- Query Client Instance --- */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

if (globalThis.window) {
  globalThis.window.fetch = fetch;
  try {
    const cached = localStorage.getItem("kazumi_settings");
    if (cached) {
      const parsed = JSON.parse(cached);
      if (parsed?.appearance?.darkMode) {
        document.documentElement.classList.add("kazumi-dark");
      }
    }
  } catch {
    // ignore
  }
}

function ErrorFallback() {
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-[#18191B] text-white px-4 py-3 rounded-lg shadow-lg">
      An unexpected error occurred.
    </div>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  console.error(error);
  return <ErrorFallback />;
}

class ErrorBoundaryWrapper extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error: unknown) { console.error(error); }
  render() {
    if (this.state.hasError) return <ErrorFallback />;
    return this.props.children;
  }
}

function ClientOnly({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  if (!mounted) return null;
  return <>{children}</>;
}

function RoleGuard() {
  const location = useLocation();
  const [role, setRole] = useState<string | null>(null);
  const [streamerId, setStreamerId] = useState<number | null>(null);
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    if (window.location.pathname.startsWith('/auth')) {
      setChecking(false);
      return;
    }

    const bypassAuth = isAuthBypassEnabled();
    if (bypassAuth) {
      setRole('streamer');
      setChecking(false);
      return;
    }
    setChecking(true);
    checkSession()
      .then(({ status, user, streamerId: activeStreamerId }) => {
        if (status === "unauthenticated") {
          clearAuthToken();
          clearActiveStreamerId();
          clearAuthBypass();
          sessionStorage.setItem("kazumi_session_expired", "true");
          toast.error("Session expired. Please sign in again.");
          window.location.href = '/auth';
          return;
        }
        if (status === "error") {
          setChecking(false);
          return;
        }
        const userRole = user?.role || null;
        if (!userRole) {
          clearAuthToken();
          clearActiveStreamerId();
          clearAuthBypass();
          sessionStorage.setItem("kazumi_session_expired", "true");
          toast.error("Session expired. Please sign in again.");
          window.location.href = '/auth';
          return;
        }
        setRole(userRole);
        setStreamerId(activeStreamerId);
        const path = window.location.pathname;
        const viewerOnly = ['/viewer'];
        const streamerOnly = [
          '/',
          '/stream-health',
          '/clips',
          '/moderation',
          '/commands',
          '/analytics',
          '/ml-training',
          '/voice',
          '/settings',
        ];

        if (userRole === 'viewer') {
          if (streamerOnly.includes(path)) {
            window.location.href = '/viewer';
          }
        }
        if (userRole === 'streamer' && viewerOnly.includes(path)) {
          window.location.href = '/';
        }
        setChecking(false);
      })
      .catch(() => {
        toast.warning("Network issue while checking session.");
        setChecking(false);
      });
  }, [location.pathname]);

  return (
    <>
      {checking && !window.location.pathname.startsWith('/auth') && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-white/80 backdrop-blur-sm">
          <div className="kazumi-card px-6 py-4">
            <div className="w-10 h-10 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <div className="text-sm text-gray-600">Checking session…</div>
          </div>
        </div>
      )}
      <div className="hidden">
        {role}
        {streamerId}
      </div>
    </>
  );
}

function GlobalExperience() {
  const isAuthRoute =
    typeof window !== 'undefined' && window.location.pathname.startsWith('/auth');

  if (isAuthRoute) {
    return <Toaster position="bottom-right" />;
  }

  return (
    <>
      <ClipSearchResults />
      <Toaster position="bottom-right" />
      <KazumiChat />
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Layout (Document Shell) - FIXING THE UI LOOK HERE                  */
/* ------------------------------------------------------------------ */
export function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link
          href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500&display=swap"
          rel="stylesheet"
        />
        <Meta />
        <Links />
      </head>
      {/* Ensure the body has the right background to match your design */}
      <body className="bg-[var(--void)] text-[var(--text)] antialiased font-body">
        <QueryClientProvider client={queryClient}>
          <ClientOnly>
            <SettingsProvider>
              <ClipSearchProvider>
                <ErrorBoundaryWrapper>
                  <RoleGuard />
                  {children}
                </ErrorBoundaryWrapper>
                <GlobalExperience />
              </ClipSearchProvider>
            </SettingsProvider>
          </ClientOnly>
        </QueryClientProvider>

        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

/* ------------------------------------------------------------------ */
/* App Root                                                           */
/* ------------------------------------------------------------------ */
export default function App() {
  const location = useLocation();
  const isAuthRoute =
    typeof window !== "undefined" && window.location.pathname.startsWith("/auth");
  const [authUser, setAuthUser] = useState<any>(null);
  const [hasSession, setHasSession] = useState<boolean>(false);
  const [sessionState, setSessionState] = useState<"checking" | "authenticated" | "unauthenticated">(
    "checking",
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"unknown" | "online" | "degraded" | "offline">("unknown");
  const menuRef = useRef<HTMLDivElement | null>(null);
  const showObs = !isAuthRoute && (isAuthBypassEnabled() || authUser?.role === "streamer");
  const { state } = useObsTruth(showObs);

  useEffect(() => {
    if (isAuthRoute) {
      setAuthUser(null);
      setHasSession(false);
      setSessionState("unauthenticated");
      return;
    }

    let mounted = true;
    const loadUser = async () => {
      setSessionState("checking");
      try {
        const { status, user } = await checkSession();
        if (!mounted) return;
        if (status === "authenticated") {
          setAuthUser(user);
          setHasSession(true);
          setSessionState("authenticated");
          return;
        }
        if (status === "unauthenticated") {
          clearAuthToken();
          clearActiveStreamerId();
          clearAuthBypass();
        }
        setSessionState((current) =>
          current === "authenticated" ? "authenticated" : "checking",
        );
      } catch {
        if (!mounted) return;
        setSessionState((current) =>
          current === "authenticated" ? "authenticated" : "checking",
        );
      }
    };
    void loadUser();
    return () => {
      mounted = false;
    };
  }, [isAuthRoute, location.pathname]);

  useEffect(() => {
    if (isAuthRoute) {
      setBackendStatus("unknown");
      return;
    }

    let mounted = true;
    let consecutiveFailures = 0;
    const check = async () => {
      try {
        const res = await apiFetch("/api/health");
        if (!mounted) return;
        if (!res.ok) {
          consecutiveFailures += 1;
          setBackendStatus(consecutiveFailures >= 2 ? "offline" : "unknown");
          return;
        }
        const data = await res.json();
        consecutiveFailures = 0;
        setBackendStatus(data?.status === "ok" ? "online" : "degraded");
      } catch {
        if (mounted) {
          consecutiveFailures += 1;
          setBackendStatus(consecutiveFailures >= 2 ? "offline" : "unknown");
        }
      }
    };
    check();
    const interval = setInterval(check, 12000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [isAuthRoute]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  const handleLogout = () => {
    clearAuthToken();
    clearActiveStreamerId();
    clearAuthBypass();
    setAuthUser(null);
    setHasSession(false);
    setSessionState("unauthenticated");
    window.location.href = '/auth';
  };

  if (isAuthRoute) {
    return (
      <div className="flex flex-col min-h-screen">
        <main className="flex-1">
          <Outlet context={{ obsState: state }} />
        </main>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Global OBS truth bar */}
      <div className="border-b px-4 py-2 bg-white sticky top-0 z-50">
        {!isAuthBypassEnabled() && sessionState === "unauthenticated" && (
          <div className="mb-2 px-3 py-2 rounded-md text-xs bg-yellow-100 text-yellow-800">
            You are signed out. Sign in to enable live actions.
          </div>
        )}
        {backendStatus !== "online" && backendStatus !== "unknown" && (
          <div className={`mb-2 px-3 py-2 rounded-md text-xs ${
            backendStatus === "degraded"
              ? "bg-yellow-100 text-yellow-800"
              : "bg-red-100 text-red-700"
          }`}>
            {backendStatus === "degraded"
              ? "Backend is degraded. Some features may be delayed."
              : (!isAuthBypassEnabled() && !hasSession)
                ? "Backend status unknown while signed out. Sign in, then retry."
                : "Backend is offline. Live actions are unavailable."}
          </div>
        )}
        <div className="flex items-center justify-between gap-4">
          {showObs ? (
            <ObsStatus state={state} />
          ) : sessionState === "checking" ? (
            <div className="text-xs text-gray-600">Checking session...</div>
          ) : (
            <div className="text-xs text-gray-600">Viewer mode active</div>
          )}
          <div className="flex items-center gap-2 text-xs" ref={menuRef}>
            {authUser?.role === "streamer" && location.pathname !== "/" && (
              <a
                href="/"
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100"
              >
                <Home className="w-4 h-4" />
                <span className="hidden sm:inline">Home</span>
              </a>
            )}
            <button
              onClick={() => setAssistantOpen(true)}
              className="hidden sm:inline-flex px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100"
            >
              Ask Kazumi
            </button>
            {authUser ? (
              <div className="relative">
                <button
                  onClick={() => setMenuOpen((v) => !v)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-full border border-gray-200 bg-white hover:bg-gray-50"
                >
                  <span className="w-7 h-7 rounded-full bg-black text-white text-[11px] font-bold flex items-center justify-center">
                    {authUser.email?.slice(0, 2)?.toUpperCase() || "KU"}
                  </span>
                  <span className="hidden md:inline text-gray-600">{authUser.email}</span>
                </button>
                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-48 rounded-lg border border-gray-200 bg-white shadow-lg z-50">
                    <a
                      href="/settings#profile"
                      className="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      Profile
                    </a>
                    <a
                      href="/settings"
                      className="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      Settings
                    </a>
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      Log out
                    </button>
                  </div>
                )}
              </div>
            ) : hasSession ? (
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100"
              >
                Sign out
              </button>
            ) : (
              <a
                href="/auth"
                className="px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100"
              >
                Sign in
              </a>
            )}
          </div>
        </div>
      </div>

      <main className="flex-1">
        <Outlet context={{ obsState: state }} />
      </main>

      <KazumiSidePanel
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        userKey={authUser?.email || null}
        role={authUser?.role || null}
      />
    </div>
  );
}
