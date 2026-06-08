"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/apiClient";
import { useSettings } from "@/lib/SettingsContext";
import {
  Mic,
  CheckCircle,
  XCircle,
  Loader2,
  Zap,
  RefreshCw,
  Shield,
} from "lucide-react";
import ObsStatus from "@/components/ObsStatus";
import { useObsTruth } from "@/hooks/useObsTruth";

const MAX_LOGS = 50;

const normalizeText = (value) =>
  String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const extractWakeWordCommand = (transcript, triggerWord) => {
  const normalizedTranscript = normalizeText(transcript);
  const wake = normalizeText(triggerWord || "kazumi");

  if (!normalizedTranscript) return { matched: false, command: "" };
  if (!wake) return { matched: true, command: normalizedTranscript };

  if (normalizedTranscript.startsWith(wake)) {
    const command = normalizedTranscript.slice(wake.length).trim();
    return { matched: true, command };
  }

  const wakeWithSpace = `${wake} `;
  const idx = normalizedTranscript.indexOf(wakeWithSpace);
  if (idx >= 0) {
    const command = normalizedTranscript.slice(idx + wakeWithSpace.length).trim();
    return { matched: true, command };
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

export default function VoiceControlPage() {
  const [isListening, setIsListening] = useState(false);
  const [commandText, setCommandText] = useState("");
  const [commandHistory, setCommandHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState("");
  const [aiReasoning, setAiReasoning] = useState("");
  const [permissionsError, setPermissionsError] = useState("");
  const [pushToTalk, setPushToTalk] = useState(false);
  const [backendVoiceStatus, setBackendVoiceStatus] = useState(null);
  const [backendVoiceLogs, setBackendVoiceLogs] = useState([]);
  const [backendVoiceBusy, setBackendVoiceBusy] = useState(false);
  const [backendVoiceError, setBackendVoiceError] = useState("");
  const [irlStatus, setIrlStatus] = useState(null);
  const [irlBusy, setIrlBusy] = useState(false);
  const [irlSafeScene, setIrlSafeScene] = useState("BRB");
  const [irlDangerPhrases, setIrlDangerPhrases] = useState(
    "my address is\nmy phone number\ndon't show this\nwait don't",
  );
  const recognitionRef = useRef(null);
  const shouldRestartRef = useRef(false);

  const { state: obsState } = useObsTruth();
  const { settings } = useSettings();
  const useGroq = settings?.ai?.useGroq ?? true;
  const voiceEnabled = settings?.voice?.enabled ?? true; // "Continuous Listening" in settings
  const triggerWord = settings?.voice?.triggerWord || "Kazumi";

  const refreshBackendVoice = useCallback(async () => {
    const [statusRes, logsRes, irlRes] = await Promise.all([
      apiFetch("/api/voice-agent/status"),
      apiFetch("/api/voice-agent/logs?limit=15"),
      apiFetch("/api/voice-agent/irl/status"),
    ]);

    const statusJson = await statusRes.json().catch(() => ({}));
    const logsJson = await logsRes.json().catch(() => ({}));
    const irlJson = await irlRes.json().catch(() => ({}));

    if (!statusRes.ok) {
      throw new Error(statusJson?.detail || statusJson?.message || "Could not load backend voice agent status.");
    }

    setBackendVoiceStatus(statusJson);
    setBackendVoiceError("");
    if (Array.isArray(logsJson?.logs)) {
      setBackendVoiceLogs(logsJson.logs);
    }
    if (irlRes.ok) {
      setIrlStatus(irlJson?.irl || null);
    }
  }, []);

  useEffect(() => {
    // Auto-start continuous listening when page loads
    if (voiceEnabled && !pushToTalk) {
      setTimeout(() => {
        shouldRestartRef.current = true;
        startListening({ continuous: true });
      }, 500);
    }

    return () => {
      shouldRestartRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onend = null;
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
    };
  }, [voiceEnabled]);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        await refreshBackendVoice();
        if (!active) return;
      } catch {
        if (!active) return;
        setBackendVoiceError("Could not load backend voice agent status.");
      }
    };

    load();
    const timer = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [refreshBackendVoice]);

  const executeCommand = async (text, options = {}) => {
    const cleaned = cleanKazumiCommand(text, triggerWord);
    if (!cleaned) return;

    const delayed = options.allowSchedule === false
      ? { command: cleaned, delayMs: 0, delayLabel: "" }
      : parseDelayedCommand(cleaned);

    if (delayed.delayMs > 0) {
      const scheduledCommand = {
        id: Date.now(),
        text: cleaned,
        timestamp: new Date().toLocaleTimeString(),
        status: "scheduled",
      };
      setCommandHistory((prev) => [
        scheduledCommand,
        ...prev.slice(0, MAX_LOGS - 1),
      ]);
      setAiResponse(`Scheduled "${delayed.command}" in ${delayed.delayLabel}.`);
      window.setTimeout(() => {
        void executeCommand(delayed.command, { allowSchedule: false });
      }, delayed.delayMs);
      setCommandText("");
      return;
    }

    setLoading(true);
    setAiReasoning("");

    const newCommand = {
      id: Date.now(),
      text: delayed.command,
      timestamp: new Date().toLocaleTimeString(),
      status: "processing",
    };

    setCommandHistory((prev) => [
      newCommand,
      ...prev.slice(0, MAX_LOGS - 1),
    ]);

    try {
      const response = await apiFetch("/api/commands/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            command: delayed.command,
            role: "streamer",
            use_ai: useGroq,
            confirmed: true,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result?.detail || result?.message || `Error (${response.status})`);
      }

      setAiResponse(result?.message || result?.director_commentary || "Command executed");
      setAiReasoning(result?.reasoning || result?.director_commentary || "");

      setCommandHistory((prev) =>
        prev.map((cmd) =>
          cmd.id === newCommand.id ? { ...cmd, status: "completed" } : cmd
        )
      );
    } catch (error) {
      console.error("Error executing command:", error);
      setAiResponse(error?.message || "System Error: Could not reach Kazumi.");
      setCommandHistory((prev) =>
        prev.map((cmd) =>
          cmd.id === newCommand.id ? { ...cmd, status: "failed" } : cmd
        )
      );
    } finally {
      setLoading(false);
      setCommandText("");
    }
  };

  const buildRecognition = ({ continuous }) => {
    const SpeechRecognition =
      typeof window !== "undefined"
        ? window.SpeechRecognition || window.webkitSpeechRecognition
        : null;

    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    recognition.continuous = Boolean(continuous);
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setPermissionsError("");
      setIsListening(true);
      if (pushToTalk) {
        setAiResponse("Listening... speak your command.");
      } else {
        setAiResponse(`Wake word active. Say "${triggerWord}" then your command.`);
      }
    };

    recognition.onresult = (event) => {
      const chunks = [];
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const res = event.results[i];
        if (res.isFinal) {
          chunks.push(String(res[0]?.transcript || "").trim());
        }
      }

      chunks.forEach((spoken) => {
        if (!spoken) return;

        if (pushToTalk) {
          executeCommand(spoken);
          return;
        }

        const parsed = extractWakeWordCommand(spoken, triggerWord);
        if (!parsed.matched) return;

        if (!parsed.command) {
          setAiResponse(`Wake word heard. Now say "${triggerWord} <command>".`);
          return;
        }

        setAiResponse(`Wake word detected. Executing: ${parsed.command}`);
        executeCommand(parsed.command);
      });
    };

    recognition.onerror = (event) => {
      const code = String(event?.error || "unknown_error");
      if (code === "not-allowed" || code === "service-not-allowed") {
        setPermissionsError("Microphone permission denied. Allow mic access for this site.");
      } else if (code !== "no-speech" && code !== "aborted") {
        setPermissionsError(`Voice error: ${code}`);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      if (shouldRestartRef.current && continuous) {
        setTimeout(() => {
          try {
            recognition.start();
          } catch {
            // ignore restart race
          }
        }, 250);
      }
    };

    return recognition;
  };

  const startListening = ({ continuous }) => {
    if (!voiceEnabled) {
      setAiResponse("Voice input is disabled in Settings.");
      return;
    }

    const recognition = buildRecognition({ continuous });
    if (!recognition) {
      setPermissionsError("Speech recognition is not supported in this browser.");
      return;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      setPermissionsError("Could not start microphone listener. Try again.");
    }
  };

  const stopListening = () => {
    shouldRestartRef.current = false;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
      return;
    }

    shouldRestartRef.current = !pushToTalk;
    startListening({ continuous: !pushToTalk });
  };

  const startBackendVoiceAgent = async () => {
    setBackendVoiceBusy(true);
    setBackendVoiceError("");
    try {
      const res = await apiFetch("/api/voice-agent/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trigger_word: triggerWord,
          require_wake_word: true,
          use_ai: useGroq,
        }),
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json?.detail || "Failed to start backend voice agent");
      }
      setAiResponse("Background voice agent started.");
      await refreshBackendVoice();
    } catch (error) {
      setBackendVoiceError(String(error?.message || error));
    } finally {
      setBackendVoiceBusy(false);
    }
  };

  const stopBackendVoiceAgent = async () => {
    setBackendVoiceBusy(true);
    setBackendVoiceError("");
    try {
      const res = await apiFetch("/api/voice-agent/stop", {
        method: "POST",
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json?.detail || "Failed to stop backend voice agent");
      }
      setAiResponse("Background voice agent stopped.");
      await refreshBackendVoice();
    } catch (error) {
      setBackendVoiceError(String(error?.message || error));
    } finally {
      setBackendVoiceBusy(false);
    }
  };

  const startIrlMode = async () => {
    setIrlBusy(true);
    setBackendVoiceError("");
    try {
      const phrases = irlDangerPhrases
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
      const res = await apiFetch("/api/voice-agent/irl/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          safe_scene: irlSafeScene || "BRB",
          danger_phrases: phrases,
        }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(json?.detail || "Failed to start IRL Safe Mode");
      }
      setAiResponse("IRL Safe Mode started.");
      await refreshBackendVoice();
    } catch (error) {
      setBackendVoiceError(String(error?.message || error));
    } finally {
      setIrlBusy(false);
    }
  };

  const stopIrlMode = async () => {
    setIrlBusy(true);
    setBackendVoiceError("");
    try {
      const res = await apiFetch("/api/voice-agent/irl/stop", {
        method: "POST",
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(json?.detail || "Failed to stop IRL Safe Mode");
      }
      setAiResponse("IRL Safe Mode stopped.");
      await refreshBackendVoice();
    } catch (error) {
      setBackendVoiceError(String(error?.message || error));
    } finally {
      setIrlBusy(false);
    }
  };

  const quickCommands = [
    "Switch to gameplay and unmute the game audio",
    "Go to BRB scene and tell chat I'll be back in 5",
    "Clip that last moment, it was insane!",
    "Check my stream health and bit rate",
  ];

  return (
    <div className="min-h-screen p-6 md:p-10">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <a href="/" className="hover:text-black">Dashboard</a>
          <span>/</span>
          <span>Voice Control</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-bold mb-2">Voice Control</h1>
        <p className="text-gray-600">Control your stream with voice commands</p>
      </div>

      <div className="mb-8">
        <ObsStatus state={obsState} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div className="kazumi-card p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">Background Voice Agent</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Always-on backend listener for wake-word commands.
                </p>
              </div>
              <div className="text-xs px-2 py-1 rounded-full bg-black/5">
                {backendVoiceStatus?.running ? "Running" : "Stopped"}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 rounded-md bg-black/5">
                <div className="text-gray-500">Available</div>
                <div className="font-medium">{backendVoiceStatus?.available ? "Yes" : "No"}</div>
              </div>
              <div className="p-3 rounded-md bg-black/5">
                <div className="text-gray-500">Listening</div>
                <div className="font-medium">{backendVoiceStatus?.listening ? "Yes" : "No"}</div>
              </div>
            </div>

            {backendVoiceStatus?.availability_detail ? (
              <p className="text-xs text-gray-500 mt-3">{backendVoiceStatus.availability_detail}</p>
            ) : null}
            {backendVoiceStatus?.last_error ? (
              <p className="text-xs text-red-600 mt-2">{backendVoiceStatus.last_error}</p>
            ) : null}
            {backendVoiceError ? (
              <p className="text-xs text-red-600 mt-2">{backendVoiceError}</p>
            ) : null}

            <div className="mt-4 flex gap-2">
              <button
                onClick={startBackendVoiceAgent}
                disabled={backendVoiceBusy || backendVoiceStatus?.running}
                className="px-4 py-2 bg-black text-white rounded-md text-sm disabled:opacity-50"
              >
                Start
              </button>
              <button
                onClick={stopBackendVoiceAgent}
                disabled={backendVoiceBusy || !backendVoiceStatus?.running}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm disabled:opacity-50"
              >
                Stop
              </button>
              <button
                onClick={() => void refreshBackendVoice()}
                disabled={backendVoiceBusy}
                className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-md text-sm disabled:opacity-50"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>

            <div className="mt-4">
              <h3 className="text-sm font-medium mb-2">Recent Backend Voice Logs</h3>
              <div className="max-h-40 overflow-y-auto space-y-2">
                {backendVoiceLogs.length ? (
                  backendVoiceLogs.slice(0, 8).map((item, idx) => (
                    <div key={`${item.time || "t"}-${idx}`} className="text-xs p-2 rounded bg-black/5">
                      <div className="font-medium">{item.event || "event"}</div>
                      <div className="text-gray-600">{item.message || ""}</div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500">No backend voice logs yet.</p>
                )}
              </div>
            </div>
          </div>

          <div className="kazumi-card p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-red-400" />
                  <h2 className="text-lg font-semibold">IRL Safe Mode</h2>
                </div>
                <p className="text-sm text-gray-600 mt-1">
                  Listen for danger phrases and switch to a safe scene automatically.
                </p>
              </div>
              <div className="text-xs px-2 py-1 rounded-full bg-black/5">
                {irlStatus?.active ? "Active" : "Off"}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="text-sm">
                <span className="block text-xs text-gray-500 mb-1">Safe scene</span>
                <input
                  value={irlSafeScene}
                  onChange={(e) => setIrlSafeScene(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white/5"
                  placeholder="BRB"
                />
              </label>
              <div className="text-sm">
                <span className="block text-xs text-gray-500 mb-1">Current state</span>
                <div className="px-3 py-2 rounded-md bg-black/5">
                  {irlStatus?.active ? `Watching, safe scene ${irlStatus?.safe_scene || irlSafeScene}` : "Not watching"}
                </div>
              </div>
            </div>

            <label className="block mt-3 text-sm">
              <span className="block text-xs text-gray-500 mb-1">Danger phrases, one per line</span>
              <textarea
                value={irlDangerPhrases}
                onChange={(e) => setIrlDangerPhrases(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white/5"
              />
            </label>

            <div className="mt-4 flex gap-2">
              <button
                onClick={startIrlMode}
                disabled={irlBusy}
                className="px-4 py-2 bg-black text-white rounded-md text-sm disabled:opacity-50"
              >
                Start Safe Mode
              </button>
              <button
                onClick={stopIrlMode}
                disabled={irlBusy}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm disabled:opacity-50"
              >
                Stop
              </button>
            </div>
          </div>

          {/* Voice Input Section */}
          <div className="kazumi-card p-8">
            <div className="text-center">
              <div className="flex items-center justify-center gap-3 mb-4 text-xs">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={pushToTalk}
                    onChange={(e) => setPushToTalk(e.target.checked)}
                  />
                  Push-to-talk
                </label>
                {permissionsError && (
                  <span className="text-red-600">{permissionsError}</span>
                )}
              </div>
              <button
                onMouseDown={() => {
                  if (!pushToTalk) return;
                  shouldRestartRef.current = false;
                  startListening({ continuous: false });
                }}
                onMouseUp={() => {
                  if (pushToTalk) stopListening();
                }}
                onMouseLeave={() => {
                  if (pushToTalk && isListening) stopListening();
                }}
                onClick={() => {
                  if (!pushToTalk) {
                    shouldRestartRef.current = true;
                    toggleListening();
                  }
                }}
                disabled={!voiceEnabled}
                className={`w-32 h-32 rounded-full flex items-center justify-center mb-6 transition-all border-4 ${
                  !voiceEnabled
                    ? "bg-gray-300 border-gray-300"
                    : isListening
                      ? "bg-red-500 border-red-600 scale-105"
                      : "bg-black border-black hover:scale-105"
                }`}
              >
                {isListening ? (
                  <div className="flex items-center gap-1">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="w-2 bg-white rounded-full animate-bounce"
                             style={{height: '20px', animationDelay: `${i * 0.2}s`}}></div>
                    ))}
                  </div>
                ) : (
                  <Mic className="w-12 h-12 text-white" />
                )}
              </button>

              <h2 className="text-xl font-semibold mb-2">
                {isListening ? "Listening..." : "Tap to Speak"}
              </h2>
              <p className="text-gray-600 text-sm">
                {!voiceEnabled
                  ? "Enable voice input in Settings to use this."
                  : isListening
                    ? pushToTalk
                      ? "Speak your command clearly"
                      : `Waiting for wake word: "${triggerWord}"`
                    : pushToTalk
                      ? "Hold to speak"
                      : "Click to start continuous wake-word listening"}
              </p>
            </div>
          </div>

          {/* Typed Command */}
          <div className="kazumi-card p-6">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-5 h-5 text-yellow-500" />
              <h2 className="text-lg font-semibold">Type a Command</h2>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={commandText}
                onChange={(e) => setCommandText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") executeCommand(commandText);
                }}
                placeholder='e.g. hi Kazumi switch to BRB in 10 minutes'
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
              <button
                onClick={() => executeCommand(commandText)}
                disabled={!commandText.trim() || loading}
                className="px-4 py-2 bg-black text-white rounded-md text-sm disabled:opacity-50"
              >
                Send
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {quickCommands.map((cmd, idx) => (
                <button
                  key={`suggest-${idx}`}
                  onClick={() => setCommandText(cmd)}
                  className="px-2 py-1 text-[11px] rounded-full bg-black/5 hover:bg-black/10"
                >
                  {cmd}
                </button>
              ))}
            </div>
          </div>

          {/* Quick Commands */}
          <div className="kazumi-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-yellow-500" />
              <h2 className="text-lg font-semibold">Quick Commands</h2>
            </div>
            <div className="space-y-2">
              {quickCommands.map((cmd, idx) => (
                <button
                  key={idx}
                  onClick={() => executeCommand(cmd)}
                  className="w-full px-4 py-3 bg-black/5 hover:bg-black/10 rounded-md text-left text-sm transition-colors"
                >
                  {cmd}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Response & History Column */}
        <div className="space-y-6">
          {/* AI Response */}
          <div className="kazumi-card p-6 min-h-[300px]">
            <h2 className="text-lg font-semibold mb-4">AI Response</h2>

            {loading ? (
              <div className="flex flex-col items-center justify-center h-32 gap-4">
                <Loader2 className="animate-spin w-8 h-8 text-gray-400" />
                <span className="text-sm text-gray-500">Processing command...</span>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-black/5 rounded-lg">
                  <p className="text-gray-900">
                    {aiResponse || "Waiting for input..."}
                  </p>
                </div>
                {aiReasoning && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h3 className="text-sm font-medium text-blue-900 mb-2">Reasoning</h3>
                    <p className="text-sm text-blue-800">{aiReasoning}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Command History */}
          <div className="kazumi-card p-6 max-h-[400px] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">Command History</h2>
            <div className="space-y-3">
              {commandHistory.length === 0 ? (
                <p className="text-gray-500 text-sm">No commands yet</p>
              ) : (
                commandHistory.map((cmd) => (
                  <div key={cmd.id} className="flex items-start gap-3 p-3 bg-black/5 rounded-lg">
                    <div className="mt-0.5">
                      {cmd.status === "completed" && <CheckCircle className="w-4 h-4 text-green-600" />}
                      {cmd.status === "processing" && <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
                      {cmd.status === "failed" && <XCircle className="w-4 h-4 text-red-600" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{cmd.text}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500">{cmd.timestamp}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          cmd.status === 'completed' ? 'bg-green-100 text-green-800' :
                          cmd.status === 'failed' ? 'bg-red-100 text-red-800' :
                          cmd.status === 'scheduled' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {cmd.status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
