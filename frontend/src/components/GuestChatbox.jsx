import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useNavigate } from "react-router-dom";
import { BsArrowUpCircleFill } from "react-icons/bs";
import "./GuestChatbox.css";

// Default suggestions for guests
const GUEST_SUGGESTIONS = [
  "What CS courses are available?",
  "What are the prerequisites for COSC 311?",
  "Who is the chair of Computer Science?",
  "What internship opportunities are available?",
  "What are the degree requirements?",
  "What research areas exist in CS?"
];

// --- SMART API SWITCHING ---
const hostname = window.location.hostname;
const API_BASE = (hostname === "localhost" || hostname === "127.0.0.1")
  ? "http://127.0.0.1:8000"
  : "http://18.214.136.155:5000";

// Guest message limit
const GUEST_MESSAGE_LIMIT = 10;
const MAX_INPUT_LENGTH = 500; // Limit input to 500 characters

export default function GuestChatbox() {
  const navigate = useNavigate();

  // State
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messageCount, setMessageCount] = useState(() => {
    const saved = localStorage.getItem("guest_message_count");
    return saved ? parseInt(saved, 10) : 0;
  });

  // Refs
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Save message count to localStorage
  useEffect(() => {
    localStorage.setItem("guest_message_count", messageCount.toString());
  }, [messageCount]);

  // Helper to add message
  const addMessage = (text, sender) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((prev) => [...prev, { text, sender, time }]);
  };

  // Handle suggestion click
  const handleSuggestion = (text) => {
    if (!isLoading) {
      setInput(text);
      inputRef.current?.focus();
    }
  };

  // Main send handler
  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setIsLoading(true);

    addMessage(userMessage, "user");
    setInput("");
    setMessageCount((prev) => prev + 1);

    try {
      const res = await fetch(`${API_BASE}/chat/guest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage }),
      });

      if (res.status === 429) {
        addMessage("You've reached the rate limit. Please wait a moment or sign up for unlimited access!", "bot");
        return;
      }

      if (!res.ok) throw new Error(res.statusText);

      const data = await res.json();
      const botResponse = data.response || "No response.";
      addMessage(botResponse, "bot");

    } catch (err) {
      console.error("Guest chat error:", err);
      addMessage("Sorry, I had trouble processing that. Please try again.", "bot");
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const remainingMessages = Math.max(0, GUEST_MESSAGE_LIMIT - messageCount);
  const isLowOnMessages = remainingMessages <= 3 && remainingMessages > 0;
  const isOutOfMessages = remainingMessages === 0;

  return (
    <div className="guest-chat-main">
      {/* Trial counter - always visible at top */}
      <div className={`guest-trial-bar ${isLowOnMessages ? 'low' : ''} ${isOutOfMessages ? 'empty' : ''}`}>
        <div className="trial-bar-content">
          {isOutOfMessages ? (
            <>
              <span className="trial-text">You've used all 10 free messages</span>
              <button onClick={() => navigate("/signup")} className="trial-cta">
                Create Free Account for Unlimited
              </button>
            </>
          ) : (
            <>
              <span className="trial-text">
                <strong>{remainingMessages}</strong> free {remainingMessages === 1 ? 'question' : 'questions'} remaining
              </span>
              <span className="trial-divider">|</span>
              <button onClick={() => navigate("/signup")} className="trial-link">
                Create an account for unlimited
              </button>
            </>
          )}
        </div>
      </div>

      <div className="guest-chat-messages">
        {messages.length === 0 ? (
          <div className="guest-welcome-container">
            <img src="/msu_logo.png" alt="MSU Logo" className="guest-welcome-logo" />
            <h1 className="guest-welcome-title">Morgan State CS Navigator</h1>
            <p className="guest-welcome-subtitle">How can I assist with your academic journey today?</p>
            <div className="guest-suggestions">
              {GUEST_SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="guest-suggestion-btn"
                  onClick={() => handleSuggestion(s)}
                  disabled={isLoading}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`guest-message ${msg.sender}`}>
              <img
                src={msg.sender === "user" ? "/user_icon.jpg" : "/bot_avatar.jpg"}
                alt={msg.sender}
                className="guest-avatar-img"
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = msg.sender === "user"
                    ? "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23666'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E"
                    : "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23002D72'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z'/%3E%3C/svg%3E";
                }}
              />
              <div className="guest-message-content">
                <div className="guest-message-bubble">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.text}
                  </ReactMarkdown>
                </div>
                <div className="guest-timestamp">{msg.time}</div>
              </div>
            </div>
          ))
        )}

        {/* Typing indicator */}
        {isLoading && (
          <div className="guest-message bot">
            <img
              src="/bot_avatar.jpg"
              alt="Bot"
              className="guest-avatar-img"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23002D72'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z'/%3E%3C/svg%3E";
              }}
            />
            <div className="guest-message-content">
              <div className="guest-message-bubble guest-typing-bubble">
                <div className="guest-dot"></div>
                <div className="guest-dot"></div>
                <div className="guest-dot"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area - matches main chat style */}
      <div className="guest-chat-input-container">
        <form onSubmit={handleSend} className="guest-chat-input-wrapper">
          <input
            type="text"
            ref={inputRef}
            className="guest-chat-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value.slice(0, MAX_INPUT_LENGTH))}
            placeholder={isOutOfMessages ? "Sign up for unlimited messages..." : "Type your message..."}
            disabled={isLoading || isOutOfMessages}
            maxLength={MAX_INPUT_LENGTH}
          />
          <button
            type="submit"
            className="guest-action-btn-icon guest-send-btn"
            title="Send message"
            disabled={isLoading || !input.trim() || isOutOfMessages}
          >
            <BsArrowUpCircleFill size={24} />
          </button>
        </form>
        {input.length > MAX_INPUT_LENGTH - 50 && (
          <div className="guest-char-counter">
            {input.length}/{MAX_INPUT_LENGTH}
          </div>
        )}
      </div>
    </div>
  );
}
