import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { FaMicrophone } from "@react-icons/all-files/fa/FaMicrophone";
import { FaPaperclip } from "@react-icons/all-files/fa/FaPaperclip";
import { FaVolumeUp } from "@react-icons/all-files/fa/FaVolumeUp";
import { FaTimes } from "@react-icons/all-files/fa/FaTimes";
import { FaStop } from "@react-icons/all-files/fa/FaStop";
import { BsSoundwave, BsArrowUpCircleFill } from "react-icons/bs";

// 🔥 Icons for File Cards
import { FaFile } from "@react-icons/all-files/fa/FaFile";
import { FaFilePdf } from "@react-icons/all-files/fa/FaFilePdf";
import { FaFileWord } from "@react-icons/all-files/fa/FaFileWord";
import { FaFileImage } from "@react-icons/all-files/fa/FaFileImage";

import "./Chatbox.css";

// Default suggestions (fallback) - 6 questions
const DEFAULT_SUGGESTIONS = [
  "Who is the chair of Computer Science department?",
  "What are the degree requirements for CS major?",
  "What programming languages should I learn?",
  "How do I contact my academic advisor?",
  "What internship opportunities are available?",
  "When is the deadline for course registration?"
];

// --- SMART API SWITCHING ---
const hostname = window.location.hostname;
const API_BASE = (hostname === "localhost" || hostname === "127.0.0.1")
  ? "http://127.0.0.1:8000"           // If on Laptop -> Use Local Backend (8000)
  : "http://18.214.136.155:5000";     // If on AWS -> Use AWS Backend (5000)

// Helper for icons
const getFileIcon = (filename) => {
  if (!filename) return <FaFile className="file-icon generic" />;
  const ext = filename.split('.').pop().toLowerCase();
  
  if (ext === 'pdf') return <FaFilePdf className="file-icon pdf" />;
  if (['doc', 'docx'].includes(ext)) return <FaFileWord className="file-icon word" />;
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return <FaFileImage className="file-icon image" />;
  
  return <FaFile className="file-icon generic" />;
};

