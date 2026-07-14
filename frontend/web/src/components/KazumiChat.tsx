"use client";
import { useEffect, useRef, useState } from "react";
import { MessageSquare, X, Send, Mic, MicOff } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/apiClient";
import { useLatencyShield } from "@/hooks/useLatencyShield";
import { useSettings } from "@/lib/SettingsContext";
import { useAvatar } from "@/lib/avatar/useAvatar";
import { useKazumiResponse } from "@/lib/KazumiResponseContext";
import KazumiAvatar from "./avatar/KazumiAvatar";

type ChatMessage = {
  sender: "user" | "kazumi";
  text: string;
  timestamp: string;
};

type KazumiChatProps = {
  isOpen?: boolean;
  onClose?: () => void;
  messages?: ChatMessage[];
  onSendMessage?: (message: string) => Promise<void> | void;
};

const renderWithLinks = (text: string) => {
  const urlRegex = /(https?:\/\/[^\s)]+)/g;
  const parts = text.split(urlRegex);
  return parts.map((part, idx) => {
    if (/^https?:\/\//.test(part)) {
      return (
        <a
          key={idx}
          href={part}
          target="_blank"
          rel="noreferrer"
          className="text-blue-600 underline break-all"
        >
          {part}
        </a>
      );
    }
    return <span key={idx}>{part}</span>;
  });
};

export default function KazumiChat(props: KazumiChatProps = {}) {
  const [isOpenInternal, setIsOpenInternal] = useState(false);
  const [messagesInternal, setMessagesInternal] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const { avatarState, setAvatarState } = useAvatar();
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const { shield, shieldMsLeft } = useLatencyShield(3500);
  const { settings } = useSettings();
  const { showAnswer } = useKazumiResponse();
  const voiceEnabled = settings?.voice?.enabled ?? true;
  const useGroq = settings?.ai?.useGroq ?? true;

  const isViewer =
    typeof window !== "undefined" &&
    window.location.pathname.includes("viewer");
  const role = isViewer ? "viewer" : "streamer";

  const isOpen = props.isOpen ?? isOpenInternal;
  const messages = props.messages ?? messagesInternal;

  const closeDrawer = () => {
    if (props.onClose) props.onClose();
    else setIsOpenInternal(false);
  };

  const openDrawer = () => setIsOpenInternal(true);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isListening) {
      setAvatarState("listening");
      return;
    }
    if (isThinking) {
      setAvatarState("thinking");
      return;
    }
    setAvatarState("idle");
  }, [isListening, isThinking, setAvatarState]);

  const sendMessage = async (text: string) => {
    if (props.onSendMessage) {
      await props.onSendMessage(text);
      return;
    }

    const userMessage: ChatMessage = {
      sender: "user",
      text,
      timestamp: new Date().toISOString(),
    };
    setMessagesInternal((prev) => [...prev, userMessage]);
    openDrawer();
    setAvatarState("speaking");
    setIsThinking(true);

    try {
      const response = await apiFetch("/api/commands/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: text, role, use_ai: useGroq }),
      });

      const data = await response.json();
      if (!response.ok) {
        setAvatarState("alert");
        toast.error("Command failed", {
          description: data?.detail || data?.message || `Error (${response.status})`,
        });
        return;
      }
      if (role === "viewer") {
        await shield();
      }
      const aiMessage: ChatMessage = {
        sender: "kazumi",
        text: data.message || "I heard you, but I'm not sure what to do.",
        timestamp: new Date().toISOString(),
      };
      setMessagesInternal((prev) => [...prev, aiMessage]);
      // Show response as floating card for immediate visibility
      showAnswer(data.message || "I heard you, but I'm not sure what to do.");
    } catch {
      setAvatarState("alert");
      toast.error("Kazumi is offline", {
        description: "Could not reach the backend.",
      });
      const errorMessage: ChatMessage = {
        sender: "kazumi",
        text: "Sorry, I encountered an error processing your request.",
        timestamp: new Date().toISOString(),
      };
      setMessagesInternal((prev) => [...prev, errorMessage]);
    }
  };

  const startListening = () => {
    if (!voiceEnabled) {
      toast.error("Voice input disabled in settings.");
      return;
    }
    if (
      !("webkitSpeechRecognition" in window) &&
      !("SpeechRecognition" in window)
    ) {
      alert("Speech recognition not supported in this browser");
      return;
    }

    const SpeechRecognitionCtor =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    recognitionRef.current = new SpeechRecognitionCtor();
    recognitionRef.current.continuous = false;
    recognitionRef.current.interimResults = false;
    recognitionRef.current.lang = "en-US";

    recognitionRef.current.onstart = () => {
      setIsListening(true);
    };

    recognitionRef.current.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setInputMessage(transcript);
      sendMessage(transcript);
    };

    recognitionRef.current.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current.onerror = (event: SpeechRecognitionEvent) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);
    };

    recognitionRef.current.start();
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
  };

  const handleSend = () => {
    const trimmed = inputMessage.trim();
    if (!trimmed) return;
    sendMessage(trimmed);
    setInputMessage("");
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {!isOpen && (
        <button
          onClick={openDrawer}
          className="fixed bottom-6 right-6 z-50 p-4 rounded-full bg-black text-white shadow-lg hover:bg-gray-800 transition-colors"
          title="Open Kazumi Chat"
        >
          <MessageSquare className="w-5 h-5" />
        </button>
      )}

      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center p-4">
          <div className="bg-white rounded-t-lg shadow-2xl w-full max-w-md h-96 flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <KazumiAvatar state={avatarState} size={40} showSpeechVisualizer={false} className="shrink-0" />
                <MessageSquare className="w-5 h-5 text-blue-600" />
                <span className="font-bold text-gray-900">
                  Kazumi Chat ({role})
                </span>
              </div>
              <button
                onClick={closeDrawer}
                className="p-1 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {role === "viewer" && shieldMsLeft > 0 && (
          <div className="text-xs text-gray-400">
            Syncing with stream delay…
          </div>
        )}
        {messages.length === 0 ? (
                <div className="text-center text-gray-500 text-sm">
                  Start a conversation with Kazumi...
                </div>
              ) : (
                messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${
                      message.sender === "user"
                        ? "justify-end"
                        : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-xs px-4 py-2 rounded-lg ${
                        message.sender === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-900"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">
                        {renderWithLinks(message.text)}
                      </p>
                      <span className="text-xs opacity-70 mt-1 block">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-gray-200">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={isListening ? stopListening : startListening}
                  disabled={!voiceEnabled}
                  className={`p-2 rounded-lg transition-colors ${
                    !voiceEnabled
                      ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                      : isListening
                        ? "bg-red-500 hover:bg-red-600 text-white"
                        : "bg-gray-100 hover:bg-gray-200 text-gray-700"
                  }`}
                  title={isListening ? "Stop listening" : "Start voice input"}
                >
                  {isListening ? (
                    <MicOff className="w-5 h-5" />
                  ) : (
                    <Mic className="w-5 h-5" />
                  )}
                </button>
                <button
                  onClick={handleSend}
                  disabled={!inputMessage.trim()}
                  className="p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
