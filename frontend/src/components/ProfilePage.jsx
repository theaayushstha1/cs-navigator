// src/components/ProfilePage.jsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { FaArrowLeft } from "@react-icons/all-files/fa/FaArrowLeft";
import { FaUser } from "@react-icons/all-files/fa/FaUser";
import { FaEnvelope } from "@react-icons/all-files/fa/FaEnvelope";
import { FaLock } from "@react-icons/all-files/fa/FaLock";
import { FaCamera } from "@react-icons/all-files/fa/FaCamera";
import { FaUniversity } from "@react-icons/all-files/fa/FaUniversity";
import { FaIdCard } from "@react-icons/all-files/fa/FaIdCard";
import { FaGraduationCap } from "@react-icons/all-files/fa/FaGraduationCap";
import { FaCheckCircle } from "@react-icons/all-files/fa/FaCheckCircle";
import { FaTimes } from "@react-icons/all-files/fa/FaTimes";
import { FaSync } from "@react-icons/all-files/fa/FaSync";
import { FaBookmark } from "@react-icons/all-files/fa/FaBookmark";
import { FaChartLine } from "@react-icons/all-files/fa/FaChartLine";
import { FaBook } from "@react-icons/all-files/fa/FaBook";
import { FaExternalLinkAlt } from "@react-icons/all-files/fa/FaExternalLinkAlt";
import { FaCog } from "@react-icons/all-files/fa/FaCog";
import { FaShieldAlt } from "@react-icons/all-files/fa/FaShieldAlt";
import "./ProfilePage.css";

import { getApiBase } from "../lib/apiBase";
const API_BASE = getApiBase();

