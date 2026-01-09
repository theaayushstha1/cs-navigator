// src/components/AdminDashboard.jsx
import React, { useState, useEffect } from "react";
import { FaCog } from "@react-icons/all-files/fa/FaCog";
import { FaTicketAlt } from "@react-icons/all-files/fa/FaTicketAlt";
import { FaBug } from "@react-icons/all-files/fa/FaBug";
import { FaLightbulb } from "@react-icons/all-files/fa/FaLightbulb";
import { FaQuestionCircle } from "@react-icons/all-files/fa/FaQuestionCircle";
import { FaEye } from "@react-icons/all-files/fa/FaEye";
import { FaTimes } from "@react-icons/all-files/fa/FaTimes";
import { FaCheck } from "@react-icons/all-files/fa/FaCheck";
import { FaClock } from "@react-icons/all-files/fa/FaClock";
import "./AdminDashboard.css";

// API Base URL - Smart switching
const hostname = window.location.hostname;
const API_BASE = (hostname === "localhost" || hostname === "127.0.0.1")
  ? "http://127.0.0.1:8000"
  : "http://18.214.136.155:5000";

export default function AdminDashboard() {
  // form state
  const [course, setCourse] = useState({
    course_code: "",
    course_name: "",
    credits: "",
    prerequisites: "",
    offered: "",
  });
  const [message, setMessage] = useState("");
  const [courses, setCourses] = useState([]);

  // Support Tickets State
  const [tickets, setTickets] = useState([]);
  const [ticketStats, setTicketStats] = useState({ total: 0, open: 0, in_progress: 0, resolved: 0 });
  const [ticketFilter, setTicketFilter] = useState("all");
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketLoading, setTicketLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("courses"); // "courses" or "tickets"

  // load from FastAPI
  const loadCourses = async () => {
    setMessage("Loading courses...");
    try {
      const res = await fetch(`${API_BASE}/api/curriculum`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCourses(data);
      setMessage("");
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  useEffect(() => {
    loadCourses();
    loadTickets();
    loadTicketStats();
  }, []);

  // Load support tickets
  const loadTickets = async (status = null) => {
    setTicketLoading(true);
    const token = localStorage.getItem("token");
    try {
      const url = status && status !== "all"
        ? `${API_BASE}/api/tickets?status=${status}`
        : `${API_BASE}/api/tickets`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTickets(data.tickets || []);
    } catch (err) {
      console.error("Failed to load tickets:", err);
    } finally {
      setTicketLoading(false);
    }
  };

  // Load ticket stats
  const loadTicketStats = async () => {
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`${API_BASE}/api/tickets/stats/summary`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTicketStats(data);
      }
    } catch (err) {
      console.error("Failed to load ticket stats:", err);
    }
  };

  // Update ticket status
  const updateTicketStatus = async (ticketId, newStatus) => {
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`${API_BASE}/api/tickets/${ticketId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        loadTickets(ticketFilter === "all" ? null : ticketFilter);
        loadTicketStats();
        if (selectedTicket?.id === ticketId) {
          setSelectedTicket(prev => ({ ...prev, status: newStatus }));
        }
      }
    } catch (err) {
      console.error("Failed to update ticket:", err);
    }
  };

  // Get category icon
  const getCategoryIcon = (category) => {
    switch (category) {
      case "bug": return <FaBug size={14} />;
      case "feature": return <FaLightbulb size={14} />;
      case "question": return <FaQuestionCircle size={14} />;
      default: return <FaTicketAlt size={14} />;
    }
  };

  // Get status badge class
  const getStatusClass = (status) => {
    switch (status) {
      case "open": return "status-open";
      case "in_progress": return "status-progress";
      case "resolved": return "status-resolved";
      case "closed": return "status-closed";
      default: return "";
    }
  };

  // Format date
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  // form input
  const handleChange = (e) => {
    const { name, value } = e.target;
    setCourse((c) => ({ ...c, [name]: value }));
  };

  // add
  const handleAddCourse = async (e) => {
    e.preventDefault();
    setMessage("Adding course...");
    const payload = {
      course_code: course.course_code,
      course_name: course.course_name,
      credits: Number(course.credits),
      prerequisites: course.prerequisites
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      offered: course.offered
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      const res = await fetch(`${API_BASE}/api/curriculum/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ Added ${data.course.course_code}`);
      setCourse({
        course_code: "",
        course_name: "",
        credits: "",
        prerequisites: "",
        offered: "",
      });
      loadCourses();
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  // delete course
  const handleDelete = async (code) => {
    if (!window.confirm(`Delete ${code}?`)) return;
    setMessage(`Deleting ${code}...`);
    try {
      const res = await fetch(
        `${API_BASE}/api/curriculum/delete/${encodeURIComponent(code)}`,
        { method: "DELETE" }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ ${data.message}`);
      loadCourses();
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  // re-ingest
  const handleReingest = async () => {
    setMessage("Re-ingesting data...");
    try {
      const res = await fetch(`${API_BASE}/ingest`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ ${data.message}`);
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  // clear index
  const handleClearIndex = async () => {
    setMessage("Clearing index...");
    try {
      const res = await fetch(`${API_BASE}/clear-index`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
      setMessage(`✔️ ${data.message}`);
    } catch (err) {
      setMessage(`❌ ${err.message}`);
    }
  };

  return (
    <div className="card page-container AdminDashboard">
      <header className="page-header">
        <FaCog className="page-icon" />
        <h1 className="page-title">Admin Dashboard</h1>
      </header>

      {/* Tab Navigation */}
      <div className="admin-tabs">
        <button
          className={`admin-tab ${activeTab === "courses" ? "active" : ""}`}
          onClick={() => setActiveTab("courses")}
        >
          <FaCog size={16} />
          <span>Curriculum</span>
        </button>
        <button
          className={`admin-tab ${activeTab === "tickets" ? "active" : ""}`}
          onClick={() => setActiveTab("tickets")}
        >
          <FaTicketAlt size={16} />
          <span>Support Tickets</span>
          {ticketStats.open > 0 && (
            <span className="ticket-badge">{ticketStats.open}</span>
          )}
        </button>
      </div>

      {/* Courses Tab */}
      {activeTab === "courses" && (
        <>
          <p>Use the controls below to manage your curriculum data.</p>

          <section className="admin-actions" style={{ marginBottom: 24 }}>
            <button onClick={handleReingest} className="action-btn">
              Re-ingest Data
            </button>
            <button onClick={handleClearIndex} className="action-btn">
              Clear Index
            </button>
          </section>

          <section>
            <h2>Add New Course</h2>
            <form onSubmit={handleAddCourse} className="admin-form">
              <input
                name="course_code"
                placeholder="Course Code (e.g. COSC 101)"
                value={course.course_code}
                onChange={handleChange}
                required
              />
              <input
                name="course_name"
                placeholder="Course Name"
                value={course.course_name}
                onChange={handleChange}
                required
              />
              <input
                name="credits"
                type="number"
                placeholder="Credits"
                value={course.credits}
                onChange={handleChange}
                required
              />
              <input
                name="prerequisites"
                placeholder="Prerequisites (comma-separated)"
                value={course.prerequisites}
                onChange={handleChange}
              />
              <input
                name="offered"
                placeholder="Offered Semesters (comma-separated)"
                value={course.offered}
                onChange={handleChange}
              />
              <button type="submit" className="action-btn">
                Add Course
              </button>
            </form>
          </section>

          <section style={{ marginTop: 32 }}>
            <h2>Existing Courses ({courses.length})</h2>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Credits</th>
                  <th>Offered</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {courses.map((c) => (
                  <tr key={c.course_code}>
                    <td>{c.course_code}</td>
                    <td>{c.course_name}</td>
                    <td>{c.credits}</td>
                    <td>{c.offered.join(", ")}</td>
                    <td>
                      <button onClick={() => handleDelete(c.course_code)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {message && <p style={{ marginTop: 16, fontStyle: "italic" }}>{message}</p>}
        </>
      )}

      {/* Tickets Tab */}
      {activeTab === "tickets" && (
        <div className="tickets-section">
          {/* Stats Cards */}
          <div className="ticket-stats">
            <div className="stat-card total">
              <span className="stat-number">{ticketStats.total}</span>
              <span className="stat-label">Total</span>
            </div>
            <div className="stat-card open">
              <span className="stat-number">{ticketStats.open}</span>
              <span className="stat-label">Open</span>
            </div>
            <div className="stat-card progress">
              <span className="stat-number">{ticketStats.in_progress}</span>
              <span className="stat-label">In Progress</span>
            </div>
            <div className="stat-card resolved">
              <span className="stat-number">{ticketStats.resolved}</span>
              <span className="stat-label">Resolved</span>
            </div>
          </div>

          {/* Filter Buttons */}
          <div className="ticket-filters">
            {["all", "open", "in_progress", "resolved"].map((filter) => (
              <button
                key={filter}
                className={`filter-btn ${ticketFilter === filter ? "active" : ""}`}
                onClick={() => {
                  setTicketFilter(filter);
                  loadTickets(filter === "all" ? null : filter);
                }}
              >
                {filter === "all" ? "All" : filter.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* Tickets List */}
          <div className="tickets-list">
            {ticketLoading ? (
              <div className="tickets-loading">Loading tickets...</div>
            ) : tickets.length === 0 ? (
              <div className="tickets-empty">No tickets found</div>
            ) : (
              tickets.map((ticket) => (
                <div key={ticket.id} className="ticket-card">
                  <div className="ticket-header-row">
                    <div className="ticket-category">
                      {getCategoryIcon(ticket.category)}
                      <span>{ticket.category}</span>
                    </div>
                    <span className={`ticket-status ${getStatusClass(ticket.status)}`}>
                      {ticket.status.replace("_", " ")}
                    </span>
                  </div>

                  <h3 className="ticket-subject">{ticket.subject}</h3>

                  <p className="ticket-preview">
                    {ticket.description.length > 150
                      ? ticket.description.slice(0, 150) + "..."
                      : ticket.description}
                  </p>

                  <div className="ticket-footer">
                    <span className="ticket-date">
                      <FaClock size={12} />
                      {formatDate(ticket.created_at)}
                    </span>
                    <div className="ticket-actions">
                      <button
                        className="view-btn"
                        onClick={() => setSelectedTicket(ticket)}
                        title="View details"
                      >
                        <FaEye size={14} />
                      </button>
                      {ticket.status === "open" && (
                        <button
                          className="progress-btn"
                          onClick={() => updateTicketStatus(ticket.id, "in_progress")}
                          title="Mark as in progress"
                        >
                          <FaClock size={14} />
                        </button>
                      )}
                      {ticket.status !== "resolved" && (
                        <button
                          className="resolve-btn"
                          onClick={() => updateTicketStatus(ticket.id, "resolved")}
                          title="Mark as resolved"
                        >
                          <FaCheck size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Ticket Detail Modal */}
      {selectedTicket && (
        <div className="ticket-modal-overlay" onClick={() => setSelectedTicket(null)}>
          <div className="ticket-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-row">
                {getCategoryIcon(selectedTicket.category)}
                <h2>{selectedTicket.subject}</h2>
              </div>
              <button className="modal-close" onClick={() => setSelectedTicket(null)}>
                <FaTimes size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div className="modal-meta">
                <span className={`ticket-status ${getStatusClass(selectedTicket.status)}`}>
                  {selectedTicket.status.replace("_", " ")}
                </span>
                <span className="ticket-date">
                  Submitted: {formatDate(selectedTicket.created_at)}
                </span>
              </div>

              <div className="modal-description">
                <h4>Description</h4>
                <p>{selectedTicket.description}</p>
              </div>

              {selectedTicket.attachment_name && (
                <div className="modal-attachment">
                  <h4>Attachment</h4>
                  <span>{selectedTicket.attachment_name}</span>
                </div>
              )}

              <div className="modal-actions">
                <h4>Update Status</h4>
                <div className="status-buttons">
                  <button
                    className={`status-btn open ${selectedTicket.status === "open" ? "active" : ""}`}
                    onClick={() => updateTicketStatus(selectedTicket.id, "open")}
                  >
                    Open
                  </button>
                  <button
                    className={`status-btn progress ${selectedTicket.status === "in_progress" ? "active" : ""}`}
                    onClick={() => updateTicketStatus(selectedTicket.id, "in_progress")}
                  >
                    In Progress
                  </button>
                  <button
                    className={`status-btn resolved ${selectedTicket.status === "resolved" ? "active" : ""}`}
                    onClick={() => updateTicketStatus(selectedTicket.id, "resolved")}
                  >
                    Resolved
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
