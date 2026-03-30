import { useState } from "react";
import { Link } from "react-router-dom";
import { getApiBase } from "./lib/apiBase";
import "./Login.css";

const API_BASE = getApiBase();

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (res.ok) {
        setSent(true);
      } else {
        setError(data.detail || "Something went wrong");
      }
    } catch (err) {
      setError("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <h1 className="login-title" style={{ color: "var(--msu-blue)" }}>Reset Password</h1>
          <p className="login-subtitle">
            {sent ? "Check your email" : "Enter your email to receive a reset link"}
          </p>

          {sent ? (
            <div style={{ textAlign: "center", padding: "20px 0" }}>
              <div style={{ fontSize: "48px", marginBottom: "16px" }}>
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <circle cx="24" cy="24" r="24" fill="#e8f5e9"/>
                  <path d="M15 24l6 6 12-12" stroke="#34A853" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                If an account exists for <strong>{email}</strong>, we've sent a password reset link. Check your inbox.
              </p>
              <Link to="/login" style={{ color: "var(--msu-blue)", fontWeight: 600, textDecoration: "none", display: "inline-block", marginTop: "16px" }}>
                Back to Login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && <div className="error-message">{error}</div>}

              <div className="input-group">
                <label>Email Address</label>
                <div className="input-wrapper">
                  <span className="input-icon">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M2 4l6 4 6-4v8H2V4zm0-1h12a1 1 0 011 1v8a1 1 0 01-1 1H2a1 1 0 01-1-1V4a1 1 0 011-1z"/></svg>
                  </span>
                  <input
                    type="email"
                    placeholder="your-email@morgan.edu"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="login-btn" disabled={loading}>
                {loading ? "Sending..." : "Send Reset Link"}
              </button>

              <p className="signup-link">
                Remember your password? <Link to="/login">Log in</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
