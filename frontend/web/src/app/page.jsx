"use client";

// Smart routing wrapper - handles landing page + auth redirect
import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { useNavigate } from "react-router";
import { getAuthToken, apiFetch } from "@/lib/apiClient";
import LandingPage from "../components/landing/LandingPage";

// Placeholder for dashboard (imported below after wrapper)
let DashboardComponent = null;

export default function HomePage() {
  const navigate = useNavigate();
  const [showDashboard, setShowDashboard] = useState(false);
  const [showLoading, setShowLoading] = useState(true);

  useEffect(() => {
    const checkAuthAndRoute = async () => {
      // Check /auth/me with session credentials included
      // This persists auth across page refreshes via session cookie
      try {
        const res = await apiFetch("/auth/me", {
          method: "GET",
          credentials: "include", // ← CRITICAL: Include session cookies
        });

        if (!res.ok) {
          // Not authenticated = show landing page
          setShowDashboard(false);
          setShowLoading(false);
          return;
        }

        const data = await res.json();
        const userRole = data?.user?.role;
        const onboardingComplete = data?.user?.onboarding_complete;

        if (userRole === "streamer") {
          // Streamer must complete onboarding first
          if (onboardingComplete === false) {
            setShowLoading(false);
            navigate("/onboarding", { replace: true });
          } else {
            // Onboarding complete = show dashboard
            setShowDashboard(true);
            setShowLoading(false);
          }
        } else if (userRole === "viewer") {
          // Authenticated viewer = redirect to /viewer
          setShowLoading(false);
          navigate("/viewer", { replace: true });
        } else {
          // Unknown role = show landing page
          setShowDashboard(false);
          setShowLoading(false);
        }
      } catch (error) {
        console.error("Error checking auth:", error);
        // On error, assume not authenticated = show landing page
        setShowDashboard(false);
        setShowLoading(false);
      }
    };

    // CRITICAL: Wait for auth check to complete before rendering
    checkAuthAndRoute();
  }, [navigate]);

  if (showLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-gray-200 border-t-gray-800 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show landing page for unauthenticated users
  // Authenticated streamers see the dashboard below
  if (!showDashboard) {
    return <LandingPage />;
  }

  // Authenticated streamer - render the full dashboard
  return <KazumiDashboard />;
}

// ============================================
// KAZUMI DASHBOARD - Streamer Command Center
// ============================================

import AIApprovalDashboard from "../components/AIApprovalDashboard";
import ClipManagement from "../components/ClipManagement";
import ObsStatus from "../components/ObsStatus";
import { useObsTruth } from "../hooks/useObsTruth";
import { usePanicMode } from "../hooks/usePanicMode";
import { useWebSocket } from "../hooks/useWebSocket";
import { useSettings } from "../lib/SettingsContext";
import { toast } from "sonner";
import { getActiveStreamerId, isAuthBypassEnabled, setActiveStreamerId } from "@/lib/apiClient";
import { API_BASE } from "../config";
import {
  Home, Radio, Scissors, Shield, Users, Settings, TrendingUp, Mic, Bot,
  ArrowRight, Activity, AlertCircle, CheckCircle, Clock, Eye, MessageSquare,
  BarChart2, Brain, Zap, MicOff, Video, Camera, Search,
} from "lucide-react";

const normalizeSpeech = (value) =>
  String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const extractWakeWordCommand = (transcript, triggerWord) => {
  const normalizedTranscript = normalizeSpeech(transcript);
  const wake = normalizeSpeech(triggerWord || "kazumi");
  if (!normalizedTranscript) return { matched: false, command: "" };
  if (!wake) return { matched: true, command: normalizedTranscript };

  if (normalizedTranscript.startsWith(wake)) {
    return { matched: true, command: normalizedTranscript.slice(wake.length).trim() };
  }

  const wakeWithSpace = `${wake} `;
  const idx = normalizedTranscript.indexOf(wakeWithSpace);
  if (idx >= 0) {
    return { matched: true, command: normalizedTranscript.slice(idx + wakeWithSpace.length).trim() };
  }
  return { matched: false, command: "" };
};

const cleanKazumiCommand = (value, triggerWord = "Kazumi") => {
  let text = String(value || "").trim();
  if (!text) return "";
  const names = [triggerWord, "kazumi", "kazumee", "zumi"]
    .map((item) => String(item || "").trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .filter(Boolean)
    .join("|");
  const greeting = "(?:hey|hi+|hello|yo|ok(?:ay)?|please)";
  let changed = true;
  while (changed) {
    const before = text;
    text = text
      .replace(new RegExp(`^\\s*${greeting}[,\\s]+`, "i"), "")
      .replace(new RegExp(`^\\s*(?:${names})[,\\s]+`, "i"), "");
    changed = text !== before;
  }
  return text.replace(/\s+/g, " ").trim();
};

const parseDelayedCommand = (value) => {
  const text = String(value || "").trim();
  const match = text.match(/\b(?:in|after)\s+(\d+)\s*(seconds?|secs?|sec|s|minutes?|mins?|min|m)\b/i);
  if (!match) return { command: text, delayMs: 0, delayLabel: "" };
  const amount = Number(match[1]);
  const unit = match[2].toLowerCase();
  const multiplier = unit.startsWith("m") ? 60_000 : 1_000;
  return {
    command: text.replace(match[0], "").replace(/\s+/g, " ").trim(),
    delayMs: Math.max(1_000, Math.min(amount * multiplier, 6 * 60 * 60 * 1000)),
    delayLabel: `${amount} ${unit.startsWith("m") ? "minute" : "second"}${amount === 1 ? "" : "s"}`,
  };
};

function KazumiDashboard() {
  const [mode, setMode] = useState("streamer");
  const [toolSearch, setToolSearch] = useState("");
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [userRole, setUserRole] = useState("streamer"); // 'streamer' or 'viewer'
  const [authUser, setAuthUser] = useState(null);
  const [streamers, setStreamers] = useState([]);
  const [activeStreamerId, setActiveStreamerIdState] = useState(getActiveStreamerId());
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showFullFeed, setShowFullFeed] = useState(false);
  const [liveEvents, setLiveEvents] = useState([]);
  const [eventStreamStatus, setEventStreamStatus] = useState("idle");
  const [eventPaused, setEventPaused] = useState(false);
  const [eventPlatformFilter, setEventPlatformFilter] = useState("all");
  const [eventTypeFilter, setEventTypeFilter] = useState("all");
  const [momentQuery, setMomentQuery] = useState("");
  const [momentResults, setMomentResults] = useState([]);
  const [momentLoading, setMomentLoading] = useState(false);
  const [momentMessage, setMomentMessage] = useState("");
  const [momentPlatforms, setMomentPlatforms] = useState(["twitch", "youtube", "tiktok", "kick"]);
  const [savedMoments, setSavedMoments] = useState([]);
  const [superChatData, setSuperChatData] = useState({ grouped_notifications: [], to_answer: [], stats: null });
  const [superChatLoading, setSuperChatLoading] = useState(false);
  const [blockedKeywordInput, setBlockedKeywordInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [isStreamer, setIsStreamer] = useState(true);
  const [micMuted, setMicMuted] = useState(false);
  const [micStatusMessage, setMicStatusMessage] = useState("");
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [clipNowBusy, setClipNowBusy] = useState(false);
  const [clipPulse, setClipPulse] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [postStreamReport, setPostStreamReport] = useState(null);
  const [postStreamGenerating, setPostStreamGenerating] = useState(false);
  const [obsSources, setObsSources] = useState([]);
  const [obsCameras, setObsCameras] = useState([]);
  const [sourcePanelLoading, setSourcePanelLoading] = useState(false);
  const [sourceActionBusy, setSourceActionBusy] = useState({});
  const [askZumiInput, setAskZumiInput] = useState("");
  const [askZumiResponse, setAskZumiResponse] = useState("");
  const [askZumiLoading, setAskZumiLoading] = useState(false);
  const [askZumiHistory, setAskZumiHistory] = useState([]);
  const recognitionRef = useRef(null);
  const shouldRestartRecognitionRef = useRef(false);
  const previousStreamingRef = useRef(null);
  const { state: obsState } = useObsTruth();
  const { lastMessage } = useWebSocket();
  const { settings, updateSetting, saveSettings } = useSettings();
  const { isPanicMode, deactivatePanicMode } = usePanicMode();
  const eventSourceRef = useRef(null);
  const continuousListening = settings?.voice?.enabled ?? true;
  const triggerWord = settings?.voice?.triggerWord || "Kazumi";

  // --- UPDATED: Polling Logic ---
  useEffect(() => {
    // Initial fetch
    fetchDashboardData();
    fetchAuthUser();
    fetchStreamers();
    fetchSuperChatSorter();

    // Set up interval to refresh every 5 seconds
    const interval = setInterval(() => {
      fetchDashboardData();
      fetchSuperChatSorter();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (userRole !== "streamer") return;
    fetchObsSourcesAndCameras();
    const interval = setInterval(() => {
      fetchObsSourcesAndCameras({ silent: true });
    }, 5000);
    return () => clearInterval(interval);
  }, [userRole, activeStreamerId]);

  useEffect(() => {
    if (userRole === "viewer" && typeof window !== "undefined" && window.location.pathname === "/") {
      window.location.href = "/viewer";
    }
  }, [userRole]);

  useEffect(() => {
    return () => {
      shouldRestartRecognitionRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onend = null;
          recognitionRef.current.stop();
        } catch {
          // ignore cleanup errors
        }
      }
    };
  }, []);

  useEffect(() => {
    if (userRole !== "streamer") return;
    const onKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "c") {
        event.preventDefault();
        void triggerClipNow();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [userRole, clipNowBusy]);

  useEffect(() => {
    if (userRole !== "streamer") return;
    const currentlyStreaming = Boolean(obsState?.streaming);
    if (previousStreamingRef.current === null) {
      previousStreamingRef.current = currentlyStreaming;
      return;
    }
    if (previousStreamingRef.current && !currentlyStreaming) {
      void triggerPostStreamReport();
    }
    previousStreamingRef.current = currentlyStreaming;
  }, [userRole, obsState?.streaming]);

  const fetchStreamers = async () => {
    try {
      const response = await apiFetch("/auth/streamers");
      const data = await response.json();
      setStreamers(data.streamers || []);
    } catch (error) {
      console.error("Error fetching streamers:", error);
    }
  };

  const fetchAuthUser = async () => {
    try {
      const response = await apiFetch("/auth/me");
      const data = await response.json();
      if (data?.user) {
        setAuthUser(data.user);
        setUserRole(data.user.role);
        setMode(data.user.role);
        setIsStreamer(data.user.role === "streamer");
        if (data.streamer_id) {
          setActiveStreamerId(data.streamer_id);
          setActiveStreamerIdState(data.streamer_id);
        }
        if (data.user.role === "viewer" && !data.streamer_id) {
          setShowOnboarding(true);
        }
      }
    } catch (error) {
      console.error("Error fetching auth user:", error);
    }
  };

  const chooseStreamer = async (streamerId) => {
    try {
      const response = await apiFetch("/auth/active-streamer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ streamer_id: streamerId }),
      });
      if (response.ok) {
        setActiveStreamerId(streamerId);
        setActiveStreamerIdState(streamerId);
        setShowOnboarding(false);
      }
    } catch (error) {
      console.error("Error setting active streamer:", error);
    }
  };

  useEffect(() => {
    if (!authUser) return;
    const authToken = getAuthToken();
    if (!authToken) return;

    let cancelled = false;

    const connectStream = async () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      setEventStreamStatus("connecting");
      try {
        const tokenRes = await apiFetch("/auth/stream-token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(activeStreamerId ? { streamer_id: Number(activeStreamerId) } : {}),
        });
        if (!tokenRes.ok) {
          setEventStreamStatus("error");
          return;
        }
        const tokenData = await tokenRes.json();
        const streamToken = tokenData?.token;
        if (!streamToken || cancelled) {
          setEventStreamStatus("error");
          return;
        }

        const params = new URLSearchParams();
        params.set("token", streamToken);
        if (activeStreamerId) params.set("streamer_id", String(activeStreamerId));
        const url = `${API_BASE}/api/events/stream?${params.toString()}`;

        const es = new EventSource(url);
        eventSourceRef.current = es;
        es.onopen = () => setEventStreamStatus("live");
        es.onerror = () => setEventStreamStatus("error");
        es.onmessage = (event) => {
          if (eventPaused) return;
          try {
            const parsed = JSON.parse(event.data);
            if (parsed?.event_type === "clip_created" || parsed?.event_type === "viewer_clip_ready") {
              setClipPulse(true);
            }
            if (parsed?.event_type === "obs_source_changed") {
              fetchObsSourcesAndCameras({ silent: true });
            }
            const enriched = {
              ...parsed,
              received_at: new Date().toISOString(),
            };
            setLiveEvents((prev) => [enriched, ...prev].slice(0, 50));
          } catch (error) {
            console.error("Failed to parse event stream message:", error);
          }
        };
      } catch (error) {
        console.error("Failed to initialize stream token:", error);
        setEventStreamStatus("error");
      }
    };

    void connectStream();

    return () => {
      cancelled = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [authUser?.id, activeStreamerId, eventPaused]);

  // --- NEW: WebSocket Notifications ---
  useEffect(() => {
    if (lastMessage) {
      if (lastMessage.type === 'CLIP_SAVED') {
        setClipPulse(true);
        toast.success('Clip Saved', {
          description: 'Your clip has been saved successfully.',
          icon: <Video className="w-4 h-4" />,
        });
      } else if (lastMessage.type === 'OBS_ACTION_CONFIRMED') {
        toast.info('OBS Action Confirmed', {
          description: lastMessage.message || 'Action completed successfully.',
        });
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    if (!clipPulse) return;
    const timer = window.setTimeout(() => setClipPulse(false), 5000);
    return () => window.clearTimeout(timer);
  }, [clipPulse]);

  const fetchDashboardData = async () => {
    try {
      const response = await apiFetch("/api/dashboard");
      if (!response.ok) throw new Error("Failed to fetch dashboard data");
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error("Error fetching dashboard:", error);
    } finally {
      if (loading) setLoading(false);
    }
  };

  const triggerClipNow = async () => {
    if (clipNowBusy) return;
    try {
      setClipNowBusy(true);
      const response = await apiFetch("/api/commands/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "clip now", role: "streamer", confirmed: true }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Clip action failed");
      }
      setClipPulse(true);
      toast.success("Clip command sent", {
        description: payload?.message || "Kazumi is saving the replay buffer now.",
      });
      fetchDashboardData();
    } catch (error) {
      toast.error("Clip action failed", {
        description: error?.message || "Could not trigger clip right now.",
      });
    } finally {
      setClipNowBusy(false);
    }
  };

  const triggerPostStreamReport = async () => {
    if (postStreamGenerating || userRole !== "streamer") return;
    try {
      setPostStreamGenerating(true);
      toast.info("Stream ended. Generating report...", {
        description: "Kazumi is compiling your post-stream intelligence.",
      });
      const res = await apiFetch("/api/streamer/director/post-stream-report?hours=6");
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || data?.message || "Report generation failed");
      }
      setPostStreamReport(data?.report || null);
      toast.success("Post-stream report ready", {
        description: "Open Analytics to review momentum and drop-off insights.",
      });
    } catch (error) {
      toast.error("Post-stream report failed", {
        description: error?.message || "Could not generate report right now.",
      });
    } finally {
      setPostStreamGenerating(false);
    }
  };

  const handleFeedAction = (item) => {
    const href = item?.action_href;
    if (href) {
      window.location.href = href;
      return;
    }
    if (item?.type?.includes("moderation")) {
      window.location.href = "/moderation";
      return;
    }
    window.location.href = "/commands";
  };

  const fetchSuperChatSorter = async () => {
    if (userRole !== "streamer") return;
    try {
      setSuperChatLoading(true);
      const response = await apiFetch("/api/events/streamer-view?window_minutes=15&limit=300");
      if (!response.ok) return;
      const data = await response.json();
      setSuperChatData({
        grouped_notifications: data.grouped_notifications || [],
        to_answer: data.to_answer || [],
        stats: data.stats || null,
      });
    } catch (error) {
      console.error("Error fetching super-chat sorter:", error);
    } finally {
      setSuperChatLoading(false);
    }
  };

  const saveSuperChatSettings = async () => {
    try {
      await saveSettings();
      fetchSuperChatSorter();
      toast.success("Sorter preferences saved");
    } catch (error) {
      console.error("Failed to save super-chat settings:", error);
      toast.error("Failed to save sorter preferences");
    }
  };

  const setQuestionMuteMinutes = (minutes) => {
    if (!minutes || minutes <= 0) {
      updateSetting("superChatSorter", "muteQuestionsUntil", null);
      return;
    }
    const until = new Date(Date.now() + minutes * 60 * 1000).toISOString();
    updateSetting("superChatSorter", "muteQuestionsUntil", until);
  };

  const isQuestionMuted = (() => {
    const raw = settings?.superChatSorter?.muteQuestionsUntil;
    if (!raw) return false;
    const until = new Date(raw);
    return !Number.isNaN(until.getTime()) && until.getTime() > Date.now();
  })();

  const mutedMinutesLeft = (() => {
    if (!isQuestionMuted) return 0;
    const until = new Date(settings?.superChatSorter?.muteQuestionsUntil).getTime();
    return Math.max(1, Math.ceil((until - Date.now()) / 60000));
  })();

  const markQuestionAnswered = async (questionKey) => {
    try {
      const res = await apiFetch("/api/events/streamer-view/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_key: questionKey }),
      });
      if (!res.ok) {
        toast.error("Could not mark question answered");
        return;
      }
      setSuperChatData((prev) => ({
        ...prev,
        to_answer: (prev.to_answer || []).filter((q) => q.question_key !== questionKey),
      }));
      toast.success("Question marked answered");
    } catch (error) {
      console.error("Failed to mark question answered:", error);
      toast.error("Could not mark question answered");
    }
  };

  const setSourceBusy = (key, busy) => {
    setSourceActionBusy((prev) => {
      const next = { ...prev };
      if (busy) next[key] = true;
      else delete next[key];
      return next;
    });
  };

  const fetchObsSourcesAndCameras = async ({ silent = false } = {}) => {
    if (userRole !== "streamer") return;
    try {
      if (!silent) setSourcePanelLoading(true);
      const [sourceRes, cameraRes] = await Promise.all([
        apiFetch("/obs/sources"),
        apiFetch("/obs/cameras"),
      ]);
      const sourceData = await sourceRes.json().catch(() => ({}));
      const cameraData = await cameraRes.json().catch(() => ({}));
      if (sourceRes.ok) {
        setObsSources(Array.isArray(sourceData.sources) ? sourceData.sources : []);
      }
      if (cameraRes.ok) {
        setObsCameras(Array.isArray(cameraData.cameras) ? cameraData.cameras : []);
      }
    } catch (error) {
      if (!silent) {
        console.error("Failed to fetch OBS source panel:", error);
      }
    } finally {
      if (!silent) setSourcePanelLoading(false);
    }
  };

  const setSourceVisibility = async (sourceName, visible) => {
    if (!window.confirm(`${visible ? "Show" : "Hide"} OBS source "${sourceName}" now?`)) return;
    const key = `visibility:${sourceName}`;
    try {
      setSourceBusy(key, true);
      const response = await apiFetch("/obs/sources/visibility", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: sourceName, visible }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Could not update source visibility");
      }
      setObsSources((prev) =>
        prev.map((source) =>
          source.source_name === sourceName
            ? { ...source, visible: Boolean(payload.visible) }
            : source,
        ),
      );
      toast.success(`${sourceName} ${visible ? "shown" : "hidden"}`);
      fetchObsSourcesAndCameras({ silent: true });
    } catch (error) {
      toast.error("Source update failed", {
        description: error?.message || "Could not update source visibility.",
      });
    } finally {
      setSourceBusy(key, false);
    }
  };

  const switchSourceDevice = async (sourceName, deviceId) => {
    if (!deviceId) return;
    const cameraLabel = obsCameras.find((camera) => camera.device_id === deviceId)?.label || deviceId;
    if (!window.confirm(`Switch "${sourceName}" to camera "${cameraLabel}" now?`)) return;
    const key = `device:${sourceName}`;
    try {
      setSourceBusy(key, true);
      const response = await apiFetch("/obs/sources/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_name: sourceName,
          device_id: deviceId,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Could not switch camera");
      }
      setObsSources((prev) =>
        prev.map((source) =>
          source.source_name === sourceName
            ? { ...source, device_id: deviceId }
            : source,
        ),
      );
      toast.success(`${sourceName} switched`);
      fetchObsSourcesAndCameras({ silent: true });
    } catch (error) {
      toast.error("Camera switch failed", {
        description: error?.message || "Could not switch camera device.",
      });
    } finally {
      setSourceBusy(key, false);
    }
  };

  const handleChecklistFix = async (check) => {
    if (!check || check.passed) return;
    if (check.fix_action === "enable_moderation") {
      try {
        updateSetting("moderation", "autoModerate", true);
        updateSetting("moderation", "enabled", true);
        await saveSettings();
        toast.success("Moderation enabled");
        fetchDashboardData();
      } catch (error) {
        console.error("Failed to enable moderation from checklist:", error);
        toast.error("Could not enable moderation");
      }
      return;
    }
    if (check.fix_href) {
      window.location.href = check.fix_href;
    }
  };

  const startVoiceListening = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition not supported in this browser');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.continuous = Boolean(continuousListening);
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    shouldRestartRecognitionRef.current = true;

    recognition.onstart = () => {
      setIsVoiceListening(true);
      if (continuousListening) {
        setMicStatusMessage(`Wake word active: "${triggerWord}"`);
      } else {
        setMicStatusMessage("Listening for command...");
      }
    };

    recognition.onresult = (event) => {
      const transcripts = [];
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) {
          transcripts.push(String(result[0]?.transcript || "").trim());
        }
      }

      transcripts.forEach((spoken) => {
        if (!spoken) return;
        if (!continuousListening) {
          handleSendMessage(spoken);
          return;
        }
        const parsed = extractWakeWordCommand(spoken, triggerWord);
        if (!parsed.matched) return;
        if (!parsed.command) {
          setMicStatusMessage(`Wake word heard. Say "${triggerWord} <command>"`);
          return;
        }
        handleSendMessage(parsed.command);
      });
    };

    recognition.onend = () => {
      setIsVoiceListening(false);
      if (shouldRestartRecognitionRef.current && continuousListening) {
        setTimeout(() => {
          try {
            recognition.start();
          } catch {
            // ignore
          }
        }, 250);
      } else {
        setTimeout(() => setMicStatusMessage(""), 2000);
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsVoiceListening(false);
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setMicStatusMessage('Microphone permission denied');
      }
    };

    recognition.start();
  };

  const stopVoiceListening = () => {
    shouldRestartRecognitionRef.current = false;
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const executeStreamerCommand = async (command, { confirmed = true } = {}) => {
    const response = await apiFetch("/api/commands/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        command,
        role: "streamer",
        use_ai: true,
        confirmed,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data?.detail || data?.message || `Command failed (${response.status})`);
    }
    return data;
  };

  const handleSendMessage = async (message, options = {}) => {
    const cleaned = cleanKazumiCommand(message, triggerWord);
    if (!cleaned) return;
    const delayed = options.allowSchedule === false
      ? { command: cleaned, delayMs: 0, delayLabel: "" }
      : parseDelayedCommand(cleaned);

    if (delayed.delayMs > 0) {
      const scheduledText = `Scheduled: ${delayed.command} in ${delayed.delayLabel}`;
      setMicStatusMessage(scheduledText);
      setChatMessages((prev) => [
        ...prev,
        { sender: "user", text: cleaned, timestamp: new Date().toISOString() },
        { sender: "kazumi", text: scheduledText, timestamp: new Date().toISOString() },
      ]);
      setIsChatOpen(true);
      window.setTimeout(() => {
        void handleSendMessage(delayed.command, { allowSchedule: false });
      }, delayed.delayMs);
      return;
    }

    // Add user message to chat
    const userMessage = {
      sender: 'user',
      text: delayed.command,
      timestamp: new Date().toISOString()
    };
    setChatMessages(prev => [...prev, userMessage]);
    setIsChatOpen(true);

    try {
      const data = await executeStreamerCommand(delayed.command);

      if (data.success || data.execution_status === "success" || data.message) {
        // OBS command executed
        setMicStatusMessage(data.message ? `Kazumi: ${data.message}` : "Command executed");
        setTimeout(() => setMicStatusMessage(''), 3000);
      } else if (data.status === 'chat') {
        // Chat response
        const aiMessage = {
          sender: 'kazumi',
          text: data.message,
          timestamp: new Date().toISOString()
        };
        setChatMessages(prev => [...prev, aiMessage]);
      } else {
        // Ignored command
        const aiMessage = {
          sender: 'kazumi',
          text: `I didn't understand that command. ${data.reason || data.message || ""}`,
          timestamp: new Date().toISOString()
        };
        setChatMessages(prev => [...prev, aiMessage]);
      }
    } catch (error) {
      console.error('Error sending command:', error);
      const errorMessage = {
        sender: 'kazumi',
        text: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleAskZumi = async () => {
    if (!askZumiInput.trim()) return;
    const question = askZumiInput.trim();
    setAskZumiInput("");
    setAskZumiLoading(true);
    try {
      const response = await apiFetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: question,
          mode: "ask",
          context: {
            viewers: dashboardData?.currentViewers || 0,
            health_score: dashboardData?.healthScore || 0,
            recent_events: (liveEvents || []).slice(-10).map(e => e.description || e.type || "event")
          }
        }),
      });
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      const data = await response.json();
      const answer = data?.message || data?.answer || "Thanks for the question! I'm analyzing your stream data.";
      setAskZumiResponse(answer);
      setAskZumiHistory(prev => [...prev, { question, answer, timestamp: new Date().toISOString() }]);
      toast.success("Zumi responded!");
    } catch (error) {
      console.error("Error asking Zumi:", error);
      // Fallback response if AI is unavailable
      const fallbackAnswer = "I'm having trouble connecting to my AI brain right now. Try again in a moment!";
      setAskZumiResponse(fallbackAnswer);
      setAskZumiHistory(prev => [...prev, { question, answer: fallbackAnswer, timestamp: new Date().toISOString() }]);
      toast.error("Zumi is temporarily unavailable");
    } finally {
      setAskZumiLoading(false);
    }
  };

  const navItems = [
    { name: "Dashboard", icon: Home, href: "/", active: true, roles: ["streamer"] },
    { name: "Viewer Mode", icon: Users, href: "/viewer", roles: ["viewer"] },
    { name: "Stream Health", icon: Radio, href: "/stream-health", roles: ["streamer"] },
    { name: "Clips Library", icon: Scissors, href: "/clips", roles: ["streamer"] },
    { name: "Moderation", icon: Shield, href: "/moderation", roles: ["streamer"] },
    { name: "Command Queue", icon: MessageSquare, href: "/commands", roles: ["streamer"] },
    { name: "Analytics", icon: TrendingUp, href: "/analytics", roles: ["streamer"] },
    { name: "ML Training", icon: Brain, href: "/ml-training", roles: ["streamer"] },
    { name: "Voice Control", icon: Mic, href: "/voice", roles: ["streamer"] },
    { name: "Setup Wizard", icon: Users, href: "/setup", roles: ["streamer"] },
    { name: "Settings", icon: Settings, href: "/settings", roles: ["streamer"] },
  ].filter((item) => item.roles.includes(userRole));
  const filteredNavItems = navItems.filter((item) =>
    item.name.toLowerCase().includes(toolSearch.trim().toLowerCase()),
  );

  const kpiCards = [
    {
      label: "Current Viewers",
      value: dashboardData?.currentViewers || "0",
      delta: dashboardData?.viewerChange || "+0%",
      icon: Eye,
      color: "text-blue-600",
    },
    {
      label: "Stream Health",
      value: dashboardData?.healthStatus || "Healthy",
      delta: `${dashboardData?.healthScore || 0}% score`,
      icon: Activity,
      color: "text-green-600",
    },
    {
      label: "Auto Clips Today",
      value: dashboardData?.autoClips || "0",
      delta: `${dashboardData?.manualClips || 0} manual`,
      icon: Scissors,
      color: "text-purple-600",
    },
    {
      label: "Mod Events",
      value: dashboardData?.modEvents || "0",
      delta: `${dashboardData?.autoModerated || 0}% auto`,
      icon: Shield,
      color: "text-orange-600",
    },
    {
      label: "Stream Pulse",
      value: String(dashboardData?.streamPulse?.score ?? 0),
      delta: `${(dashboardData?.streamPulse?.trend ?? 0) >= 0 ? "+" : ""}${dashboardData?.streamPulse?.trend ?? 0} trend`,
      icon: TrendingUp,
      color: "text-indigo-600",
    },
  ];

  const recentActivity = dashboardData?.recentActivity || [];
  const compactRecentActivity = useMemo(() => {
    const seen = new Map();
    for (const item of recentActivity) {
      const key = [
        item?.action_type || item?.type || "watching",
        item?.description || "",
        item?.commentary || "",
        item?.action_label || "",
      ].join("|").toLowerCase();
      if (seen.has(key)) {
        const existing = seen.get(key);
        existing.count += 1;
        continue;
      }
      seen.set(key, { ...item, count: 1 });
    }
    return Array.from(seen.values());
  }, [recentActivity]);
  const visibleRecentActivity = (showFullFeed ? compactRecentActivity.slice(0, 20) : compactRecentActivity.slice(0, 5));
  const streamMetrics = dashboardData?.streamMetrics || {};
  const streamPulse = dashboardData?.streamPulse || { score: 0, trend: 0, label: "warming_up" };
  const preStreamChecklist = dashboardData?.preStreamChecklist || { ready: false, checks: [] };
  const activeStreamer = streamers.find((s) => Number(s.id) === Number(activeStreamerId));
  const lastHandledActivity = recentActivity.find((item) => item?.action_type === "handled");
  const eventTypes = Array.from(new Set(liveEvents.map((event) => event.event_type))).filter(Boolean);
  const filteredEvents = liveEvents.filter((event) => {
    if (eventPlatformFilter !== "all" && event.platform !== eventPlatformFilter) return false;
    if (eventTypeFilter !== "all" && event.event_type !== eventTypeFilter) return false;
    return true;
  });

  const searchMoments = async () => {
    if (!momentQuery.trim()) return;
    setMomentLoading(true);
    setMomentMessage("");
    try {
      const res = await apiFetch("/api/moment-finder/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: momentQuery.trim(),
          platforms: momentPlatforms,
          limit: 5,
        }),
      });
      const data = await res.json();
      setMomentResults(data.results || []);
      if (data.status !== "success") {
        setMomentMessage(data.message || "No results yet.");
      }
    } catch (error) {
      console.error("Moment Finder error:", error);
      setMomentMessage("Search failed. Check backend or API key.");
    } finally {
      setMomentLoading(false);
    }
  };

  useEffect(() => {
    try {
      const raw = localStorage.getItem("kazumi_saved_moments");
      if (raw) setSavedMoments(JSON.parse(raw));
    } catch {
      setSavedMoments([]);
    }
  }, []);

  const saveMoment = (item) => {
    const next = [item, ...savedMoments].slice(0, 20);
    setSavedMoments(next);
    localStorage.setItem("kazumi_saved_moments", JSON.stringify(next));
  };

  const togglePlatform = (platform) => {
    setMomentPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform],
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Kazumi...</p>
        </div>
      </div>
    );
  }

  return (
    <>
    <div className="flex flex-col md:flex-row min-h-screen text-[var(--text)]">
      {/* LEFT SIDEBAR */}
      <div className={`${sidebarCollapsed ? "w-20" : "w-full md:w-72"} transition-all duration-300 border-r border-white/10 p-6 flex flex-col bg-[rgba(23,20,42,0.88)] backdrop-blur-xl`}>
        {/* Header with Collapse Button */}
        <div className="flex items-center justify-between mb-8">
          <div className={`flex items-center gap-3 ${sidebarCollapsed ? "opacity-0 w-0" : "opacity-100"} transition-opacity`}>
            <div className="w-8 h-8 bg-black rounded-md flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" strokeWidth={1.5} />
            </div>
          </div>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1 hover:bg-white/10 rounded-lg transition-colors"
            title={sidebarCollapsed ? "Expand" : "Collapse"}
          >
            {sidebarCollapsed ? "☰" : "✕"}
          </button>
        </div>

        {/* Streamer Name / Role Display */}
        {!sidebarCollapsed && (
          <div className="mb-6 p-3 bg-black/30 rounded-xl border border-white/10">
            <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Mode</div>
            <div className="text-sm font-semibold text-white">
              {settings?.profile?.displayName || "Streamer"}
            </div>
            <div className="text-xs text-gray-500 capitalize mt-1">{userRole}</div>
          </div>
        )}



        {!sidebarCollapsed && userRole === "streamer" && (
          <div className="mb-4">
            <label className="sr-only" htmlFor="tool-search">Search tools</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                id="tool-search"
                value={toolSearch}
                onChange={(e) => setToolSearch(e.target.value)}
                placeholder="Search tools..."
                className="w-full h-10 pl-9 pr-3 rounded-lg border border-white/10 bg-white/5 text-sm text-[var(--text)] placeholder:text-gray-500 focus:border-white/30"
              />
            </div>
          </div>
        )}

        <nav className={`space-y-2 flex-1 ${sidebarCollapsed ? "flex flex-col items-center" : ""}`}>
          {filteredNavItems.map((item, index) => {
            const IconComponent = item.icon;
            return (
              <a
                key={index}
                href={item.href}
                title={sidebarCollapsed ? item.name : ""}
	                className={`flex items-center gap-3 px-3 py-2 rounded-xl w-full text-left text-sm transition-colors ${
	                  item.active
	                    ? "bg-black text-white shadow-sm"
	                    : "text-gray-700 hover:bg-white/10"
	                } ${sidebarCollapsed ? "justify-center" : ""}`}
              >
                <IconComponent className="w-[18px] h-[18px]" strokeWidth={1.5} />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </a>
	            );
	          })}
          {filteredNavItems.length === 0 && (
            <div className="px-3 py-2 text-xs text-gray-500">No tools match that search.</div>
          )}
        </nav>

        {!sidebarCollapsed && userRole === "viewer" && streamers.length > 0 && (
          <div className="mt-4 rounded-2xl border border-black/5 bg-white/80 p-3">
            <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-2">
              Watching
            </div>
            <div className="space-y-1">
              {streamers.slice(0, 3).map((s) => (
                <button
                  key={s.id}
                  onClick={() => chooseStreamer(s.id)}
                  className={`w-full text-left px-2 py-1 rounded-lg text-xs ${
                    Number(activeStreamerId) === Number(s.id)
                      ? "bg-black text-white"
                      : "bg-black/5 text-gray-700 hover:bg-black/10"
                  }`}
                >
                  {s.display_name}
                </button>
              ))}
              {streamers.length > 3 && (
                <a href="/auth" className="text-xs text-gray-500 hover:text-black">
                  Manage streamers -{'>'}
                </a>
              )}
            </div>
          </div>
        )}

        {!sidebarCollapsed && (
          <>
        {/* AI Status Card */}
        <div className="kazumi-card flex items-center gap-3 p-4 mt-8">
          <Zap className={`w-5 h-5 ${dashboardData?.aiActive ? 'text-green-400' : 'text-gray-300'}`} fill="currentColor" />
          <div className="flex-1">
            <div className="text-sm font-bold">AI Kazumi {dashboardData?.aiActive ? 'Live' : 'Idle'}</div>
            <div className="text-xs text-gray-500">
              {dashboardData?.mlConfidence || 0}% confidence
            </div>
          </div>
        </div>

        <div className="kazumi-card p-4 mt-4">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-1">Last action</div>
          <div className="text-[11px] text-gray-700">
            {lastHandledActivity?.description || lastHandledActivity?.commentary || "No handled actions yet."}
          </div>
        </div>

        <div className="kazumi-card flex items-center justify-between p-4 mt-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-black/5 rounded-full flex items-center justify-center text-xs font-semibold">
              {authUser?.email ? authUser.email.slice(0, 2).toUpperCase() : "KP"}
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold">
                {settings?.profile?.displayName || authUser?.email || dashboardData?.userName || "KazumiPro"}
              </span>
              <span className="text-[10px] uppercase tracking-widest text-gray-500">
                {authUser?.role || "guest"}
              </span>
            </div>
          </div>
          <a
            href="/auth"
            className="px-3 py-1.5 text-xs font-semibold border border-gray-300 rounded-full hover:bg-gray-50"
          >
            {authUser ? "Account" : "Sign In"}
          </a>
        </div>
          </>
        )}
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* HEADER WITH LOGO & STREAMER INFO */}
        <div className="border-b border-white/10 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 md:p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <img
                src="/logo.png"
                alt="Kazumi"
                className="w-12 h-12 md:w-14 md:h-14 rounded-lg object-contain bg-white/5 p-2"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-white">Kazumi AI</h1>
                <p className="text-sm text-gray-400">Stream Director & Command Center</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-white">{authUser?.email || "Streamer"}</p>
              <p className="text-xs text-gray-500 capitalize">{userRole || "guest"}</p>
            </div>
          </div>

          {/* OBS STATUS BAR */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/20 border border-green-500/40 text-green-300">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
              OBS Connected
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-gray-400">
              {dashboardData?.streaming ? "🔴 Streaming" : "Streaming Off"}
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-gray-400">
              {dashboardData?.recording ? "🔴 Recording" : "Recording Off"}
            </div>
            {dashboardData?.currentScene && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-gray-400">
                Scene: <span className="font-semibold text-white">{dashboardData.currentScene}</span>
              </div>
            )}
          </div>
        </div>

        {/* SCROLLABLE CONTENT */}
        <div className="flex-1 p-6 md:p-10 overflow-y-auto">
        <div className="text-sm text-gray-500 mb-4 flex items-center gap-2">
          <button
            onClick={() => window.history.back()}
            className="p-1 hover:bg-white/5 rounded-lg transition-colors"
            title="Go back"
          >
            ←
          </button>
          <span>Pages</span>
          <span className="mx-1.5 text-gray-300">/</span>
          <span>Main Dashboard</span>
        </div>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
          <div className="flex items-center gap-3">
            <h2 className="text-3xl md:text-4xl font-bold leading-tight">
              Main Dashboard
            </h2>
            {isAuthBypassEnabled() && (
              <span className="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-yellow-100 text-yellow-700">
                Demo Mode
              </span>
            )}
          </div>
          {userRole === "streamer" && (
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={isVoiceListening ? stopVoiceListening : startVoiceListening}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-2xl border shadow-sm transition-colors ${
                  isVoiceListening
                    ? 'bg-red-500/15 border-red-400/30 text-red-100 animate-pulse'
                    : 'bg-white/5 border-white/10 text-[var(--text)] hover:bg-white/10'
                }`}
                title={isVoiceListening ? 'Stop listening' : 'Start voice command'}
              >
                {isVoiceListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                <span className="text-sm font-semibold">{isVoiceListening ? "Listening" : "Voice"}</span>
              </button>
              <button
                onClick={async () => {
                  setClipNowBusy(true);
                  toast.loading("Clipping...");
                  try {
                    const res = await apiFetch("/api/clips/save-now", { method: "POST" });
                    if (res.ok) {
                      toast.success("Clip saved!");
                    } else {
                      toast.error("Failed to save clip");
                    }
                  } catch (error) {
                    console.error("Clip error:", error);
                    toast.error("Error saving clip");
                  } finally {
                    setClipNowBusy(false);
                  }
                }}
                disabled={clipNowBusy}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-2xl border shadow-sm transition-colors bg-white/5 border-white/10 text-[var(--text)] hover:bg-white/10 disabled:opacity-50"
                title="Save a clip now"
              >
                <Scissors className="w-5 h-5" />
                <span className="text-sm font-semibold">{clipNowBusy ? "Saving..." : "Clip Now"}</span>
              </button>
              <div className="px-4 py-2 rounded-2xl border border-white/10 bg-white/5 shadow-sm min-w-[170px]">
                <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Stream Pulse</div>
                <div className="flex items-end justify-between">
                  <div className={`text-3xl font-bold tabular-nums ${
                    (streamPulse?.score ?? 0) >= 70 ? "text-green-600" : (streamPulse?.score ?? 0) >= 40 ? "text-amber-500" : "text-red-500"
                  }`}>
                    {streamPulse?.score ?? 0}
                  </div>
                  <div className={`text-xs font-semibold ${
                    (streamPulse?.trend ?? 0) >= 0 ? "text-green-600" : "text-red-500"
                  }`}>
                    {(streamPulse?.trend ?? 0) >= 0 ? "\u2191" : "\u2193"} {Math.abs(streamPulse?.trend ?? 0)}
                  </div>
                </div>
              </div>
            </div>
          )}
          {userRole === "viewer" && activeStreamer && (
            <div className="px-4 py-2 rounded-full border border-gray-200 text-xs font-semibold uppercase tracking-widest text-gray-600">
              Connected to {activeStreamer.display_name}
            </div>
          )}
        </div>

        {userRole === "streamer" && !obsState?.streaming && (
          <div className="kazumi-card p-5 mb-8 border-l-4 border-black">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-sm">Pre-stream Checklist</h3>
              {preStreamChecklist?.ready && (
                <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">
                  Ready to go live
                </span>
              )}
            </div>
            <div className="space-y-2">
              {(preStreamChecklist?.checks || []).map((check) => (
                <div key={check.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                      check.passed ? "bg-green-500" : "bg-red-100 border border-red-300"
                    }`}>
                      {check.passed ? <CheckCircle className="w-3 h-3 text-white" /> : null}
                    </div>
                    <span className={`text-sm ${check.passed ? "text-gray-600" : "text-gray-900 font-medium"}`}>
                      {check.label}
                    </span>
                  </div>
                  {!check.passed && (
                    <button
                      onClick={() => handleChecklistFix(check)}
                      className="text-xs font-semibold text-black underline underline-offset-2"
                    >
                      {check.fix_label || "Fix"}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {kpiCards.map((card, index) => {
            const IconComponent = card.icon;
            return (
              <div key={index} className="kazumi-card p-6 flex items-center gap-4">
                <div className={`w-[52px] h-[52px] border border-black/10 rounded-2xl flex items-center justify-center flex-shrink-0 bg-white ${card.color}`}>
                  <IconComponent className="w-6 h-6" strokeWidth={1.5} />
                </div>
                <div className="min-w-0">
                  <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">{card.label}</div>
                  <div className="text-[28px] font-semibold leading-none mb-1">{card.value}</div>
                  <div className="text-xs text-[#16A34A]">{card.delta}</div>
                </div>
              </div>
            );
          })}
        </div>

        {postStreamReport && (
          <div className="kazumi-card p-4 mb-8 border border-green-200 bg-green-50/60">
            <div className="text-xs uppercase tracking-widest text-green-700 mb-1">Post-Stream Report</div>
            <div className="text-sm text-green-900">
              {postStreamReport.summary || "Report generated successfully."}
            </div>
          </div>
        )}

        {/* OBS Status */}
        <div className="kazumi-card p-6 mb-8">
          <ObsStatus state={obsState} />
        </div>

        {/* Ask Zumi */}
        {userRole === "streamer" && (
          <div className="kazumi-card p-6 mb-8">
            <div className="mb-4">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Ask Zumi</div>
              <h2 className="text-lg font-bold">Stream Intelligence</h2>
            </div>
            <div className="space-y-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={askZumiInput}
                  onChange={(e) => setAskZumiInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleAskZumi()}
                  placeholder="Ask Zumi... e.g., 'Why is chat so hyped?', 'What should I do next?'"
                  className="flex-1 px-4 py-2 text-sm rounded-lg border border-black/10 bg-white focus:outline-none focus:ring-2 focus:ring-black/20"
                  disabled={askZumiLoading}
                />
                <button
                  onClick={handleAskZumi}
                  disabled={askZumiLoading || !askZumiInput.trim()}
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-black text-white hover:bg-black/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {askZumiLoading ? "..." : "Ask"}
                </button>
              </div>
              {askZumiResponse && (
                <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                  <div className="text-xs uppercase tracking-widest text-blue-700 font-semibold mb-2">Zumi's Response</div>
                  <div className="text-sm text-blue-900 leading-relaxed">{askZumiResponse}</div>
                </div>
              )}
              {askZumiHistory.length > 0 && (
                <div className="mt-4 pt-4 border-t border-black/10">
                  <div className="text-xs uppercase tracking-widest text-gray-400 mb-3">Recent Questions</div>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {askZumiHistory.slice(-5).reverse().map((item, idx) => (
                      <div key={idx} className="text-xs">
                        <div className="font-semibold text-gray-700">Q: {item.question}</div>
                        <div className="text-gray-500 italic">A: {item.answer.substring(0, 100)}...</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {userRole === "streamer" && (
          <div className="kazumi-card p-6 mb-8">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">OBS Control</div>
                <h2 className="text-lg font-bold">Sources & Cameras</h2>
              </div>
              <button
                onClick={() => fetchObsSourcesAndCameras()}
                className="px-3 py-1.5 text-xs rounded-md border border-black/10 hover:bg-black/5"
              >
                Refresh
              </button>
            </div>

            {sourcePanelLoading ? (
              <div className="text-xs text-gray-500">Loading sources...</div>
            ) : obsSources.length === 0 ? (
              <div className="text-xs text-gray-500">No sources found for the active scene.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {obsSources.map((source) => {
                  const busyVisibility = Boolean(sourceActionBusy[`visibility:${source.source_name}`]);
                  const busyDevice = Boolean(sourceActionBusy[`device:${source.source_name}`]);
                  return (
                    <div
                      key={`${source.scene_item_id}-${source.source_name}`}
                      className="rounded-xl border border-black/10 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            {source.is_camera ? <Camera className="w-4 h-4" /> : <Video className="w-4 h-4" />}
                            <div className="text-sm font-semibold truncate">{source.source_name}</div>
                          </div>
                          <div className="text-[11px] text-gray-500 mt-1">{source.source_type || "source"}</div>
                        </div>
                        <label className="inline-flex items-center gap-2 text-xs">
                          <span className="text-gray-500">{source.visible ? "Visible" : "Hidden"}</span>
                          <input
                            type="checkbox"
                            checked={Boolean(source.visible)}
                            disabled={busyVisibility}
                            onChange={(event) => setSourceVisibility(source.source_name, event.target.checked)}
                            className="accent-black"
                          />
                        </label>
                      </div>
                      {source.is_camera && (
                        <div className="mt-3">
                          <select
                            value={source.device_id || ""}
                            disabled={busyDevice || obsCameras.length === 0}
                            onChange={(event) => switchSourceDevice(source.source_name, event.target.value)}
                            className="w-full border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
                          >
                            <option value="">Select camera device</option>
                            {obsCameras.map((camera) => (
                              <option key={camera.device_id} value={camera.device_id}>
                                {camera.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Stream Metrics Chart */}
        <div className="kazumi-card p-6 mb-8">
          <div className="flex items-center gap-6 mb-6">
            <div className="w-[52px] h-[52px] border border-black/10 rounded-2xl flex items-center justify-center flex-shrink-0 bg-white">
              <BarChart2 className="w-6 h-6" strokeWidth={1.5} />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">Current Scene</div>
              <div className="text-[28px] font-semibold leading-none">
                {obsState?.scene || "Unknown"}
              </div>
            </div>
          </div>

          <div className="h-56 w-full mb-4">
            <svg className="w-full h-full" viewBox="0 0 800 200">
              <path
                d="M 50 120 L 150 100 L 250 80 L 350 90 L 450 70 L 550 85 L 650 60 L 750 75"
                stroke="#000000"
                strokeWidth="2"
                fill="none"
              />
              <circle cx="750" cy="75" r="4" fill="#000000" />
            </svg>
          </div>
        </div>
        
        {/* --- NEW: AI APPROVAL SECTION --- */}
        <div className="mb-8">
          <AIApprovalDashboard />
        </div>

        {/* --- NEW: CLIP MANAGEMENT SECTION --- */}
        <div className="mb-8">
          <ClipManagement />
        </div>

        {/* Moment Finder */}
        <div className="kazumi-card p-6 mb-8">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Moment Finder</div>
              <h2 className="text-lg font-bold">Search Clips Across Platforms</h2>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mb-3">
            {["twitch", "youtube", "tiktok", "kick"].map((platform) => (
              <button
                key={platform}
                onClick={() => togglePlatform(platform)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
                  momentPlatforms.includes(platform)
                    ? "bg-black text-white border-black"
                    : "bg-white text-gray-600 border-gray-200"
                }`}
              >
                {platform}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2 mb-4">
            {[
              "best clip yesterday",
              "most viral moment this week",
              "funniest reaction clip",
              "top highlight last stream",
            ].map((preset) => (
              <button
                key={preset}
                onClick={() => setMomentQuery(preset)}
                className="px-3 py-1.5 rounded-full text-xs font-semibold border border-gray-200 bg-gray-50 text-gray-600 hover:text-black"
              >
                {preset}
              </button>
            ))}
          </div>
          <div className="flex flex-col md:flex-row gap-3 mb-4">
            <input
              value={momentQuery}
              onChange={(e) => setMomentQuery(e.target.value)}
              placeholder="e.g., MrBeast money clip yesterday"
              className="flex-1 px-4 py-2 border border-black/10 rounded-md text-sm bg-white"
            />
            <button
              onClick={searchMoments}
              className="px-4 py-2 bg-black text-white rounded-md text-sm"
              disabled={momentLoading}
            >
              {momentLoading ? "Searching..." : "Search"}
            </button>
          </div>
          {momentMessage && (
            <div className="text-xs text-gray-500 mb-3">{momentMessage}</div>
          )}
          <div className="space-y-3">
            {momentResults.map((item, index) => (
              <div
                key={`${item.url}-${index}`}
                className="border border-black/5 rounded-xl p-4 hover:border-black/20 transition-colors bg-white"
              >
                <a href={item.url} target="_blank" rel="noreferrer" className="block">
                  <div className="text-sm font-semibold text-gray-900">{item.title || "Untitled Result"}</div>
                  <div className="text-xs text-gray-500 break-all">{item.url}</div>
                  {item.snippet && (
                    <div className="text-xs text-gray-600 mt-2">{item.snippet}</div>
                  )}
                </a>
                <div className="mt-3">
                  <button
                    onClick={() => saveMoment(item)}
                    className="text-xs font-semibold text-gray-700 hover:text-black"
                  >
                    Save to Collection
                  </button>
                </div>
              </div>
            ))}
            {momentResults.length === 0 && !momentMessage && (
              <div className="text-xs text-gray-500">No results yet.</div>
            )}
          </div>
          {savedMoments.length > 0 && (
            <div className="mt-6">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">
                Saved Collection
              </div>
              <div className="space-y-2">
                {savedMoments.map((item, index) => (
                  <a
                    key={`${item.url}-saved-${index}`}
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block border border-gray-100 rounded-md p-3 hover:border-gray-300 transition-colors"
                  >
                    <div className="text-xs font-semibold text-gray-800">{item.title || "Untitled Result"}</div>
                    <div className="text-[10px] text-gray-500 break-all">{item.url}</div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Super-Chat Sorter */}
        <div className="kazumi-card p-6 mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Super-Chat Sorter</div>
              <h2 className="text-lg font-bold">Grouped chat + To-Answer queue</h2>
            </div>
            {superChatData?.stats && (
              <div className="text-xs text-gray-500">
                {superChatData.stats.messages_scanned} scanned · {superChatData.stats.groups_detected} groups · {superChatData.stats.questions_detected} questions
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <label className="flex items-center justify-between rounded-lg border border-black/10 px-3 py-2">
              <span className="text-sm">Enable Super-Chat Sorter</span>
              <input
                type="checkbox"
                checked={Boolean(settings?.superChatSorter?.enabled)}
                onChange={(e) => updateSetting("superChatSorter", "enabled", e.target.checked)}
                className="accent-black"
              />
            </label>
            <label className="flex items-center justify-between rounded-lg border border-black/10 px-3 py-2">
              <span className="text-sm">Extract Questions</span>
              <input
                type="checkbox"
                checked={Boolean(settings?.superChatSorter?.extractQuestions)}
                onChange={(e) => updateSetting("superChatSorter", "extractQuestions", e.target.checked)}
                className="accent-black"
              />
            </label>
          </div>

          <div className="mb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-lg border border-black/10 px-3 py-2">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Question Source</div>
              <select
                value={settings?.superChatSorter?.questionSourceMode || "all"}
                onChange={(e) => updateSetting("superChatSorter", "questionSourceMode", e.target.value)}
                className="w-full border border-black/10 rounded-md px-2 py-1 text-sm bg-white"
              >
                <option value="all">All chat users</option>
                <option value="subs_mods">Subscribers + Mods only</option>
              </select>
            </div>
            <div className="rounded-lg border border-black/10 px-3 py-2">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Question Mute</div>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => setQuestionMuteMinutes(5)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">5m</button>
                <button onClick={() => setQuestionMuteMinutes(15)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">15m</button>
                <button onClick={() => setQuestionMuteMinutes(30)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">30m</button>
                <button onClick={() => setQuestionMuteMinutes(0)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">Unmute</button>
              </div>
              <div className="text-[11px] text-gray-500 mt-2">
                {isQuestionMuted ? `Questions muted for ${mutedMinutesLeft}m` : "Questions active"}
              </div>
            </div>
          </div>

          <div className="mb-4">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Blocked Question Keywords</div>
            <div className="flex flex-col md:flex-row gap-2">
              <input
                value={blockedKeywordInput}
                onChange={(e) => setBlockedKeywordInput(e.target.value)}
                placeholder="Add keyword (example: drama)"
                className="flex-1 px-3 py-2 border border-black/10 rounded-md text-sm bg-white"
              />
              <button
                onClick={() => {
                  const value = blockedKeywordInput.trim().toLowerCase();
                  if (!value) return;
                  const prev = settings?.superChatSorter?.blockedQuestionKeywords || [];
                  if (prev.includes(value)) return;
                  updateSetting("superChatSorter", "blockedQuestionKeywords", [...prev, value]);
                  setBlockedKeywordInput("");
                }}
                className="px-3 py-2 text-sm rounded-md border border-black/10 bg-white hover:bg-black/5"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {(settings?.superChatSorter?.blockedQuestionKeywords || []).map((keyword) => (
                <button
                  key={keyword}
                  onClick={() => {
                    const next = (settings?.superChatSorter?.blockedQuestionKeywords || []).filter((k) => k !== keyword);
                    updateSetting("superChatSorter", "blockedQuestionKeywords", next);
                  }}
                  className="px-2 py-1 rounded-full text-xs bg-black/5 hover:bg-black/10"
                >
                  {keyword} ×
                </button>
              ))}
            </div>
          </div>

          <div className="mb-4">
            <button
              onClick={saveSuperChatSettings}
              className="px-4 py-2 rounded-md bg-black text-white text-sm font-semibold"
            >
              Save Sorter Preferences
            </button>
          </div>

          {superChatLoading && (
            <div className="text-xs text-gray-500 mb-3">Refreshing sorter...</div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="rounded-xl border border-black/10 p-4">
              <div className="text-sm font-semibold mb-3">Grouped Notifications</div>
              {superChatData.grouped_notifications.length === 0 ? (
                <div className="text-xs text-gray-500">No repeated chat bursts detected yet.</div>
              ) : (
                <div className="space-y-2">
                  {superChatData.grouped_notifications.slice(0, 8).map((group, idx) => (
                    <div key={`${group.message}-${idx}`} className="border border-black/5 rounded-md p-3">
                      <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">
                        {group.count} people said
                      </div>
                      <div className="text-sm font-semibold">{group.message}</div>
                      {group.sample_users?.length > 0 && (
                        <div className="text-[11px] text-gray-500 mt-1">
                          Sample: {group.sample_users.join(", ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-black/10 p-4">
              <div className="text-sm font-semibold mb-3">To-Answer Questions</div>
              {superChatData.to_answer.length === 0 ? (
                <div className="text-xs text-gray-500">No questions extracted yet.</div>
              ) : (
                <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                  {superChatData.to_answer.slice(0, 12).map((q) => (
                    <div key={q.id} className="border border-black/5 rounded-md p-3">
                      <div className="text-[11px] uppercase tracking-widest text-gray-400 mb-1">
                        {q.platform} · {q.username}{q.is_sub_or_mod ? " · sub/mod" : ""}
                      </div>
                      <div className="text-sm">{q.message}</div>
                      <div className="mt-2">
                        <button
                          onClick={() => markQuestionAnswered(q.question_key)}
                          className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5"
                        >
                          Mark answered
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Live Event Feed */}
          <div className="kazumi-card p-6 mb-8">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <Activity className="w-5 h-5" />
                <h2 className="text-lg font-bold">Live Event Feed</h2>
              </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
              <select
                value={eventPlatformFilter}
                onChange={(e) => setEventPlatformFilter(e.target.value)}
                className="border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
              >
                <option value="all">All platforms</option>
                <option value="twitch">Twitch</option>
                <option value="youtube">YouTube</option>
              </select>
              <select
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                className="border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
              >
                <option value="all">All types</option>
                {eventTypes.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
              <button
                onClick={() => setEventPaused((prev) => !prev)}
                className="border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
              >
                {eventPaused ? "Resume" : "Pause"}
              </button>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span
                  className={`w-2 h-2 rounded-full ${
                    eventStreamStatus === "live"
                      ? "bg-green-500"
                      : eventStreamStatus === "connecting"
                        ? "bg-yellow-500"
                        : "bg-red-500"
                  }`}
                />
                <span className="uppercase tracking-widest">{eventStreamStatus}</span>
              </div>
            </div>
          </div>
          {filteredEvents.length === 0 ? (
            <div className="text-sm text-gray-500">No live events yet.</div>
          ) : (
            <div className="space-y-3">
              {filteredEvents.slice(0, 6).map((event) => (
                <div
                  key={event.id}
                  className="flex items-start justify-between gap-4 border-b border-black/5 pb-3"
                >
                  <div>
                    <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">
                      {event.platform} · {event.event_type}
                    </div>
                    <div className="text-sm font-medium">
                      {event.username || "Anonymous"}
                    </div>
                    {event.message && (
                      <div className="text-xs text-gray-600 mt-1">
                        {event.message}
                      </div>
                    )}
                  </div>
                  <div className="text-[10px] text-gray-400 whitespace-nowrap">
                    {event.received_at
                      ? new Date(event.received_at).toLocaleTimeString()
                      : ""}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="kazumi-card p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5" />
              <h2 className="text-lg font-bold">Kazumi Feed</h2>
            </div>
            {compactRecentActivity.length > 5 && (
              <button
                onClick={() => setShowFullFeed((value) => !value)}
                className="text-xs font-semibold px-3 py-1.5 rounded-md border border-white/10 bg-white/5 hover:bg-white/10"
              >
                {showFullFeed ? "Show less" : `Show ${Math.min(compactRecentActivity.length, 20)}`}
              </button>
            )}
          </div>
          <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
            {compactRecentActivity.length === 0 ? (
              <div className="text-sm text-gray-500">No recent activity yet.</div>
            ) : (
              visibleRecentActivity.map((activity, index) => {
                const actionType = activity?.action_type || "watching";
                const style =
                  actionType === "handled"
                    ? { dot: "#00E5A0", badge: "bg-[rgba(0,229,160,0.1)] text-[#00A36F]", label: "Handled", card: "bg-[rgba(0,229,160,0.06)]" }
                    : actionType === "needs_you"
                      ? { dot: "#F5A623", badge: "bg-[rgba(245,166,35,0.12)] text-[#C97B0A]", label: "Needs you", card: "bg-[rgba(245,166,35,0.08)]" }
                      : { dot: "#4C9FFF", badge: "bg-[rgba(76,159,255,0.12)] text-[#2B79D5]", label: "Watching", card: "bg-[rgba(76,159,255,0.07)]" };

                return (
                  <div key={index} className={`${style.card} rounded-xl px-3 py-2.5 flex items-start gap-3 border border-white/10`}>
                    <div
                      className={`w-2.5 h-2.5 rounded-full mt-1.5 ${actionType === "needs_you" ? "animate-pulse" : ""}`}
                      style={{ backgroundColor: style.dot }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full ${style.badge}`}>
                          {style.label}
                        </span>
	                        <span className="text-[10px] text-gray-400">{activity.time}</span>
	                        {activity.count > 1 && (
	                          <span className="text-[10px] text-gray-500">x{activity.count}</span>
	                        )}
	                      </div>
	                      <p className="text-sm text-gray-800">{activity.description}</p>
	                      {activity.commentary && (
	                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">{activity.commentary}</p>
	                      )}
                      {actionType === "needs_you" && (
                        <button
                          onClick={() => handleFeedAction(activity)}
                          className="mt-2 text-xs font-semibold text-[#7C5CFC] underline underline-offset-2"
                        >
                          {activity.action_label || "Review"} {"->"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Mic Status Overlay */}
        {micStatusMessage && (
          <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg border-2 ${
            micMuted
              ? 'bg-red-100 border-red-300 text-red-800'
              : 'bg-green-100 border-green-300 text-green-800'
          }`}>
            <div className="flex items-center gap-2">
              <Mic className="w-4 h-4" />
              <span className="font-medium">{micStatusMessage}</span>
            </div>
          </div>
        )}

        {/* Panic Mode Overlay */}
        {isPanicMode && (
          <div className="fixed inset-0 z-50 bg-red-600 bg-opacity-90 flex items-center justify-center">
            <div className="text-center text-white">
              <Shield className="w-24 h-24 mx-auto mb-4 animate-pulse" />
              <h1 className="text-4xl font-bold mb-2">SHIELD ACTIVE</h1>
              <p className="text-lg mb-4">Panic mode engaged. Stream protected.</p>
              <button
                onClick={deactivatePanicMode}
                className="px-6 py-3 bg-white text-red-600 font-bold rounded-lg hover:bg-gray-100 transition-colors"
              >
                Deactivate Shield
              </button>
            </div>
          </div>
        )}

        {userRole === "streamer" && obsState?.streaming && (
          <button
            onClick={() => void triggerClipNow()}
            disabled={clipNowBusy}
            className={`fixed bottom-6 right-6 z-40 w-14 h-14 bg-black text-white rounded-full shadow-xl flex items-center justify-center hover:scale-110 active:scale-95 transition-transform ${
              clipPulse ? "ring-4 ring-indigo-300 ring-offset-2 animate-pulse" : ""
            } ${clipNowBusy ? "opacity-60 cursor-not-allowed" : ""}`}
            title="Clip now (Ctrl/Cmd+Shift+C)"
          >
            <Scissors className="w-5 h-5" />
          </button>
        )}

        {/* Kazumi Chat Drawer */}
      </div>
      </div>

    </div>

    {/* Lightweight Onboarding */}
    {userRole === "viewer" && showOnboarding && (
      <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">
            Welcome Viewer
          </div>
          <h2 className="text-xl font-bold mb-2">Who are you watching?</h2>
          <p className="text-sm text-gray-600 mb-4">
            Pick a streamer to sync clips, lore, and voting.
          </p>
          <div className="space-y-2">
            {streamers.map((s) => (
              <button
                key={s.id}
                onClick={() => chooseStreamer(s.id)}
                className="w-full text-left px-3 py-2 rounded-md bg-gray-100 hover:bg-gray-200 text-sm"
              >
                {s.display_name}{" "}
                <span className="text-xs text-gray-500">({s.platform})</span>
              </button>
            ))}
            {streamers.length === 0 && (
              <div className="text-xs text-gray-500">
                No streamers found yet.
              </div>
            )}
          </div>
          <button
            onClick={() => setShowOnboarding(false)}
            className="mt-4 w-full px-4 py-2 border border-gray-200 rounded-md text-sm hover:bg-gray-50"
          >
            Skip for now
          </button>
        </div>
      </div>
    )}
    </>
  );
}