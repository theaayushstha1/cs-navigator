import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { FaMicrophone } from "@react-icons/all-files/fa/FaMicrophone";
import { FaPaperclip } from "@react-icons/all-files/fa/FaPaperclip";
import { FaVolumeUp } from "@react-icons/all-files/fa/FaVolumeUp";
import { FaTimes } from "@react-icons/all-files/fa/FaTimes";
import { FaStop } from "@react-icons/all-files/fa/FaStop";
import { FaEllipsisV } from "@react-icons/all-files/fa/FaEllipsisV";
import { FaThumbsUp } from "@react-icons/all-files/fa/FaThumbsUp";
import { FaThumbsDown } from "@react-icons/all-files/fa/FaThumbsDown";
import { FaFlag } from "@react-icons/all-files/fa/FaFlag";
import { BsSoundwave, BsArrowUpCircleFill } from "react-icons/bs";

// 🔥 Icons for File Cards
import { FaFile } from "@react-icons/all-files/fa/FaFile";
import { FaFilePdf } from "@react-icons/all-files/fa/FaFilePdf";
import { FaFileWord } from "@react-icons/all-files/fa/FaFileWord";
import { FaFileImage } from "@react-icons/all-files/fa/FaFileImage";

import "./Chatbox.css";

// Featured questions that showcase chatbot capabilities
const FEATURED_QUESTIONS = [
  "What courses should I take next semester if I'm interested in AI/ML?",
  "Can you recommend a study plan for the cybersecurity track?",
  "What are the prerequisites for COSC 450 Operating Systems?",
  "Who are the professors in the CS department and what do they teach?",
  "What internship and co-op opportunities are available for CS majors?",
  "How do I apply for graduation and what requirements do I need?",
  "What research labs and projects can I join in the CS department?",
  "What is the difference between a B.S. and B.A. in Computer Science?",
];

