// src/components/AdminDashboard.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { FaCog } from "@react-icons/all-files/fa/FaCog";
import { FaTicketAlt } from "@react-icons/all-files/fa/FaTicketAlt";
import { FaBug } from "@react-icons/all-files/fa/FaBug";
import { FaLightbulb } from "@react-icons/all-files/fa/FaLightbulb";
import { FaQuestionCircle } from "@react-icons/all-files/fa/FaQuestionCircle";
import { FaEye } from "@react-icons/all-files/fa/FaEye";
import { FaTimes } from "@react-icons/all-files/fa/FaTimes";
import { FaCheck } from "@react-icons/all-files/fa/FaCheck";
import { FaClock } from "@react-icons/all-files/fa/FaClock";
import { FaInbox } from "@react-icons/all-files/fa/FaInbox";
import { FaExclamationCircle } from "@react-icons/all-files/fa/FaExclamationCircle";
import { FaSpinner } from "@react-icons/all-files/fa/FaSpinner";
import { FaCheckCircle } from "@react-icons/all-files/fa/FaCheckCircle";
import { FaUser } from "@react-icons/all-files/fa/FaUser";
import { FaUsers } from "@react-icons/all-files/fa/FaUsers";
import { FaDatabase } from "@react-icons/all-files/fa/FaDatabase";
import { FaServer } from "@react-icons/all-files/fa/FaServer";
import { FaChartBar } from "@react-icons/all-files/fa/FaChartBar";
import { FaEdit } from "@react-icons/all-files/fa/FaEdit";
import { FaSearch } from "@react-icons/all-files/fa/FaSearch";
import { FaSync } from "@react-icons/all-files/fa/FaSync";
import { FaTrash } from "@react-icons/all-files/fa/FaTrash";
import { FaSave } from "@react-icons/all-files/fa/FaSave";
import { FaUserShield } from "@react-icons/all-files/fa/FaUserShield";
import { FaUserGraduate } from "@react-icons/all-files/fa/FaUserGraduate";
import { FaCalendarPlus } from "@react-icons/all-files/fa/FaCalendarPlus";
import { FaLink } from "@react-icons/all-files/fa/FaLink";
import { FaMicrophone } from "@react-icons/all-files/fa/FaMicrophone";
import { FaStop } from "@react-icons/all-files/fa/FaStop";
import { FaFileAlt } from "@react-icons/all-files/fa/FaFileAlt";
import { FaRoad } from "@react-icons/all-files/fa/FaRoad";
import { FaRobot } from "@react-icons/all-files/fa/FaRobot";
import { FaThumbsUp } from "@react-icons/all-files/fa/FaThumbsUp";
import { FaThumbsDown } from "@react-icons/all-files/fa/FaThumbsDown";
import { FaFlag } from "@react-icons/all-files/fa/FaFlag";
import { FaSmile } from "@react-icons/all-files/fa/FaSmile";
import DocumentationViewer from "./DocumentationViewer";
import "./AdminDashboard.css";

import { getApiBase } from "../lib/apiBase";
const API_BASE = getApiBase();

