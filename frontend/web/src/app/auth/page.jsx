"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import "../auth.css";
import { AuthSocialProof, AuthErrorMessage, AuthSuccessMessage } from "@/components/auth/AuthSocialProof";
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

    // Validation
    if (!email.trim()) {
      setMessage("Email is required");
      toast.error("Email is required");
      setSubmitting(false);
      return;
    }
    if (!password.trim()) {
      setMessage("Password is required");
      toast.error("Password is required");
      setSubmitting(false);
      return;
    }
    if (mode === "register" && password.length < 8) {
      setMessage("Password must be at least 8 characters");
      toast.error("Password must be at least 8 characters");
      setSubmitting(false);
      return;
    }

    try {
      const payload = { email: email.toLowerCase().trim(), password };
      if (mode === "register") payload.role = role;

      const res = await apiFetch(`/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // Keep UI responsive even if backend returns non-JSON.
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const msg = data.detail || "Auth failed";
        setMessage(msg);
        toast.error(msg);
        return;
      }

      setAuthToken(
        data.token,
        Boolean(rememberMe || data?.user?.role === "streamer"),
      );
      setUser(data.user);

      if (data?.streamer_id) {
        setActiveStreamerId(data.streamer_id);
        setActiveStreamerIdState(data.streamer_id);
      } else {
        fetchStreamers();
      }

      setMessage("Welcome to Kazumi.");
      toast.success("Welcome to Kazumi.");

      // Redirect AFTER a successful response.
      if (mode === "login") {
        if (data?.user?.role === "streamer") {
          window.location.href = "/";
        } else if (data?.user?.role === "viewer") {
          window.location.href = "/viewer";
        }
      } else if (mode === "register") {
        if (data?.user?.role === "streamer") {
          window.location.href = "/onboarding";
        } else if (data?.user?.role === "viewer") {
          window.location.href = "/viewer";
        }
      }
    } catch (error) {
      const detail =
        error instanceof DOMException && error.name === "AbortError"
          ? "request timed out"
          : error instanceof Error && error.message
            ? error.message
            : "Unknown network error";
      setMessage(
        `Could not reach the backend (${detail}). Check API URL/server and try again.`,
      );
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

  return (
    <div
      className="auth-page-root"
      style={{
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0B1020",
      }}
    >
      {authLoading ? (
        <div className="auth-loading-spinner"></div>
      ) : (
        <div
          className={`container ${mode === "register" ? "right-panel-active" : ""}`}
          style={{
            width: "900px",
            maxWidth: "calc(100vw - 48px)",
          }}
        >
          {/* Sign In Form */}
          <div className="form-container sign-in-container">
            <form>
              <div style={{ textAlign: "center" }}>
                <img src="/logo.png" alt="Kazumi" className="auth-logo" />
              </div>

              <h2>Sign In</h2>
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <label>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                Remember me
              </label>

              {message && mode === "login" && (
                <div
                  className={`auth-message ${
                    message.includes("failed") || message.includes("could not")
                      ? "error"
                      : "success"
                  }`}
                >
                  {message}
                </div>
              )}

              <button type="button" onClick={handleAuth} disabled={submitting}>
                {submitting ? "Signing In..." : "Sign In"}
              </button>

              {mode === "login" && (
                <div className="reset-section">
                  <span className="reset-label">Forgot Password?</span>
                  <div className="reset-input-group">
                    <input
                      type="email"
                      placeholder="Email"
                      value={resetEmail}
                      onChange={(e) => setResetEmail(e.target.value)}
                    />
                    <button
                      type="button"
                      className="reset-button"
                      onClick={handleReset}
                      disabled={resetSending}
                    >
                      {resetSending ? "Sending..." : "Send"}
                    </button>
                  </div>
                </div>
              )}

              {user && (
                <>
                  <div className="user-section">
                    <div className="user-info">
                      Signed in as <strong>{user.email}</strong>
                    </div>

                    <label className="reset-label">Switch Role:</label>
                    <div className="role-selector">
                      {["viewer", "streamer"].map((r) => (
                        <button
                          key={r}
                          type="button"
                          className={`role-button ${user.role === r ? "active" : ""}`}
                          onClick={() => updateRole(r)}
                        >
                          {r === "viewer" ? "Viewer" : "Streamer"}
                        </button>
                      ))}
                    </div>
                  </div>

                  {user?.role === "viewer" && streamers.length > 0 && (
                    <div className="user-section">
                      <label className="reset-label">Who are you watching?</label>
                      <div className="streamer-list">
                        {streamers.map((s) => (
                          <button
                            key={s.id}
                            type="button"
                            className={`streamer-button ${
                              Number(activeStreamerId) === Number(s.id)
                                ? "active"
                                : ""
                            }`}
                            onClick={() => setActiveStreamer(s.id)}
                          >
                            {s.display_name}
                            <span className="streamer-platform">({s.platform})</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </form>
          </div>

          {/* Sign Up Form */}
          <div className="form-container sign-up-container">
            <form>
              <h2>Create Account</h2>
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <label className="reset-label">I want to be a:</label>
              <div className="role-selector">
                {["viewer", "streamer"].map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={`role-button ${role === r ? "active" : ""}`}
                    onClick={() => setRole(r)}
                  >
                    {r === "viewer" ? "Viewer" : "Streamer"}
                  </button>
                ))}
              </div>

              <label>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                Remember me
              </label>

              {message && mode === "register" && (
                <div
                  className={`auth-message ${
                    message.includes("failed") || message.includes("could not")
                      ? "error"
                      : "success"
                  }`}
                >
                  {message}
                </div>
              )}

              <button type="button" onClick={handleAuth} disabled={submitting}>
                {submitting ? "Creating..." : "Create Account"}
              </button>
            </form>
          </div>

          {/* Overlay */}
          <div className="overlay-container">
            <div className="overlay">
              <div className="overlay-panel overlay-left">
                <h1>Already have an account?</h1>
                <p>
                  Sign in with your email and password to access all the streaming tools.
                </p>
                <button type="button" className="ghost" onClick={() => setMode("login")}> 
                  Sign In
                </button>
              </div>
              <div className="overlay-panel overlay-right">
                <h1>Join Kazumi</h1>
                <p>
                  Create an account to get started with smart streaming.
                </p>
                <AuthSocialProof />
                <button type="button" className="ghost" onClick={() => setMode("register")} style={{marginTop: "24px"}}>
                  Create Account
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

