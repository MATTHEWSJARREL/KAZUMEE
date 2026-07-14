"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, MicOff } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/apiClient";
import { useSettings } from "../../lib/SettingsContext";

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

export default function VoiceControlPanel({ userRole, streamPulse }) {
  const { settings } = useSettings();
  const recognitionRef = useRef(null);
  const shouldRestartRecognitionRef = useRef(false);
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [micStatusMessage, setMicStatusMessage] = useState("");
  const [micMuted] = useState(false);
  const continuousListening = settings?.voice?.enabled ?? true;
  const triggerWord = settings?.voice?.triggerWord || "Kazumi";

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
    const delayed =
      options.allowSchedule === false ? { command: cleaned, delayMs: 0, delayLabel: "" } : parseDelayedCommand(cleaned);

    if (delayed.delayMs > 0) {
      setMicStatusMessage(`Scheduled: ${delayed.command} in ${delayed.delayLabel}`);
      window.setTimeout(() => {
        void handleSendMessage(delayed.command, { allowSchedule: false });
      }, delayed.delayMs);
      return;
    }

    try {
      const data = await executeStreamerCommand(delayed.command);
      if (data.success || data.execution_status === "success" || data.message) {
        setMicStatusMessage(data.message ? `Kazumi: ${data.message}` : "Command executed");
        window.setTimeout(() => setMicStatusMessage(""), 3000);
      } else {
        setMicStatusMessage(`I didn't understand that command. ${data.reason || data.message || ""}`);
      }
    } catch (error) {
      console.error("Error sending command:", error);
      setMicStatusMessage("Sorry, I encountered an error processing your request.");
    }
  };

  const startVoiceListening = () => {
    if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
      alert("Speech recognition not supported in this browser");
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
    recognition.lang = "en-US";
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
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) {
          transcripts.push(String(result[0]?.transcript || "").trim());
        }
      }

      transcripts.forEach((spoken) => {
        if (!spoken) return;
        if (!continuousListening) {
          void handleSendMessage(spoken);
          return;
        }
        const parsed = extractWakeWordCommand(spoken, triggerWord);
        if (!parsed.matched) return;
        if (!parsed.command) {
          setMicStatusMessage(`Wake word heard. Say "${triggerWord} <command>"`);
          return;
        }
        void handleSendMessage(parsed.command);
      });
    };

    recognition.onend = () => {
      setIsVoiceListening(false);
      if (shouldRestartRecognitionRef.current && continuousListening) {
        window.setTimeout(() => {
          try {
            recognition.start();
          } catch {
            // ignore
          }
        }, 250);
      } else {
        window.setTimeout(() => setMicStatusMessage(""), 2000);
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      setIsVoiceListening(false);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setMicStatusMessage("Microphone permission denied");
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

  if (userRole !== "streamer") {
    return null;
  }

  return (
    <>
      <button
        onClick={isVoiceListening ? stopVoiceListening : startVoiceListening}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-2xl border shadow-sm transition-colors ${
          isVoiceListening
            ? "bg-red-500/15 border-red-400/30 text-red-100 animate-pulse"
            : "bg-white/5 border-white/10 text-[var(--text)] hover:bg-white/10"
        }`}
        title={isVoiceListening ? "Stop listening" : "Start voice command"}
      >
        {isVoiceListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        <span className="text-sm font-semibold">{isVoiceListening ? "Listening" : "Voice"}</span>
      </button>
      <div className="px-4 py-2 rounded-2xl border border-white/10 bg-white/5 shadow-sm min-w-[170px]">
        <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Stream Pulse</div>
        <div className="flex items-end justify-between">
          <div
            className={`text-3xl font-bold tabular-nums ${
              (streamPulse?.score ?? 0) >= 70 ? "text-green-600" : (streamPulse?.score ?? 0) >= 40 ? "text-amber-500" : "text-red-500"
            }`}
          >
            {streamPulse?.score ?? 0}
          </div>
          <div className={`text-xs font-semibold ${(streamPulse?.trend ?? 0) >= 0 ? "text-green-600" : "text-red-500"}`}>
            {(streamPulse?.trend ?? 0) >= 0 ? "↑" : "↓"} {Math.abs(streamPulse?.trend ?? 0)}
          </div>
        </div>
      </div>

      {micStatusMessage && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg border-2 ${
            micMuted ? "bg-red-100 border-red-300 text-red-800" : "bg-green-100 border-green-300 text-green-800"
          }`}
        >
          <div className="flex items-center gap-2">
            <Mic className="w-4 h-4" />
            <span className="font-medium">{micStatusMessage}</span>
          </div>
        </div>
      )}
    </>
  );
}
