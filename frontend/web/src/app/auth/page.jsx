"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  apiFetch,
  setAuthToken,
  getAuthToken,
  setActiveStreamerId,
  getActiveStreamerId,
  getAuthPersist,
  clearAuthToken,
  clearActiveStreamerId,
  clearAuthBypass,
} from "@/lib/apiClient";

export default function AuthPage() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");
  const [user, setUser] = useState(null);
  const [message, setMessage] = useState("");
  const [streamers, setStreamers] = useState([]);
  const [rememberMe, setRememberMe] = useState(getAuthPersist());
  const [authLoading, setAuthLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetSending, setResetSending] = useState(false);
  const [activeStreamerId, setActiveStreamerIdState] = useState(
    getActiveStreamerId(),
  );

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      fetchMe().finally(() => {
        fetchStreamers();
        setAuthLoading(false);
      });
    } else {
      fetchStreamers();
      setAuthLoading(false);
    }
    const expired = sessionStorage.getItem("kazumi_session_expired");
    if (expired) {
      setMessage("Session expired. Please sign in again.");
      toast.error("Session expired. Please sign in again.");
      sessionStorage.removeItem("kazumi_session_expired");
    }
  }, []);

  const fetchMe = async () => {
    try {
      const res = await apiFetch("/auth/me");
      if (res.status === 401 || res.status === 403) {
        clearAuthToken();
        clearActiveStreamerId();
        clearAuthBypass();
        setUser(null);
        setMessage("Session expired. Please sign in again.");
        return;
      }
      if (!res.ok) {
        setMessage("Could not verify session right now. Please retry.");
        return;
      }
      const data = await res.json();
      if (!data?.user) {
        clearAuthToken();
        clearActiveStreamerId();
        clearAuthBypass();
        setUser(null);
        setMessage("Session expired. Please sign in again.");
        return;
      }
      setUser(data.user || null);
      if (data?.streamer_id) {
        setActiveStreamerId(data.streamer_id);
        setActiveStreamerIdState(data.streamer_id);
      }
    } catch {
      setMessage("Network issue while restoring session.");
      return;
    }
  };

  const fetchStreamers = async () => {
    try {
      const res = await apiFetch("/auth/streamers");
      if (!res.ok) {
        setStreamers([]);
        return;
      }
      const data = await res.json().catch(() => ({}));
      setStreamers(data.streamers || []);
    } catch {
      setStreamers([]);
    }
  };

  const handleAuth = async () => {
    setMessage("");
    setSubmitting(true);
    try {
      const payload = { email, password };
      if (mode === "register") payload.role = role;

      const res = await apiFetch(`/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = data.detail || "Auth failed";
        setMessage(msg);
        toast.error(msg);
        return;
      }
      setAuthToken(data.token, rememberMe);
      setUser(data.user);
      if (data?.streamer_id) {
        setActiveStreamerId(data.streamer_id);
        setActiveStreamerIdState(data.streamer_id);
      } else {
        fetchStreamers();
      }
      setMessage("Welcome to Kazumi.");
      toast.success("Welcome to Kazumi.");
      if (mode === "login" && data?.user?.role === "streamer") {
        window.location.href = "/";
      }
      if (mode === "login" && data?.user?.role === "viewer") {
        window.location.href = "/viewer";
      }
    } catch (error) {
      const detail =
        error instanceof DOMException && error.name === "AbortError"
          ? "request timed out"
          : error instanceof Error && error.message
            ? error.message
            : "Unknown network error";
      setMessage(`Could not reach the backend (${detail}). Check API URL/server and try again.`);
      toast.error("Could not reach backend.");
    } finally {
      setSubmitting(false);
    }
  };

  const updateRole = async (newRole) => {
    const res = await apiFetch("/auth/role", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: newRole }),
    });
    const data = await res.json();
    if (res.ok) {
      setUser((prev) => (prev ? { ...prev, role: data.role } : prev));
      if (data?.streamer_id) {
        setActiveStreamerId(data.streamer_id);
        setActiveStreamerIdState(data.streamer_id);
      }
      setMessage(`Role updated to ${data.role}.`);
      if (data.role === "streamer") {
        window.location.href = "/";
      } else if (data.role === "viewer") {
        window.location.href = "/viewer";
      }
    } else {
      setMessage(data.detail || "Failed to update role");
    }
  };

  const setActiveStreamer = async (streamerId) => {
    const res = await apiFetch("/auth/active-streamer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ streamer_id: streamerId }),
    });
    const data = await res.json();
    if (res.ok) {
      setActiveStreamerId(streamerId);
      setActiveStreamerIdState(streamerId);
      setMessage("Streamer selected.");
      window.location.href = "/viewer";
    } else {
      setMessage(data.detail || "Failed to set streamer.");
    }
  };

  const handleReset = async () => {
    if (!resetEmail.trim()) {
      toast.error("Enter your email to reset password.");
      return;
    }
    setResetSending(true);
    try {
      const res = await apiFetch("/auth/password-reset/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: resetEmail }),
      });
      const data = await res.json();
      toast.success(data?.message || "Reset link sent.");
      setMessage(data?.message || "Reset link sent.");
    } catch {
      toast.error("Failed to request reset.");
    } finally {
      setResetSending(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="kazumi-card w-full max-w-md p-6 text-center">
          <div className="w-10 h-10 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-sm text-gray-600">Checking session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="kazumi-card p-6 md:p-8">
          <h1 className="text-3xl font-bold mb-2">Welcome to Kazumi</h1>
          <p className="text-sm text-gray-600 mb-6">
            Stream smarter. Clip faster. Control your broadcast with confidence.
          </p>
          <div className="space-y-3 text-sm text-gray-700">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-black"></span>
              Real-time OBS control with safe viewer policies
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-black"></span>
              Groq-powered decisions and clip suggestions
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-black"></span>
              Viewer + streamer roles with proper guardrails
            </div>
          </div>
          <div className="mt-6 rounded-lg border border-black/10 bg-black/5 p-4 text-xs text-gray-600">
            Tip: Toggle “Remember me” if you’re on a shared machine.
          </div>
        </div>

        <div className="kazumi-card w-full p-6">
          <h2 className="text-2xl font-bold mb-1">Kazumi Access</h2>
          <p className="text-sm text-gray-600 mb-6">
            Sign in and pick your role to unlock the right tools.
          </p>

        <div className="flex gap-2 mb-6">
          {["login", "register"].map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 px-3 py-2 rounded-md text-sm font-semibold ${
                mode === m ? "bg-black text-white" : "bg-black/5 text-gray-700"
              }`}
            >
              {m === "login" ? "Sign In" : "Create Account"}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="w-full px-3 py-2 border border-black/10 rounded-md bg-white"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full px-3 py-2 border border-black/10 rounded-md bg-white"
          />
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            Remember me on this device
          </label>
          <div className="text-[11px] text-gray-500">
            If unchecked, you’ll be signed out when you close the tab.
          </div>

          {mode === "register" && (
            <div className="flex gap-2">
              {["viewer", "streamer"].map((r) => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  className={`flex-1 px-3 py-2 rounded-md text-sm font-semibold ${
                    role === r
                      ? "bg-black text-white"
                      : "bg-black/5 text-gray-700"
                  }`}
                >
                  {r === "viewer" ? "Viewer" : "Streamer"}
                </button>
              ))}
            </div>
          )}

          <button
            onClick={handleAuth}
            disabled={submitting}
            className="w-full px-4 py-2 bg-black text-white rounded-md hover:bg-gray-800"
          >
            {submitting ? "Working..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>
          {mode === "login" && (
            <div className="mt-3 text-xs text-gray-500">
              <div className="mb-2">Forgot your password?</div>
              <div className="flex gap-2">
                <input
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  placeholder="Email for reset link"
                  className="flex-1 px-3 py-2 border border-black/10 rounded-md bg-white text-xs"
                />
                <button
                  onClick={handleReset}
                  disabled={resetSending}
                  className="px-3 py-2 text-xs rounded-md border border-black/10 hover:bg-black/5"
                >
                  {resetSending ? "Sending..." : "Send"}
                </button>
              </div>
            </div>
          )}
        </div>

        {user && (
          <div className="mt-6 border-t border-black/5 pt-4">
            <div className="text-sm text-gray-700">
              Signed in as <span className="font-semibold">{user.email}</span>
            </div>
            <div className="flex gap-2 mt-3">
              {["viewer", "streamer"].map((r) => (
                <button
                  key={r}
                  onClick={() => updateRole(r)}
                className={`flex-1 px-3 py-2 rounded-md text-sm font-semibold ${
                  user.role === r
                    ? "bg-black text-white"
                    : "bg-black/5 text-gray-700"
                }`}
              >
                  {r === "viewer" ? "Viewer" : "Streamer"}
                </button>
              ))}
            </div>
          </div>
        )}

        {user?.role === "viewer" && (
          <div className="mt-6 border-t border-black/5 pt-4">
            <div className="text-sm font-semibold mb-2">Who are you watching?</div>
            <div className="space-y-2">
              {(streamers || []).map((s) => (
                <button
                  key={s.id}
                  onClick={() => setActiveStreamer(s.id)}
                  className={`w-full px-3 py-2 rounded-md text-sm font-semibold text-left ${
                    Number(activeStreamerId) === Number(s.id)
                      ? "bg-black text-white"
                      : "bg-black/5 text-gray-700"
                  }`}
                >
                  {s.display_name}{" "}
                  <span className="text-xs opacity-70">({s.platform})</span>
                </button>
              ))}
              {streamers.length === 0 && (
                <div className="text-xs text-gray-500">
                  No streamers yet. Ask a streamer to create an account.
                </div>
              )}
            </div>
          </div>
        )}

        {message && (
          <div className="mt-4 text-sm text-gray-600">{message}</div>
        )}
        {user && (
          <div className="mt-4 text-xs text-gray-500">
            Need to verify your email? (Stub){" "}
            <button
              onClick={async () => {
                try {
                  const res = await apiFetch("/auth/verify/request", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: user.email }),
                  });
                  const data = await res.json();
                  toast.success(data?.message || "Verification sent.");
                } catch {
                  toast.error("Failed to send verification.");
                }
              }}
              className="underline"
            >
              Resend verification
            </button>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
