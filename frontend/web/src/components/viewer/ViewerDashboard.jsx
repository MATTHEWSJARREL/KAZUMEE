"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { apiFetch, buildApiUrl, getActiveStreamerId, getAuthToken, isAuthBypassEnabled, setActiveStreamerId as setActiveStreamerStorage } from "@/lib/apiClient";
import { useLatencyShield } from "@/hooks/useLatencyShield";
import ViewerSettingsModal from "./ViewerSettingsModal";
import "../../app/viewer.css";
import {
  Play,
  MessageSquare,
  Heart,
  Send,
  Vote,
  Timer,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from "lucide-react";

const VIBE_PRESETS = {
  chill: { aggressionThreshold: 3, spamThreshold: 8, capsThreshold: 1.0 },
  balanced: { aggressionThreshold: 2, spamThreshold: 5, capsThreshold: 0.9 },
  mild: { aggressionThreshold: 2, spamThreshold: 5, capsThreshold: 0.9 },
  strict: { aggressionThreshold: 1, spamThreshold: 3, capsThreshold: 0.65 },
};

const DEFAULT_CLEANSE_CONFIG = {
  hideAggression: true,
  hideSpam: true,
  hideCaps: true,
  aggressionThreshold: 2,
  spamThreshold: 5,
  capsThresholdPct: 90,
};

const VIEWER_SETTINGS_STORAGE_KEY = "kazumi_viewer_settings";
const DEFAULT_VIEWER_SETTINGS = {
  theme: "system",
  layout_mode: "focus",
  compact_mode: false,
  show_hidden_default: false,
  latency_ms: 3500,
};

const normalizeViewerSettings = (value) => {
  const source = value || {};
  const theme = ["system", "light", "dark"].includes(source.theme) ? source.theme : "system";
  const layoutMode = ["focus", "full"].includes(source.layout_mode) ? source.layout_mode : "focus";
  const compactMode = Boolean(source.compact_mode);
  const showHiddenDefault = Boolean(source.show_hidden_default);
  const latencyMs = clampNumber(source.latency_ms, 2000, 8000, 3500);
  return {
    theme,
    layout_mode: layoutMode,
    compact_mode: compactMode,
    show_hidden_default: showHiddenDefault,
    latency_ms: latencyMs,
  };
};

const clampNumber = (value, min, max, fallback) => {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
};

const toViewerVibeMode = (cloudMode, enabled) => {
  if (!enabled) return "off";
  if (cloudMode === "strict") return "strict";
  if (cloudMode === "custom") return "custom";
  if (cloudMode === "chill") return "chill";
  if (cloudMode === "balanced") return "balanced";
  return "balanced";
};

const toCloudVibeMode = (viewerMode) => {
  if (viewerMode === "strict") return "strict";
  if (viewerMode === "custom") return "custom";
  if (viewerMode === "chill") return "chill";
  if (viewerMode === "mild") return "balanced";
  return "balanced";
};

const formatApiError = (payload, fallback) => {
  if (!payload) return fallback;
  if (typeof payload === "string" && payload.trim()) return payload;
  if (typeof payload?.message === "string" && payload.message.trim()) return payload.message;
  if (typeof payload?.detail === "string" && payload.detail.trim()) return payload.detail;
  if (payload?.detail && typeof payload.detail === "object") {
    if (typeof payload.detail.message === "string" && payload.detail.message.trim()) {
      return payload.detail.message;
    }
  }
  return fallback;
};

function CatchUpClipCard({ clip }) {
  const videoRef = useRef(null);
  const title = clip?.title || "Highlight";
  const subtitle = clip?.moment_label || "Recent clip";
  const timestamp = clip?.created_at ? new Date(clip.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";

  return (
    <div
      className="relative flex-shrink-0 w-[130px] rounded-xl border border-black/10 bg-[#0f0f12] p-2 cursor-pointer group"
      onMouseEnter={() => videoRef.current?.play?.()}
      onMouseLeave={() => {
        if (videoRef.current) {
          videoRef.current.pause();
          videoRef.current.currentTime = 0;
        }
      }}
    >
      <div className="relative w-full h-[72px] rounded-md overflow-hidden">
        {clip?.thumbnail_url ? (
          <img
            src={clip.thumbnail_url}
            className="absolute inset-0 w-full h-full object-cover z-10 group-hover:opacity-0 transition-opacity duration-200"
            alt={title}
          />
        ) : null}
        <video
          ref={videoRef}
          src={clip?.url}
          className="w-full h-full object-cover"
          muted
          loop
          playsInline
          preload="metadata"
        />
        <div className="absolute inset-0 flex items-center justify-center group-hover:opacity-0 transition-opacity duration-200">
          <div className="w-7 h-7 bg-black/35 backdrop-blur-sm rounded-full flex items-center justify-center">
            <Play className="w-3.5 h-3.5 text-white ml-0.5" />
          </div>
        </div>
      </div>
      <div className="pt-2">
        <p className="text-white text-[11px] font-semibold truncate">{title}</p>
        <p className="text-gray-400 text-[10px] truncate">{subtitle}{timestamp ? ` - ${timestamp}` : ""}</p>
      </div>
    </div>
  );
}

export default function ViewerModePage() {
  const [viewerData, setViewerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [commandText, setCommandText] = useState("");
  const [activeStreamerId, setActiveStreamerIdState] = useState(getActiveStreamerId());
  const [viewerSettingsReady, setViewerSettingsReady] = useState(false);
  const [viewerSettings, setViewerSettings] = useState(DEFAULT_VIEWER_SETTINGS);
  const [voteDelay, setVoteDelay] = useState(0);
  const [latencyMs, setLatencyMs] = useState(3500);
  const [liveEvents, setLiveEvents] = useState([]);
  const [eventStreamStatus, setEventStreamStatus] = useState("idle");
  const [eventPaused, setEventPaused] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [eventPlatformFilter, setEventPlatformFilter] = useState("all");
  const [eventTypeFilter, setEventTypeFilter] = useState("all");
  const [vibeStrictness, setVibeStrictness] = useState("off");
  const [cleanseConfig, setCleanseConfig] = useState({ ...DEFAULT_CLEANSE_CONFIG });
  const [cleanseSyncReady, setCleanseSyncReady] = useState(false);
  const [showHiddenEvents, setShowHiddenEvents] = useState(false);
  const [viewerCredits, setViewerCredits] = useState(0);
  const [impactMessage, setImpactMessage] = useState("");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [viewerCooldown, setViewerCooldown] = useState(0);
  const [importantOnly, setImportantOnly] = useState(false);
  const [toastQueue, setToastQueue] = useState([]);
  const [trustLog, setTrustLog] = useState([]);
  const [voteCounts, setVoteCounts] = useState({});
  const [companionInput, setCompanionInput] = useState("");
  const [companionResult, setCompanionResult] = useState(null);
  const [companionLoading, setCompanionLoading] = useState(false);
  const [companionTrackers, setCompanionTrackers] = useState([]);
  const [retryLoadingId, setRetryLoadingId] = useState(null);
  const [catchupRecap, setCatchupRecap] = useState(null);
  const [catchupLoading, setCatchupLoading] = useState(false);
  const [catchupHighlights, setCatchupHighlights] = useState([]);
  const [catchUpNudgeVisible, setCatchUpNudgeVisible] = useState(false);
  const [catchUpNudgeDismissed, setCatchUpNudgeDismissed] = useState(false);
  const [hasUsedCatchUp, setHasUsedCatchUp] = useState(false);
  const [highlightReelOpen, setHighlightReelOpen] = useState(false);
  const [highlightReel, setHighlightReel] = useState([]);
  const [availableStreamers, setAvailableStreamers] = useState([]);
  const [streamerSearch, setStreamerSearch] = useState("");
  const [streamerLoading, setStreamerLoading] = useState(false);
  const [streamerDiagnostics, setStreamerDiagnostics] = useState(null);
  const [freshnessTick, setFreshnessTick] = useState(0);
  const { shield, shieldMsLeft } = useLatencyShield(3500);
  const eventDelayTimersRef = useRef(new Set());
  const viewerSettingsSaveTimerRef = useRef(null);
  const catchupSectionRef = useRef(null);

  const applyViewerTheme = (themeMode) => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    let useDark = false;
    if (themeMode === "dark") useDark = true;
    if (themeMode === "system") {
      useDark = Boolean(window.matchMedia?.("(prefers-color-scheme: dark)").matches);
    }
    if (useDark) root.classList.add("kazumi-dark");
    else root.classList.remove("kazumi-dark");

    try {
      const cached = JSON.parse(localStorage.getItem("kazumi_settings") || "{}");
      const merged = {
        ...cached,
        appearance: {
          ...(cached.appearance || {}),
          darkMode: useDark,
        },
      };
      localStorage.setItem("kazumi_settings", JSON.stringify(merged));
    } catch {
      // ignore storage failures
    }
  };

  const handleSettingsChange = (key, value) => {
    setViewerSettings((prev) => {
      const updated = { ...prev, [key]: value };
      localStorage.setItem(VIEWER_SETTINGS_STORAGE_KEY, JSON.stringify(updated));
      if (key === "theme") applyViewerTheme(value);
      return updated;
    });
  };

  useEffect(() => {
    const sharedStreamerId = new URLSearchParams(window.location.search).get("s")
      || new URLSearchParams(window.location.search).get("streamer_id");
    if (sharedStreamerId && Number.isFinite(Number(sharedStreamerId))) {
      const selected = Number(sharedStreamerId);
      setActiveStreamerStorage(selected);
      setActiveStreamerIdState(selected);
    }
    fetchViewerContext();
    fetchViewerData();
    fetchViewerCredits();
    const seen = localStorage.getItem("kazumi_viewer_onboarded");
    if (!seen) setShowOnboarding(true);
    const storedVibe = localStorage.getItem("kazumi_vibe_strictness");
    if (storedVibe && ["off", "chill", "mild", "balanced", "strict", "custom"].includes(storedVibe)) {
      setVibeStrictness(storedVibe === "mild" ? "balanced" : storedVibe);
    }
    const storedCleanseConfig = localStorage.getItem("kazumi_vibe_cleanse_config");
    if (storedCleanseConfig) {
      try {
        const parsed = JSON.parse(storedCleanseConfig);
        setCleanseConfig({
          hideAggression: parsed.hideAggression !== false,
          hideSpam: parsed.hideSpam !== false,
          hideCaps: parsed.hideCaps !== false,
          aggressionThreshold: clampNumber(parsed.aggressionThreshold, 0.5, 3, DEFAULT_CLEANSE_CONFIG.aggressionThreshold),
          spamThreshold: clampNumber(parsed.spamThreshold, 2, 10, DEFAULT_CLEANSE_CONFIG.spamThreshold),
          capsThresholdPct: clampNumber(parsed.capsThresholdPct, 40, 100, DEFAULT_CLEANSE_CONFIG.capsThresholdPct),
        });
      } catch {
        setCleanseConfig({ ...DEFAULT_CLEANSE_CONFIG });
      }
    }
    const loadCloudCleanseProfile = async () => {
      try {
        const res = await apiFetch("/api/viewer/chat-cleanse/preferences");
        if (!res.ok) return;
        const data = await res.json().catch(() => ({}));
        const prefs = data?.preferences || {};
        setVibeStrictness(toViewerVibeMode(prefs.mode, prefs.enabled));
        setCleanseConfig({
          hideAggression: prefs.hide_aggression !== false,
          hideSpam: prefs.hide_spam !== false,
          hideCaps: prefs.hide_caps !== false,
          aggressionThreshold: clampNumber(prefs.aggression_threshold, 0.5, 3, DEFAULT_CLEANSE_CONFIG.aggressionThreshold),
          spamThreshold: clampNumber(prefs.spam_threshold, 2, 10, DEFAULT_CLEANSE_CONFIG.spamThreshold),
          capsThresholdPct: clampNumber(prefs.caps_threshold_pct, 40, 100, DEFAULT_CLEANSE_CONFIG.capsThresholdPct),
        });
      } catch {
        // local fallback is already loaded from browser storage
      } finally {
        setCleanseSyncReady(true);
      }
    };
    void loadCloudCleanseProfile();

    // Use useEffect with 45s timer for catch-up nudge (only occurrence)
  }, []);

  useEffect(() => {
    let cancelled = false;

    const applyLoadedSettings = (raw) => {
      const normalized = normalizeViewerSettings(raw);
      if (cancelled) return;
      setViewerSettings(normalized);
      setLatencyMs(normalized.latency_ms);
      setShowHiddenEvents(normalized.show_hidden_default);
      applyViewerTheme(normalized.theme);
    };

    try {
      const cached = localStorage.getItem(VIEWER_SETTINGS_STORAGE_KEY);
      if (cached) {
        applyLoadedSettings(JSON.parse(cached));
      } else {
        applyLoadedSettings(DEFAULT_VIEWER_SETTINGS);
      }
    } catch {
      applyLoadedSettings(DEFAULT_VIEWER_SETTINGS);
    }

    const loadRemoteSettings = async () => {
      try {
        const res = await apiFetch("/api/viewer/preferences");
        if (!res.ok) return;
        const data = await res.json().catch(() => ({}));
        if (data?.preferences) applyLoadedSettings(data.preferences);
      } catch {
        // local settings remain in effect
      } finally {
        if (!cancelled) setViewerSettingsReady(true);
      }
    };

    void loadRemoteSettings();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!viewerSettingsReady) return;
    applyViewerTheme(viewerSettings.theme);
    localStorage.setItem(VIEWER_SETTINGS_STORAGE_KEY, JSON.stringify(viewerSettings));

    if (viewerSettingsSaveTimerRef.current) clearTimeout(viewerSettingsSaveTimerRef.current);
    viewerSettingsSaveTimerRef.current = setTimeout(async () => {
      try {
        await apiFetch("/api/viewer/preferences", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(viewerSettings),
        });
      } catch {
        // silent fallback to local persistence
      }
    }, 450);

    return () => {
      if (viewerSettingsSaveTimerRef.current) clearTimeout(viewerSettingsSaveTimerRef.current);
    };
  }, [viewerSettingsReady, viewerSettings]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchStreamers(streamerSearch);
    }, 250);
    return () => clearTimeout(timer);
  }, [streamerSearch]);

  useEffect(() => {
    setCatchUpNudgeVisible(false);
    setCatchupRecap(null);
    setCatchupHighlights([]);
  }, [activeStreamerId]);

  useEffect(() => {
    if (loading || hasUsedCatchUp || catchUpNudgeDismissed || !activeStreamerId) return;
    const timer = window.setTimeout(() => {
      setCatchUpNudgeVisible(true);
    }, 45000);
    return () => window.clearTimeout(timer);
  }, [loading, hasUsedCatchUp, catchUpNudgeDismissed, activeStreamerId]);

  useEffect(() => {
    localStorage.setItem("kazumi_vibe_strictness", vibeStrictness);
  }, [vibeStrictness]);

  useEffect(() => {
    localStorage.setItem("kazumi_vibe_cleanse_config", JSON.stringify(cleanseConfig));
  }, [cleanseConfig]);

  useEffect(() => {
    if (!cleanseSyncReady) return;
    const timer = setTimeout(async () => {
      try {
        await apiFetch("/api/viewer/chat-cleanse/preferences", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: vibeStrictness !== "off",
            mode: toCloudVibeMode(vibeStrictness),
            local_scoring_only: true,
            hide_aggression: cleanseConfig.hideAggression,
            hide_spam: cleanseConfig.hideSpam,
            hide_caps: cleanseConfig.hideCaps,
            aggression_threshold: cleanseConfig.aggressionThreshold,
            spam_threshold: cleanseConfig.spamThreshold,
            caps_threshold_pct: cleanseConfig.capsThresholdPct,
            whitelist: [],
          }),
        });
      } catch {
        // Keep local-only fallback when cloud sync is unavailable.
      }
    }, 600);
    return () => clearTimeout(timer);
  }, [cleanseSyncReady, vibeStrictness, cleanseConfig]);

  useEffect(() => {
    if (voteDelay <= 0) return;
    const interval = setInterval(() => setVoteDelay((prev) => Math.max(prev - 1, 0)), 1000);
    return () => clearInterval(interval);
  }, [voteDelay]);

  useEffect(() => {
    if (viewerCooldown <= 0) return;
    const interval = setInterval(() => setViewerCooldown((prev) => Math.max(prev - 1, 0)), 1000);
    return () => clearInterval(interval);
  }, [viewerCooldown]);

  useEffect(() => {
    const authToken = getAuthToken();
    const bypass = isAuthBypassEnabled();
    const shouldConnect = Boolean(authToken && (bypass || activeStreamerId));
    if (!shouldConnect) {
      setEventStreamStatus("idle");
      return undefined;
    }

    let cancelled = false;
    let es = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;

    const closeEventSource = () => {
      if (es) {
        es.close();
        es = null;
      }
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      closeEventSource();
      reconnectAttempts += 1;
      const delayMs = Math.min(15000, 1000 * 2 ** Math.min(reconnectAttempts - 1, 4));
      setEventStreamStatus("error");
      reconnectTimer = window.setTimeout(() => {
        if (!cancelled) {
          void connectStream();
        }
      }, delayMs);
    };

    const connectStream = async () => {
      closeEventSource();
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      setEventStreamStatus("connecting");
      try {
        const tokenRes = await apiFetch("/auth/stream-token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(activeStreamerId ? { streamer_id: Number(activeStreamerId) } : {}),
        });
        if (!tokenRes.ok) {
          const tokenErr = await tokenRes.json().catch(() => ({}));
          const detail = formatApiError(tokenErr, "");
          if (tokenRes.status === 400 && detail.toLowerCase().includes("streamer_id required")) {
            setEventStreamStatus("idle");
          } else if (tokenRes.status === 403 || tokenRes.status === 404) {
            if (typeof window !== "undefined") {
              localStorage.removeItem("kazumi_active_streamer_id");
            }
            setActiveStreamerIdState(null);
            setEventStreamStatus("idle");
          } else {
            scheduleReconnect();
          }
          return;
        }
        const tokenData = await tokenRes.json();
        const streamToken = tokenData?.token;
        if (!streamToken || cancelled) {
          scheduleReconnect();
          return;
        }

        const params = new URLSearchParams();
        params.set("token", streamToken);
        // For authenticated viewer mode, server-side active_streamer_id is the source of truth.
        // Only force streamer_id in auth bypass/demo mode.
        if (bypass) {
          params.set("streamer_id", String(activeStreamerId || 1));
        }
        const url = `${buildApiUrl("/api/events/stream")}?${params.toString()}`;

        es = new EventSource(url);
        es.onopen = () => {
          reconnectAttempts = 0;
          setEventStreamStatus("live");
        };
        es.onerror = () => {
          scheduleReconnect();
        };
        es.onmessage = (event) => {
          if (eventPaused) return;
          try {
            const parsed = JSON.parse(event.data);
            const queuedEvent = { ...parsed, received_at: new Date().toISOString() };
            if (parsed?.event_type === "clip_created" || parsed?.event_type === "viewer_clip_ready") {
              const clipPayload = parsed?.payload || {};
              if (clipPayload?.clip_id || clipPayload?.url) {
                setCatchupHighlights((prev) => {
                  const next = [
                    {
                      id: clipPayload.clip_id || parsed.id,
                      title: clipPayload.title || parsed.message || "New highlight",
                      url: clipPayload.url,
                      thumbnail_url: clipPayload.thumbnail_url,
                      moment_label: clipPayload.moment_label || "Live moment",
                      status: clipPayload.status || "approved",
                    },
                    ...prev,
                  ];
                  const deduped = [];
                  const seen = new Set();
                  for (const item of next) {
                    const key = String(item?.id || item?.url || JSON.stringify(item));
                    if (seen.has(key)) continue;
                    seen.add(key);
                    deduped.push(item);
                    if (deduped.length >= 8) break;
                  }
                  return deduped;
                });
              }
              pushFeedback("approved", parsed.message || "New clip is ready.", "live clip signal");
            }
            const delayMs = Math.max(0, Math.round(Number(latencyMs) || 0));
            if (!delayMs) {
              setLiveEvents((prev) => [queuedEvent, ...prev].slice(0, 60));
              return;
            }
            const timer = window.setTimeout(() => {
              eventDelayTimersRef.current.delete(timer);
              setLiveEvents((prev) => [queuedEvent, ...prev].slice(0, 60));
            }, delayMs);
            eventDelayTimersRef.current.add(timer);
          } catch (error) {
            console.error("Failed to parse event stream message:", error);
          }
        };
      } catch (error) {
        if (error?.name !== "AbortError") console.error("Failed to initialize stream token:", error);
        scheduleReconnect();
      }
    };

    void connectStream();

    return () => {
      cancelled = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      closeEventSource();
    };
  }, [activeStreamerId, eventPaused, latencyMs]);

  useEffect(() => {
    return () => {
      eventDelayTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      eventDelayTimersRef.current.clear();
    };
  }, []);

  useEffect(() => {
    if (!toastQueue.length) return;
    const timer = setTimeout(() => setToastQueue((prev) => prev.slice(1)), 3000);
    return () => clearTimeout(timer);
  }, [toastQueue]);

  useEffect(() => {
    const interval = setInterval(() => setFreshnessTick((n) => n + 1), 10000);
    return () => clearInterval(interval);
  }, []);


  useEffect(() => {
    if (!companionTrackers.length) return;
    const interval = setInterval(async () => {
      try {
        const updates = await Promise.all(
          companionTrackers.map(async (tracker) => {
            const res = await apiFetch(`/api/viewer/companion/status?tracking_id=${tracker.id}`);
            if (!res.ok) return tracker;
            const data = await res.json();
            return {
              ...tracker,
              state: data.state || tracker.state,
              duplicate_count: data.duplicate_count ?? tracker.duplicate_count,
              elapsed_min: data.elapsed_min ?? tracker.elapsed_min,
            };
          }),
        );
        setCompanionTrackers(updates);
      } catch {
        // keep previous state
      }
    }, 8000);
    return () => clearInterval(interval);
  }, [companionTrackers]);

  const pushFeedback = (status, message, reason = "") => {
    setImpactMessage(message);
    setToastQueue((prev) => [...prev, { id: `${Date.now()}-${Math.random()}`, status, message }]);
    setTrustLog((prev) => [
      { at: new Date().toISOString(), status, message, reason },
      ...prev,
    ].slice(0, 10));
  };

  const recapFreshness = (() => {
    const _tick = freshnessTick;
    void _tick;
    if (!catchupRecap?.generated_at) return "";
    const generated = new Date(catchupRecap.generated_at).getTime();
    if (Number.isNaN(generated)) return "";
    const seconds = Math.max(0, Math.floor((Date.now() - generated) / 1000));
    if (seconds < 60) return `Updated ${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `Updated ${minutes}m ago`;
  })();

  const analyzeCompanion = async () => {
    const message = companionInput.trim();
    if (!message) return;
    try {
      setCompanionLoading(true);
      const res = await apiFetch("/api/viewer/companion/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 429) {
          pushFeedback("denied", formatApiError(data, "Please try again later."), "companion rate limit");
          return;
        }
        pushFeedback("denied", formatApiError(data, "Companion analysis failed."), "companion analyze");
        return;
      }
      setCompanionResult(data);
      pushFeedback("approved", "Companion suggestion ready.", "question optimization");
    } catch (error) {
      console.error("Companion analyze error:", error);
      pushFeedback("denied", "Companion analysis failed.", "network error");
    } finally {
      setCompanionLoading(false);
    }
  };

  const markCompanionSent = async () => {
    const sent = (companionResult?.improved_message || companionInput || "").trim();
    if (!sent) return;
    try {
      const res = await apiFetch("/api/viewer/companion/sent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_message: companionInput,
          sent_message: sent,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        pushFeedback("denied", formatApiError(data, "Could not start tracking."), "companion sent");
        return;
      }
      setCompanionTrackers((prev) => [
        { id: data.tracking_id, message: sent, state: "sent", duplicate_count: 0, elapsed_min: 0 },
        ...prev,
      ].slice(0, 8));
      pushFeedback("queued", "Tracking started. Paste this in Twitch/YouTube chat now.", "companion tracking");
    } catch (error) {
      console.error("Companion sent error:", error);
      pushFeedback("denied", "Could not start tracking.", "network error");
    }
  };

  const markTrackerAnswered = async (trackingId) => {
    try {
      const res = await apiFetch("/api/viewer/companion/mark-answered", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tracking_id: trackingId }),
      });
      if (!res.ok) {
        pushFeedback("denied", "Could not mark answered.", "companion answered");
        return;
      }
      setCompanionTrackers((prev) =>
        prev.map((t) => (t.id === trackingId ? { ...t, state: "answered" } : t)),
      );
      pushFeedback("approved", "Marked as answered.", "manual confirmation");
    } catch (error) {
      console.error("Companion answer error:", error);
      pushFeedback("denied", "Could not mark answered.", "network error");
    }
  };

  const getRetrySuggestion = async (trackingId) => {
    try {
      setRetryLoadingId(trackingId);
      const res = await apiFetch("/api/viewer/companion/retry-suggestion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tracking_id: trackingId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        pushFeedback("denied", formatApiError(data, "Retry suggestion failed."), "retry suggestion");
        return;
      }
      setCompanionTrackers((prev) =>
        prev.map((t) =>
          t.id === trackingId
            ? {
                ...t,
                retry_message: data.retry_message,
                retry_timing_advice: data.timing_advice,
              }
            : t,
        ),
      );
      pushFeedback("approved", "Retry suggestion ready.", "retry optimization");
    } catch (error) {
      console.error("Retry suggestion error:", error);
      pushFeedback("denied", "Retry suggestion failed.", "network error");
    } finally {
      setRetryLoadingId(null);
    }
  };

  const fetchCatchupHighlights = async ({ openModal = false, silent = false } = {}) => {
    try {
      const res = await apiFetch("/api/viewer/catchup/highlights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 3 }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (!silent) {
          pushFeedback("denied", formatApiError(data, "Could not load highlights."), "highlight reel");
        }
        return false;
      }
      const highlights = data.highlights || [];
      setCatchupHighlights(highlights);
      setHighlightReel(highlights);
      if (openModal) setHighlightReelOpen(true);
      if (!silent) {
        pushFeedback("approved", "Highlight reel loaded.", "catchup highlights");
      }
      return true;
    } catch (error) {
      if (error?.name !== "AbortError") console.error("Highlight reel error:", error);
      if (!silent && error?.name !== "AbortError") pushFeedback("info", "Highlights unavailable for this streamer.", "network error");
      return false;
    }
  };

  const openCatchUpPanel = () => {
    requestAnimationFrame(() => {
      catchupSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const dismissCatchUpNudge = () => {
    setCatchUpNudgeVisible(false);
    setCatchUpNudgeDismissed(true);
  };

  const triggerCatchUp = () => {
    setHasUsedCatchUp(true);
    setCatchUpNudgeDismissed(true);
    setCatchUpNudgeVisible(false);
    openCatchUpPanel();
    void runCatchupRecap("quick");
  };

  const runCatchupRecap = async (mode = "quick") => {
    try {
      setCatchupLoading(true);
      if (!activeStreamerId) {
        pushFeedback("denied", "No streamer selected.", "catchup recap");
        return;
      }
      const res = await apiFetch(
        `/api/viewer/catchup/recap?mode=${mode}&streamer_id=${activeStreamerId}`,
        { method: "GET" }
      );
      const data = await res.json().catch(() => ({}));

      // Handle no stream data gracefully
      if (res.status === 404 || (data && data.detail && data.detail.includes("no stream"))) {
        pushFeedback("info", "This streamer hasn't streamed yet or has no recent activity.", "catchup recap");
        return;
      }

      if (!res.ok) {
        if (res.status === 403) {
          pushFeedback("denied", "Access denied. Try selecting a different streamer.", "catchup recap");
        } else {
          pushFeedback("denied", formatApiError(data, "Recap failed."), "catchup recap");
        }
        return;
      }

      setCatchupRecap(data);
      setHasUsedCatchUp(true);
      setCatchUpNudgeDismissed(true);
      setCatchUpNudgeVisible(false);
      await fetchCatchupHighlights({ openModal: false, silent: true });
      pushFeedback("approved", "Recap ready.", "catchup recap");
    } catch (error) {
      if (error?.name === "AbortError") {
        // Request was cancelled/timed out, don't show error to user
        return;
      }
      console.error("Catchup recap error:", error);
      // Handle CORS and network errors gracefully
      if (error.message.includes("CORS")) {
        pushFeedback("info", "Can't reach streamer data right now.", "network error");
      } else {
        pushFeedback("info", "Recap unavailable for this streamer. They may not be using Kazumi yet.", "network error");
      }
    } finally {
      setCatchupLoading(false);
    }
  };

  const openHighlightReel = async () => {
    try {
      setCatchupLoading(true);
      await fetchCatchupHighlights({ openModal: true, silent: false });
      setHasUsedCatchUp(true);
      setCatchUpNudgeDismissed(true);
      setCatchUpNudgeVisible(false);
    } finally {
      setCatchupLoading(false);
    }
  };

  const shareCatchup = async () => {
    if (!catchupRecap?.recap) {
      pushFeedback("queued", "Run recap first, then share it.", "share catchup");
      return;
    }
    const streamerName =
      viewerData?.active_streamer?.display_name
      || viewerData?.active_streamer?.username
      || "this stream";
    const recapPreview80 = String(catchupRecap.recap || "").slice(0, 80);
    const shareText = `Just joined ${streamerName}'s stream and Kazumee told me everything I missed in 30 seconds including the highlights 🎬 ${recapPreview80}... Watch with context: ${window.location.origin}/viewer?s=${encodeURIComponent(String(activeStreamerId || ""))}`;
    try {
      if (navigator.share) {
        await navigator.share({
          title: `${streamerName} - Kazumi Catch-Up`,
          text: shareText,
        });
        pushFeedback("approved", "Shared with your device targets.", "share catchup");
      } else {
        await navigator.clipboard.writeText(shareText);
        pushFeedback("approved", "Copied - share it anywhere.", "share catchup");
      }
    } catch {
      pushFeedback("denied", "Could not share catch-up right now.", "share catchup");
    }
  };

  const switchToRecommendedStreamer = async (streamerId, displayName) => {
    const numericStreamerId = Number(streamerId);
    if (!Number.isFinite(numericStreamerId)) {
      pushFeedback("queued", `Opening ${displayName} on its platform.`, "external stream");
      return;
    }
    try {
      const res = await apiFetch("/auth/active-streamer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ streamer_id: numericStreamerId }),
      });
      if (!res.ok) {
        pushFeedback("denied", "Could not switch stream.", "active streamer");
        return;
      }
      setActiveStreamerStorage(numericStreamerId);
      setActiveStreamerIdState(numericStreamerId);
      setLiveEvents([]);
      await fetchViewerData();
      await fetchViewerCredits();
      pushFeedback("approved", `Switched to ${displayName}. Viewer feed synced.`, "stream switch");
    } catch (error) {
      console.error("Switch streamer error:", error);
      pushFeedback("denied", "Could not switch stream.", "network error");
    }
  };

  const openExternalStreamer = (streamer) => {
    if (streamer?.url) {
      window.open(streamer.url, "_blank", "noopener,noreferrer");
      return;
    }
    const username = streamer?.username || streamer?.display_name || "";
    if (!username) return;
    if (streamer.platform === "twitch") {
      window.open(`https://www.twitch.tv/${username}`, "_blank", "noopener,noreferrer");
      return;
    }
    if (streamer.platform === "youtube") {
      window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(username)}`, "_blank", "noopener,noreferrer");
      return;
    }
    pushFeedback("queued", `Could not auto-open ${streamer.platform}.`, "external link");
  };

  const fetchViewerContext = async () => {
    try {
      const res = await apiFetch("/auth/me");
      if (!res.ok) return;
      const data = await res.json().catch(() => ({}));
      const selected = data?.streamer_id ?? null;
      setActiveStreamerIdState(selected);
      if (selected) setActiveStreamerStorage(selected);
    } catch (error) {
      if (error?.name !== "AbortError") console.error("Error fetching viewer context:", error);
    }
  };

  const fetchStreamers = async (queryValue = "") => {
    try {
      setStreamerLoading(true);
      const q = (queryValue || "").trim();

      // New unified search endpoint (Kazumee, Twitch, YouTube)
      // Docs: GET /api/streamers/search?q={searchTerm}
      const res = await apiFetch(`/api/streamers/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) return;

      const data = await res.json().catch(() => ({}));
      // Backend returns { results: [...] }
      const results = Array.isArray(data?.results) ? data.results : [];
      // Normalize to the existing UI shape.
      setAvailableStreamers(
        results.map((r) => ({
          id: r.id,
          display_name: r.display_name,
          platform: r.platform,
          live: Boolean(r.is_live),
          avatar_url: r.profile_image_url || r.thumbnail_url,
          profile_image_url: r.profile_image_url,
          thumbnail_url: r.thumbnail_url,
          url: r.url,
          // external streamers use the URL; local Kazumee won't have it.
          source: r.platform === "kazumee" ? "local" : "external",
          username: r.display_name,
        })),
      );
      setStreamerDiagnostics(null);
    } catch (error) {
      if (error?.name !== "AbortError") {
        console.error("Error fetching streamers:", error);
        setStreamerDiagnostics({
          message: "Streamer discovery failed. Check backend connectivity and try again.",
        });
      }
    } finally {
      setStreamerLoading(false);
    }
  };

  const fetchViewerData = async () => {
    try {
      const response = await apiFetch("/api/viewer/dashboard");
      if (!response.ok) throw new Error("Failed to fetch viewer data");
      const data = await response.json();
      setViewerData(data);
      if (Number.isFinite(Number(data?.active_streamer_id))) {
        const selected = Number(data.active_streamer_id);
        setActiveStreamerIdState(selected);
        setActiveStreamerStorage(selected);
      }
    } catch (error) {
      if (error?.name !== "AbortError") console.error("Error fetching viewer data:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchViewerCredits = async () => {
    try {
      const res = await apiFetch("/api/viewer/credits");
      if (!res.ok) return;
      const data = await res.json();
      setViewerCredits(data.credits || 0);
    } catch (error) {
      if (error?.name !== "AbortError") console.error("Error fetching viewer credits:", error);
    }
  };

  const isViewerClipCommand = (input) => {
    const text = (input || "").trim().toLowerCase();
    if (!text) return false;
    return (
      text.startsWith("clip") ||
      text.startsWith("!clip") ||
      text.includes("clip that") ||
      text.includes("clip this") ||
      text.includes("save a clip") ||
      text.includes("save clip")
    );
  };

  const requestPrimaryViewerClip = async (rawCommand) => {
    const res = await apiFetch("/api/viewer/clip/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: rawCommand }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (res.status === 429) {
        pushFeedback("denied", formatApiError(data, "Please try again later."), "clip request limit");
        return;
      }
      pushFeedback("denied", formatApiError(data, "Clip request failed."), "viewer primary clip");
      return;
    }
    const successMessage = data?.clip_id
      ? `Clip requested on Twitch (ID: ${data.clip_id}).`
      : data?.message || "Clip requested on Twitch.";
    pushFeedback("approved", successMessage, "viewer primary clip");
    setCommandText("");
    setViewerCooldown(8);
  };

  const submitVote = async (scene) => {
    try {
      const res = await apiFetch("/api/viewer/vote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scene }),
      });
      if (!res.ok) {
        const text = await res.text();
        if (res.status === 429) {
          pushFeedback("denied", text || "Please try again later.", "vote rate limit");
          return;
        }
        pushFeedback("denied", `Vote failed: ${text}`, "vote request rejected");
        return;
      }
      const data = await res.json();
      setVoteCounts(data.counts || {});
      setViewerCredits(data.credits || viewerCredits);
      if (data.winner) {
        pushFeedback("approved", `Impact: viewers switched to ${data.winner}`, "vote threshold reached");
      } else {
        pushFeedback("queued", `Vote counted for ${scene}`, "waiting for more votes");
      }
    } catch (error) {
      console.error("Vote error:", error);
      pushFeedback("denied", "Vote failed. Try again.", "network error");
    }
  };

  const handleSubmitCommand = async () => {
    if (!commandText.trim()) return;

    try {
      if (viewerCooldown > 0) {
        pushFeedback("denied", `Please wait ${viewerCooldown}s before sending another request.`, "cooldown active");
        return;
      }
      if (isViewerClipCommand(commandText)) {
        await requestPrimaryViewerClip(commandText.trim());
        return;
      }
      const response = await apiFetch("/api/commands/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: commandText, role: "viewer" }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 429) {
          pushFeedback("denied", formatApiError(payload, "Please try again later."), "command rate limit");
          return;
        }
        pushFeedback("denied", formatApiError(payload, "Request failed."), "backend rejected request");
        return;
      }

      await shield(latencyMs);
      setCommandText("");
      const msg = payload?.message || "Request sent to the streamer. Waiting for approval.";
      const status = /restricted|denied/i.test(msg) ? "denied" : (/queued|approval/i.test(msg) ? "queued" : "approved");
      pushFeedback(status, msg, "policy evaluation");
      setViewerCooldown(15);
    } catch (error) {
      console.error("Error:", error);
      pushFeedback("denied", "Request failed. Please try again.", "network error");
    }
  };

  const classifySeverity = (event) => {
    if (event.event_type?.includes("moderation") || event.event_type?.includes("impact")) return "high";
    if (event.event_type?.includes("moment") || event.event_type?.includes("clip")) return "medium";
    return "low";
  };

  const normalizeMsg = (text) =>
    (text || "")
      .toLowerCase()
      .replace(/[^\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

  const toxicityScore = (text) => {
    const lower = (text || "").toLowerCase();
    const aggressive = [
      "idiot", "stupid", "trash", "garbage", "kill", "hate", "pathetic", "loser", "dumb", "moron",
    ];
    let score = 0;
    for (const word of aggressive) {
      if (lower.includes(word)) score += 1;
    }
    if (/[!?]{3,}/.test(text || "")) score += 0.5;
    return score;
  };

  const allCapsRatio = (text) => {
    const words = (text || "").split(/\s+/).filter(Boolean);
    if (!words.length) return 0;
    const caps = words.filter((w) => w.length > 2 && w === w.toUpperCase()).length;
    return caps / words.length;
  };

  const eventTypes = Array.from(new Set(liveEvents.map((event) => event.event_type))).filter(Boolean);
  const filteredEvents = liveEvents.filter((event) => {
    if (eventPlatformFilter !== "all" && event.platform !== eventPlatformFilter) return false;
    if (eventTypeFilter !== "all" && event.event_type !== eventTypeFilter) return false;
    if (importantOnly && classifySeverity(event) === "low") return false;
    return true;
  });

  const duplicateMap = useMemo(() => {
    const map = new Map();
    for (const e of filteredEvents) {
      const key = normalizeMsg(e.message || "");
      if (!key) continue;
      map.set(key, (map.get(key) || 0) + 1);
    }
    return map;
  }, [filteredEvents]);

  const activeCleanseThresholds = useMemo(() => {
    if (vibeStrictness === "off") return null;
    if (["chill", "mild", "balanced", "strict"].includes(vibeStrictness)) {
      return {
        ...VIBE_PRESETS[vibeStrictness],
        hideAggression: cleanseConfig.hideAggression,
        hideSpam: cleanseConfig.hideSpam,
        hideCaps: cleanseConfig.hideCaps,
      };
    }
    return {
      aggressionThreshold: cleanseConfig.aggressionThreshold,
      spamThreshold: cleanseConfig.spamThreshold,
      capsThreshold: cleanseConfig.capsThresholdPct / 100,
      hideAggression: cleanseConfig.hideAggression,
      hideSpam: cleanseConfig.hideSpam,
      hideCaps: cleanseConfig.hideCaps,
    };
  }, [vibeStrictness, cleanseConfig]);

  const cleanseResult = useMemo(() => {
    if (!activeCleanseThresholds) {
      return {
        visible: filteredEvents,
        hidden: [],
        hiddenCount: 0,
        hiddenByReason: { aggression: 0, spam: 0, caps: 0 },
      };
    }

    const visible = [];
    const hidden = [];
    const hiddenByReason = { aggression: 0, spam: 0, caps: 0 };

    for (const event of filteredEvents) {
      const msg = event.message || "";
      const normalized = normalizeMsg(msg);
      const dupCount = duplicateMap.get(normalized) || 0;
      const tox = toxicityScore(msg);
      const caps = allCapsRatio(msg);
      const isChatLike = Boolean(msg) || (event.event_type || "").includes("chat");

      let reason = "";
      if (isChatLike) {
        if (activeCleanseThresholds.hideAggression && tox >= activeCleanseThresholds.aggressionThreshold) reason = "aggression";
        else if (activeCleanseThresholds.hideSpam && dupCount >= activeCleanseThresholds.spamThreshold) reason = "spam";
        else if (activeCleanseThresholds.hideCaps && caps >= activeCleanseThresholds.capsThreshold) reason = "caps";
      }

      if (reason) {
        hiddenByReason[reason] += 1;
        hidden.push({ ...event, _hiddenReason: reason });
      } else {
        visible.push(event);
      }
    }

    return {
      visible,
      hidden,
      hiddenCount: hidden.length,
      hiddenByReason,
    };
  }, [filteredEvents, duplicateMap, activeCleanseThresholds]);

  const groupedEvents = useMemo(() => {
    const groups = new Map();
    for (const event of cleanseResult.visible) {
      const key = event.event_type || "unknown";
      const existing = groups.get(key) || [];
      existing.push(event);
      groups.set(key, existing);
    }
    return Array.from(groups.entries()).slice(0, 4);
  }, [cleanseResult.visible]);

  const filteredStreamers = useMemo(() => {
    const query = (streamerSearch || "").trim().toLowerCase();
    if (!query) return availableStreamers.slice(0, 8);
    // Backend already returns ranked search results for query mode.
    return availableStreamers.slice(0, 12);
  }, [availableStreamers, streamerSearch]);

  const getStreamerName = (streamer) => {
    const raw = String(streamer?.display_name || streamer?.username || "Streamer").trim();
    if (raw.includes("@")) {
      const left = raw.split("@")[0] || "Streamer";
      return left.replace(/[_\-]+/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
    }
    return raw;
  };

  const getStreamerInitials = (name) => {
    const parts = String(name || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (!parts.length) return "ST";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  };

  const streamStatusLabel = (() => {
    if (eventStreamStatus === "live") return "Watching";
    if (eventStreamStatus === "connecting") return "Syncing";
    if (eventStreamStatus === "error") return "Retrying";
    return "Waiting";
  })();

  const capabilityState = (() => {
    if (activeStreamerId && eventStreamStatus === "live") {
      return "Connected";
    }
    if (activeStreamerId) return "Hybrid";
    return "Solo";
  })();

  const streamerDisplayName =
    viewerData?.active_streamer?.display_name
    || viewerData?.active_streamer?.username
    || "Streamer";

  const streamVibe = useMemo(() => {
    const serverLabel = viewerData?.stream_vibe?.label;
    const now = Date.now();
    const recent = (liveEvents || []).filter((event) => {
      const ts = new Date(event.received_at || event.created_at || 0).getTime();
      return Number.isFinite(ts) && now - ts <= 10 * 60 * 1000;
    });
    const chatEvents = recent.filter((event) =>
      (event.event_type || "").includes("chat") || Boolean((event.message || "").trim()),
    );
    const clipSignals = recent.filter((event) =>
      ["clip_created", "viewer_clip_ready", "viewer_impact"].includes(event.event_type || ""),
    ).length;
    const chatPerMin = Number((chatEvents.length / 10).toFixed(1));
    const hypeSignals = chatEvents.filter((event) =>
      /wow|omg|insane|clutch|pog|let'?s go|holy/i.test(event.message || ""),
    ).length + clipSignals;

    const vibeConfig = {
      "Focused gameplay": {
        background: "linear-gradient(135deg, #0F0D22 0%, #140F2A 50%, #0D0B18 100%)",
        glow: "rgba(76,159,255,0.35)",
        emoji: "\u{1F3AE}",
        subtext: "Deep focus mode",
      },
      "Hype moment": {
        background: "linear-gradient(135deg, #1A0A00 0%, #2A1000 100%)",
        glow: "rgba(232,132,58,0.35)",
        emoji: "\u{1F525}",
        subtext: "Chat is going crazy",
      },
      "Chill vibes": {
        background: "linear-gradient(135deg, #001A12 0%, #001A0A 100%)",
        glow: "rgba(0,229,160,0.35)",
        emoji: "\u{1F60C}",
        subtext: "Relaxed atmosphere",
      },
      Intense: {
        background: "linear-gradient(135deg, #1A0010 0%, #200014 100%)",
        glow: "rgba(255,61,154,0.35)",
        emoji: "\u26A1",
        subtext: "High stakes moment",
      },
    };

    let label = "Focused gameplay";
    if (serverLabel && /hype|viral|popping/i.test(serverLabel)) label = "Hype moment";
    else if (serverLabel && /intense|critical|heat/i.test(serverLabel)) label = "Intense";
    else if (serverLabel && /chill|calm|steady/i.test(serverLabel)) label = "Chill vibes";
    else if (hypeSignals >= 12 || chatPerMin >= 8) label = "Hype moment";
    else if (hypeSignals >= 6 || chatPerMin >= 4) label = "Intense";
    else if (chatPerMin >= 1.5) label = "Chill vibes";

    const config = vibeConfig[label] || vibeConfig["Focused gameplay"];

    return {
      label,
      ...config,
      chatPerMin,
      viewerCount: Number(viewerData?.currentStream?.viewer_count || 0),
    };
  }, [liveEvents, viewerData?.stream_vibe?.label, viewerData?.currentStream?.viewer_count]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><div className="text-center"><div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4" /><p className="text-gray-600">Loading viewer mode...</p></div></div>;
  }

  return (
    <div className={`viewer-redesign-v2 ${viewerSettings.compact_mode ? "kazumi-compact" : ""}`}>
      <aside className="viewer-shell-sidebar">
        <div className="viewer-brand-row">
          <img src="/logo.png" alt="Kazumee" style={{ width: 26, height: 26, borderRadius: 6, objectFit: "contain" }} />
          <span>Kazumee</span>
        </div>

        <section className="viewer-glass-card viewer-profile-card">
          <img className="viewer-profile-avatar" src="/logo.png" alt="Kazumee viewer" />
          <div className="viewer-profile-copy">
            <strong>{viewerData?.viewer?.id ? `Viewer #${viewerData.viewer.id}` : "Viewer"}</strong>
            <span>{viewerData?.viewer?.email || viewerData?.viewer?.username || "viewer@kazumee.live"}</span>
          </div>
          <div className="viewer-account-actions">
            <a href="/auth">Account</a>
            <a href="/auth">Logout</a>
          </div>
        </section>

        <nav className="viewer-side-nav" aria-label="Viewer navigation">
          <a href="/viewer">Home</a>
          <a href="#clips" onClick={(e) => {
            e.preventDefault();
            document.getElementById("viewer-clips-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}>Clip Library</a>
          <a href="#settings" onClick={(e) => {
            e.preventDefault();
            setSettingsModalOpen(true);
          }}>Settings</a>
          <a href="#comments" onClick={(e) => {
            e.preventDefault();
            document.getElementById("viewer-ask-zumi")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}>Comments</a>
        </nav>

        <section className="viewer-glass-card viewer-vote-card">
          <div className="viewer-card-heading">
            <Vote className="viewer-icon" />
            <h2>Scene Voting</h2>
          </div>
          {impactMessage && <p className="viewer-mini-note">{impactMessage}</p>}
          {voteDelay > 0 && (
            <p className="viewer-delay-note"><Timer className="viewer-tiny-icon" /> Results update in {voteDelay}s</p>
          )}
          <div className="viewer-scene-list">
            {["Gameplay Camera", "Reaction Cam", "Full Screen", "Chat Overlay"].map((scene) => (
              <button
                key={scene}
                type="button"
                onClick={() => { setVoteDelay(Math.ceil(latencyMs / 1000)); submitVote(scene); }}
                className="viewer-scene-button"
              >
                <span>{scene}</span>
                <small>{voteCounts[scene] || 0} votes <Heart className="viewer-heart" /></small>
              </button>
            ))}
          </div>
        </section>

        <section className="viewer-glass-card viewer-status-card">
          <h2>Credits & Status</h2>
          <dl>
            <div><dt>Credits</dt><dd>{viewerCredits}</dd></div>
            <div><dt>Shield</dt><dd>{shieldMsLeft > 0 ? `${Math.ceil(shieldMsLeft / 1000)}s` : `${Math.round(latencyMs / 1000)}s`}</dd></div>
            <div><dt>Stream</dt><dd>{streamStatusLabel}</dd></div>
            <div><dt>Cooldown</dt><dd>{viewerCooldown}s</dd></div>
          </dl>
        </section>
      </aside>

      <main className="viewer-main-column">
        {showOnboarding && (
          <section className="viewer-glass-card viewer-onboarding">
            <div>
              <h2>Welcome to Viewer Mode</h2>
              <p>You can ask questions, request clips, and vote on scenes. Some actions require streamer approval.</p>
            </div>
            <button type="button" className="viewer-secondary-button" onClick={() => { localStorage.setItem("kazumi_viewer_onboarded", "true"); setShowOnboarding(false); }}>Got it</button>
          </section>
        )}

        <section className="viewer-player-shell">
          <div
            className="viewer-player-frame"
            role="button"
            tabIndex={0}
            onClick={triggerCatchUp}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                triggerCatchUp();
              }
            }}
          >
            <div className="viewer-live-chip"><span />{viewerData?.currentStream ? "LIVE" : "OFFLINE"}</div>
            <button type="button" className="viewer-play-button" aria-label="Catch up to stream">
              <Play className="viewer-play-icon" />
            </button>
          </div>
          <div className="viewer-player-actions">
            <button type="button" className="viewer-primary-button" onClick={triggerCatchUp} disabled={catchupLoading}>{catchupLoading ? "Working" : "Catch Up"}</button>
            <button type="button" className="viewer-secondary-button" onClick={() => runCatchupRecap("full")} disabled={catchupLoading}>Recap</button>
            <button type="button" className="viewer-secondary-button" onClick={() => document.getElementById("viewer-discover-streamers")?.scrollIntoView({ behavior: "smooth", block: "start" })}>Find Stream</button>
          </div>
        </section>

        <section className="viewer-glass-card viewer-highlights-section">
          <div className="viewer-section-title-row">
            <div>
              <span className="viewer-eyebrow">Highlights</span>
              <h2>Recent clips</h2>
            </div>
            <button type="button" className="viewer-secondary-button viewer-small-button" onClick={openHighlightReel} disabled={catchupLoading}>See All</button>
          </div>
          <div className="viewer-highlights-row">
            {(catchupHighlights.length ? catchupHighlights : (viewerData?.yourClips || [])).slice(0, 8).map((clip, index) => (
              <CatchUpClipCard key={`${clip.id || clip.url || index}`} clip={clip} />
            ))}
            {!catchupHighlights.length && !(viewerData?.yourClips || []).length && (
              <div className="viewer-empty-card">No highlights yet. Run catch-up or request a clip while watching.</div>
            )}
          </div>
        </section>

        <section id="viewer-clips-panel" className="viewer-glass-card viewer-clips-panel">
          <div className="viewer-section-title-row">
            <div>
              <span className="viewer-eyebrow">Clip Library</span>
              <h2>Your clip requests</h2>
            </div>
            <button type="button" className="viewer-secondary-button viewer-small-button" onClick={() => document.getElementById("viewer-ask-zumi")?.scrollIntoView({ behavior: "smooth", block: "start" })}>New Clip</button>
          </div>
          <div className="viewer-clips-list">
            {companionTrackers.length > 0 ? (
              companionTrackers.map((tracker, idx) => (
                <div key={idx} className="viewer-clip-request-item">
                  <div>
                    <strong>{tracker.question || "Clip request"}</strong>
                    <small>{tracker.status === "answered" ? "✓ Approved" : tracker.status === "pending" ? "⏳ Pending" : "✗ Denied"}</small>
                  </div>
                  <time>{tracker.timestamp ? new Date(tracker.timestamp).toLocaleTimeString() : ""}</time>
                </div>
              ))
            ) : (
              <div className="viewer-empty-card">No clip requests yet. Use the Comments section to request clips.</div>
            )}
          </div>
        </section>

        <section className="viewer-glass-card viewer-leaderboard-panel">
          <div className="viewer-section-title-row">
            <div>
              <span className="viewer-eyebrow">Engagement</span>
              <h2>Top Contributors</h2>
            </div>
          </div>
          <div className="viewer-leaderboard-list">
            {trustLog.length > 0 ? (
              trustLog.slice(0, 10).map((entry, idx) => (
                <div key={idx} className="viewer-leaderboard-item">
                  <span className="viewer-rank">#{idx + 1}</span>
                  <div>
                    <strong>{entry.username || "Anonymous"}</strong>
                    <small>{entry.action_type || "Participated"}</small>
                  </div>
                  <span className="viewer-score">{entry.impact_points || 0}⚡</span>
                </div>
              ))
            ) : (
              <div className="viewer-empty-card">No votes or commands yet. Participate to appear here!</div>
            )}
          </div>
        </section>

        <section id="viewer-discover-streamers" className="viewer-glass-card viewer-search-section">
          <div className="viewer-section-title-row">
            <div>
              <span className="viewer-eyebrow">Find Streamer</span>
              <h2>Choose a live feed</h2>
            </div>
            <button type="button" className="viewer-secondary-button viewer-small-button" onClick={() => fetchStreamers(streamerSearch)}>Refresh</button>
          </div>
          <input
            type="text"
            value={streamerSearch}
            onChange={(e) => setStreamerSearch(e.target.value)}
            placeholder="🔍 Search any Twitch or YouTube streamer..."
            className="viewer-input"
          />
          <div className="viewer-streamer-list">
            {!!streamerDiagnostics?.message && <div className="viewer-alert-note">{streamerDiagnostics.message}</div>}
            {!!streamerDiagnostics?.external_requested && (
              <div className="viewer-muted-line">
                External discovery: Twitch {streamerDiagnostics.twitch_enabled ? "on" : "off"} | YouTube {streamerDiagnostics.youtube_enabled ? "on" : "off"} | results {Number(streamerDiagnostics.twitch_results || 0) + Number(streamerDiagnostics.youtube_results || 0)}
              </div>
            )}
            {streamerLoading ? (
              <div className="viewer-muted-line">Loading streamers...</div>
            ) : filteredStreamers.length ? (
              filteredStreamers.map((streamer) => {
                const displayName = getStreamerName(streamer);
                const initials = getStreamerInitials(displayName);
                return (
                  <article key={streamer.id} className="viewer-streamer-card">
                    <div className="viewer-streamer-avatar-wrap">
                      <img src={streamer.avatar_url || streamer.profile_image_url || "/logo.png"} alt={displayName} className="viewer-streamer-avatar" />
                    </div>
                    <div className="viewer-streamer-copy">
                      <strong>{displayName}{streamer.live ? <span>LIVE</span> : null}</strong>
                      <small>{initials} · {streamer.platform || "Platform"}</small>
                    </div>
                    <div className="viewer-streamer-platform-row">
                      {streamer.platform === "twitch" ? (
                        <span className="viewer-platform-badge viewer-platform-badge--twitch">T</span>
                      ) : null}
                      {streamer.platform === "youtube" ? (
                        <span className="viewer-platform-badge viewer-platform-badge--youtube">Y</span>
                      ) : null}
                      {streamer.platform === "kazumee" ? (
                        <span className="viewer-platform-badge viewer-platform-badge--kazumee">K</span>
                      ) : null}
                    </div>
                    {streamer.platform === "twitch" || streamer.platform === "youtube" ? (
                      <button
                        type="button"
                        className="viewer-secondary-button viewer-watch-button"
                        onClick={() => {
                          if (streamer?.url) {
                            window.open(streamer.url, "_blank", "noopener,noreferrer");
                            return;
                          }
                          openExternalStreamer(streamer);
                        }}
                      >
                        Watch
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="viewer-secondary-button viewer-watch-button"
                        onClick={() => switchToRecommendedStreamer(streamer.id, displayName)}
                        disabled={Number(activeStreamerId) === Number(streamer.id)}
                      >
                        {Number(activeStreamerId) === Number(streamer.id) ? "Watching" : "Watch"}
                      </button>
                    )}
                  </article>
                );
              })
            ) : (
              <div className="viewer-search-empty">
                <div className="viewer-muted-line">
                  {streamerSearch.trim() ? (
                    <>
                      <p>No results for "{streamerSearch}"</p>
                      <p style={{fontSize: '12px', marginTop: '8px', color: 'rgba(255,255,255,0.5)'}}>
                        Try searching with a different name or visit the platform directly
                      </p>
                    </>
                  ) : (
                    <>
                      <p>🔍 Search for any Twitch or YouTube streamer</p>
                      <p style={{fontSize: '12px', marginTop: '8px', color: 'rgba(255,255,255,0.5)'}}>
                        Enter a streamer username to find them
                      </p>
                    </>
                  )}
                </div>
                <div className="viewer-search-tips" style={{marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap'}}>
                  <a href="https://twitch.tv" target="_blank" rel="noopener noreferrer" className="viewer-secondary-button viewer-small-button">
                    Visit Twitch
                  </a>
                  <a href="https://youtube.com/live" target="_blank" rel="noopener noreferrer" className="viewer-secondary-button viewer-small-button">
                    Visit YouTube
                  </a>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>

      <aside className="viewer-right-panel">
        <section className="viewer-glass-card viewer-now-card">
          <span className="viewer-eyebrow">Now Watching</span>
          <h1>{streamerDisplayName}</h1>
          <p>{viewerData?.currentStream?.title || "Pick a streamer, catch up fast, and use Zumi to understand the stream."}</p>
          <div className="viewer-now-actions">
            <button type="button" className="viewer-primary-button" onClick={triggerCatchUp} disabled={catchupLoading}>Catch Up</button>
            <button type="button" className="viewer-secondary-button" onClick={() => document.getElementById("viewer-ask-zumi")?.scrollIntoView({ behavior: "smooth", block: "start" })}>Ask Zumi</button>
            <button type="button" className="viewer-connected-button">{capabilityState}</button>
          </div>
        </section>

        <section className="viewer-vibe-strip" style={{ background: streamVibe.background }}>
          <div className="viewer-vibe-main">
            <span className="viewer-vibe-emoji">{streamVibe.emoji}</span>
            <div>
              <h2>{streamVibe.label}</h2>
              <p>{streamVibe.subtext}</p>
            </div>
          </div>
          <div className="viewer-vibe-stats">
            <div><strong>{streamVibe.chatPerMin}</strong><span>msg/min</span></div>
            <div><strong>{streamVibe.viewerCount.toLocaleString()}</strong><span>viewers</span></div>
          </div>
        </section>

        <section ref={catchupSectionRef} className="viewer-glass-card viewer-recap-panel">
          <div className="viewer-recap-head">
            <img src="/logo.png" alt="Zumi" className="viewer-zumi-avatar" />
            <div>
              <span className="viewer-eyebrow">Catch-Up Recap</span>
              <h2>{catchupRecap?.mode === "full" ? "Full recap" : "Quick recap"}</h2>
            </div>
          </div>
          <div className="viewer-tab-row">
            <button type="button" className="viewer-tab-button active" onClick={() => runCatchupRecap("quick")} disabled={catchupLoading}>{catchupLoading ? "Working" : "Quick"}</button>
            <button type="button" className="viewer-tab-button" onClick={() => runCatchupRecap("full")} disabled={catchupLoading}>Full</button>
            <button type="button" className="viewer-tab-button" onClick={openHighlightReel} disabled={catchupLoading}>Clips</button>
          </div>
          <div className="viewer-recap-box">
            <p>{catchupRecap?.recap || "Click Quick to get caught up in 30 seconds"}</p>

            {Array.isArray(catchupRecap?.clips) && catchupRecap.clips.length > 0 && (
              <div className="viewer-recap-clips-row">
                {catchupRecap.clips.map((clip) => (
                  <div
                    key={clip.id || clip.url}
                    className="viewer-recap-clip-card"
                    onMouseEnter={() => {
                      try {
                        const v = document.getElementById(`kazumi-recap-video-${clip.id}`);
                        v?.play?.();
                      } catch {}
                    }}
                    onMouseLeave={() => {
                      try {
                        const v = document.getElementById(`kazumi-recap-video-${clip.id}`);
                        if (v) {
                          v.pause();
                          v.currentTime = 0;
                        }
                      } catch {}
                    }}
                  >
                    <div className="viewer-recap-clip-media">
                      {clip.thumbnail_url ? (
                        <img src={clip.thumbnail_url} className="viewer-recap-clip-thumb" alt={clip.title || "clip"} />
                      ) : null}
                      {clip.url ? (
                        <video
                          id={`kazumi-recap-video-${clip.id}`}
                          className="viewer-recap-clip-video"
                          src={clip.url}
                          muted
                          loop
                          playsInline
                          preload="metadata"
                        />
                      ) : null}
                      <div className="viewer-recap-clip-play-overlay">
                        <Play className="w-3.5 h-3.5 text-white ml-0.5" />
                      </div>
                    </div>
                    <div className="viewer-recap-clip-meta">
                      <p className="viewer-recap-clip-title">{clip.title}</p>
                      <p className="viewer-recap-clip-moment">{clip.moment_label}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {catchupRecap?.energy_rating && (
              <div
                className={`viewer-recap-energy-badge viewer-recap-energy-badge--${String(catchupRecap.energy_rating).toLowerCase().replace(/\s+/g, "")}`}
              >
                {catchupRecap.energy_rating}
              </div>
            )}

            {recapFreshness && <small>{recapFreshness}</small>}
            {catchupRecap?.topics?.length > 0 && <small>Topics: {catchupRecap.topics.join(", ")}</small>}
            {catchupRecap?.dominant_platform && <small>Main platform: {catchupRecap.dominant_platform}</small>}
          </div>
          <button type="button" className="viewer-secondary-button viewer-share-button" onClick={shareCatchup}>Share recap</button>

        </section>

        <section id="viewer-ask-zumi" className="viewer-glass-card viewer-ask-panel">
          <div className="viewer-section-title-row compact">
            <div>
              <span className="viewer-eyebrow">Ask Zumi</span>
              <h2>Stream context</h2>
            </div>
          </div>
          <div className="viewer-question-pills">
            {(viewerData?.loreSuggestions || ["What did I miss?", "Why is chat hyped?", "Which clip should I watch?"]).slice(0, 3).map((suggestion, index) => (
              <button key={index} type="button" onClick={() => setCompanionInput(suggestion)}>{suggestion}</button>
            ))}
          </div>
          <textarea
            value={companionInput}
            onChange={(e) => setCompanionInput(e.target.value)}
            placeholder="Ask what is happening, why chat is hyped, or what you missed..."
            className="viewer-textarea"
            rows={3}
          />
          <button type="button" className="viewer-primary-button viewer-full-button" onClick={analyzeCompanion} disabled={companionLoading}>{companionLoading ? "Thinking" : "Ask"}</button>
          {companionResult && (
            <div className="viewer-answer-box">
              <span>Answer</span>
              <p>{companionResult.improved_message}</p>
              <div className="viewer-answer-metrics">
                <small>Timing {companionResult.timing_score}</small>
                <small>Notice {companionResult.notice_score}</small>
                <small>Dupes {companionResult.duplicate_count_recent}</small>
              </div>
              <div className="viewer-answer-actions">
                <button type="button" onClick={() => navigator.clipboard.writeText(companionResult.improved_message || "")}>Copy</button>
                <button type="button" onClick={markCompanionSent}>I Sent It</button>
              </div>
            </div>
          )}
          {companionTrackers.length > 0 && (
            <div className="viewer-tracker-list">
              {companionTrackers.slice(0, 3).map((t) => (
                <article key={t.id}>
                  <small>#{t.id} · {t.state} · dupes {t.duplicate_count || 0}</small>
                  <p>{t.message}</p>
                  {t.retry_message && <p className="viewer-retry-message">{t.retry_message}</p>}
                  <div>
                    {t.state === "needs_retry" && <button type="button" onClick={() => getRetrySuggestion(t.id)} disabled={retryLoadingId === t.id}>{retryLoadingId === t.id ? "Generating" : "Retry"}</button>}
                    <button type="button" onClick={() => markTrackerAnswered(t.id)}>Answered</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="viewer-glass-card viewer-feed-panel">
          <div className="viewer-section-title-row compact">
            <div>
              <span className="viewer-eyebrow">Live Event Feed</span>
              <h2>Grouped events</h2>
            </div>
            <button type="button" className="viewer-secondary-button viewer-small-button" onClick={() => setEventPaused((prev) => !prev)}>{eventPaused ? "Resume" : "Pause"}</button>
          </div>
          <div className="viewer-feed-controls">
            <select value={eventPlatformFilter} onChange={(e) => setEventPlatformFilter(e.target.value)}><option value="all">All platforms</option><option value="twitch">Twitch</option><option value="youtube">YouTube</option></select>
            <select value={eventTypeFilter} onChange={(e) => setEventTypeFilter(e.target.value)}><option value="all">All types</option>{eventTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select>
            <button type="button" onClick={() => setImportantOnly((prev) => !prev)} className={importantOnly ? "active" : ""}>Important</button>
          </div>
          {latencyMs > 0 && <p className="viewer-mini-note">Feed delay active: {Math.round(latencyMs / 1000)}s</p>}
          {vibeStrictness !== "off" && cleanseResult.hiddenCount > 0 && <p className="viewer-mini-note">{cleanseResult.hiddenCount} messages filtered</p>}
          <div className="viewer-event-groups">
            {!cleanseResult.visible.length ? <div className="viewer-muted-line">No live events visible right now.</div> : groupedEvents.map(([type, events]) => (
              <article key={type} className="viewer-event-group">
                <header><span>{type}</span><small>{classifySeverity(events[0])}</small></header>
                {events.slice(0, 3).map((event, idx) => (
                  <div key={event.id ?? `${event.platform}-${event.event_type}-${idx}`} className="viewer-event-row">
                    <div><small>{event.platform}</small><strong>{event.username || "Anonymous"}</strong>{event.message && <p>{event.message}</p>}</div>
                    <time>{event.received_at ? new Date(event.received_at).toLocaleTimeString() : ""}</time>
                  </div>
                ))}
              </article>
            ))}
          </div>
          {showHiddenEvents && cleanseResult.hidden.length > 0 && (
            <div className="viewer-hidden-feed">
              <span>Filtered Messages</span>
              {cleanseResult.hidden.slice(0, 8).map((event, idx) => (
                <p key={`${event.id || idx}-hidden`}>{event._hiddenReason} · {event.username || "Anonymous"}: {event.message}</p>
              ))}
            </div>
          )}
        </section>

        <section className="viewer-glass-card viewer-command-panel">
          <div className="viewer-card-heading">
            <MessageSquare className="viewer-icon" />
            <h2>Submit Command</h2>
          </div>
          {shieldMsLeft > 0 && <p className="viewer-mini-note">Syncing with stream delay...</p>}
          <textarea
            value={commandText}
            onChange={(e) => setCommandText(e.target.value)}
            placeholder="Request a scene change, clip, or interaction..."
            className="viewer-textarea"
            rows={3}
          />
          <button type="button" onClick={handleSubmitCommand} disabled={viewerCooldown > 0} className="viewer-primary-button viewer-full-button">
            <Send className="viewer-tiny-icon" />{viewerCooldown > 0 ? `Wait ${viewerCooldown}s` : "Submit Command"}
          </button>
        </section>
      </aside>

      {catchUpNudgeVisible && !hasUsedCatchUp && (
        <div className="viewer-nudge">
          <p>Joined mid-stream?</p>
          <span>Get caught up in 30 seconds</span>
          <div>
            <button type="button" onClick={triggerCatchUp}>Catch Up</button>
            <button type="button" onClick={dismissCatchUpNudge}>x</button>
          </div>
        </div>
      )}

      <div className="viewer-toast-stack">
        {toastQueue.slice(-3).map((toast) => (
          <div key={toast.id} className="viewer-toast">
            {toast.status === "approved" ? <CheckCircle2 className="viewer-tiny-icon" /> : toast.status === "queued" ? <AlertTriangle className="viewer-tiny-icon" /> : <XCircle className="viewer-tiny-icon" />}
            <span>{toast.message}</span>
          </div>
        ))}
      </div>

      {highlightReelOpen && (
        <div className="viewer-highlight-modal">
          <div className="viewer-highlight-card">
            <header>
              <div>
                <span className="viewer-eyebrow">Picture in Picture</span>
                <h2>Top 3 Highlights</h2>
              </div>
              <button type="button" className="viewer-secondary-button viewer-small-button" onClick={() => setHighlightReelOpen(false)}>Close</button>
            </header>
            <div className="viewer-highlight-list">
              {highlightReel.length === 0 ? <div className="viewer-muted-line">No highlights available yet.</div> : highlightReel.map((clip) => (
                <article key={clip.id}>
                  <strong>{clip.title}</strong>
                  {clip.url ? <video src={clip.url} controls muted /> : <div className="viewer-clip-unavailable">Clip preview unavailable</div>}
                </article>
              ))}
            </div>
          </div>
        </div>
      )}

      <ViewerSettingsModal
        isOpen={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        settings={viewerSettings}
        onSettingsChange={handleSettingsChange}
      />
    </div>
  );
}


