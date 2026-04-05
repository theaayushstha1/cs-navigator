import React from "react";
import { FaGithub } from "@react-icons/all-files/fa/FaGithub";
import { FaStar } from "@react-icons/all-files/fa/FaStar";
import { FaCodeBranch } from "@react-icons/all-files/fa/FaCodeBranch";
import { FaTimes } from "@react-icons/all-files/fa/FaTimes";
import "./WelcomeModal.css";

const GITHUB_REPO = "https://github.com/theaayushstha1/cs-chatbot-morganstate";

export default function WelcomeModal({ onClose }) {
  return (
    <div className="welcome-overlay" onClick={onClose}>
      <div className="welcome-modal" onClick={(e) => e.stopPropagation()}>
        <button className="welcome-close" onClick={onClose}>
          <FaTimes size={16} />
        </button>

        <div className="welcome-header">
          <h2>Welcome to CS Navigator</h2>
          <p className="welcome-subtitle">
            Your AI-powered academic advisor for Morgan State CS.
          </p>
        </div>

        <div className="welcome-body">
          <p>
            CS Navigator is open source. If it helps you out, consider
            starring the repo or contributing.
          </p>

          <div className="welcome-actions">
            <a
              href={GITHUB_REPO}
              target="_blank"
              rel="noopener noreferrer"
              className="welcome-btn star-btn"
            >
              <FaStar size={16} />
              <span>Star on GitHub</span>
            </a>
            <a
              href={`${GITHUB_REPO}/fork`}
              target="_blank"
              rel="noopener noreferrer"
              className="welcome-btn fork-btn"
            >
              <FaCodeBranch size={16} />
              <span>Fork & Contribute</span>
            </a>
          </div>

          <p className="welcome-contribute">
            Want to add a feature or fix a bug? Fork the repo, make your changes,
            and open a pull request.
          </p>
        </div>

        <div className="welcome-footer">
          <a
            href={GITHUB_REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="welcome-dev"
          >
            <FaGithub size={14} />
            <span>View on GitHub</span>
          </a>
          <button className="welcome-dismiss" onClick={onClose}>
            Got it, let's go
          </button>
        </div>
      </div>
    </div>
  );
}
