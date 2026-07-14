"use client";

import { useState, useEffect, useRef } from "react";
import { Send, X, MessageCircle } from "lucide-react";

export default function KazumeeChatDrawer() {
  const [messages, setMessages] = useState([
    { id: 1, type: "kazumee", text: "Hey! 👋 I'm Kazumee, your AI streaming assistant. What do you need help with today?" }
  ]);
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: "user",
      text: input
    };
    setMessages([...messages, userMessage]);

    // Simulate Kazumee response
    setTimeout(() => {
      const responses = [
        "That's a great question! Let me help you with that.",
        "I've got you covered! 💪",
        "Sounds good! What else can I help you with?",
        "Let me know if you need anything else!",
        "I'm here to make your streaming easier! 🚀"
      ];
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];

      const kazumeeMessage = {
        id: messages.length + 2,
        type: "kazumee",
        text: randomResponse
      };
      setMessages([...messages, userMessage, kazumeeMessage]);
    }, 500);

    setInput("");
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
          fontFamily: "inherit"
        }}
        onMouseEnter={(e) => e.target.style.transform = "translateY(-2px)"}
        onMouseLeave={(e) => e.target.style.transform = "translateY(0)"}
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
            <p>Always here to help</p>
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

      {/* Messages */}
      <div className="streamer-chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`streamer-chat-message from-${msg.type}`}>
            <div className="streamer-chat-bubble">
              {msg.text}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="streamer-chat-input-area">
        <input
          type="text"
          className="streamer-chat-input"
          placeholder="Message Kazumee..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
        />
        <button
          className="streamer-chat-send"
          onClick={handleSend}
          disabled={!input.trim()}
          title="Send message"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
