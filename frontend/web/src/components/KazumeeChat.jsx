"use client";

import { useState, useEffect, useRef } from "react";
import { Send, X, MessageCircle, Mic, MicOff, AlertCircle } from "lucide-react";
import { askGroq } from "@/lib/groqClient";
import { SpeechToText } from "@/lib/speechRecognition";

export default function KazumeeChatDrawer() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "kazumee",
      text: "Hey! 👋 I'm Kazumee, your AI streaming assistant. Ask me anything about gaming, streaming, or content creation!",
    },
  ]);
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const messagesEndRef = useRef(null);
  const speechRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!speechRef.current) {
      speechRef.current = new SpeechToText();
    }
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      id: messages.length + 1,
      type: "user",
      text: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError("");
    setLoading(true);

    try {
      // Get response from Groq
      const response = await askGroq(input);

      const kazumeeMessage = {
        id: messages.length + 2,
        type: "kazumee",
        text: response,
      };

      setMessages((prev) => [...prev, kazumeeMessage]);
    } catch (err) {
      setError(err.message || "Failed to get response. Check your Groq API key.");
      const errorMessage = {
        id: messages.length + 2,
        type: "kazumee",
        text: `Error: ${err.message}. Make sure you've added your Groq API key to .env.local`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleVoice = async () => {
    if (!speechRef.current?.isSupported()) {
      setError("Speech recognition not supported in your browser");
      return;
    }

    if (isListening) {
      const transcript = speechRef.current.stop();
      setIsListening(false);
      setInterimTranscript("");
      if (transcript) {
        setInput(transcript);
      }
      return;
    }

    setIsListening(true);
    setInterimTranscript("");
    setError("");

    try {
      await speechRef.current.start({
        language: "en-US",
        continuous: false,
        interimResults: true,
        onResult: (transcript, isFinal) => {
          if (isFinal) {
            setInput(transcript);
            setInterimTranscript("");
          } else {
            setInterimTranscript(transcript);
          }
        },
        onError: (error) => {
          setError(`Voice error: ${error}`);
          setIsListening(false);
        },
        onEnd: () => {
          setIsListening(false);
        },
      });
    } catch (err) {
      setError("Failed to start listening");
      setIsListening(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={{
          position: "fixed",
          right: "20px",
          bottom: "20px",
          padding: "12px 24px",
          borderRadius: "25px",
          background: "linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)",
          border: "none",
          color: "white",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          fontSize: "14px",
          fontWeight: "600",
          boxShadow: "0 8px 24px rgba(124, 58, 237, 0.3)",
          zIndex: 40,
          transition: "all 0.2s",
          fontFamily: "inherit",
        }}
        onMouseEnter={(e) => (e.target.style.transform = "translateY(-2px)")}
        onMouseLeave={(e) => (e.target.style.transform = "translateY(0)")}
        title="Ask Kazumee for help"
      >
        <MessageCircle size={20} />
        Ask Kazumi
      </button>
    );
  }

  return (
    <div className="streamer-chat-drawer">
      {/* Header */}
      <div className="streamer-chat-header">
        <div className="streamer-chat-header-content">
          <div className="streamer-chat-avatar stick-figure">
            👾
          </div>
          <div className="streamer-chat-header-text">
            <h3>Kazumee</h3>
            <p>AI Streaming Assistant</p>
          </div>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="streamer-chat-toggle"
          title="Minimize"
        >
          ✕
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
            background: "rgba(239, 68, 68, 0.1)",
            borderBottom: "1px solid rgba(239, 68, 68, 0.3)",
            display: "flex",
            gap: "8px",
            alignItems: "flex-start",
            color: "#ef4444",
            fontSize: "12px",
          }}
        >
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
          <div>{error}</div>
        </div>
      )}

      {/* Messages */}
      <div className="streamer-chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`streamer-chat-message from-${msg.type}`}>
            <div className="streamer-chat-bubble">{msg.text}</div>
          </div>
        ))}
        {loading && (
          <div className="streamer-chat-message from-kazumee">
            <div className="streamer-chat-bubble">
              <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
                <span>Thinking</span>
                <span style={{ animation: "blink 1s infinite" }}>.</span>
                <span style={{ animation: "blink 1s infinite 0.2s" }}>.</span>
                <span style={{ animation: "blink 1s infinite 0.4s" }}>.</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="streamer-chat-input-area">
        <div style={{ flex: 1, position: "relative" }}>
          <input
            type="text"
            className="streamer-chat-input"
            placeholder={isListening ? "Listening..." : "Ask Kazumee..."}
            value={isListening ? interimTranscript || input : input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            disabled={loading}
            style={{
              opacity: loading ? 0.6 : 1,
              cursor: loading ? "not-allowed" : "text",
            }}
          />
        </div>

        <button
          className="streamer-chat-send"
          onClick={handleVoice}
          disabled={loading}
          title={isListening ? "Stop listening" : "Start voice input"}
          style={{
            background: isListening
              ? "linear-gradient(135deg, #ef4444 0%, #f87171 100%)"
              : "linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)",
          }}
        >
          {isListening ? <MicOff size={16} /> : <Mic size={16} />}
        </button>

        <button
          className="streamer-chat-send"
          onClick={handleSend}
          disabled={!input.trim() || loading}
          title="Send message"
        >
          <Send size={16} />
        </button>
      </div>

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
