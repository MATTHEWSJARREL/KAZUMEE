"use client";

import { useEffect, useRef, useState } from "react";
import { X, Send, Pin, Search } from "lucide-react";
import { apiFetch } from "@/lib/apiClient";
import { useSettings } from "@/lib/SettingsContext";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  meta?: {
    command?: string | null;
    executed?: boolean;
  };
};

type Props = {
  open: boolean;
  onClose: () => void;
  userKey?: string | null;
  role?: string | null;
};

const buildStorageKey = (userKey?: string | null, mode?: string) =>
  `kazumi_assistant_history_${userKey || "anonymous"}_${mode || "ask"}`;

export default function KazumiSidePanel({ open, onClose, userKey, role }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"ask" | "command">("ask");
  const [search, setSearch] = useState("");
  const [pinned, setPinned] = useState<ChatMessage[]>([]);
  const [savingPrompt, setSavingPrompt] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);
  const storageKey = buildStorageKey(userKey, mode);
  const pinKey = `kazumi_assistant_pins_${userKey || "anonymous"}_${mode}`;
  const { settings, updateSetting, saveSettings } = useSettings();

  const loadHistory = async () => {
    if (typeof window === "undefined") return;
    if (userKey) {
      try {
        const res = await apiFetch(`/api/assistant/history?mode=${mode}`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data?.messages)) {
            const mapped = data.messages.map((m: any) => ({
              role: m.role,
              content: m.content,
              timestamp: m.timestamp || new Date().toISOString(),
              meta: { command: m.command },
            }));
            setMessages(mapped);
            return;
          }
        }
      } catch {
        // fall through to local
      }
    }
    const cached = localStorage.getItem(storageKey);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed)) setMessages(parsed);
      } catch {
        // ignore
      }
    } else {
      setMessages([]);
    }
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (open) loadHistory();
  }, [storageKey, open, mode]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages, storageKey]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const cached = localStorage.getItem(pinKey);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed)) setPinned(parsed);
      } catch {
        // ignore
      }
    }
  }, [pinKey]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(pinKey, JSON.stringify(pinned));
  }, [pinned, pinKey]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    const nextUser: ChatMessage = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, nextUser]);
    setInput("");
    setLoading(true);

    try {
      const response = await apiFetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          mode,
          history: messages.slice(-8).map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      const data = await response.json();
      const reply =
        response.ok && data?.message
          ? data.message
          : data?.detail || "Kazumi could not respond right now.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: reply,
          timestamp: new Date().toISOString(),
          meta: {
            command: data?.command,
            executed: data?.executed,
          },
        },
      ]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Kazumi is offline or unreachable.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const runCommand = async (command: string, idx: number) => {
    try {
      const res = await apiFetch("/api/assistant/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      const data = await res.json();
      setMessages((prev) => {
        const next = [...prev];
        const target = next[idx];
        if (target?.meta) target.meta.executed = res.ok;
        next.push({
          role: "assistant",
          content: res.ok ? `Executed: ${command}` : `Failed to execute: ${data?.message || "error"}`,
          timestamp: new Date().toISOString(),
        });
        return next;
      });
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Failed to execute command (network error).",
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const dismissCommand = (idx: number) => {
    setMessages((prev) => {
      const next = [...prev];
      if (next[idx]?.meta) {
        next[idx].meta = { ...next[idx].meta, command: null, executed: false };
      }
      return next;
    });
  };

  const filtered = messages.filter((m) =>
    m.content.toLowerCase().includes(search.toLowerCase())
  );

  const isPinned = (m: ChatMessage) =>
    pinned.some((p) => p.timestamp === m.timestamp && p.role === m.role && p.content === m.content);

  const togglePin = (m: ChatMessage) => {
    if (isPinned(m)) {
      setPinned((prev) => prev.filter((p) => !(p.timestamp === m.timestamp && p.role === m.role && p.content === m.content)));
    } else {
      setPinned((prev) => [m, ...prev].slice(0, 10));
    }
  };

  const saveAssistantPrompt = async () => {
    setSavingPrompt(true);
    try {
      await saveSettings();
    } finally {
      setSavingPrompt(false);
    }
  };

  return (
    <div
      className={`fixed top-0 right-0 h-full w-full sm:w-[420px] bg-white border-l border-gray-200 shadow-2xl z-[9998] transition-transform ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
      aria-hidden={!open}
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <div className="font-semibold text-gray-900">Ask Kazumi</div>
          <div className="flex items-center gap-1 text-[11px]">
            <button
              onClick={() => setMode("ask")}
              className={`px-2 py-1 rounded ${
                mode === "ask" ? "bg-black text-white" : "bg-gray-100 text-gray-600"
              }`}
            >
              Ask
            </button>
            <button
              onClick={() => setMode("command")}
              className={`px-2 py-1 rounded ${
                mode === "command" ? "bg-black text-white" : "bg-gray-100 text-gray-600"
              }`}
            >
              Command
            </button>
          </div>
          <div className="text-[11px] text-gray-500">
            {role === "streamer" ? "Commands enabled" : "Viewer mode"}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100"
            aria-label="Close panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-4 py-3 border-b border-gray-200 space-y-2">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversation..."
              className="flex-1 text-sm px-2 py-1 border border-gray-200 rounded-md"
            />
          </div>
          {role === "streamer" && (
            <div className="space-y-2">
              <div className="text-[11px] text-gray-500">Assistant memory (streamer only)</div>
              <textarea
                value={settings?.ai?.assistantPrompt || ""}
                onChange={(e) => updateSetting("ai", "assistantPrompt", e.target.value)}
                rows={3}
                className="w-full text-xs px-2 py-1 border border-gray-200 rounded-md"
                placeholder="e.g. Always prioritize FPS games, prefer short witty responses."
              />
              <button
                onClick={saveAssistantPrompt}
                disabled={savingPrompt}
                className="px-2 py-1 text-[11px] rounded bg-black text-white disabled:opacity-50"
              >
                {savingPrompt ? "Saving..." : "Save memory"}
              </button>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {pinned.length > 0 && (
            <div className="mb-2">
              <div className="text-[11px] text-gray-500 mb-1">Pinned</div>
              <div className="space-y-2">
                {pinned.map((m, idx) => (
                  <div key={`pin-${idx}`} className="text-xs bg-yellow-50 border border-yellow-200 rounded-md px-2 py-1">
                    <span className="font-semibold">{m.role === "user" ? "You" : "Kazumi"}:</span>{" "}
                    {m.content}
                  </div>
                ))}
              </div>
            </div>
          )}
          {messages.length === 0 && (
            <div className="text-sm text-gray-500">
              Ask anything about your stream, clips, or settings.
            </div>
          )}
          {filtered.map((m, idx) => (
            <div
              key={`${m.timestamp}-${idx}`}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-black text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>
                {m.meta?.command && (
                  <div className="mt-2 text-[10px] opacity-70">
                    Command: {m.meta.command}{" "}
                    {role === "streamer"
                      ? m.meta.executed
                        ? "(executed)"
                        : "(pending)"
                      : "(streamer only)"}
                  </div>
                )}
                {m.meta?.command && role === "streamer" && mode === "command" && !m.meta.executed && (
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => runCommand(m.meta?.command as string, idx)}
                      className="px-2 py-1 text-[10px] rounded bg-black text-white"
                    >
                      Run
                    </button>
                    <button
                      onClick={() => dismissCommand(idx)}
                      className="px-2 py-1 text-[10px] rounded border border-gray-300 text-gray-600"
                    >
                      Dismiss
                    </button>
                  </div>
                )}
                <div className="mt-1 text-[10px] opacity-70">
                  {new Date(m.timestamp).toLocaleTimeString()}
                </div>
              </div>
              <button
                onClick={() => togglePin(m)}
                className="ml-2 mt-1 text-gray-400 hover:text-black"
                title={isPinned(m) ? "Unpin" : "Pin"}
              >
                <Pin className={`w-3.5 h-3.5 ${isPinned(m) ? "fill-black" : ""}`} />
              </button>
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div className="p-3 border-t border-gray-200">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={loading ? "Kazumi is thinking..." : "Ask Kazumi anything..."}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
              disabled={loading}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              className="p-2 rounded-md bg-black text-white disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