export default function Chatbox({ initialMessages = [], onSessionChange, sessionId }) {
  // --- STATE ---
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [userProfilePicture, setUserProfilePicture] = useState("/user_icon.jpg");

  // 🔥 Staging State for File Uploads
  const [pendingFile, setPendingFile] = useState(null);

  // 🔥 Dynamic Suggestions State
  const [suggestions, setSuggestions] = useState(DEFAULT_SUGGESTIONS);
  const [suggestionsLoading, setSuggestionsLoading] = useState(true);

  // 🔥 Voice Mode State
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("idle"); // idle, listening, processing, speaking

  // --- REFS ---
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const isRemoteUpdate = useRef(false);
  const audioRef = useRef(null);
  const recognitionRef = useRef(null);
  const isVoiceModeRef = useRef(false); // 🔥 Ref to track voice mode for callbacks

  // --- EFFECTS ---

  // 1. Focus input on load
  useEffect(() => { 
    const focusInput = () => inputRef.current?.focus();
    focusInput();
    window.addEventListener('focus', focusInput);
    return () => window.removeEventListener('focus', focusInput);
  }, []);

  // 2. Sync Messages FROM Parent (Database Load)
  useEffect(() => {
    if (JSON.stringify(initialMessages) !== JSON.stringify(messages)) {
      isRemoteUpdate.current = true;
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  // 3. Sync Messages TO Parent (User typed something)
  useEffect(() => {
    if (!onSessionChange) return;
    if (isRemoteUpdate.current) { 
        isRemoteUpdate.current = false; 
        return; 
    }
    onSessionChange(messages);
  }, [messages, onSessionChange]);

  // 4. Auto-Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 5. Fetch User Profile Picture
  useEffect(() => {
    const fetchUserProfile = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;
      try {
        const response = await fetch(`${API_BASE}/api/profile`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          if (data.profilePicture) {
             // Handle base64 data URLs, full URLs, and relative paths
             let picUrl = data.profilePicture;
             if (picUrl.startsWith("data:")) {
                // Base64 data URL - use directly
                setUserProfilePicture(picUrl);
             } else if (picUrl.startsWith("http")) {
                // Full URL - use directly
                setUserProfilePicture(picUrl);
             } else {
                // Relative path - prepend API base
                setUserProfilePicture(`${API_BASE}${picUrl}`);
             }
          }
        }
      } catch (error) {
        console.error("❌ Profile Error:", error);
      }
    };
    fetchUserProfile();
  }, []);

  // 6. Fetch Dynamic Suggestions
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (messages.length > 0) {
        setSuggestionsLoading(false);
        return;
      }
      try {
        setSuggestionsLoading(true);
        const response = await fetch(`${API_BASE}/api/popular-questions`);
        if (response.ok) {
          const data = await response.json();
          if (data.questions && data.questions.length > 0) {
            setSuggestions(data.questions.slice(0, 6)); // Show 6 suggestions
          }
        }
      } catch (error) {
        console.error("Failed to fetch suggestions:", error);
      } finally {
        setSuggestionsLoading(false);
      }
    };
    fetchSuggestions();
  }, []);

  // 7. Cleanup voice mode on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      if (audioRef.current) {
        audioRef.current.pause();
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  // --- HANDLERS ---

  // Helper to add message to local state
  const addMessage = (text, sender) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((prev) => [...prev, { text, sender, time }]);
  };

  // 🔥 Enhanced TTS using OpenAI API
  const speakWithTTS = async (text) => {
    if (isSpeaking) return;

    setIsSpeaking(true);
    setVoiceStatus("speaking");

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ text: text.substring(0, 4000), voice: "alloy" })
      });

      if (!response.ok) throw new Error("TTS request failed");

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.onended = () => {
          setIsSpeaking(false);
          URL.revokeObjectURL(audioUrl);
          // 🔥 Use ref to check voice mode (avoids closure issues)
          if (isVoiceModeRef.current) {
            setVoiceStatus("listening");
            setTimeout(() => startListening(), 500);
          } else {
            setVoiceStatus("idle");
          }
        };
        audioRef.current.onerror = () => {
          setIsSpeaking(false);
          setVoiceStatus("idle");
          fallbackSpeak(text);
        };
        await audioRef.current.play();
      }
    } catch (error) {
      console.error("TTS Error:", error);
      fallbackSpeak(text);
    }
  };

  // Browser TTS fallback
  const fallbackSpeak = (text) => {
    if (!window.speechSynthesis) {
      setIsSpeaking(false);
      setVoiceStatus("idle");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.onend = () => {
      setIsSpeaking(false);
      // 🔥 Use ref to check voice mode (avoids closure issues)
      if (isVoiceModeRef.current) {
        setVoiceStatus("listening");
        setTimeout(() => startListening(), 500);
      } else {
        setVoiceStatus("idle");
      }
    };
    window.speechSynthesis.speak(utterance);
  };

  // Simple TTS for manual speaker button (uses browser TTS)
  const speak = (text) => {
    if (!window.speechSynthesis) return alert("Text-to-speech not supported.");
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    window.speechSynthesis.speak(utterance);
  };

  // Handle File Selection (Staging)
  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setPendingFile(e.target.files[0]);
    }
    // Reset value so onChange triggers again if same file selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Clear Staged File
  const clearFile = () => {
    setPendingFile(null);
  };

  // 🔥 Enhanced Voice Input with Voice Mode Support - CONTINUOUS
  const startListening = (forceVoiceMode = false) => {
    // Don't start if already listening or speaking
    if (isListening || isSpeaking) return;

    // Extra safety check - if not in voice mode and not forced, don't start
    if (!forceVoiceMode && !isVoiceModeRef.current) return;

    const SpeechAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechAPI) {
      alert("Speech recognition not supported. Try Chrome or Edge.");
      return;
    }

    const rec = new SpeechAPI();
    rec.lang = "en-US";
    rec.continuous = false;
    rec.interimResults = false;
    recognitionRef.current = rec;

    // Track if we got a result (to handle silence timeouts)
    let gotResult = false;

    rec.onstart = () => {
      setIsListening(true);
      setVoiceStatus("listening");
      console.log("🎤 Voice mode: Started listening...");
    };

    rec.onresult = async (e) => {
      gotResult = true;
      const transcript = e.results[0][0].transcript;
      console.log("🎤 Voice mode: Got transcript:", transcript);
      setInput(transcript);
      setIsListening(false);

      // 🔥 Check ref for current voice mode state (not stale closure)
      if (isVoiceModeRef.current) {
        setVoiceStatus("processing");
        await handleVoiceSend(transcript);
      }
    };

    rec.onerror = (e) => {
      console.error("🎤 Speech error:", e.error);
      setIsListening(false);

      // 🔥 FIXED: For certain errors, retry listening if still in voice mode
      if (isVoiceModeRef.current) {
        // "no-speech" means user was silent - just restart listening
        // "aborted" means we stopped it intentionally - don't restart
        // "network" - network issue, try again
        if (e.error === "no-speech" || e.error === "network") {
          console.log("🎤 Voice mode: Restarting after", e.error);
          setVoiceStatus("listening");
          setTimeout(() => startListening(), 300);
        } else if (e.error !== "aborted") {
          // Other errors - still try to restart after a delay
          setVoiceStatus("listening");
          setTimeout(() => startListening(), 1000);
        }
      } else {
        setVoiceStatus("idle");
      }
    };

    rec.onend = () => {
      console.log("🎤 Voice mode: Recognition ended, gotResult:", gotResult);
      setIsListening(false);

      // 🔥 FIXED: If voice mode is active and we didn't get a result, restart
      // This handles the case where recognition ends without triggering onresult or onerror
      if (isVoiceModeRef.current && !gotResult && !isSpeaking) {
        console.log("🎤 Voice mode: Restarting (no result received)");
        setVoiceStatus("listening");
        setTimeout(() => startListening(), 300);
      }
    };

    rec.start();
  };

  // Voice mode send handler - sends and speaks response
  const handleVoiceSend = async (transcript) => {
    if (!transcript.trim()) {
      // Empty transcript - restart listening if in voice mode
      if (isVoiceModeRef.current) {
        setVoiceStatus("listening");
        setTimeout(() => startListening(), 300);
      }
      return;
    }

    const token = localStorage.getItem("token");
    addMessage(transcript, "user");
    setInput("");

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          query: transcript,
          session_id: sessionId || "default"
        })
      });

      if (!res.ok) throw new Error(res.statusText);

      const data = await res.json();
      const botResponse = data.response || data.message || "No response.";

      addMessage(botResponse, "bot");

      // Speak the response with OpenAI TTS
      await speakWithTTS(botResponse);

    } catch (err) {
      console.error("🎤 Voice send error:", err);
      addMessage("Sorry, I had trouble processing that. Please try again.", "bot");

      // 🔥 FIXED: Restart listening even on error if still in voice mode
      if (isVoiceModeRef.current) {
        setVoiceStatus("listening");
        setTimeout(() => startListening(), 1000);
      } else {
        setVoiceStatus("idle");
      }
    }
  };

  // Toggle voice mode on/off
  const toggleVoiceMode = () => {
    if (isVoiceMode) {
      // Stop voice mode
      setIsVoiceMode(false);
      isVoiceModeRef.current = false; // 🔥 Sync ref with state
      setVoiceStatus("idle");
      setIsListening(false);
      if (audioRef.current) {
        audioRef.current.pause();
      }
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      window.speechSynthesis?.cancel();
    } else {
      // Start voice mode
      setIsVoiceMode(true);
      isVoiceModeRef.current = true; // 🔥 Sync ref with state
      startListening(true); // 🔥 Pass true to force voice mode for first listen
    }
  };

  // Simple voice input (tap mic without entering voice mode) - FIXED
  const handleVoiceInput = () => {
    // If already listening, stop it
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    const SpeechAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechAPI) {
      alert("Speech recognition not supported. Try Chrome or Edge.");
      return;
    }

    const rec = new SpeechAPI();
    rec.lang = "en-US";
    rec.continuous = false;
    rec.interimResults = false;
    recognitionRef.current = rec;

    rec.onstart = () => {
      setIsListening(true);
      console.log("🎤 Simple mic: Started listening...");
    };

    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      console.log("🎤 Simple mic: Got transcript:", transcript);
      setInput(transcript);
      setIsListening(false);
      // Auto-focus input so user can edit or send
      inputRef.current?.focus();
    };

    rec.onerror = (e) => {
      console.error("🎤 Simple mic error:", e.error);
      setIsListening(false);
      if (e.error === "no-speech") {
        // User was silent, just stop quietly
      } else if (e.error !== "aborted") {
        alert("Voice input error: " + e.error);
      }
    };

    rec.onend = () => {
      setIsListening(false);
    };

    rec.start();
  };

  const handleSuggestion = (text) => {
      if (!isLoading) {
          setInput(text);
          inputRef.current?.focus();
      }
  };

  // 🔥 MAIN SEND LOGIC
  const handleSend = async (e) => {
    e.preventDefault();
    if ((!input.trim() && !pendingFile) || isLoading) return;

    setIsLoading(true);
    let finalMessage = input.trim();

    try {
        const token = localStorage.getItem("token");

        // 1. Upload File (if exists)
        if (pendingFile) {
            const formData = new FormData();
            formData.append("file", pendingFile);

            const uploadRes = await fetch(`${API_BASE}/api/upload-file`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` },
                body: formData
            });

            if (uploadRes.ok) {
                const data = await uploadRes.json();
                const fullUrl = data.url.startsWith("http") ? data.url : `${API_BASE}${data.url}`;
                
                // Create Markdown Link: [filename](url)
                const fileMarkdown = `[${data.filename}](${fullUrl})`;
                
                // Append to message
                if (finalMessage) {
                    finalMessage = `${fileMarkdown}\n${finalMessage}`;
                } else {
                    finalMessage = fileMarkdown;
                }
            } else {
                alert("File upload failed. Sending text only.");
            }
        }

        // 2. Optimistic UI Update
        addMessage(finalMessage, "user");
        setInput("");
        setPendingFile(null);

        // 3. Send to Chat API
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json", 
                "Authorization": `Bearer ${token}` 
            },
            body: JSON.stringify({ 
                query: finalMessage, 
                session_id: sessionId || "default" 
            }),
        });

        if (res.status === 401 || res.status === 403) {
            addMessage("⚠️ Session expired. Please log in again.", "bot");
            return;
        }
        
        if (!res.ok) throw new Error(res.statusText);
        
        const data = await res.json();
        const botResponse = data.response || data.message || "No response.";
        
        addMessage(botResponse, "bot");

    } catch (err) {
        addMessage("Error: " + err.message, "bot");
    } finally {
        setIsLoading(false);
        // Regain focus
        setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  return (
    <div className="chat-main">
      {/* Hidden audio element for TTS playback */}
      <audio ref={audioRef} style={{ display: 'none' }} />

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="welcome-container">
            <img src="/msu_logo.png" alt="MSU Logo" className="welcome-logo" />
            <h1 className="welcome-title">Morgan State CS Navigator</h1>
            <p className="welcome-subtitle">How can I assist with your academic journey today?</p>
            <div className="suggestions">
              {suggestionsLoading ? (
                <>
                  <div className="suggestion-skeleton"></div>
                  <div className="suggestion-skeleton"></div>
                  <div className="suggestion-skeleton"></div>
                </>
              ) : (
                suggestions.map((s, i) => (
                  <button key={i} className="suggestion-btn" onClick={() => handleSuggestion(s)} disabled={isLoading}>
                    {s}
                  </button>
                ))
              )}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`message ${msg.sender}`}>
              <img 
                src={msg.sender === "user" ? userProfilePicture : "/bot_avatar.jpg"} 
                alt={msg.sender} 
                className="avatar-img"
                onError={(e) => { if (msg.sender === "user") e.target.src = "/user_icon.jpg"; }}
              />
              <div className="message-content">
                <div className="message-bubble">
                  
                  {/* 🔥 UPDATED: Use ReactMarkdown for Bullets, Bold, & File Cards */}
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                        // Custom Renderer for Links to handle File Cards
                        a: ({node, href, children, ...props}) => {
                            const isFile = href.includes("uploads/chat_files") || href.includes("uploads/profile_pictures");
                            
                            if (isFile) {
                                return (
                                    <a href={href} target="_blank" rel="noopener noreferrer" className="file-card">
                                        <div className="file-icon-wrapper">
                                            {getFileIcon(children[0])}
                                        </div>
                                        <div className="file-info">
                                            <span className="file-name">{children}</span>
                                            <span className="file-action">Click to view file</span>
                                        </div>
                                    </a>
                                );
                            }
                            return <a href={href} target="_blank" rel="noopener noreferrer" className="message-link" {...props}>{children}</a>;
                        }
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>

                  {msg.sender === "bot" && (
                    <button 
                      className="tts-btn" 
                      onClick={() => speak(msg.text)} 
                      title="Read response aloud"
                    >
                      <FaVolumeUp size={14}/>
                    </button>
                  )}
                </div>
                <div className="timestamp">{msg.time}</div>
              </div>
            </div>
          ))
        )}
        
        {/* Typing Indicator */}
        {isLoading && (
          <div className="message bot">
            <img src="/bot_avatar.jpg" alt="Bot" className="avatar-img" />
            <div className="message-content">
              <div className="message-bubble typing-bubble">
                <div className="dot"></div><div className="dot"></div><div className="dot"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />

        {/* 🔥 Voice Mode Overlay - Seamless ChatGPT-style */}
        {isVoiceMode && (
          <div className="voice-overlay">
            <div className="voice-orb-container">
              <div className={`voice-orb ${voiceStatus}`}>
                <div className="orb-ring ring-1"></div>
                <div className="orb-ring ring-2"></div>
                <div className="orb-ring ring-3"></div>
                <div className="orb-core">
                  {voiceStatus === "listening" && <FaMicrophone size={32} />}
                  {voiceStatus === "processing" && <div className="orb-spinner" />}
                  {voiceStatus === "speaking" && <FaVolumeUp size={32} />}
                  {voiceStatus === "idle" && <FaMicrophone size={32} />}
                </div>
              </div>
              <p className="voice-label">
                {voiceStatus === "listening" && "Listening..."}
                {voiceStatus === "processing" && "Thinking..."}
                {voiceStatus === "speaking" && "Speaking..."}
                {voiceStatus === "idle" && "Ready"}
              </p>
              <button className="voice-end-btn" onClick={toggleVoiceMode}>
                End
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="chat-input-container">

        <form onSubmit={handleSend} className="chat-input-wrapper">

          {/* 🔥 STAGING AREA: Shows file before sending */}
          {pendingFile && (
            <div className="attachment-preview">
              {getFileIcon(pendingFile.name)}
              <span className="file-name-preview">{pendingFile.name}</span>
              <button
                type="button"
                className="remove-attachment-btn"
                onClick={clearFile}
                title="Remove file"
              >
                <FaTimes />
              </button>
            </div>
          )}

          <div className="input-row">
            <button
                type="button"
                className="action-btn-icon"
                onClick={() => fileInputRef.current.click()}
                title="Attach a file"
                disabled={isLoading || isVoiceMode}
            >
                <FaPaperclip size={18} />
            </button>

            <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileSelect}
            />

            <button
                type="button"
                className={`action-btn-icon voice-btn ${isListening ? 'listening' : ''}`}
                onClick={handleVoiceInput}
                title="Voice input"
                disabled={isLoading || isSpeaking || isVoiceMode}
            >
                <FaMicrophone size={18} />
            </button>

            <input
                type="text"
                ref={inputRef}
                className="chat-input-field"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isVoiceMode ? (voiceStatus === "listening" ? "Listening..." : voiceStatus === "speaking" ? "Speaking..." : "Speak now...") : pendingFile ? "Add a message..." : "Type your message..."}
                disabled={isLoading || isVoiceMode}
            />

            <button
                type="submit"
                className="action-btn-icon send-btn"
                title="Send message"
                disabled={isLoading || (!input.trim() && !pendingFile) || isVoiceMode}
            >
                <BsArrowUpCircleFill size={24} />
            </button>

            {/* 🔥 Live Voice Mode Button */}
            <button
                type="button"
                className={`live-mode-btn ${isVoiceMode ? 'active' : ''}`}
                onClick={toggleVoiceMode}
                title={isVoiceMode ? "Exit Live Mode" : "Enter Live Mode"}
                disabled={isLoading}
            >
                <BsSoundwave size={18} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}