export default function ProfilePage({ userEmail, onLogout }) {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pendingResearch, setPendingResearch] = useState(0);
  const [message, setMessage] = useState({ type: "", text: "" });
  
  const [profile, setProfile] = useState({
    name: "",
    email: userEmail || "",
    studentId: "",
    major: "Computer Science",
    profilePicture: "/user_icon.webp",
    morganConnected: false,
    role: "student"
  });

  const [passwords, setPasswords] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });

  const [showPasswordForm, setShowPasswordForm] = useState(false);

  // Bookmarklet ref - React blocks javascript: URLs, so we set href via DOM
  const bookmarkletRef = useRef(null);
  const setBookmarkletHref = useCallback((node) => {
    if (node) {
      node.setAttribute('href', getBookmarkletCode());
      bookmarkletRef.current = node;
    }
  }, []);

  // DegreeWorks Modal State
  const [showMorganModal, setShowMorganModal] = useState(false);
  const [degreeWorksData, setDegreeWorksData] = useState(null);
  const [syncStep, setSyncStep] = useState(1); // 1=instructions, 2=syncing, 3=success

  // Banner Auto-Sync State
  const [bannerCreds, setBannerCreds] = useState({ username: "", password: "" });
  const [bannerSyncing, setBannerSyncing] = useState(false);
  const [bannerProgress, setBannerProgress] = useState([]);
  const [bannerSummary, setBannerSummary] = useState(null);
  const [bannerError, setBannerError] = useState("");

  // Fetch profile data on mount
  useEffect(() => {
    fetchProfile();
    fetchDegreeWorksData();
    // Fetch pending research suggestions count for admin badge
    const token = localStorage.getItem("token");
    if (token) {
      fetch(`${API_BASE}/api/admin/research/stats`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setPendingResearch(d.pending_suggestions || 0); })
        .catch(() => {});
    }
  }, []);

  const fetchProfile = async () => {
  try {
    const token = localStorage.getItem("token");
    const response = await fetch(`${API_BASE}/api/profile`, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });

    if (response.ok) {
      const data = await response.json();

      // 🔥 FIX: Handle base64 data URLs, full URLs, and relative paths
      if (data.profilePicture) {
        if (data.profilePicture.startsWith('data:')) {
          // Base64 data URL - use directly
        } else if (data.profilePicture.startsWith('http')) {
          // Full URL - use directly
        } else {
          // Relative path - prepend API base
          data.profilePicture = `${API_BASE}${data.profilePicture}`;
        }
      }

      console.log("Profile loaded:", data);
      setProfile(data);
    }
  } catch (error) {
    console.error("Error fetching profile:", error);
  }
};


  const fetchDegreeWorksData = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/degreeworks`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        if (data.connected && data.data) {
          setDegreeWorksData(data.data);
        }
      }
    } catch (error) {
      console.error("Error fetching DegreeWorks data:", error);
    }
  };

  const handleDisconnectMorgan = async () => {
    if (!window.confirm("Are you sure you want to disconnect your DegreeWorks data? This will remove all synced academic data.")) {
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/degreeworks/disconnect`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (response.ok) {
        setProfile({ ...profile, morganConnected: false });
        setDegreeWorksData(null);
        setMessage({ type: "success", text: "DegreeWorks data disconnected successfully." });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Failed to disconnect. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  // Generate the bookmarklet code - tiny loader that fetches the full script from the server
  // This avoids Chrome's ~2KB URL length limit for bookmarklets
  const getBookmarkletCode = () => {
    const token = localStorage.getItem("token");
    return `javascript:void(function(){var s=document.createElement('script');s.src='${API_BASE}/api/bookmarklet.js?token=${token}&api=${encodeURIComponent(API_BASE)}';document.body.appendChild(s)}())`;
  };

  const copyBookmarklet = () => {
    navigator.clipboard.writeText(getBookmarkletCode());
    setMessage({ type: "success", text: "Bookmarklet code copied! Paste it as the URL of a new bookmark." });
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: profile.name,
          studentId: profile.studentId,
          major: profile.major
        })
      });

      if (response.ok) {
        setMessage({ type: "success", text: "Profile updated successfully!" });
        setIsEditing(false);
        fetchProfile();
      } else {
        const error = await response.json();
        setMessage({ type: "error", text: error.detail || "Failed to update profile" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (passwords.newPassword !== passwords.confirmPassword) {
      setMessage({ type: "error", text: "New passwords don't match!" });
      return;
    }

    if (passwords.newPassword.length < 6) {
      setMessage({ type: "error", text: "Password must be at least 6 characters" });
      return;
    }

    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          currentPassword: passwords.currentPassword,
          newPassword: passwords.newPassword
        })
      });

      if (response.ok) {
        setMessage({ type: "success", text: "Password changed successfully!" });
        setPasswords({ currentPassword: "", newPassword: "", confirmPassword: "" });
        setShowPasswordForm(false);
      } else {
        const error = await response.json();
        setMessage({ type: "error", text: error.detail || "Failed to change password" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleProfilePictureUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("profilePicture", file);

    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/upload-profile-picture`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setProfile({ ...profile, profilePicture: data.url });
        setMessage({ type: "success", text: "Profile picture updated! Refreshing..." });
        
        // 🔥 AUTO-REFRESH to update navbar
        setTimeout(() => window.location.reload(), 1000);
      } else {
        const error = await response.json();
        setMessage({ type: "error", text: error.detail || "Failed to upload picture" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleConnectMorgan = () => {
    setSyncStep(1);
    setShowMorganModal(true);
  };

  const openMorganPortal = () => {
    window.open("https://morgan.edu", "_blank");
  };

  const handleBannerSync = async () => {
    if (!bannerCreds.username || !bannerCreds.password) {
      setBannerError("Please enter your MSU username and password.");
      return;
    }

    setBannerSyncing(true);
    setBannerProgress([]);
    setBannerSummary(null);
    setBannerError("");

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/banner/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          username: bannerCreds.username,
          password: bannerCreds.password
        })
      });

      if (!response.ok && response.status === 429) {
        setBannerError("Rate limit exceeded. Maximum 3 syncs per hour.");
        setBannerSyncing(false);
        return;
      }

      // Read SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));

            if (event.type === "progress") {
              setBannerProgress(prev => [...prev, event.detail]);
            } else if (event.type === "done") {
              setBannerSummary(event.summary);
              setProfile(prev => ({ ...prev, morganConnected: true }));
              fetchDegreeWorksData();
              fetchProfile();
            } else if (event.type === "error") {
              setBannerError(event.detail);
            }
          } catch (e) {
            // Skip malformed SSE lines
          }
        }
      }
    } catch (error) {
      setBannerError("Connection failed: " + error.message);
    } finally {
      setBannerSyncing(false);
      // Clear password from memory
      setBannerCreds(prev => ({ ...prev, password: "" }));
    }
  };

  // Manual entry state
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [showPdfUpload, setShowPdfUpload] = useState(false);
  const [pdfUploading, setPdfUploading] = useState(false);

  // 🔥 Ref for PDF file input (more reliable than label htmlFor)
  const pdfInputRef = React.useRef(null);

  const [manualData, setManualData] = useState({
    student_name: "",
    classification: "Freshman",
    degree_program: "Bachelor of Science in Computer Science",
    overall_gpa: "",
    total_credits_earned: "",
    credits_remaining: ""
  });

  const handleManualSubmit = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/api/degreeworks/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          ...manualData,
          overall_gpa: manualData.overall_gpa ? parseFloat(manualData.overall_gpa) : null,
          total_credits_earned: manualData.total_credits_earned ? parseFloat(manualData.total_credits_earned) : null,
          credits_remaining: manualData.credits_remaining ? parseFloat(manualData.credits_remaining) : null
        })
      });

      if (response.ok) {
        setProfile({ ...profile, morganConnected: true });
        setMessage({ type: "success", text: "Academic data saved successfully!" });
        setShowMorganModal(false);
        setShowManualEntry(false);
        fetchDegreeWorksData();
      } else {
        setMessage({ type: "error", text: "Failed to save data. Please try again." });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handlePdfUpload = async (e) => {
    console.log("📄 PDF Upload triggered", e);
    const file = e.target.files?.[0];
    console.log("📄 Selected file:", file);

    if (!file) {
      console.log("❌ No file selected");
      return;
    }

    const allowedExts = ['.pdf', '.docx'];
    const fileName = file.name.toLowerCase();
    if (!allowedExts.some(ext => fileName.endsWith(ext))) {
      setMessage({ type: "error", text: "Please upload a PDF or DOCX file." });
      return;
    }

    console.log("📄 Starting upload for:", file.name, "Size:", file.size);
    setPdfUploading(true);
    setMessage({ type: "", text: "" });

    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem("token");
      console.log("📄 Uploading to:", `${API_BASE}/api/degreeworks/upload-pdf`);

      const response = await fetch(`${API_BASE}/api/degreeworks/upload-pdf`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      });

      console.log("📄 Response status:", response.status);
      const data = await response.json();
      console.log("📄 Response data:", data);

      if (response.ok && data.success) {
        setProfile({ ...profile, morganConnected: true });
        setMessage({ type: "success", text: "DegreeWorks PDF uploaded successfully! Your academic data is now available." });
        setShowMorganModal(false);
        setShowPdfUpload(false);
        fetchDegreeWorksData();
      } else {
        console.error("❌ Upload failed:", data);
        setMessage({ type: "error", text: data.detail || data.message || "Failed to parse PDF. Please try manual entry instead." });
      }
    } catch (error) {
      console.error("❌ Upload error:", error);
      setMessage({ type: "error", text: "Upload failed: " + error.message });
    } finally {
      setPdfUploading(false);
      // Reset the input so the same file can be selected again
      if (pdfInputRef.current) {
        pdfInputRef.current.value = "";
      }
    }
  };

  // 🔥 Direct click handler for PDF upload button
  const triggerPdfUpload = () => {
    console.log("📄 Triggering PDF file picker");
    if (pdfInputRef.current) {
      pdfInputRef.current.click();
    }
  };

  return (
    <div className="profile-page">
      <div className="profile-header">
        <button className="back-button" onClick={() => navigate("/")}>
          <FaArrowLeft /> Back to Chat
        </button>
        <h1>Profile Settings</h1>
      </div>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="profile-container">
        {/* Profile Picture Section */}
        <div className="profile-picture-section">
          <div className="profile-picture-wrapper">
            <img 
              src={profile.profilePicture} 
              alt="Profile" 
              className="profile-picture"
              onError={(e) => e.target.src = "/user_icon.webp"}
            />
            <label className="upload-overlay">
              <FaCamera size={24} />
              <input 
                type="file" 
                accept="image/*" 
                onChange={handleProfilePictureUpload}
                style={{ display: "none" }}
              />
            </label>
          </div>
          <h2>{profile.name || profile.email}</h2>
          <p className="profile-email">{profile.email}</p>
        </div>

        {/* Profile Information */}
        <div className="profile-section">
          <div className="section-header">
            <h3>Personal Information</h3>
            {!isEditing && (
              <button className="edit-btn" onClick={() => setIsEditing(true)}>
                Edit
              </button>
            )}
          </div>

          <form onSubmit={handleUpdateProfile}>
            <div className="form-group">
              <label>
                <FaUser /> Full Name
              </label>
              <input
                type="text"
                value={profile.name || ""}
                onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                disabled={!isEditing}
                placeholder="Enter your full name"
              />
            </div>

            <div className="form-group">
              <label>
                <FaEnvelope /> Email
              </label>
              <input
                type="email"
                value={profile.email}
                disabled
                className="disabled-input"
              />
            </div>

            <div className="form-group">
              <label>
                <FaIdCard /> Student ID
              </label>
              <input
                type="text"
                value={profile.studentId || ""}
                onChange={(e) => setProfile({ ...profile, studentId: e.target.value })}
                disabled={!isEditing}
                placeholder="Enter your student ID"
              />
            </div>

            <div className="form-group">
              <label>
                <FaGraduationCap /> Major
              </label>
              <select
                value={profile.major || "Computer Science"}
                onChange={(e) => setProfile({ ...profile, major: e.target.value })}
                disabled={!isEditing}
              >
                <option value="Computer Science">Computer Science</option>
                <option value="Information Systems">Information Systems</option>
                <option value="Cybersecurity">Cybersecurity</option>
                <option value="Software Engineering">Software Engineering</option>
                <option value="Data Science">Data Science</option>
              </select>
            </div>

            {isEditing && (
              <div className="form-actions">
                <button type="submit" className="save-btn" disabled={loading}>
                  {loading ? "Saving..." : "Save Changes"}
                </button>
                <button 
                  type="button" 
                  className="cancel-btn" 
                  onClick={() => {
                    setIsEditing(false);
                    fetchProfile();
                  }}
                >
                  Cancel
                </button>
              </div>
            )}
          </form>
        </div>

        {/* Password Section */}
        <div className="profile-section">
          <div className="section-header">
            <h3>Security</h3>
            {!showPasswordForm && (
              <button className="edit-btn" onClick={() => setShowPasswordForm(true)}>
                Change Password
              </button>
            )}
          </div>

          {showPasswordForm && (
            <form onSubmit={handleChangePassword}>
              <div className="form-group">
                <label>
                  <FaLock /> Current Password
                </label>
                <input
                  type="password"
                  value={passwords.currentPassword}
                  onChange={(e) => setPasswords({ ...passwords, currentPassword: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>
                  <FaLock /> New Password
                </label>
                <input
                  type="password"
                  value={passwords.newPassword}
                  onChange={(e) => setPasswords({ ...passwords, newPassword: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>
                  <FaLock /> Confirm New Password
                </label>
                <input
                  type="password"
                  value={passwords.confirmPassword}
                  onChange={(e) => setPasswords({ ...passwords, confirmPassword: e.target.value })}
                  required
                />
              </div>

              <div className="form-actions">
                <button type="submit" className="save-btn" disabled={loading}>
                  {loading ? "Changing..." : "Change Password"}
                </button>
                <button 
                  type="button" 
                  className="cancel-btn" 
                  onClick={() => {
                    setShowPasswordForm(false);
                    setPasswords({ currentPassword: "", newPassword: "", confirmPassword: "" });
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Morgan Connection */}
        <div className="profile-section morgan-section">
          <div className="section-header">
            <h3><FaUniversity /> DegreeWorks Integration</h3>
            {profile.morganConnected && (
              <button className="disconnect-btn" onClick={handleDisconnectMorgan} disabled={loading}>
                Disconnect
              </button>
            )}
          </div>

          {profile.morganConnected && degreeWorksData ? (
            <div className="degreeworks-data">
              <div className="dw-header">
                <FaCheckCircle className="success-icon" />
                <div>
                  <p className="connected-text">Connected to DegreeWorks</p>
                  <p className="sync-time">Last synced: {degreeWorksData.updated_at ? new Date(degreeWorksData.updated_at).toLocaleDateString() : 'Recently'}</p>
                </div>
                <button className="resync-btn" onClick={handleConnectMorgan}>
                  <FaSync /> Re-sync
                </button>
              </div>

              <div className="dw-stats-grid">
                <div className={`dw-stat-card ${!degreeWorksData.overall_gpa ? 'empty' : ''}`}>
                  <FaChartLine className="stat-icon" />
                  <div className="stat-value">{degreeWorksData.overall_gpa ? degreeWorksData.overall_gpa.toFixed(2) : '--'}</div>
                  <div className="stat-label">{degreeWorksData.overall_gpa ? 'Overall GPA' : 'GPA Not Found'}</div>
                </div>
                <div className={`dw-stat-card ${!degreeWorksData.total_credits_earned ? 'empty' : ''}`}>
                  <FaBook className="stat-icon" />
                  <div className="stat-value">{degreeWorksData.total_credits_earned || '--'}</div>
                  <div className="stat-label">{degreeWorksData.total_credits_earned ? 'Credits Earned' : 'Credits Not Found'}</div>
                </div>
                <div className={`dw-stat-card ${!degreeWorksData.classification ? 'empty' : ''}`}>
                  <FaGraduationCap className="stat-icon" />
                  <div className="stat-value">{degreeWorksData.classification || '--'}</div>
                  <div className="stat-label">{degreeWorksData.classification ? 'Classification' : 'Class Not Found'}</div>
                </div>
              </div>

              {degreeWorksData.degree_program && (
                <div className="dw-info-row">
                  <strong>Program:</strong> {degreeWorksData.degree_program}
                </div>
              )}
              {degreeWorksData.advisor && (
                <div className="dw-info-row">
                  <strong>Advisor:</strong> {degreeWorksData.advisor}
                </div>
              )}
              {degreeWorksData.courses_completed && degreeWorksData.courses_completed.length > 0 && (
                <div className="dw-courses-section">
                  <strong>Courses Found ({degreeWorksData.courses_completed.length}):</strong>
                  <div className="dw-courses-list">
                    {degreeWorksData.courses_completed.slice(0, 10).map((c, i) => (
                      <span key={i} className="course-tag">{c.code} {c.grade && `(${c.grade})`}</span>
                    ))}
                    {degreeWorksData.courses_completed.length > 10 && (
                      <span className="course-tag more">+{degreeWorksData.courses_completed.length - 10} more</span>
                    )}
                  </div>
                </div>
              )}

              {(!degreeWorksData.overall_gpa || !degreeWorksData.classification) && (
                <div className="dw-warning">
                  <p>Some data couldn't be extracted from your PDF. Use <strong>Quick Manual Entry</strong> to add missing info.</p>
                  <button className="text-btn" onClick={() => { setShowManualEntry(true); setShowMorganModal(true); }}>Add Missing Data</button>
                </div>
              )}
            </div>
          ) : (
            <div className="connect-morgan-prompt">
              <div className="connect-info">
                <FaUniversity className="connect-icon" />
                <div>
                  <h4>Sync Your Academic Data</h4>
                  <p>Connect your DegreeWorks to get personalized course recommendations, track your progress, and more.</p>
                </div>
              </div>
              <button className="connect-btn" onClick={handleConnectMorgan} disabled={loading}>
                <FaSync /> Connect DegreeWorks
              </button>
            </div>
          )}
        </div>

        {/* Admin Access - Only show for admins */}
        {profile.role === "admin" && (
          <div className="profile-section admin-section">
            <div className="section-header">
              <h3><FaShieldAlt /> Admin Access</h3>
            </div>
            <div className="admin-access-content">
              <p>You have administrator privileges. Access the admin dashboard to manage tickets and curriculum.</p>
              <div style={{ position: "relative", display: "inline-block", width: "100%" }}>
                <button className="admin-access-btn" onClick={() => navigate("/admin")}>
                  <FaCog /> Open Admin Dashboard
                </button>
                {pendingResearch > 0 && (
                  <span style={{
                    position: "absolute", top: "-8px", right: "-4px",
                    background: "#ef4444", color: "white", borderRadius: "50%",
                    width: "22px", height: "22px", display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: "11px", fontWeight: 700,
                    boxShadow: "0 2px 6px rgba(239,68,68,0.4)", border: "2px solid var(--bg-card)"
                  }}>
                    {pendingResearch}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Logout */}
        <div className="profile-section">
          <button className="logout-btn" onClick={onLogout}>
            Sign Out
          </button>
        </div>
      </div>

      {/* DegreeWorks Connection Modal */}
      {showMorganModal && (
        <div className="modal-overlay" onClick={() => setShowMorganModal(false)}>
          <div className="modal-content degreeworks-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => {
              setShowMorganModal(false);
              setShowManualEntry(false);
              setShowPdfUpload(false);
            }}>
              <FaTimes />
            </button>

            <div className="modal-header">
              <FaUniversity className="modal-icon" />
              <h2>Connect Academic Data</h2>
              <p>Get personalized course recommendations</p>
            </div>

            <div className="modal-body">
              {!showManualEntry && !showPdfUpload ? (
                <>
                  {/* Option Selection */}
                  <div className="sync-options">
                    {/* Option 0: Auto-Sync from Banner (NEW) */}
                    <div className="sync-option highlighted" onClick={() => setShowPdfUpload('banner')}>
                      <div className="option-icon sync-icon">
                        <FaSync />
                      </div>
                      <div className="option-content">
                        <h4>Auto-Sync from Banner (Recommended)</h4>
                        <p>Log in with your MSU credentials to automatically pull all your academic data.</p>
                      </div>
                      <FaExternalLinkAlt className="option-arrow" />
                    </div>

                    {/* Option 1: One-Click Sync via Bookmarklet */}
                    <div className="sync-option" onClick={() => setShowPdfUpload('bookmarklet')}>
                      <div className="option-icon sync-icon">
                        <FaSync />
                      </div>
                      <div className="option-content">
                        <h4>Bookmarklet Sync</h4>
                        <p>Already on DegreeWorks? Use our sync button to instantly import your data.</p>
                      </div>
                      <FaExternalLinkAlt className="option-arrow" />
                    </div>

                    {/* Option 2: PDF Upload */}
                    <div className="sync-option" onClick={() => setShowPdfUpload('pdf')}>
                      <div className="option-icon pdf-icon">
                        <FaBook />
                      </div>
                      <div className="option-content">
                        <h4>Upload DegreeWorks Document</h4>
                        <p>Upload a PDF, screenshot, or DOCX of your DegreeWorks page.</p>
                      </div>
                      <FaExternalLinkAlt className="option-arrow" />
                    </div>

                    {/* Option 3: Manual Entry */}
                    <div className="sync-option" onClick={() => setShowManualEntry(true)}>
                      <div className="option-icon">
                        <FaUser />
                      </div>
                      <div className="option-content">
                        <h4>Quick Manual Entry</h4>
                        <p>Type in your GPA, classification, and credits manually.</p>
                      </div>
                      <FaExternalLinkAlt className="option-arrow" />
                    </div>
                  </div>
                </>
              ) : showPdfUpload === 'banner' ? (
                /* Banner Auto-Sync */
                <div className="pdf-upload-section">
                  <button className="back-to-options" onClick={() => {
                    setShowPdfUpload(false);
                    setBannerError("");
                    setBannerProgress([]);
                    setBannerSummary(null);
                  }}>
                    <FaArrowLeft /> Back to options
                  </button>

                  <h3>Auto-Sync from Banner</h3>

                  {!bannerSyncing && !bannerSummary ? (
                    <>
                      <p className="form-subtitle">
                        Enter your MSU credentials to automatically sync your profile, registration, and grades.
                      </p>

                      <div className="manual-form-grid">
                        <div className="form-group">
                          <label>MSU Username</label>
                          <input
                            type="text"
                            placeholder="e.g., jsmith1"
                            value={bannerCreds.username}
                            onChange={(e) => setBannerCreds({ ...bannerCreds, username: e.target.value })}
                            autoComplete="username"
                          />
                        </div>
                        <div className="form-group">
                          <label>MSU Password</label>
                          <input
                            type="password"
                            placeholder="Your MSU password"
                            value={bannerCreds.password}
                            onChange={(e) => setBannerCreds({ ...bannerCreds, password: e.target.value })}
                            autoComplete="current-password"
                            onKeyDown={(e) => e.key === "Enter" && handleBannerSync()}
                          />
                        </div>
                      </div>

                      {bannerError && (
                        <div className="message error" style={{ marginBottom: 12 }}>
                          {bannerError}
                        </div>
                      )}

                      <div className="security-note" style={{ marginBottom: 16 }}>
                        <FaShieldAlt />
                        <div>
                          <strong>Your credentials are never stored</strong>
                          <p>Your password is used once to authenticate with MSU and is immediately discarded. It is never saved to our servers.</p>
                        </div>
                      </div>

                      <button
                        className="modal-primary-btn submit-manual"
                        onClick={handleBannerSync}
                        disabled={bannerSyncing || !bannerCreds.username || !bannerCreds.password}
                      >
                        <FaSync /> Sync My Data
                      </button>
                    </>
                  ) : bannerSyncing ? (
                    <div className="banner-progress">
                      <div className="progress-steps">
                        {bannerProgress.map((step, i) => (
                          <div key={i} className="progress-step completed">
                            <FaCheckCircle className="step-check" />
                            <span>{step}</span>
                          </div>
                        ))}
                        <div className="progress-step active">
                          <FaSync className="spinning" />
                          <span>Working...</span>
                        </div>
                      </div>
                    </div>
                  ) : bannerSummary ? (
                    <div className="banner-success">
                      <div className="success-header">
                        <FaCheckCircle className="success-icon large" />
                        <h4>Sync Complete!</h4>
                      </div>

                      <div className="dw-stats-grid" style={{ marginTop: 16 }}>
                        {bannerSummary.cumulative_gpa ? (
                          <div className="dw-stat-card">
                            <FaChartLine className="stat-icon" />
                            <div className="stat-value">{Number(bannerSummary.cumulative_gpa).toFixed(2)}</div>
                            <div className="stat-label">Overall GPA</div>
                          </div>
                        ) : null}
                        {bannerSummary.total_credits > 0 ? (
                          <div className="dw-stat-card">
                            <FaBook className="stat-icon" />
                            <div className="stat-value">{bannerSummary.total_credits}</div>
                            <div className="stat-label">Credits Earned</div>
                          </div>
                        ) : null}
                        {bannerSummary.classification ? (
                          <div className="dw-stat-card">
                            <FaGraduationCap className="stat-icon" />
                            <div className="stat-value">{bannerSummary.classification}</div>
                            <div className="stat-label">Classification</div>
                          </div>
                        ) : null}
                        {bannerSummary.courses_count > 0 ? (
                          <div className="dw-stat-card">
                            <FaBook className="stat-icon" />
                            <div className="stat-value">{bannerSummary.courses_count}</div>
                            <div className="stat-label">Courses Found</div>
                          </div>
                        ) : null}
                      </div>
                      <div style={{ marginTop: 12, fontSize: '0.9rem', color: 'var(--text-secondary, #666)' }}>
                        {bannerSummary.name && <div><strong>Name:</strong> {bannerSummary.name}</div>}
                        {bannerSummary.major && <div><strong>Program:</strong> {bannerSummary.major}</div>}
                        {bannerSummary.advisor && <div><strong>Advisor:</strong> {bannerSummary.advisor}</div>}
                        {bannerSummary.student_id && <div><strong>ID:</strong> {bannerSummary.student_id}</div>}
                        {bannerSummary.courses_completed > 0 && <div><strong>Courses completed:</strong> {bannerSummary.courses_completed}</div>}
                        {bannerSummary.courses_in_progress > 0 && <div><strong>In progress:</strong> {bannerSummary.courses_in_progress}</div>}
                        {bannerSummary.degreeworks_synced && <div style={{color: '#34a853', marginTop: 4}}>DegreeWorks data synced</div>}
                        {bannerSummary.profile_synced && <div style={{color: '#34a853'}}>Student Profile synced</div>}
                      </div>

                      <button
                        className="modal-primary-btn submit-manual"
                        style={{ marginTop: 16 }}
                        onClick={() => {
                          setShowMorganModal(false);
                          setShowPdfUpload(false);
                          setBannerSummary(null);
                          setBannerProgress([]);
                        }}
                      >
                        Done
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : showPdfUpload === 'bookmarklet' ? (
                /* One-Click Sync Instructions */
                <div className="pdf-upload-section">
                  <button className="back-to-options" onClick={() => setShowPdfUpload(false)}>
                    <FaArrowLeft /> Back to options
                  </button>

                  <h3>Sync DegreeWorks</h3>

                  <div className="pdf-instructions">
                    <div className="instruction-step">
                      <span className="step-num">1</span>
                      <div>
                        <strong>Drag this button to your bookmarks bar</strong>
                        <p>This is a one-time setup. Just drag it up there.</p>
                        <div className="bookmarklet-drag-container">
                          <a
                            ref={setBookmarkletHref}
                            onClick={(e) => e.preventDefault()}
                            className="bookmarklet-drag-btn"
                            title="Drag me to your bookmarks bar!"
                          >
                            <FaSync /> Sync to CS Navigator
                          </a>
                          <span className="drag-hint">Drag me up to your bookmarks bar</span>
                        </div>
                        <div className="bookmark-instructions">
                          <small>
                            Don't see a bookmarks bar? Press <strong>Ctrl+Shift+B</strong> (Chrome) or <strong>Ctrl+B</strong> (Firefox) to show it.
                          </small>
                        </div>
                        <div className="bookmark-instructions" style={{ marginTop: '8px' }}>
                          <small>
                            <strong>Can't drag?</strong>{' '}
                            <button className="inline-copy-btn" onClick={copyBookmarklet}>
                              Copy the code
                            </button>{' '}
                            and create a bookmark manually with it as the URL.
                          </small>
                        </div>
                      </div>
                    </div>
                    <div className="instruction-step">
                      <span className="step-num">2</span>
                      <div>
                        <strong>Go to DegreeWorks and log in</strong>
                        <p>Open your DegreeWorks audit page through MyMSU Banner.</p>
                        <button className="step-action-btn small" onClick={openMorganPortal}>
                          <FaExternalLinkAlt /> Open MyMSU
                        </button>
                      </div>
                    </div>
                    <div className="instruction-step">
                      <span className="step-num">3</span>
                      <div>
                        <strong>Click "Sync to CS Navigator" in your bookmarks bar</strong>
                        <p>While on the DegreeWorks page, click the bookmark. You'll see a confirmation when it's done.</p>
                      </div>
                    </div>
                  </div>

                  <div className="info-box">
                    <FaCheckCircle />
                    <p>After syncing, refresh this page to see your GPA, courses, and academic progress.</p>
                  </div>
                </div>
              ) : showPdfUpload === 'pdf' ? (
                /* PDF Upload Section */
                <div className="pdf-upload-section">
                  <button className="back-to-options" onClick={() => setShowPdfUpload(false)}>
                    <FaArrowLeft /> Back to options
                  </button>

                  <h3>Upload DegreeWorks Document</h3>

                  <div className="pdf-instructions">
                    <div className="instruction-step">
                      <span className="step-num">1</span>
                      <div>
                        <strong>Open DegreeWorks</strong>
                        <p>Go to your DegreeWorks page in MyMSU Banner</p>
                        <button className="step-action-btn small" onClick={openMorganPortal}>
                          <FaExternalLinkAlt /> Open Morgan State
                        </button>
                      </div>
                    </div>
                    <div className="instruction-step">
                      <span className="step-num">2</span>
                      <div>
                        <strong>Save as PDF</strong>
                        <p>Click the <strong>"Save as PDF"</strong> or <strong>"Print"</strong> button in DegreeWorks, then save/print to PDF</p>
                      </div>
                    </div>
                    <div className="instruction-step">
                      <span className="step-num">3</span>
                      <div>
                        <strong>Upload below</strong>
                        <p>Select the PDF file you just saved</p>
                      </div>
                    </div>
                  </div>

                  <div className="pdf-upload-area">
                    {/* Hidden file input with ref */}
                    <input
                      type="file"
                      accept=".pdf,.docx,.png,.jpg,.jpeg,.gif,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/*"
                      ref={pdfInputRef}
                      onChange={handlePdfUpload}
                      disabled={pdfUploading}
                      style={{ display: 'none' }}
                    />
                    {/* Clickable button that triggers file picker */}
                    <button
                      type="button"
                      className={`upload-label ${pdfUploading ? 'uploading' : ''}`}
                      onClick={triggerPdfUpload}
                      disabled={pdfUploading}
                    >
                      {pdfUploading ? (
                        <>
                          <FaSync className="spinning" /> Uploading document...
                        </>
                      ) : (
                        <>
                          <FaBook /> Click to Upload DegreeWorks Document
                        </>
                      )}
                    </button>
                    <p className="upload-hint">Supports PDF, DOCX, and images (PNG, JPG, GIF) from DegreeWorks</p>
                  </div>
                </div>
              ) : (
                /* Manual Entry Form */
                <div className="manual-entry-form">
                  <button className="back-to-options" onClick={() => setShowManualEntry(false)}>
                    <FaArrowLeft /> Back to options
                  </button>

                  <h3>Enter Your Academic Info</h3>
                  <p className="form-subtitle">This helps us give you personalized recommendations</p>

                  <div className="manual-form-grid">
                    <div className="form-group">
                      <label>Full Name</label>
                      <input
                        type="text"
                        placeholder="e.g., John Smith"
                        value={manualData.student_name}
                        onChange={(e) => setManualData({...manualData, student_name: e.target.value})}
                      />
                    </div>

                    <div className="form-group">
                      <label>Classification</label>
                      <select
                        value={manualData.classification}
                        onChange={(e) => setManualData({...manualData, classification: e.target.value})}
                      >
                        <option value="Freshman">Freshman</option>
                        <option value="Sophomore">Sophomore</option>
                        <option value="Junior">Junior</option>
                        <option value="Senior">Senior</option>
                        <option value="Graduate">Graduate</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Degree Program</label>
                      <select
                        value={manualData.degree_program}
                        onChange={(e) => setManualData({...manualData, degree_program: e.target.value})}
                      >
                        <option value="Bachelor of Science in Computer Science">B.S. Computer Science</option>
                        <option value="Bachelor of Science in Information Systems">B.S. Information Systems</option>
                        <option value="Bachelor of Science in Cybersecurity">B.S. Cybersecurity</option>
                        <option value="Master of Science in Computer Science">M.S. Computer Science</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Overall GPA</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="4"
                        placeholder="e.g., 3.50"
                        value={manualData.overall_gpa}
                        onChange={(e) => setManualData({...manualData, overall_gpa: e.target.value})}
                      />
                    </div>

                    <div className="form-group">
                      <label>Credits Earned</label>
                      <input
                        type="number"
                        min="0"
                        placeholder="e.g., 60"
                        value={manualData.total_credits_earned}
                        onChange={(e) => setManualData({...manualData, total_credits_earned: e.target.value})}
                      />
                    </div>

                    <div className="form-group">
                      <label>Credits Remaining</label>
                      <input
                        type="number"
                        min="0"
                        placeholder="e.g., 60"
                        value={manualData.credits_remaining}
                        onChange={(e) => setManualData({...manualData, credits_remaining: e.target.value})}
                      />
                    </div>
                  </div>

                  <button
                    className="modal-primary-btn submit-manual"
                    onClick={handleManualSubmit}
                    disabled={loading}
                  >
                    {loading ? "Saving..." : "Save Academic Data"}
                  </button>
                </div>
              )}

              <div className="security-note">
                <FaLock />
                <div>
                  <strong>Your data is secure</strong>
                  <p>Your academic information is stored securely and only used to personalize your chatbot experience.</p>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="modal-secondary-btn" onClick={() => {
                setShowMorganModal(false);
                setShowManualEntry(false);
                setShowPdfUpload(false);
              }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