import { getApiBase } from "../lib/apiBase";
const API_BASE = getApiBase();

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
  const [suggestions, setSuggestions] = useState(FEATURED_QUESTIONS);
  const [suggestionsLoading, setSuggestionsLoading] = useState(true);

  // 🔥 Voice Mode State
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("idle"); // idle, listening, processing, speaking

  // 🔥 Feedback State
  const [feedbackMenuOpen, setFeedbackMenuOpen] = useState(null); // index of message with open menu
  const [feedbackGiven, setFeedbackGiven] = useState({}); // {messageIndex: 'helpful' | 'not_helpful' | 'reported'}
  const [reportModal, setReportModal] = useState(null); // index of message being reported
  const [reportText, setReportText] = useState("");

  // 🔥 Thinking status - cycles through messages like ChatGPT/Claude
  const [thinkingStatus, setThinkingStatus] = useState("Searching knowledge base");
  const [thinkingTimer, setThinkingTimer] = useState(0);
  const thinkingMessages = [
    "Searching knowledge base",
    "Analyzing your question",
    "Reviewing course catalog",
    "Checking department info",
    "Preparing response"
  ];

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

  // 6. Fetch randomized featured questions from backend
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (messages.length > 0) {
        setSuggestionsLoading(false);
        return;
      }
      try {
        const response = await fetch(`${API_BASE}/api/popular-questions`);
        if (response.ok) {
          const data = await response.json();
          if (data.questions && data.questions.length > 0) {
            setSuggestions(data.questions.slice(0, 8));
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

  // 8. Cycle through thinking messages and timer while loading
  useEffect(() => {
    if (!isLoading || messages.some(m => m.isStreaming)) {
      setThinkingTimer(0);
      return;
    }

    let index = 0;
    setThinkingStatus(thinkingMessages[0]);
    setThinkingTimer(0);

    // Status message cycle
    const statusInterval = setInterval(() => {
      index = (index + 1) % thinkingMessages.length;
      setThinkingStatus(thinkingMessages[index]);
    }, 2500);

    // Timer countdown
    const timerInterval = setInterval(() => {
      setThinkingTimer(prev => prev + 1);
    }, 1000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(timerInterval);
    };
  }, [isLoading, messages]);

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

  // 🔥 FEEDBACK HANDLERS
  const handleFeedback = async (messageIndex, feedbackType, messageText) => {
    const token = localStorage.getItem("token");

    try {
      await fetch(`${API_BASE}/api/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          message_text: messageText,
          feedback_type: feedbackType, // 'helpful', 'not_helpful', 'report'
          report_details: feedbackType === 'report' ? reportText : null,
          session_id: sessionId || "default"
        })
      });

      // Update local state to show feedback was given
      setFeedbackGiven(prev => ({ ...prev, [messageIndex]: feedbackType }));
      setFeedbackMenuOpen(null);

      if (feedbackType === 'report') {
        setReportModal(null);
        setReportText("");
      }
    } catch (error) {
      console.error("Failed to submit feedback:", error);
    }
  };

  const openReportModal = (messageIndex) => {
    setReportModal(messageIndex);
    setFeedbackMenuOpen(null);
  };

  const closeReportModal = () => {
    setReportModal(null);
    setReportText("");
  };

  // Close feedback menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (feedbackMenuOpen !== null && !e.target.closest('.feedback-menu-container')) {
        setFeedbackMenuOpen(null);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [feedbackMenuOpen]);

  // 🔥 MAIN SEND LOGIC - With Streaming Support
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

        // 3. Add placeholder bot message for streaming
        const botMessageIndex = messages.length + 1; // Index after user message
        const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setMessages((prev) => [...prev, { text: "", sender: "bot", time, isStreaming: true }]);

        // 4. Stream from Chat API using fetch with ReadableStream
        const res = await fetch(`${API_BASE}/chat/stream`, {
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
            setMessages((prev) => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                    ...newMessages[newMessages.length - 1],
                    text: "Session expired. Please log in again.",
                    isStreaming: false
                };
                return newMessages;
            });
            setIsLoading(false);
            return;
        }

        if (!res.ok) throw new Error(res.statusText);

        // 5. Read SSE stream
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || ""; // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const event = JSON.parse(line.slice(6));

                        if (event.type === "status") {
                            // Real-time status from ADK tool calls
                            setThinkingStatus(event.content);
                        } else if (event.type === "chunk") {
                            fullText += event.content;
                            // Update the streaming message
                            setMessages((prev) => {
                                const newMessages = [...prev];
                                newMessages[newMessages.length - 1] = {
                                    ...newMessages[newMessages.length - 1],
                                    text: fullText
                                };
                                return newMessages;
                            });
                        } else if (event.type === "done") {
                            // Finalize the message
                            fullText = event.content || fullText;
                            setMessages((prev) => {
                                const newMessages = [...prev];
                                newMessages[newMessages.length - 1] = {
                                    ...newMessages[newMessages.length - 1],
                                    text: fullText,
                                    isStreaming: false
                                };
                                return newMessages;
                            });
                        } else if (event.type === "error") {
                            setMessages((prev) => {
                                const newMessages = [...prev];
                                newMessages[newMessages.length - 1] = {
                                    ...newMessages[newMessages.length - 1],
                                    text: event.content || "An error occurred.",
                                    isStreaming: false
                                };
                                return newMessages;
                            });
                        }
                    } catch (parseErr) {
                        console.warn("SSE parse error:", parseErr);
                    }
                }
            }
        }

        // Finalize if stream ended without explicit done
        setMessages((prev) => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            if (lastMsg.isStreaming) {
                newMessages[newMessages.length - 1] = {
                    ...lastMsg,
                    isStreaming: false
                };
            }
            return newMessages;
        });

    } catch (err) {
        console.error("Send error:", err);
        setMessages((prev) => {
            const newMessages = [...prev];
            if (newMessages.length > 0 && newMessages[newMessages.length - 1].sender === "bot") {
                newMessages[newMessages.length - 1] = {
                    ...newMessages[newMessages.length - 1],
                    text: "Error: " + err.message,
                    isStreaming: false
                };
            } else {
                newMessages.push({ text: "Error: " + err.message, sender: "bot", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) });
            }
            return newMessages;
        });
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
                <div className="message-bubble-wrapper">
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

                    {/* Streaming indicator - show status when no text, dots when text is streaming */}
                    {msg.isStreaming && !msg.text && (
                      <div className="inline-thinking">
                        <div className="thinking-orb"><div className="orb-pulse"></div></div>
                        <span className="thinking-text-shimmer">{thinkingStatus}</span>
                      </div>
                    )}
                    {msg.isStreaming && msg.text && (
                      <span className="streaming-cursor">
                        <span className="stream-dot"></span>
                        <span className="stream-dot"></span>
                        <span className="stream-dot"></span>
                      </span>
                    )}

                    {msg.sender === "bot" && !msg.isStreaming && (
                      <button
                        className="tts-btn"
                        onClick={() => speak(msg.text)}
                        title="Read response aloud"
                      >
                        <FaVolumeUp size={14}/>
                      </button>
                    )}
                  </div>

                  {/* 🔥 FEEDBACK MENU - Right side of bot messages */}
                  {msg.sender === "bot" && (
                    <div className="feedback-menu-container">
                      {/* Show feedback status if already given */}
                      {feedbackGiven[i] ? (
                        <div className={`feedback-status feedback-status--${feedbackGiven[i]}`}>
                          {feedbackGiven[i] === 'helpful' && <FaThumbsUp size={12} />}
                          {feedbackGiven[i] === 'not_helpful' && <FaThumbsDown size={12} />}
                          {feedbackGiven[i] === 'report' && <FaFlag size={12} />}
                        </div>
                      ) : (
                        <>
                          {/* Three-dot menu button - visible on hover */}
                          <button
                            className="feedback-menu-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              setFeedbackMenuOpen(feedbackMenuOpen === i ? null : i);
                            }}
                            title="Rate this response"
                          >
                            <FaEllipsisV size={14} />
                          </button>

                          {/* Dropdown menu */}
                          {feedbackMenuOpen === i && (
                            <div className="feedback-dropdown">
                              <button
                                className="feedback-option feedback-option--helpful"
                                onClick={() => handleFeedback(i, 'helpful', msg.text)}
                              >
                                <FaThumbsUp size={14} />
                                <span>Helpful</span>
                              </button>
                              <button
                                className="feedback-option feedback-option--not-helpful"
                                onClick={() => handleFeedback(i, 'not_helpful', msg.text)}
                              >
                                <FaThumbsDown size={14} />
                                <span>Not Helpful</span>
                              </button>
                              <button
                                className="feedback-option feedback-option--report"
                                onClick={() => openReportModal(i)}
                              >
                                <FaFlag size={14} />
                                <span>Report Issue</span>
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="timestamp">{msg.time}</div>
              </div>
            </div>
          ))
        )}
        
        {/* Thinking Indicator - ChatGPT/Claude style with shimmer */}
        {isLoading && !messages.some(m => m.isStreaming) && (
          <div className="message bot">
            <img src="/bot_avatar.jpg" alt="Bot" className="avatar-img" />
            <div className="message-content">
              <div className="message-bubble thinking-bubble">
                <div className="thinking-status">
                  <div className="thinking-orb">
                    <div className="orb-pulse"></div>
                  </div>
                  <span className="thinking-text-shimmer">{thinkingStatus}</span>
                  <span className="thinking-timer">{thinkingTimer}s</span>
                </div>
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

        {/* 🔥 REPORT MODAL */}
        {reportModal !== null && (
          <div className="report-modal-overlay" onClick={closeReportModal}>
            <div className="report-modal" onClick={(e) => e.stopPropagation()}>
              <div className="report-modal-header">
                <h3>Report an Issue</h3>
                <button className="report-modal-close" onClick={closeReportModal}>
                  <FaTimes size={16} />
                </button>
              </div>
              <div className="report-modal-body">
                <p>Help us improve! What was wrong with this response?</p>
                <textarea
                  className="report-textarea"
                  placeholder="Describe the issue (e.g., incorrect information, unhelpful response, inappropriate content...)"
                  value={reportText}
                  onChange={(e) => setReportText(e.target.value)}
                  rows={4}
                />
              </div>
              <div className="report-modal-footer">
                <button className="report-cancel-btn" onClick={closeReportModal}>
                  Cancel
                </button>
                <button
                  className="report-submit-btn"
                  onClick={() => handleFeedback(reportModal, 'report', messages[reportModal]?.text)}
                  disabled={!reportText.trim()}
                >
                  Submit Report
                </button>
              </div>
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