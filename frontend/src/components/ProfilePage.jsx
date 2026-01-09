// src/components/ProfilePage.jsx
import React, { useState, useEffect } from "react";
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

// 🔥 Smart API switching - same logic as Chatbox.jsx
const hostname = window.location.hostname;
const API_BASE = (hostname === "localhost" || hostname === "127.0.0.1")
  ? "http://127.0.0.1:8000"           // Local development
  : "http://18.214.136.155:5000";     // AWS production

export default function ProfilePage({ userEmail, onLogout }) {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  
  const [profile, setProfile] = useState({
    name: "",
    email: userEmail || "",
    studentId: "",
    major: "Computer Science",
    profilePicture: "/user_icon.jpg",
    morganConnected: false,
    role: "student"
  });

  const [passwords, setPasswords] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });

  const [showPasswordForm, setShowPasswordForm] = useState(false);

  // DegreeWorks Modal State
  const [showMorganModal, setShowMorganModal] = useState(false);
  const [degreeWorksData, setDegreeWorksData] = useState(null);
  const [syncStep, setSyncStep] = useState(1); // 1=instructions, 2=syncing, 3=success

  // Fetch profile data on mount
  useEffect(() => {
    fetchProfile();
    fetchDegreeWorksData();
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

  // Generate the bookmarklet code - sends HTML to backend for parsing
  const getBookmarkletCode = () => {
    const token = localStorage.getItem("token");
    return `javascript:(function(){
      const API='${API_BASE}';
      const TOKEN='${token}';

      // Show loading message
      const msg=document.createElement('div');
      msg.style.cssText='position:fixed;top:20px;right:20px;background:#333;color:#fff;padding:20px;border-radius:10px;z-index:999999;font-family:Arial;';
      msg.innerHTML='<strong>CS Navigator</strong><br>Syncing your DegreeWorks data...';
      document.body.appendChild(msg);

      // Get the page HTML
      const html=document.documentElement.outerHTML;

      fetch(API+'/api/degreeworks/scrape-html',{
        method:'POST',
        headers:{
          'Content-Type':'application/json',
          'Authorization':'Bearer '+TOKEN
        },
        body:JSON.stringify({html:html})
      })
      .then(r=>r.json())
      .then(d=>{
        msg.remove();
        if(d.success){
          const info=d.data||{};
          let details='';
          if(info.overall_gpa) details+='GPA: '+info.overall_gpa+'\\n';
          if(info.classification) details+='Classification: '+info.classification+'\\n';
          if(info.total_credits_earned) details+='Credits: '+info.total_credits_earned+'\\n';
          if(info.courses_count) details+='Courses found: '+info.courses_count+'\\n';
          alert('✅ DegreeWorks synced successfully!\\n\\n'+details+'\\nYou can now close this tab and return to CS Navigator.');
        }else{
          alert('❌ Sync failed: '+(d.detail||d.message||'Unknown error')+'\\n\\nTry using manual entry instead.');
        }
      })
      .catch(e=>{
        msg.remove();
        alert('❌ Error: '+e.message+'\\n\\nTry using manual entry instead.');
      });
    })();`;
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

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setMessage({ type: "error", text: "Please upload a PDF file" });
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
              onError={(e) => e.target.src = "/user_icon.jpg"}
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
              <button className="admin-access-btn" onClick={() => navigate("/admin")}>
                <FaCog /> Open Admin Dashboard
              </button>
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
                    {/* Option 1: One-Click Sync via Bookmarklet */}
                    <div className="sync-option highlighted" onClick={() => setShowPdfUpload('bookmarklet')}>
                      <div className="option-icon sync-icon">
                        <FaSync />
                      </div>
                      <div className="option-content">
                        <h4>One-Click Sync (Recommended)</h4>
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
                        <h4>Upload DegreeWorks PDF</h4>
                        <p>Save your DegreeWorks as PDF and upload it here.</p>
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
              ) : showPdfUpload === 'bookmarklet' ? (
                /* One-Click Sync Instructions */
                <div className="pdf-upload-section">
                  <button className="back-to-options" onClick={() => setShowPdfUpload(false)}>
                    <FaArrowLeft /> Back to options
                  </button>

                  <h3>One-Click Sync</h3>

                  <div className="pdf-instructions">
                    <div className="instruction-step">
                      <span className="step-num">1</span>
                      <div>
                        <strong>Open DegreeWorks</strong>
                        <p>Go to your DegreeWorks page in MyMSU Banner (if not already there)</p>
                        <button className="step-action-btn small" onClick={openMorganPortal}>
                          <FaExternalLinkAlt /> Open Morgan State
                        </button>
                      </div>
                    </div>
                    <div className="instruction-step">
                      <span className="step-num">2</span>
                      <div>
                        <strong>Create Sync Bookmark</strong>
                        <p>Click the button below to copy the sync code, then create a new bookmark and paste it as the URL:</p>
                        <button className="bookmarklet-copy-btn" onClick={copyBookmarklet}>
                          <FaBookmark /> Copy Sync Code
                        </button>
                        <div className="bookmark-instructions">
                          <small>
                            <strong>Chrome:</strong> Right-click bookmarks bar → Add page → Paste code as URL<br/>
                            <strong>Firefox:</strong> Ctrl+Shift+B → Right-click → New Bookmark → Paste code as URL
                          </small>
                        </div>
                      </div>
                    </div>
                    <div className="instruction-step">
                      <span className="step-num">3</span>
                      <div>
                        <strong>Click the Bookmark</strong>
                        <p>While on your DegreeWorks page, click the bookmark you just created. Your data will sync automatically!</p>
                      </div>
                    </div>
                  </div>

                  <div className="info-box">
                    <FaCheckCircle />
                    <p>After syncing, refresh this page to see your updated academic data.</p>
                  </div>
                </div>
              ) : showPdfUpload === 'pdf' ? (
                /* PDF Upload Section */
                <div className="pdf-upload-section">
                  <button className="back-to-options" onClick={() => setShowPdfUpload(false)}>
                    <FaArrowLeft /> Back to options
                  </button>

                  <h3>Upload DegreeWorks PDF</h3>

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
                      accept=".pdf,application/pdf"
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
                          <FaSync className="spinning" /> Uploading PDF...
                        </>
                      ) : (
                        <>
                          <FaBook /> Click to Upload DegreeWorks PDF
                        </>
                      )}
                    </button>
                    <p className="upload-hint">Supports PDF files exported from DegreeWorks</p>
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
