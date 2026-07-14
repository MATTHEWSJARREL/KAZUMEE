"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router";

import { apiFetch } from '../../lib/apiClient';

const COLORS = {
  bg: "#08070F",
  surface: "#131120",
  accent: "#7C5CFC",
  text: "#EDE8FF",
  border: "#242235",
  dimDot: "#2E2B42",
  green: "#1FD47B",
  red: "#FF4D6D",
};

function LotusLogo() {
  return (
    <img
      src="/logo.png"
      alt="Kazumee"
      style={{ width: 120, height: 120, objectFit: "contain" }}
      onError={(e) => {
        e.currentTarget.style.display = "none";
      }}
    />
  );
}

function StepDots({ step }: { step: number }) {
  const steps = [1, 2, 3, 4];

  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: "flex", alignItems: "center" }}>
        {steps.map((s, idx) => {
          const isCompleted = s < step;
          const isCurrent = s === step;
          const dotBg = isCompleted || isCurrent ? COLORS.accent : COLORS.dimDot;
          const lineFill = s < step;

          return (
            <div key={s} style={{ display: "flex", alignItems: "center" }}>
              {idx !== 0 && (
                <div
                  style={{
                    width: 44,
                    height: 2,
                    background: lineFill ? COLORS.accent : COLORS.dimDot,
                    opacity: lineFill ? 1 : 0.85,
                    boxShadow: lineFill
                      ? `0 0 10px rgba(124,92,252,0.35)`
                      : undefined,
                  }}
                />
              )}
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: 999,
                  background: dotBg,
                  boxShadow: isCurrent
                    ? `0 0 0 6px rgba(124,92,252,0.16), 0 0 18px rgba(124,92,252,0.55)`
                    : isCompleted
                      ? `0 0 10px rgba(124,92,252,0.25)`
                      : "none",
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FieldLabel({ label }: { label: string }) {
  return (
    <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: "rgba(237,232,255,0.9)" }}>
      {label}
    </div>
  );
}

function Pill({
  tone,
  children,
}: {
  tone: "green" | "red" | "purple";
  children: React.ReactNode;
}) {
  const map = {
    green: {
      bg: "rgba(31,212,123,0.14)",
      border: "rgba(31,212,123,0.35)",
      text: COLORS.green,
    },
    red: {
      bg: "rgba(255,77,109,0.12)",
      border: "rgba(255,77,109,0.35)",
      text: COLORS.red,
    },
    purple: {
      bg: "rgba(124,92,252,0.14)",
      border: "rgba(124,92,252,0.35)",
      text: COLORS.accent,
    },
  }[tone];

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        borderRadius: 999,
        background: map.bg,
        border: `1px solid ${map.border}`,
        color: map.text,
        fontWeight: 800,
        fontSize: 12,
      }}
    >
      {children}
    </div>
  );
}

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);

  const [displayName, setDisplayName] = useState("");
  const [platform, setPlatform] = useState<"twitch" | "youtube" | "both">("twitch");

  const [obsPassword, setObsPassword] = useState("");
  const [obsTestState, setObsTestState] = useState<
    "idle" | "testing" | "connected" | "failed"
  >("idle");
  const [obsError, setObsError] = useState("");

  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(10);
  const [voiceStatus, setVoiceStatus] = useState<
    "idle" | "saving" | "saved" | "failed"
  >("idle");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const countdownTimerRef = useRef<number | null>(null);

  const [scenes, setScenes] = useState<Array<{ name: string }>>([]);
  const [sceneAliases, setSceneAliases] = useState<
    Record<string, Array<"Main" | "BRB" | "Facecam">>
  >({});
  const [savingScenes, setSavingScenes] = useState(false);

  const outerWrapperStyle = useMemo(
    () => ({
      minHeight: "100vh",
      background: COLORS.bg,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "'DM Sans', sans-serif",
      color: COLORS.text,
      padding: "24px",
    }),
    [],
  );

  const cardStyle = useMemo(
    () => ({
      background: COLORS.surface,
      border: `1px solid ${COLORS.border}`,
      borderRadius: "20px",
      padding: "48px",
      maxWidth: "520px",
      width: "100%",
      position: "relative",
    }),
    [],
  );

  useEffect(() => {
    void (async () => {
      try {
        const res = await apiFetch("/auth/me");
        if (!res.ok) return;
        const data = await res.json().catch(() => ({}));
        const user = data?.user || {};
        // Pre-fill display name from account.
        // Using the username part of email as a safe fallback.
        setDisplayName(
          user?.email ? String(user.email).split("@")[0] : "",
        );
      } catch {
        // ignore
      }
    })();
  }, []);

  const dotButtonStyle = (active: boolean) => ({
    flex: 1,
    padding: "12px 12px",
    borderRadius: 14,
    border: `1px solid ${active ? "rgba(124,92,252,0.55)" : "rgba(36,34,53,1)"}`,
    background: active ? "rgba(124,92,252,0.14)" : "rgba(0,0,0,0)",
    color: active ? COLORS.accent : COLORS.text,
    fontWeight: 900,
    cursor: "pointer",
    transition: "transform 80ms ease, background 120ms ease, border-color 120ms ease",
  });

  const stepTitleStyle = {
    fontFamily: "'Syne', sans-serif",
    fontSize: 28,
    fontWeight: 800,
    letterSpacing: "0.2px",
    marginBottom: 10,
  };

  const primaryButton = {
    width: "100%",
    padding: "14px 16px",
    borderRadius: 14,
    border: `1px solid rgba(124,92,252,0.55)`,
    background: COLORS.accent,
    color: "#0B0616",
    fontWeight: 1000,
    cursor: "pointer",
    boxShadow: `0 0 0 0 rgba(124,92,252,0)`,
  };

  const disabledButton = {
    ...primaryButton,
    opacity: 0.45,
    cursor: "not-allowed",
  };

  // ---------- Step 1 ----------
  const saveStep1AndNext = async () => {
    if (!displayName.trim()) return;
    // Save to localStorage as fallback, backend save happens at the end
    try {
      localStorage.setItem("kazumi_onboarding_display_name", displayName);
      localStorage.setItem("kazumi_onboarding_platform", platform);
    } catch {
      // ignore
    }
    setStep(2);
  };


  // ---------- Step 2 ----------
  const testObsConnection = async () => {
    setObsTestState("testing");
    setObsError("");

    try {
      const res = await apiFetch("/api/obs/test-connection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: obsPassword }),
      });

      if (res.ok) {
        setObsTestState("connected");
        return;
      }

      const payload = await res.json().catch(() => ({}));
      setObsTestState("failed");
      setObsError(payload?.detail || payload?.message || "Connection failed");
    } catch (e: any) {
      setObsTestState("failed");
      setObsError(e?.message || "Connection failed — is OBS open?");
    }
  };

  const saveObsPasswordAndNext = async () => {
    const res = await apiFetch("/api/streamer/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        obs_password: obsPassword,
      }),
    });

    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(payload?.detail || payload?.message || "Failed to save OBS password");
    }

    setStep(3);
  };

  // ---------- Step 3 ----------
  const animateWaveformBarStyle = (i: number) => {
    const delay = i * 0.12;
    return {
      width: 6,
      height: 22,
      background: COLORS.accent,
      borderRadius: 999,
      opacity: 0.9,
      animation: `kazumiWave 1s ${delay}s infinite ease-in-out`,
    };
  };

  const start10SecondRecording = async () => {
    if (recording) return;

    setVoiceStatus("saving");
    setRecording(true);
    setCountdown(10);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      chunksRef.current = [];

      const mimeCandidates = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/ogg",
      ];
      let mimeType = "";
      for (const candidate of mimeCandidates) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if ((window as any).MediaRecorder?.isTypeSupported?.(candidate)) {
          mimeType = candidate;
          break;
        }
      }

      const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
        const formData = new FormData();
        formData.append("audio", blob, "voice-sample.webm");
        try {
          await apiFetch("/api/voice-agent/fingerprint/record", {
            method: "POST",
            body: formData,
          });
          setVoiceStatus("saved");
        } catch {
          setVoiceStatus("failed");
        }
        stream.getTracks().forEach((t) => t.stop());
      };

      mr.start();

      countdownTimerRef.current = window.setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            window.clearInterval(countdownTimerRef.current ?? undefined);
            mr.stop();
            setRecording(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

    } catch (err) {
      console.error("Microphone error:", err);
      setVoiceStatus("failed");
      setRecording(false);
    }
  };
  return (
    <div style={outerWrapperStyle}>
      <style>{`
        @keyframes kazumiWave {
          0%, 100% { transform: scaleY(0.4); opacity: 0.5; }
          50% { transform: scaleY(1.2); opacity: 1; }
        }
      `}</style>

      <div style={cardStyle as React.CSSProperties}>

        {/* STEP 1 */}
        {step === 1 && (
          <div>
            <StepDots step={step} />
            <div style={stepTitleStyle}>Welcome to Kazumee</div>
            <div style={{ fontSize: 14, color: "rgba(237,232,255,0.55)", marginBottom: 28 }}>
              Let's get your stream AI ready in 4 steps.
            </div>
            <FieldLabel label="Your display name" />
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="How should Zumi call you?"
              style={{ width: "100%", padding: "12px 14px", borderRadius: 12, border: `1px solid ${COLORS.border}`, background: "rgba(255,255,255,0.04)", color: COLORS.text, fontSize: 14, marginBottom: 20, outline: "none", fontFamily: "'DM Sans', sans-serif" }}
            />
            <FieldLabel label="Where do you stream?" />
            <div style={{ display: "flex", gap: 10, marginBottom: 28 }}>
              {(["twitch", "youtube", "both"] as const).map((p) => (
                <button key={p} onClick={() => setPlatform(p)} style={dotButtonStyle(platform === p)}>
                  {p === "twitch" ? "Twitch" : p === "youtube" ? "YouTube" : "Both"}
                </button>
              ))}
            </div>
            <button style={displayName.trim() ? primaryButton : disabledButton} disabled={!displayName.trim()} onClick={saveStep1AndNext}>
              Continue →
            </button>
          </div>
        )}

        {/* STEP 2 */}
        {step === 2 && (
          <div>
            <StepDots step={step} />
            <div style={stepTitleStyle}>Connect OBS</div>
            <div style={{ fontSize: 14, color: "rgba(237,232,255,0.55)", marginBottom: 24 }}>
              Kazumee controls your stream through OBS WebSocket.
            </div>
            {["Open OBS → Tools → WebSocket Server Settings", "Enable the WebSocket server", "Set port to 4455 and create a password"].map((line, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 12, fontSize: 13, color: "rgba(237,232,255,0.75)" }}>
                <div style={{ width: 22, height: 22, borderRadius: 999, background: COLORS.accent, color: "#0B0616", fontWeight: 900, fontSize: 11, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  {i + 1}
                </div>
                {line}
              </div>
            ))}
            <div style={{ marginTop: 20, marginBottom: 14 }}>
              <FieldLabel label="OBS WebSocket Password" />
              <input
                type="password"
                value={obsPassword}
                onChange={(e) => setObsPassword(e.target.value)}
                placeholder="Your OBS password"
                style={{ width: "100%", padding: "12px 14px", borderRadius: 12, border: `1px solid ${COLORS.border}`, background: "rgba(255,255,255,0.04)", color: COLORS.text, fontSize: 14, outline: "none", fontFamily: "'DM Sans', sans-serif" }}
              />
            </div>
            <button style={{ ...primaryButton, background: "transparent", border: `1px solid ${COLORS.border}`, color: COLORS.text, marginBottom: 10 }} onClick={testObsConnection} disabled={obsTestState === "testing"}>
              {obsTestState === "testing" ? "Testing..." : "Test Connection"}
            </button>
            {obsTestState === "connected" && <div style={{ marginBottom: 12 }}><Pill tone="green">✓ OBS Connected</Pill></div>}
            {obsTestState === "failed" && <div style={{ marginBottom: 12 }}><Pill tone="red">✗ {obsError || "Connection failed — is OBS open?"}</Pill></div>}
            <button style={obsTestState === "connected" ? primaryButton : disabledButton} disabled={obsTestState !== "connected"} onClick={saveObsPasswordAndNext}>
              Continue →
            </button>
            <button onClick={() => setStep(3)} style={{ marginTop: 12, width: "100%", background: "none", border: "none", color: "rgba(237,232,255,0.35)", fontSize: 12, cursor: "pointer" }}>
              Skip for now
            </button>
          </div>
        )}

        {/* STEP 3 */}
        {step === 3 && (
          <div>
            <StepDots step={step} />
            <div style={stepTitleStyle}>Set up your voice</div>
            <div style={{ fontSize: 14, color: "rgba(237,232,255,0.55)", marginBottom: 28 }}>
              Zumi learns your voice so only you can control the stream.
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 28 }}>
              <button
                onClick={start10SecondRecording}
                disabled={recording || voiceStatus === "saved"}
                style={{ width: 90, height: 90, borderRadius: 999, background: recording ? "rgba(124,92,252,0.25)" : COLORS.accent, border: `2px solid ${COLORS.accent}`, display: "flex", alignItems: "center", justifyContent: "center", cursor: recording || voiceStatus === "saved" ? "not-allowed" : "pointer", marginBottom: 16, boxShadow: recording ? `0 0 28px rgba(124,92,252,0.55)` : "none" }}
              >
                {recording ? (
                  <span style={{ fontFamily: "'Syne',sans-serif", fontSize: 22, fontWeight: 800, color: COLORS.accent }}>{countdown}</span>
                ) : (
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0B0616" strokeWidth="2.5">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                  </svg>
                )}
              </button>
              {recording && (
                <div style={{ display: "flex", gap: 5, alignItems: "center", height: 32 }}>
                  {Array.from({ length: 9 }).map((_, i) => (
                    <div key={i} style={animateWaveformBarStyle(i)} />
                  ))}
                </div>
              )}
              {voiceStatus === "saved" && <Pill tone="green">✓ Voice fingerprint saved</Pill>}
              {voiceStatus === "failed" && <Pill tone="red">✗ Could not save — try again</Pill>}
              {!recording && voiceStatus === "idle" && (
                <div style={{ fontSize: 12, color: "rgba(237,232,255,0.4)", textAlign: "center", marginTop: 8 }}>
                  Press and speak naturally for 10 seconds
                </div>
              )}
            </div>
            <button style={voiceStatus === "saved" ? primaryButton : disabledButton} disabled={voiceStatus !== "saved"} onClick={() => setStep(4)}>
              Continue →
            </button>
            <button onClick={() => setStep(4)} style={{ marginTop: 12, width: "100%", background: "none", border: "none", color: "rgba(237,232,255,0.35)", fontSize: 12, cursor: "pointer" }}>
              Skip for now
            </button>
          </div>
        )}

        {/* STEP 4 */}
        {step === 4 && (
          <div>
            <StepDots step={step} />
            <div style={stepTitleStyle}>Name your scenes</div>
            <div style={{ fontSize: 14, color: "rgba(237,232,255,0.55)", marginBottom: 24 }}>
              Tell Zumi which scenes you use so voice commands work instantly.
            </div>
            {scenes.length === 0 && (
              <div style={{ fontSize: 13, color: "rgba(237,232,255,0.4)", marginBottom: 20 }}>
                No OBS scenes found. Make sure OBS is open, or skip and set this up later in settings.
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 24, maxHeight: 260, overflowY: "auto" }}>
              {scenes.map((scene) => {
                const aliases = sceneAliases[scene.name] || [];
                return (
                  <div key={scene.name} style={{ background: "rgba(255,255,255,0.03)", border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: "12px 14px" }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{scene.name}</div>
                    <div style={{ display: "flex", gap: 8 }}>
                      {(["Main", "BRB", "Facecam"] as const).map((alias) => (
                        <button
                          key={alias}
                          onClick={() => {
                            setSceneAliases((prev) => {
                              const current = prev[scene.name] || [];
                              const has = current.includes(alias);
                              return { ...prev, [scene.name]: has ? current.filter((a) => a !== alias) : [...current, alias] };
                            });
                          }}
                          style={{ padding: "5px 12px", borderRadius: 8, border: `1px solid ${aliases.includes(alias) ? COLORS.accent : COLORS.border}`, background: aliases.includes(alias) ? "rgba(124,92,252,0.2)" : "transparent", color: aliases.includes(alias) ? COLORS.accent : "rgba(237,232,255,0.5)", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
                        >
                          {alias}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
            <button
              style={savingScenes ? disabledButton : primaryButton}
              disabled={savingScenes}
              onClick={async () => {
                setSavingScenes(true);
                try {
                  const payload = Object.entries(sceneAliases).filter(([, a]) => a.length > 0).map(([scene, aliases]) => ({ scene, aliases }));
                  await apiFetch("/api/streamer/scene-aliases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ aliases: payload }) });
                  await apiFetch("/api/streamer/onboarding/complete", { method: "POST" });
                } catch { /* ignore */ } finally {
                  setSavingScenes(false);
                  setStep(5);
                }
              }}
            >
              {savingScenes ? "Saving..." : "Finish Setup →"}
            </button>
            <button onClick={() => setStep(5)} style={{ marginTop: 12, width: "100%", background: "none", border: "none", color: "rgba(237,232,255,0.35)", fontSize: 12, cursor: "pointer" }}>
              Skip — set up later
            </button>
          </div>
        )}

        {/* STEP 5 - COMPLETION */}
        {step === 5 && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "20px 0" }}>
            <LotusLogo />
            <div style={{ ...stepTitleStyle, marginTop: 28, fontSize: 32 }}>Zumi is ready.</div>
            <div style={{ fontSize: 14, color: "rgba(237,232,255,0.55)", marginBottom: 36, lineHeight: 1.7 }}>
              Your stream AI is configured and ready to go live with you.
            </div>
            <button style={{ ...primaryButton, maxWidth: 280 }} onClick={() => navigate("/")}>
              Go to Dashboard →
            </button>
            <style>{`
              @keyframes slideInFade {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
              }
              @keyframes pulse-dot {
                0%, 100% { opacity: 0.4; }
                50% { opacity: 1; }
              }
            `}</style>
          </div>
        )}

      </div>
    </div>
  );
}