export default function AdminDashboard() {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  // Tab state
  const [activeTab, setActiveTab] = useState("users");

  // Course state
  const [course, setCourse] = useState({
    course_code: "", course_name: "", credits: "", prerequisites: "", offered: "",
  });
  const [message, setMessage] = useState("");
  const [courses, setCourses] = useState([]);
  const [editingCourse, setEditingCourse] = useState(null);

  // Support Tickets State
  const [tickets, setTickets] = useState([]);
  const [ticketStats, setTicketStats] = useState({ total: 0, open: 0, in_progress: 0, resolved: 0 });
  const [ticketFilter, setTicketFilter] = useState("all");
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketLoading, setTicketLoading] = useState(false);

  // Users State
  const [users, setUsers] = useState([]);
  const [userStats, setUserStats] = useState({ total: 0, students: 0, admins: 0, new_this_week: 0, morgan_connected: 0 });
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("all");
  const [usersLoading, setUsersLoading] = useState(false);

  // System Health State
  const [healthStatus, setHealthStatus] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);

  // Knowledge Base State
  const [kbFiles, setKbFiles] = useState([]);
  const [selectedKbFile, setSelectedKbFile] = useState(null);
  const [kbContent, setKbContent] = useState("");
  const [kbLoading, setKbLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [kbSearch, setKbSearch] = useState("");
  const [kbSearchResults, setKbSearchResults] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [highlightTerm, setHighlightTerm] = useState("");

  // Find & Replace State
  const [findText, setFindText] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [matchCount, setMatchCount] = useState(0);
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);
  const [matchedFiles, setMatchedFiles] = useState([]); // Files with matches
  const [showMatchedFiles, setShowMatchedFiles] = useState(false);
  const textareaRef = useRef(null);
  const highlightRef = useRef(null);

  // Analytics State
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Cloud KB State
  const [cloudKbDocs, setCloudKbDocs] = useState([]);
  const [cloudKbLoading, setCloudKbLoading] = useState(false);
  const [cloudKbSelected, setCloudKbSelected] = useState(null);
  const [cloudKbContent, setCloudKbContent] = useState("");
  const [cloudKbEditing, setCloudKbEditing] = useState(false);
  const [cloudKbEditContent, setCloudKbEditContent] = useState("");
  const [cloudKbSyncing, setCloudKbSyncing] = useState(false);
  const [cloudKbUploading, setCloudKbUploading] = useState(false);
  const [cloudKbSearchResults, setCloudKbSearchResults] = useState(null); // null = no search, [] = no results
  const [cloudKbSearching, setCloudKbSearching] = useState(false);
  const cloudKbFileRef = useRef(null);
  const cloudKbSearchTimer = useRef(null);

  // Documentation Viewer State
  const [showDocViewer, setShowDocViewer] = useState(false);
  const [docViewerMode, setDocViewerMode] = useState("docs"); // "docs" or "roadmap"

  // Feedback State
  const [feedbackData, setFeedbackData] = useState([]);
  const [feedbackStats, setFeedbackStats] = useState({ total: 0, helpful: 0, not_helpful: 0, reports: 0, satisfaction_rate: 0 });
  const [feedbackFilter, setFeedbackFilter] = useState("all");
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [selectedFeedback, setSelectedFeedback] = useState(null);

  // ===========================================
  // DATA LOADING FUNCTIONS
  // ===========================================

  const loadCourses = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/curriculum`);
      if (res.ok) {
        const data = await res.json();
        // API returns {degree_info, courses, elective_requirements} - extract just courses array
        setCourses(data.courses || data || []);
      }
    } catch (err) { console.error("Failed to load courses:", err); }
  };

  const loadTickets = async (status = null) => {
    setTicketLoading(true);
    try {
      const url = status && status !== "all" ? `${API_BASE}/api/tickets?status=${status}` : `${API_BASE}/api/tickets`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setTickets(data.tickets || []);
      }
    } catch (err) { console.error("Failed to load tickets:", err); }
    finally { setTicketLoading(false); }
  };

  const loadTicketStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tickets/stats/summary`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setTicketStats(await res.json());
    } catch (err) { console.error("Failed to load ticket stats:", err); }
  };

  const loadUsers = async () => {
    setUsersLoading(true);
    try {
      let url = `${API_BASE}/api/admin/users`;
      const params = new URLSearchParams();
      if (userSearch) params.append("search", userSearch);
      if (userRoleFilter !== "all") params.append("role", userRoleFilter);
      if (params.toString()) url += `?${params.toString()}`;

      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      }
    } catch (err) { console.error("Failed to load users:", err); }
    finally { setUsersLoading(false); }
  };

  const loadUserStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/users/stats`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setUserStats(await res.json());
    } catch (err) { console.error("Failed to load user stats:", err); }
  };

  const loadHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/health`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setHealthStatus(await res.json());
    } catch (err) { console.error("Failed to load health:", err); }
    finally { setHealthLoading(false); }
  };

  const loadKbFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/knowledge-base/files`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setKbFiles(data.files || []);
      }
    } catch (err) { console.error("Failed to load KB files:", err); }
  };

  const loadKbFileContent = async (filename) => {
    setKbLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/knowledge-base/${filename}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setKbContent(JSON.stringify(data.content, null, 2));
      }
    } catch (err) { console.error("Failed to load KB file:", err); }
    finally { setKbLoading(false); }
  };

  const loadAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/analytics`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setAnalytics(await res.json());
    } catch (err) { console.error("Failed to load analytics:", err); }
    finally { setAnalyticsLoading(false); }
  };

  // Cloud KB Functions
  const loadCloudKbDocs = async () => {
    setCloudKbLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/cloud-kb/documents`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setCloudKbDocs(data.documents || []);
      }
    } catch (err) { console.error("Failed to load cloud KB:", err); }
    finally { setCloudKbLoading(false); }
  };

  const loadCloudKbContent = async (doc) => {
    setCloudKbSelected(doc);
    setCloudKbEditing(false);
    setCloudKbContent("Loading...");
    try {
      const res = await fetch(`${API_BASE}/api/admin/cloud-kb/documents/${doc.id}/content?uri=${encodeURIComponent(doc.uri)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCloudKbContent(data.content || "");
      } else {
        setCloudKbContent("Failed to load content.");
      }
    } catch (err) { setCloudKbContent("Error loading content."); }
  };

  const searchCloudKb = async (query) => {
    if (!query || query.length < 2) {
      setCloudKbSearchResults(null);
      return;
    }
    setCloudKbSearching(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/cloud-kb/search?q=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCloudKbSearchResults(data.results || []);
      }
    } catch (err) { console.error("Cloud KB search failed:", err); }
    finally { setCloudKbSearching(false); }
  };

  const handleCloudKbSearch = (value) => {
    setKbSearch(value);
    if (value.length >= 2) {
      setFindText(value);
    } else {
      setFindText("");
    }
    // Debounce the API search
    if (cloudKbSearchTimer.current) clearTimeout(cloudKbSearchTimer.current);
    cloudKbSearchTimer.current = setTimeout(() => searchCloudKb(value), 300);
  };

  const handleCloudKbUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCloudKbUploading(true);
    setMessage("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/admin/cloud-kb/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setMessage("Uploaded: " + (data.message || file.name));
        loadCloudKbDocs();
      } else {
        setMessage("Upload failed: " + (data.detail || "Unknown error"));
      }
    } catch (err) { setMessage("Upload error: " + err.message); }
    finally {
      setCloudKbUploading(false);
      if (cloudKbFileRef.current) cloudKbFileRef.current.value = "";
    }
  };

  const handleCloudKbSave = async () => {
    if (!cloudKbSelected) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/cloud-kb/documents/${cloudKbSelected.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ uri: cloudKbSelected.uri, content: cloudKbEditContent })
      });
      if (res.ok) {
        setMessage("Document updated successfully!");
        setCloudKbContent(cloudKbEditContent);
        setCloudKbEditing(false);
        loadCloudKbDocs();
      } else {
        const data = await res.json();
        setMessage("Save failed: " + (data.detail || "Unknown error"));
      }
    } catch (err) { setMessage("Save error: " + err.message); }
  };

  const handleCloudKbDelete = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename}" from the cloud knowledge base? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/cloud-kb/documents/${doc.id}?uri=${encodeURIComponent(doc.uri)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setMessage("Deleted: " + doc.filename);
        if (cloudKbSelected?.id === doc.id) {
          setCloudKbSelected(null);
          setCloudKbContent("");
        }
        loadCloudKbDocs();
      } else {
        const data = await res.json();
        setMessage("Delete failed: " + (data.detail || "Unknown error"));
      }
    } catch (err) { setMessage("Delete error: " + err.message); }
  };

  const handleCloudKbSync = async () => {
    if (!window.confirm("Re-sync all documents from GCS into the datastore? This may take a few minutes.")) return;
    setCloudKbSyncing(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/cloud-kb/sync`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setMessage(res.ok ? (data.message || "Sync started!") : "Sync failed: " + (data.detail || "Unknown error"));
    } catch (err) { setMessage("Sync error: " + err.message); }
    finally { setCloudKbSyncing(false); }
  };

  const loadFeedbackStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/feedback/stats`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setFeedbackStats(data);
        setFeedbackData(data.recent_reports || []);
      }
    } catch (err) { console.error("Failed to load feedback stats:", err); }
  };

  const loadAllFeedback = async (filterType = null) => {
    setFeedbackLoading(true);
    try {
      let url = `${API_BASE}/api/feedback/all`;
      if (filterType && filterType !== "all") {
        url += `?type=${filterType}`;
      }
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setFeedbackData(data.feedback || []);
      }
    } catch (err) { console.error("Failed to load feedback:", err); }
    finally { setFeedbackLoading(false); }
  };

  const searchKnowledgeBase = async (searchTerm) => {
    if (!searchTerm || searchTerm.length < 2) {
      setKbSearchResults([]);
      setHighlightTerm("");
      setMatchedFiles([]);
      setShowMatchedFiles(false);
      return;
    }
    setHighlightTerm(searchTerm);
    try {
      const res = await fetch(`${API_BASE}/api/admin/knowledge-base/search?q=${encodeURIComponent(searchTerm)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const results = data.results || [];
        setKbSearchResults(results);

        // Extract unique files with match counts
        const fileMap = {};
        results.forEach(r => {
          if (!fileMap[r.filename]) {
            fileMap[r.filename] = { filename: r.filename, matchCount: 0 };
          }
          fileMap[r.filename].matchCount++;
        });
        const files = Object.values(fileMap).sort((a, b) => b.matchCount - a.matchCount);
        setMatchedFiles(files);
        setShowMatchedFiles(files.length > 0);
      }
    } catch (err) { console.error("Failed to search KB:", err); }
  };

  // Voice Search Functions
  const startVoiceSearch = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice search is not supported in your browser. Please use Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      console.log("Voice input:", transcript);

      // Extract search keywords from natural language
      const keywords = extractKeywords(transcript);
      if (keywords) {
        setKbSearch(keywords);
        searchKnowledgeBase(keywords);
      }
    };

    recognition.onerror = (event) => {
      console.error("Voice recognition error:", event.error);
      setIsListening(false);
      if (event.error === 'not-allowed') {
        alert("Microphone access denied. Please allow microphone access to use voice search.");
      }
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  const extractKeywords = (transcript) => {
    // Remove common phrases and extract the key search terms
    const lowerTranscript = transcript.toLowerCase();

    // Common patterns to remove
    const patternsToRemove = [
      /^(can you |please |i want to |i need to |help me )/i,
      /(search for |find |look for |look up |search |find me )/i,
      /('s | the | a | an | to | for | of | in | on | with | and | or )/gi,
      /(phone number|email|address|contact|information|info|details)/gi,
      /(so i can |so we can |that i can |change it|edit it|update it)/gi,
    ];

    let cleaned = lowerTranscript;

    // Extract names or specific terms (capitalized words or quoted text)
    const nameMatch = transcript.match(/(?:for |find |search )([A-Z][a-z]+ [A-Z][a-z]+)/);
    if (nameMatch) {
      return nameMatch[1];
    }

    // Clean up common phrases
    patternsToRemove.forEach(pattern => {
      cleaned = cleaned.replace(pattern, ' ');
    });

    // Clean up and return
    cleaned = cleaned.replace(/\s+/g, ' ').trim();

    // If we got something meaningful, return it
    if (cleaned.length >= 2) {
      return cleaned;
    }

    // Fallback: just use key words from original
    const words = transcript.split(' ').filter(w => w.length > 3);
    return words.slice(0, 3).join(' ');
  };

  const stopVoiceSearch = () => {
    setIsListening(false);
  };

  // Check voice support on mount
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setVoiceSupported(!!SpeechRecognition);
  }, []);

  useEffect(() => {
    loadCourses();
    loadTickets();
    loadTicketStats();
    loadUsers();
    loadUserStats();
  }, []);

  useEffect(() => {
    if (activeTab === "system") loadHealth();
    if (activeTab === "knowledge") loadKbFiles();
    if (activeTab === "analytics") loadAnalytics();
    if (activeTab === "feedback") loadFeedbackStats();
    if (activeTab === "cloud-kb") loadCloudKbDocs();
  }, [activeTab]);

  useEffect(() => {
    loadUsers();
  }, [userSearch, userRoleFilter]);

  // ===========================================
  // ACTION HANDLERS
  // ===========================================

  const updateTicketStatus = async (ticketId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE}/api/tickets/${ticketId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        loadTickets(ticketFilter === "all" ? null : ticketFilter);
        loadTicketStats();
        if (selectedTicket?.id === ticketId) setSelectedTicket(prev => ({ ...prev, status: newStatus }));
      }
    } catch (err) { console.error("Failed to update ticket:", err); }
  };

  const handleAddCourse = async (e) => {
    e.preventDefault();
    setMessage("Adding course...");
    const payload = {
      course_code: course.course_code,
      course_name: course.course_name,
      credits: Number(course.credits),
      prerequisites: course.prerequisites.split(",").map(s => s.trim()).filter(Boolean),
      offered: course.offered.split(",").map(s => s.trim()).filter(Boolean),
    };
    try {
      const res = await fetch(`${API_BASE}/api/curriculum/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      setMessage(`Added ${data.course.course_code}`);
      setCourse({ course_code: "", course_name: "", credits: "", prerequisites: "", offered: "" });
      loadCourses();
    } catch (err) { setMessage(`Error: ${err.message}`); }
  };

  const handleEditCourse = async (e) => {
    e.preventDefault();
    setMessage("Updating course...");
    const payload = {
      course_code: editingCourse.course_code,
      course_name: editingCourse.course_name,
      credits: Number(editingCourse.credits),
      prerequisites: typeof editingCourse.prerequisites === 'string'
        ? editingCourse.prerequisites.split(",").map(s => s.trim()).filter(Boolean)
        : editingCourse.prerequisites || [],
      offered: typeof editingCourse.offered === 'string'
        ? editingCourse.offered.split(",").map(s => s.trim()).filter(Boolean)
        : editingCourse.offered || [],
    };
    try {
      const res = await fetch(`${API_BASE}/api/curriculum/${encodeURIComponent(editingCourse.course_code)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      setMessage(`Updated ${editingCourse.course_code}`);
      setEditingCourse(null);
      loadCourses();
    } catch (err) { setMessage(`Error: ${err.message}`); }
  };

  const handleDeleteCourse = async (code) => {
    if (!window.confirm(`Delete ${code}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/curriculum/delete/${encodeURIComponent(code)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) loadCourses();
    } catch (err) { console.error(err); }
  };

  const handleReingest = async () => {
    setMessage("Re-ingesting data...");
    try {
      const res = await fetch(`${API_BASE}/api/admin/knowledge-base/ingest`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) setMessage("Ingestion completed!");
      else throw new Error(data.detail);
    } catch (err) { setMessage(`Error: ${err.message}`); }
  };

  const handleClearIndex = async () => {
    if (!window.confirm("Clear all vectors from index? This cannot be undone.")) return;
    setMessage("Clearing index...");
    try {
      const res = await fetch(`${API_BASE}/clear-index`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) setMessage("Index cleared!");
      else throw new Error(data.detail);
    } catch (err) { setMessage(`Error: ${err.message}`); }
  };

  const handleUpdateUserRole = async (userId, newRole) => {
    if (!window.confirm(`Change user role to ${newRole}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/users/${userId}/role?new_role=${newRole}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        loadUsers();
        loadUserStats();
      }
    } catch (err) { console.error(err); }
  };

  const handleSaveKbFile = async () => {
    if (!selectedKbFile) return;
    setKbLoading(true);
    try {
      const content = JSON.parse(kbContent);
      const res = await fetch(`${API_BASE}/api/admin/knowledge-base/${selectedKbFile}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(content)
      });
      if (res.ok) {
        alert("File saved successfully!");
        loadKbFiles();
      } else {
        const data = await res.json();
        throw new Error(data.detail);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally { setKbLoading(false); }
  };

  const handleTriggerIngestion = async () => {
    setIngesting(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/knowledge-base/ingest`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) alert("Ingestion completed successfully!");
      else throw new Error(data.detail);
    } catch (err) { alert(`Ingestion failed: ${err.message}`); }
    finally { setIngesting(false); }
  };

  // ===========================================
  // FIND & REPLACE FUNCTIONS
  // ===========================================

  // Count matches when findText changes
  useEffect(() => {
    const content = cloudKbEditing ? cloudKbEditContent : cloudKbContent;
    if (findText && content) {
      const regex = new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      const matches = content.match(regex);
      setMatchCount(matches ? matches.length : 0);
      setCurrentMatchIndex(0);
    } else {
      setMatchCount(0);
      setCurrentMatchIndex(0);
    }
  }, [findText, cloudKbContent, cloudKbEditContent, cloudKbEditing]);

  // Auto-scroll to first match when opening Find & Replace from search
  useEffect(() => {
    const content = cloudKbEditing ? cloudKbEditContent : cloudKbContent;
    if (showFindReplace && findText && content && textareaRef.current) {
      const timer = setTimeout(() => {
        const textarea = textareaRef.current;
        if (textarea) {
          const text = content.toLowerCase();
          const searchTerm = findText.toLowerCase();
          const foundIndex = text.indexOf(searchTerm);
          if (foundIndex !== -1) {
            if (cloudKbEditing) {
              textarea.focus();
              textarea.setSelectionRange(foundIndex, foundIndex + findText.length);
            }
            const lineHeight = 20;
            const linesBeforeMatch = content.substring(0, foundIndex).split('\n').length - 1;
            textarea.scrollTop = Math.max(0, linesBeforeMatch * lineHeight - 100);
            setCurrentMatchIndex(1);
          }
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [showFindReplace, cloudKbContent, cloudKbEditContent, cloudKbEditing]);

  // Get the active content for find/replace (cloud KB editing or viewing)
  const getActiveContent = () => cloudKbEditing ? cloudKbEditContent : cloudKbContent;

  const findNextMatch = () => {
    if (!findText || !textareaRef.current) return;

    const textarea = textareaRef.current;
    const content = getActiveContent();
    const text = content.toLowerCase();
    const searchTerm = findText.toLowerCase();

    let startPos = textarea.selectionEnd || 0;
    let foundIndex = text.indexOf(searchTerm, startPos);
    if (foundIndex === -1) foundIndex = text.indexOf(searchTerm, 0);

    if (foundIndex !== -1) {
      if (cloudKbEditing) {
        textarea.focus();
        textarea.setSelectionRange(foundIndex, foundIndex + findText.length);
      }
      const lineHeight = 20;
      const linesBeforeMatch = content.substring(0, foundIndex).split('\n').length - 1;
      textarea.scrollTop = linesBeforeMatch * lineHeight - 100;
      setCurrentMatchIndex(prev => (prev % matchCount) + 1);
    }
  };

  const findPrevMatch = () => {
    if (!findText || !textareaRef.current) return;

    const textarea = textareaRef.current;
    const content = getActiveContent();
    const text = content.toLowerCase();
    const searchTerm = findText.toLowerCase();

    let startPos = Math.max(0, (textarea.selectionStart || 0) - 1);
    let foundIndex = text.lastIndexOf(searchTerm, startPos);
    if (foundIndex === -1) foundIndex = text.lastIndexOf(searchTerm);

    if (foundIndex !== -1) {
      if (cloudKbEditing) {
        textarea.focus();
        textarea.setSelectionRange(foundIndex, foundIndex + findText.length);
      }
      const lineHeight = 20;
      const linesBeforeMatch = content.substring(0, foundIndex).split('\n').length - 1;
      textarea.scrollTop = linesBeforeMatch * lineHeight - 100;
      setCurrentMatchIndex(prev => prev > 1 ? prev - 1 : matchCount);
    }
  };

  const replaceCurrentMatch = () => {
    if (!findText || !textareaRef.current || !cloudKbEditing) return;

    const textarea = textareaRef.current;
    const selStart = textarea.selectionStart;
    const selEnd = textarea.selectionEnd;
    const selectedText = cloudKbEditContent.substring(selStart, selEnd);

    if (selectedText.toLowerCase() === findText.toLowerCase()) {
      const newContent = cloudKbEditContent.substring(0, selStart) + replaceText + cloudKbEditContent.substring(selEnd);
      setCloudKbEditContent(newContent);
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(selStart + replaceText.length, selStart + replaceText.length);
        findNextMatch();
      }, 10);
    } else {
      findNextMatch();
    }
  };

  const replaceAllMatches = () => {
    if (!findText || !cloudKbEditing) return;
    const regex = new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    const newContent = cloudKbEditContent.replace(regex, replaceText);
    const replacedCount = matchCount;
    setCloudKbEditContent(newContent);
    alert(`Replaced ${replacedCount} occurrence(s)`);
  };

  // ===========================================
  // HELPER FUNCTIONS
  // ===========================================

  const getCategoryIcon = (category) => {
    switch (category) {
      case "bug": return <FaBug size={14} />;
      case "feature": return <FaLightbulb size={14} />;
      case "question": return <FaQuestionCircle size={14} />;
      default: return <FaTicketAlt size={14} />;
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case "open": return "status-open";
      case "in_progress": return "status-progress";
      case "resolved": return "status-resolved";
      case "closed": return "status-closed";
      default: return "";
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric"
    });
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
    });
  };

  // Generate highlighted HTML content for preview
  const getHighlightedContent = () => {
    const content = getActiveContent();
    if (!findText || !content) return content;

    const escapedSearch = findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedSearch})`, 'gi');

    const escaped = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    return escaped.replace(regex, '<mark class="highlight-match">$1</mark>');
  };

  // Sync scroll between highlight preview and textarea
  const handleTextareaScroll = () => {
    if (highlightRef.current && textareaRef.current) {
      highlightRef.current.scrollTop = textareaRef.current.scrollTop;
      highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  const formatBytes = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  // ===========================================
  // RENDER
  // ===========================================

  return (
    <div className="card page-container AdminDashboard">
      <header className="page-header">
        <div className="header-left">
          <FaCog className="page-icon" />
          <h1 className="page-title">Admin Dashboard</h1>
        </div>
        <button className="back-home-btn" onClick={() => navigate("/chat")}>
          <span>Back to Home</span>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </button>
      </header>

      {/* Tab Navigation */}
      <div className="admin-tabs">
        <button className={`admin-tab ${activeTab === "users" ? "active" : ""}`} onClick={() => setActiveTab("users")}>
          <FaUsers size={16} /><span>Users</span>
        </button>
        <button className={`admin-tab ${activeTab === "courses" ? "active" : ""}`} onClick={() => setActiveTab("courses")}>
          <FaCog size={16} /><span>Curriculum</span>
        </button>
        <button className={`admin-tab ${activeTab === "tickets" ? "active" : ""}`} onClick={() => setActiveTab("tickets")}>
          <FaTicketAlt size={16} /><span>Tickets</span>
          {ticketStats.open > 0 && <span className="ticket-badge">{ticketStats.open}</span>}
        </button>
        {/* Old local KB tab removed - replaced by Cloud KB */}
        <button className={`admin-tab ${activeTab === "analytics" ? "active" : ""}`} onClick={() => setActiveTab("analytics")}>
          <FaChartBar size={16} /><span>Analytics</span>
        </button>
        <button className={`admin-tab ${activeTab === "feedback" ? "active" : ""}`} onClick={() => setActiveTab("feedback")}>
          <FaSmile size={16} /><span>Feedback</span>
          {feedbackStats.reports > 0 && <span className="ticket-badge">{feedbackStats.reports}</span>}
        </button>
        <button className={`admin-tab ${activeTab === "cloud-kb" ? "active" : ""}`} onClick={() => setActiveTab("cloud-kb")}>
          <FaRobot size={16} /><span>Cloud KB</span>
        </button>
        <button className={`admin-tab ${activeTab === "system" ? "active" : ""}`} onClick={() => setActiveTab("system")}>
          <FaServer size={16} /><span>System</span>
        </button>
      </div>

      {/* =================== USERS TAB =================== */}
      {activeTab === "users" && (
        <div className="tab-content">
          <div className="ticket-stats">
            <div className="stat-card total">
              <FaUsers className="stat-icon" />
              <span className="stat-number">{userStats.total}</span>
              <span className="stat-label">Total Users</span>
            </div>
            <div className="stat-card open">
              <FaUserGraduate className="stat-icon" />
              <span className="stat-number">{userStats.students}</span>
              <span className="stat-label">Students</span>
            </div>
            <div className="stat-card progress">
              <FaUserShield className="stat-icon" />
              <span className="stat-number">{userStats.admins}</span>
              <span className="stat-label">Admins</span>
            </div>
            <div className="stat-card resolved">
              <FaCalendarPlus className="stat-icon" />
              <span className="stat-number">{userStats.new_this_week}</span>
              <span className="stat-label">New This Week</span>
            </div>
          </div>

          <div className="search-filter-bar">
            <div className="search-box">
              <FaSearch size={14} />
              <input
                type="text"
                placeholder="Search by email, name, or student ID..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
              />
            </div>
            <div className="filter-buttons">
              {["all", "student", "admin"].map((role) => (
                <button
                  key={role}
                  className={`filter-btn ${userRoleFilter === role ? "active" : ""}`}
                  onClick={() => setUserRoleFilter(role)}
                >
                  {role === "all" ? "All" : role.charAt(0).toUpperCase() + role.slice(1)}s
                </button>
              ))}
            </div>
          </div>

          <div className="table-container">
            {usersLoading ? (
              <div className="loading-state">Loading users...</div>
            ) : (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Major</th>
                    <th>Morgan</th>
                    <th>Joined</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.email}</td>
                      <td>{u.name || "-"}</td>
                      <td><span className={`role-badge ${u.role}`}>{u.role}</span></td>
                      <td>{u.major || "-"}</td>
                      <td>{u.morgan_connected ? <FaLink size={14} className="connected" /> : "-"}</td>
                      <td>{formatDate(u.created_at)}</td>
                      <td>
                        <select
                          value={u.role}
                          onChange={(e) => handleUpdateUserRole(u.id, e.target.value)}
                          className="role-select"
                        >
                          <option value="student">Student</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* =================== COURSES TAB =================== */}
      {activeTab === "courses" && (
        <div className="tab-content">
          <section>
            <h2>Add New Course</h2>
            <form onSubmit={handleAddCourse} className="admin-form">
              <input name="course_code" placeholder="Course Code (e.g. COSC 101)" value={course.course_code} onChange={(e) => setCourse({...course, course_code: e.target.value})} required />
              <input name="course_name" placeholder="Course Name" value={course.course_name} onChange={(e) => setCourse({...course, course_name: e.target.value})} required />
              <input name="credits" type="number" placeholder="Credits" value={course.credits} onChange={(e) => setCourse({...course, credits: e.target.value})} required />
              <input name="prerequisites" placeholder="Prerequisites (comma-separated)" value={course.prerequisites} onChange={(e) => setCourse({...course, prerequisites: e.target.value})} />
              <input name="offered" placeholder="Offered Semesters (comma-separated)" value={course.offered} onChange={(e) => setCourse({...course, offered: e.target.value})} />
              <button type="submit" className="action-btn">Add Course</button>
            </form>
          </section>

          <section style={{ marginTop: 32 }}>
            <h2>Existing Courses ({courses.length})</h2>
            <table className="admin-table">
              <thead>
                <tr><th>Code</th><th>Name</th><th>Credits</th><th>Offered</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {courses.map((c) => (
                  <tr key={c.course_code}>
                    <td>{c.course_code}</td>
                    <td>{c.course_name}</td>
                    <td>{c.credits}</td>
                    <td>{Array.isArray(c.offered) ? c.offered.join(", ") : c.offered}</td>
                    <td className="action-cell">
                      <button className="edit-btn-labeled" onClick={() => setEditingCourse({
                        ...c,
                        prerequisites: Array.isArray(c.prerequisites) ? c.prerequisites.join(", ") : c.prerequisites || "",
                        offered: Array.isArray(c.offered) ? c.offered.join(", ") : c.offered || ""
                      })}>
                        <FaEdit size={16} />
                        <span>Edit</span>
                      </button>
                      <button className="delete-btn-labeled" onClick={() => handleDeleteCourse(c.course_code)}>
                        <FaTrash size={16} />
                        <span>Delete</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {message && <p className="message">{message}</p>}
        </div>
      )}

      {/* =================== TICKETS TAB =================== */}
      {activeTab === "tickets" && (
        <div className="tickets-section">
          <div className="ticket-stats">
            <div className="stat-card total"><FaInbox className="stat-icon" /><span className="stat-number">{ticketStats.total}</span><span className="stat-label">Total</span></div>
            <div className="stat-card open"><FaExclamationCircle className="stat-icon" /><span className="stat-number">{ticketStats.open}</span><span className="stat-label">Open</span></div>
            <div className="stat-card progress"><FaSpinner className="stat-icon" /><span className="stat-number">{ticketStats.in_progress}</span><span className="stat-label">In Progress</span></div>
            <div className="stat-card resolved"><FaCheckCircle className="stat-icon" /><span className="stat-number">{ticketStats.resolved}</span><span className="stat-label">Resolved</span></div>
          </div>

          <div className="ticket-filters">
            {["all", "open", "in_progress", "resolved"].map((filter) => (
              <button key={filter} className={`filter-btn ${ticketFilter === filter ? "active" : ""}`}
                onClick={() => { setTicketFilter(filter); loadTickets(filter === "all" ? null : filter); }}>
                {filter === "all" ? "All" : filter.replace("_", " ")}
              </button>
            ))}
          </div>

          <div className="tickets-list">
            {ticketLoading ? <div className="tickets-loading">Loading tickets...</div> : tickets.length === 0 ? <div className="tickets-empty">No tickets found</div> : (
              tickets.map((ticket) => (
                <div key={ticket.id} className="ticket-card">
                  <div className="ticket-header-row">
                    <div className="ticket-category">{getCategoryIcon(ticket.category)}<span>{ticket.category}</span></div>
                    <span className={`ticket-status ${getStatusClass(ticket.status)}`}>{ticket.status.replace("_", " ")}</span>
                  </div>
                  <h3 className="ticket-subject">{ticket.subject}</h3>
                  <p className="ticket-preview">{ticket.description.length > 150 ? ticket.description.slice(0, 150) + "..." : ticket.description}</p>
                  <div className="ticket-footer">
                    <div className="ticket-meta">
                      <span className="ticket-user"><FaUser size={11} />{ticket.user_email || "Unknown"}</span>
                      <span className="ticket-date"><FaClock size={11} />{formatDateTime(ticket.created_at)}</span>
                    </div>
                    <div className="ticket-actions">
                      <button className="view-btn" onClick={() => setSelectedTicket(ticket)} title="View"><FaEye size={14} /></button>
                      {ticket.status === "open" && <button className="progress-btn" onClick={() => updateTicketStatus(ticket.id, "in_progress")} title="In Progress"><FaClock size={14} /></button>}
                      {ticket.status !== "resolved" && <button className="resolve-btn" onClick={() => updateTicketStatus(ticket.id, "resolved")} title="Resolve"><FaCheck size={14} /></button>}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Old local Knowledge Base tab removed - replaced by Cloud KB tab */}

      {/* =================== ANALYTICS TAB =================== */}
      {activeTab === "analytics" && (
        <div className="tab-content">
          {analyticsLoading ? (
            <div className="loading-state">Loading analytics...</div>
          ) : analytics ? (
            <>
              <div className="ticket-stats">
                <div className="stat-card total"><FaUsers className="stat-icon" /><span className="stat-number">{analytics.total_users}</span><span className="stat-label">Total Users</span></div>
                <div className="stat-card open"><FaTicketAlt className="stat-icon" /><span className="stat-number">{analytics.total_tickets}</span><span className="stat-label">Total Tickets</span></div>
                <div className="stat-card progress"><FaExclamationCircle className="stat-icon" /><span className="stat-number">{analytics.open_tickets}</span><span className="stat-label">Open Tickets</span></div>
              </div>

              <div className="analytics-section">
                <h3>User Signups (Last 7 Days)</h3>
                <div className="chart-container">
                  {analytics.signups_by_day?.map((day, i) => (
                    <div key={i} className="chart-bar-wrapper">
                      <div className="chart-bar" style={{ height: `${Math.max(day.count * 30, 5)}px` }}>
                        <span className="chart-value">{day.count}</span>
                      </div>
                      <span className="chart-label">{day.day}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">No analytics data available</div>
          )}
        </div>
      )}

      {/* =================== FEEDBACK TAB =================== */}
      {activeTab === "feedback" && (
        <div className="tab-content">
          {/* Feedback Stats */}
          <div className="ticket-stats">
            <div className="stat-card total">
              <FaSmile className="stat-icon" />
              <span className="stat-number">{feedbackStats.total}</span>
              <span className="stat-label">Total Feedback</span>
            </div>
            <div className="stat-card" style={{ background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)', color: '#166534' }}>
              <FaThumbsUp className="stat-icon" style={{ color: '#22c55e' }} />
              <span className="stat-number" style={{ color: '#166534' }}>{feedbackStats.helpful}</span>
              <span className="stat-label" style={{ color: '#166534' }}>Helpful</span>
            </div>
            <div className="stat-card" style={{ background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)', color: '#991b1b' }}>
              <FaThumbsDown className="stat-icon" style={{ color: '#ef4444' }} />
              <span className="stat-number" style={{ color: '#991b1b' }}>{feedbackStats.not_helpful}</span>
              <span className="stat-label" style={{ color: '#991b1b' }}>Not Helpful</span>
            </div>
            <div className="stat-card" style={{ background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', color: '#92400e' }}>
              <FaFlag className="stat-icon" style={{ color: '#f59e0b' }} />
              <span className="stat-number" style={{ color: '#92400e' }}>{feedbackStats.reports}</span>
              <span className="stat-label" style={{ color: '#92400e' }}>Reports</span>
            </div>
          </div>

          {/* Satisfaction Rate */}
          <div className="satisfaction-card">
            <h3>User Satisfaction Rate</h3>
            <div className="satisfaction-bar-container">
              <div
                className="satisfaction-bar"
                style={{ width: `${feedbackStats.satisfaction_rate || 0}%` }}
              />
            </div>
            <span className="satisfaction-percent">{feedbackStats.satisfaction_rate || 0}%</span>
          </div>

          {/* Recent Reports Section */}
          <div className="feedback-reports-section">
            <h3><FaFlag size={16} /> Recent Reports ({feedbackStats.reports})</h3>
            {feedbackStats.recent_reports && feedbackStats.recent_reports.length > 0 ? (
              <div className="feedback-list">
                {feedbackStats.recent_reports.map((report) => (
                  <div key={report.id} className="feedback-card report">
                    <div className="feedback-header">
                      <span className="feedback-type-badge report">
                        <FaFlag size={12} /> Report
                      </span>
                      <span className="feedback-date">
                        <FaClock size={11} /> {formatDateTime(report.timestamp)}
                      </span>
                    </div>
                    <div className="feedback-message">
                      <strong>Bot Response:</strong>
                      <p>{report.message_preview}</p>
                    </div>
                    {report.details && (
                      <div className="feedback-details">
                        <strong>User's Report:</strong>
                        <p>{report.details}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <FaCheckCircle size={32} style={{ color: '#22c55e', marginBottom: 12 }} />
                <p>No reports yet! Users are happy with the responses.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =================== SYSTEM TAB =================== */}
      {/* =================== CLOUD KB TAB =================== */}
      {activeTab === "cloud-kb" && (
        <div className="tab-content">
          <div className="kb-header">
            <h2>Cloud Knowledge Base</h2>
            <p>Manage documents in the Vertex AI Search datastore. Edit content directly or upload new files.</p>
          </div>

          {/* Search Bar */}
          <div className="kb-search-bar">
            <div className="search-box-with-voice">
              <div className="search-box">
                <FaSearch size={14} />
                <input
                  type="text"
                  placeholder="Search across all cloud KB documents..."
                  value={kbSearch}
                  onChange={(e) => handleCloudKbSearch(e.target.value)}
                />
                {kbSearch && (
                  <button className="clear-search" onClick={() => { setKbSearch(""); setFindText(""); setShowFindReplace(false); setCloudKbSearchResults(null); }}>
                    <FaTimes size={12} />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Search Results Summary */}
          {cloudKbSearchResults !== null && kbSearch && (
            <div className="kb-search-summary">
              <span className="search-summary-text">
                {cloudKbSearching ? "Searching..." : (
                  <>Found matches in <strong>{cloudKbSearchResults.length}</strong> files for "<strong>{kbSearch}</strong>"</>
                )}
              </span>
            </div>
          )}

          {message && <p className="message" style={{ margin: "8px 0" }}>{message}</p>}
          {cloudKbUploading && <div className="loading-state">Uploading document...</div>}

          <div className="kb-layout">
            {/* Document List Sidebar */}
            <div className="kb-sidebar">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h3>{cloudKbSearchResults !== null && kbSearch
                  ? `Matches (${cloudKbSearchResults.length})`
                  : `Documents (${cloudKbDocs.length})`
                }</h3>
                <div style={{ display: "flex", gap: "4px" }}>
                  <button className="action-btn" onClick={loadCloudKbDocs} disabled={cloudKbLoading} title="Refresh" style={{ padding: "4px 8px" }}>
                    <FaSync size={12} className={cloudKbLoading ? "spinning" : ""} />
                  </button>
                  <label className="action-btn" style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "4px", padding: "4px 8px" }} title="Upload new document">
                    <FaCalendarPlus size={12} />
                    <input type="file" ref={cloudKbFileRef} accept=".txt,.pdf,.html,.csv,.json" onChange={handleCloudKbUpload} style={{ display: "none" }} />
                  </label>
                </div>
              </div>
              {cloudKbLoading || cloudKbSearching ? (
                <div className="loading-state">{cloudKbSearching ? "Searching..." : "Loading..."}</div>
              ) : cloudKbSearchResults !== null && kbSearch ? (
                // Show only matched files when searching
                cloudKbSearchResults.length === 0 ? (
                  <div className="empty-state">No matches found</div>
                ) : (
                  cloudKbSearchResults.map((result) => {
                    // Find matching doc from full list to get the id
                    const doc = cloudKbDocs.find(d => d.filename === result.filename) || { id: result.filename, filename: result.filename, uri: result.uri, size: result.size };
                    return (
                      <div
                        key={result.filename}
                        className={`kb-file-item ${cloudKbSelected?.filename === result.filename ? "active" : ""}`}
                        onClick={() => {
                          loadCloudKbContent(doc);
                          setFindText(kbSearch);
                          setShowFindReplace(true);
                        }}
                      >
                        <span className="kb-filename">{result.filename}</span>
                        <span className="match-badge" style={{ background: "#e8f0fe", color: "#1a73e8", borderRadius: "10px", padding: "1px 8px", fontSize: "11px", fontWeight: 600 }}>
                          {result.match_count} {result.match_count === 1 ? "match" : "matches"}
                        </span>
                      </div>
                    );
                  })
                )
              ) : (
                // Show all files when not searching
                cloudKbDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className={`kb-file-item ${cloudKbSelected?.id === doc.id ? "active" : ""}`}
                    onClick={() => loadCloudKbContent(doc)}
                  >
                    <span className="kb-filename">{doc.filename}</span>
                    <span className="kb-filesize">{doc.size > 0 ? formatBytes(doc.size) : ""}</span>
                  </div>
                ))
              )}
            </div>

            {/* Document Editor */}
            <div className="kb-editor">
              {cloudKbSelected ? (
                <>
                  <div className="kb-editor-header">
                    <h3>{cloudKbSelected.filename}</h3>
                    <div className="kb-editor-actions">
                      <button
                        className={`action-btn ${showFindReplace ? "active" : ""}`}
                        onClick={() => setShowFindReplace(!showFindReplace)}
                        title="Find & Replace"
                      >
                        <FaSearch size={14} /> Find & Replace
                      </button>
                      {cloudKbEditing ? (
                        <>
                          <button className="action-btn save-btn" onClick={handleCloudKbSave}>
                            <FaSave size={14} /> Save to Cloud
                          </button>
                          <button className="action-btn" onClick={() => { setCloudKbEditing(false); }}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button className="action-btn" onClick={() => { setCloudKbEditing(true); setCloudKbEditContent(cloudKbContent); }}>
                          <FaEdit size={14} /> Edit
                        </button>
                      )}
                      <button className="action-btn secondary" onClick={handleCloudKbSync} disabled={cloudKbSyncing}>
                        <FaSync size={14} className={cloudKbSyncing ? "spinning" : ""} /> {cloudKbSyncing ? "Syncing..." : "Re-sync"}
                      </button>
                      <button className="action-btn danger" onClick={() => handleCloudKbDelete(cloudKbSelected)} title="Delete this document">
                        <FaTrash size={14} /> Delete
                      </button>
                    </div>
                  </div>

                  {/* Find & Replace Toolbar */}
                  {showFindReplace && (
                    <div className="find-replace-toolbar">
                      <div className="find-replace-row">
                        <label>Find:</label>
                        <input
                          type="text"
                          value={findText}
                          onChange={(e) => setFindText(e.target.value)}
                          placeholder="Search text..."
                          onKeyDown={(e) => e.key === 'Enter' && findNextMatch()}
                        />
                        <span className="match-counter">
                          {matchCount > 0 ? `${currentMatchIndex || 1} of ${matchCount}` : "No matches"}
                        </span>
                        <button onClick={findPrevMatch} disabled={matchCount === 0} title="Previous match">
                          &#9650;
                        </button>
                        <button onClick={findNextMatch} disabled={matchCount === 0} title="Next match">
                          &#9660;
                        </button>
                      </div>
                      {cloudKbEditing && (
                        <div className="find-replace-row">
                          <label>Replace:</label>
                          <input
                            type="text"
                            value={replaceText}
                            onChange={(e) => setReplaceText(e.target.value)}
                            placeholder="Replace with..."
                            onKeyDown={(e) => e.key === 'Enter' && replaceCurrentMatch()}
                          />
                          <button onClick={replaceCurrentMatch} disabled={matchCount === 0} className="replace-btn">
                            Replace
                          </button>
                          <button onClick={replaceAllMatches} disabled={matchCount === 0} className="replace-all-btn">
                            Replace All
                          </button>
                        </div>
                      )}
                      <button className="close-find-replace" onClick={() => setShowFindReplace(false)}>
                        <FaTimes size={12} />
                      </button>
                    </div>
                  )}

                  {cloudKbContent === "Loading..." ? (
                    <div className="loading-state">Loading file...</div>
                  ) : cloudKbEditing ? (
                    <div className="kb-editor-container">
                      {findText && (
                        <div
                          ref={highlightRef}
                          className="kb-highlight-backdrop"
                          dangerouslySetInnerHTML={{ __html: getHighlightedContent() }}
                        />
                      )}
                      <textarea
                        ref={textareaRef}
                        className={`kb-textarea ${findText ? "with-highlights" : ""}`}
                        value={cloudKbEditContent}
                        onChange={(e) => setCloudKbEditContent(e.target.value)}
                        onScroll={handleTextareaScroll}
                        spellCheck={false}
                      />
                    </div>
                  ) : (
                    <div className="kb-editor-container">
                      {findText ? (
                        <div
                          ref={textareaRef}
                          className="kb-textarea"
                          style={{
                            whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "monospace",
                            fontSize: "13px", background: "#f8f9fa", padding: "16px", borderRadius: "6px",
                            border: "1px solid #e0e0e0", overflow: "auto", lineHeight: "1.5",
                            height: "100%", margin: 0
                          }}
                          dangerouslySetInnerHTML={{ __html: getHighlightedContent() }}
                        />
                      ) : (
                        <pre
                          ref={textareaRef}
                          className="kb-textarea"
                          style={{
                            whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "monospace",
                            fontSize: "13px", background: "#f8f9fa", padding: "16px", borderRadius: "6px",
                            border: "1px solid #e0e0e0", overflow: "auto", lineHeight: "1.5",
                            height: "100%", margin: 0
                          }}
                        >
                          {cloudKbContent}
                        </pre>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="kb-placeholder">Select a document to view or edit</div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "system" && (
        <div className="tab-content">
          <div className="system-header">
            <h2>System Health</h2>
            <button className="action-btn" onClick={loadHealth}><FaSync size={14} /> Refresh</button>
          </div>

          {healthLoading ? (
            <div className="loading-state">Checking system health...</div>
          ) : healthStatus ? (
            <>
              <div className="health-cards">
                <div className={`health-card ${healthStatus.database?.status === "connected" ? "healthy" : "error"}`}>
                  <FaDatabase className="health-icon" />
                  <div className="health-info">
                    <h4>Database (RDS)</h4>
                    <span className="health-status">{healthStatus.database?.status}</span>
                    <p>{healthStatus.database?.message}</p>
                  </div>
                </div>

                <div className={`health-card ${healthStatus.pinecone?.status === "connected" ? "healthy" : healthStatus.pinecone?.status === "not_configured" ? "warning" : "error"}`}>
                  <FaServer className="health-icon" />
                  <div className="health-info">
                    <h4>Pinecone Vector DB</h4>
                    <span className="health-status">{healthStatus.pinecone?.status}</span>
                    <p>{healthStatus.pinecone?.message}</p>
                    {healthStatus.vector_count > 0 && <p className="vector-count">{healthStatus.vector_count.toLocaleString()} vectors</p>}
                  </div>
                </div>

                <div className={`health-card ${healthStatus.openai?.status === "configured" ? "healthy" : "warning"}`}>
                  <FaLightbulb className="health-icon" />
                  <div className="health-info">
                    <h4>OpenAI API</h4>
                    <span className="health-status">{healthStatus.openai?.status}</span>
                    <p>{healthStatus.openai?.message}</p>
                  </div>
                </div>
              </div>

              <div className="system-actions">
                <h3>Quick Actions</h3>
                <div className="action-buttons">
                  <button className="action-btn" onClick={handleReingest}><FaSync size={14} /> Re-ingest Data</button>
                  <button className="action-btn danger" onClick={handleClearIndex}><FaTrash size={14} /> Clear Index</button>
                </div>
                {message && <p className="message">{message}</p>}
              </div>
            </>
          ) : (
            <div className="empty-state">Unable to load health status</div>
          )}
        </div>
      )}

      {/* =================== EDIT COURSE MODAL =================== */}
      {editingCourse && (
        <div className="ticket-modal-overlay" onClick={() => setEditingCourse(null)}>
          <div className="ticket-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit Course: {editingCourse.course_code}</h2>
              <button className="modal-close" onClick={() => setEditingCourse(null)}><FaTimes size={18} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleEditCourse} className="edit-form">
                <div className="form-group">
                  <label>Course Code</label>
                  <input value={editingCourse.course_code} disabled />
                </div>
                <div className="form-group">
                  <label>Course Name</label>
                  <input value={editingCourse.course_name} onChange={(e) => setEditingCourse({...editingCourse, course_name: e.target.value})} required />
                </div>
                <div className="form-group">
                  <label>Credits</label>
                  <input type="number" value={editingCourse.credits} onChange={(e) => setEditingCourse({...editingCourse, credits: e.target.value})} required />
                </div>
                <div className="form-group">
                  <label>Prerequisites (comma-separated)</label>
                  <input value={editingCourse.prerequisites} onChange={(e) => setEditingCourse({...editingCourse, prerequisites: e.target.value})} />
                </div>
                <div className="form-group">
                  <label>Offered Semesters (comma-separated)</label>
                  <input value={editingCourse.offered} onChange={(e) => setEditingCourse({...editingCourse, offered: e.target.value})} />
                </div>
                <div className="modal-actions">
                  <button type="button" className="action-btn secondary" onClick={() => setEditingCourse(null)}>Cancel</button>
                  <button type="submit" className="action-btn">Save Changes</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* =================== TICKET DETAIL MODAL =================== */}
      {selectedTicket && (
        <div className="ticket-modal-overlay" onClick={() => setSelectedTicket(null)}>
          <div className="ticket-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-row">{getCategoryIcon(selectedTicket.category)}<h2>{selectedTicket.subject}</h2></div>
              <button className="modal-close" onClick={() => setSelectedTicket(null)}><FaTimes size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="modal-meta">
                <span className={`ticket-status ${getStatusClass(selectedTicket.status)}`}>{selectedTicket.status.replace("_", " ")}</span>
                <span className="ticket-user"><FaUser size={12} />{selectedTicket.user_email || "Unknown"}</span>
                <span className="ticket-date"><FaClock size={12} />{formatDateTime(selectedTicket.created_at)}</span>
              </div>
              <div className="modal-description"><h4>Description</h4><p>{selectedTicket.description}</p></div>
              {selectedTicket.attachment_name && <div className="modal-attachment"><h4>Attachment</h4><span>{selectedTicket.attachment_name}</span></div>}
              <div className="modal-actions">
                <h4>Update Status</h4>
                <div className="status-buttons">
                  <button className={`status-btn open ${selectedTicket.status === "open" ? "active" : ""}`} onClick={() => updateTicketStatus(selectedTicket.id, "open")}>Open</button>
                  <button className={`status-btn progress ${selectedTicket.status === "in_progress" ? "active" : ""}`} onClick={() => updateTicketStatus(selectedTicket.id, "in_progress")}>In Progress</button>
                  <button className={`status-btn resolved ${selectedTicket.status === "resolved" ? "active" : ""}`} onClick={() => updateTicketStatus(selectedTicket.id, "resolved")}>Resolved</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Admin Footer with Documentation Icons */}
      <div className="admin-footer">
        <button
          className="footer-icon-btn"
          onClick={() => { setDocViewerMode("technical"); setShowDocViewer(true); }}
          title="View Technical Documentation"
        >
          <FaFileAlt size={20} />
          <span>Docs</span>
        </button>
        <button
          className="footer-icon-btn"
          onClick={() => { setDocViewerMode("roadmap"); setShowDocViewer(true); }}
          title="View Development Roadmap"
        >
          <FaRoad size={20} />
          <span>Roadmap</span>
        </button>
        <button
          className="footer-icon-btn agents"
          onClick={() => { setDocViewerMode("agents"); setShowDocViewer(true); }}
          title="View AI Agents Plan"
        >
          <FaRobot size={20} />
          <span>AI Agents</span>
        </button>
      </div>

      {/* Documentation Viewer Modal */}
      <DocumentationViewer
        isOpen={showDocViewer}
        onClose={() => setShowDocViewer(false)}
        darkMode={true}
        mode={docViewerMode}
      />
    </div>
  );
}
