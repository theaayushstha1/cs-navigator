import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FaBook } from "@react-icons/all-files/fa/FaBook";
import { FaExclamationTriangle as FaWarning } from "@react-icons/all-files/fa/FaExclamationTriangle";
import { FaCheckCircle } from "@react-icons/all-files/fa/FaCheckCircle";
import { FaClock as FaTime } from "@react-icons/all-files/fa/FaClock";
import { FaSync as FaRefresh } from "@react-icons/all-files/fa/FaSync";
import { FaCalendarAlt as FaCal } from "@react-icons/all-files/fa/FaCalendarAlt";
import { getApiBase } from "../lib/apiBase";
import "./MyClassesPage.css";

const API_BASE = getApiBase();

export default function MyClassesPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    fetchCanvasData();
  }, []);

  const fetchCanvasData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE}/api/canvas`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const d = await res.json();
        if (d.connected) setData(d);
      }
    } catch (err) {
      console.error("Failed to load Canvas data:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "No date";
    const d = new Date(dateStr);
    const now = new Date();
    const diff = d - now;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor(diff / (1000 * 60 * 60));

    if (hours < 0) return `Overdue (${d.toLocaleDateString()})`;
    if (hours < 24) return `Due in ${hours}h`;
    if (days < 7) return `Due in ${days}d`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const getUrgencyClass = (dateStr) => {
    if (!dateStr) return "";
    const hours = (new Date(dateStr) - new Date()) / (1000 * 60 * 60);
    if (hours < 0) return "overdue";
    if (hours < 24) return "urgent";
    if (hours < 72) return "soon";
    return "";
  };

  const getGradeColor = (score) => {
    if (!score) return "var(--text-secondary)";
    if (score >= 90) return "#2e7d32";
    if (score >= 80) return "#1565c0";
    if (score >= 70) return "#e65100";
    return "#c62828";
  };

  if (loading) {
    return (
      <div className="my-classes-page">
        <div className="classes-loading">Loading your Canvas data...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="my-classes-page">
        <div className="classes-empty">
          <FaBook size={48} style={{ color: "var(--text-secondary)", marginBottom: "16px" }} />
          <h2>Connect Canvas</h2>
          <p>Sync your Canvas account to see your courses, assignments, and grades here.</p>
          <button className="connect-canvas-btn" onClick={() => navigate("/profile")}>
            Go to Profile to Connect
          </button>
        </div>
      </div>
    );
  }

  const courses = data.courses || [];
  const assignments = data.upcoming_assignments || [];
  const missing = data.missing_assignments || [];

  // Split assignments
  const dueSoon = assignments.filter(a => {
    if (!a.due_at) return false;
    const hours = (new Date(a.due_at) - new Date()) / (1000 * 60 * 60);
    return hours > 0 && hours < 72;
  });

  const upcoming = assignments.filter(a => {
    if (!a.due_at) return false;
    const hours = (new Date(a.due_at) - new Date()) / (1000 * 60 * 60);
    return hours >= 72;
  });

  return (
    <div className="my-classes-page">
      <div className="classes-header">
        <h1>My Classes</h1>
        <div className="classes-meta">
          <span className="sync-time">Last synced: {data.updated_at ? new Date(data.updated_at).toLocaleString() : "Never"}</span>
          <button className="refresh-btn" onClick={() => navigate("/profile")} title="Re-sync from Profile">
            <FaRefresh size={12} /> Sync
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="classes-stats">
        <div className="stat-pill">
          <FaBook size={14} />
          <span>{courses.length} Courses</span>
        </div>
        {dueSoon.length > 0 && (
          <div className="stat-pill urgent">
            <FaWarning size={14} />
            <span>{dueSoon.length} Due Soon</span>
          </div>
        )}
        {missing.length > 0 && (
          <div className="stat-pill overdue">
            <FaWarning size={14} />
            <span>{missing.length} Missing</span>
          </div>
        )}
        <div className="stat-pill">
          <FaCal size={14} />
          <span>{assignments.length} Upcoming</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="classes-tabs">
        {["overview", "assignments", "grades"].map(tab => (
          <button
            key={tab}
            className={`classes-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="classes-content">
          {/* Alerts */}
          {missing.length > 0 && (
            <div className="alert-banner overdue">
              <FaWarning size={16} />
              <div>
                <strong>{missing.length} missing assignment{missing.length > 1 ? "s" : ""}</strong>
                <div className="alert-items">
                  {missing.map((m, i) => (
                    <span key={i}>{m.title} ({m.points}pts)</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {dueSoon.length > 0 && (
            <div className="alert-banner urgent">
              <FaTime size={16} />
              <div>
                <strong>{dueSoon.length} due within 72 hours</strong>
                <div className="alert-items">
                  {dueSoon.map((a, i) => (
                    <span key={i}>{a.title} - {formatDate(a.due_at)}</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Course Cards */}
          <h3 className="section-title">Your Courses</h3>
          <div className="course-grid">
            {courses.map(c => (
              <div key={c.id} className="course-card">
                <div className="course-code">{c.code?.split("_")[0] || c.code}</div>
                <div className="course-name">{c.name}</div>
                {c.current_score != null && (
                  <div className="course-grade" style={{ color: getGradeColor(c.current_score) }}>
                    {c.current_score.toFixed(1)}%
                    {c.current_grade && <span className="letter-grade">{c.current_grade}</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Assignments Tab */}
      {activeTab === "assignments" && (
        <div className="classes-content">
          {assignments.length === 0 ? (
            <div className="empty-state">No upcoming assignments. You're all caught up!</div>
          ) : (
            <div className="assignment-list">
              {assignments.filter(a => a.type !== "calendar_event").map((a, i) => (
                <div key={i} className={`assignment-row ${getUrgencyClass(a.due_at)}`}>
                  <div className="assignment-icon">
                    {a.type === "quiz" ? "Q" : a.type === "discussion_topic" ? "D" : "A"}
                  </div>
                  <div className="assignment-info">
                    <div className="assignment-title">{a.title}</div>
                    <div className="assignment-course">{a.course_name}</div>
                  </div>
                  <div className="assignment-meta">
                    <div className="assignment-due">{formatDate(a.due_at)}</div>
                    {a.points && <div className="assignment-points">{a.points} pts</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Grades Tab */}
      {activeTab === "grades" && (
        <div className="classes-content">
          <div className="grades-list">
            {courses.map(c => (
              <div key={c.id} className="grade-row">
                <div className="grade-course">
                  <div className="grade-code">{c.code?.split("_")[0] || c.code}</div>
                  <div className="grade-name">{c.name}</div>
                </div>
                <div className="grade-score" style={{ color: getGradeColor(c.current_score) }}>
                  {c.current_score != null ? (
                    <>
                      <span className="score-num">{c.current_score.toFixed(1)}%</span>
                      {c.current_grade && <span className="score-letter">{c.current_grade}</span>}
                    </>
                  ) : (
                    <span className="no-grade">N/A</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
