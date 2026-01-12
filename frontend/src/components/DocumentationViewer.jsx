import React, { useState, useEffect, useRef } from 'react';
import { FaTimes } from '@react-icons/all-files/fa/FaTimes';
import { FaBook } from '@react-icons/all-files/fa/FaBook';
import { FaProjectDiagram } from '@react-icons/all-files/fa/FaProjectDiagram';
import { FaServer } from '@react-icons/all-files/fa/FaServer';
import { FaCode } from '@react-icons/all-files/fa/FaCode';
import { FaRoad } from '@react-icons/all-files/fa/FaRoad';
import { FaCheckCircle } from '@react-icons/all-files/fa/FaCheckCircle';
import { FaClock } from '@react-icons/all-files/fa/FaClock';
import { FaRocket } from '@react-icons/all-files/fa/FaRocket';
import './DocumentationViewer.css';

export default function DocumentationViewer({ isOpen, onClose, darkMode, mode = 'technical' }) {
  const [activeTab, setActiveTab] = useState('overview');
  const mermaidRef = useRef(null);

  const technicalTabs = [
    { id: 'overview', label: 'Overview', icon: FaBook },
    { id: 'architecture', label: 'Architecture', icon: FaProjectDiagram },
    { id: 'workflow', label: 'Workflow', icon: FaServer },
    { id: 'api', label: 'API Docs', icon: FaCode },
  ];

  const roadmapTabs = [
    { id: 'completed', label: 'Completed', icon: FaCheckCircle },
    { id: 'current', label: 'In Progress', icon: FaClock },
    { id: 'planned', label: 'Planned', icon: FaRocket },
  ];

  const tabs = mode === 'roadmap' ? roadmapTabs : technicalTabs;

  useEffect(() => {
    if (isOpen) {
      setActiveTab(mode === 'roadmap' ? 'completed' : 'overview');
    }
  }, [isOpen, mode]);

  // Render mermaid diagrams
  useEffect(() => {
    if (isOpen && (activeTab === 'architecture' || activeTab === 'workflow')) {
      const renderMermaid = async () => {
        try {
          const mermaid = (await import('mermaid')).default;
          mermaid.initialize({
            startOnLoad: false,
            theme: darkMode ? 'dark' : 'default',
            securityLevel: 'loose',
          });

          const elements = document.querySelectorAll('.mermaid-diagram');
          elements.forEach(async (el, index) => {
            const code = el.getAttribute('data-diagram');
            if (code) {
              try {
                const { svg } = await mermaid.render(`mermaid-${activeTab}-${index}`, code);
                el.innerHTML = svg;
              } catch (e) {
                console.error('Mermaid render error:', e);
              }
            }
          });
        } catch (e) {
          console.error('Mermaid import error:', e);
        }
      };

      setTimeout(renderMermaid, 100);
    }
  }, [isOpen, activeTab, darkMode]);

  if (!isOpen) return null;

  const renderOverview = () => (
    <div className="doc-section">
      <h2>CS Navigator - Technical Documentation</h2>
      <p className="doc-intro">
        CS Navigator is an AI-powered academic assistant that uses RAG (Retrieval-Augmented Generation)
        to help Computer Science students at Morgan State University.
      </p>

      <h3>Technology Stack</h3>
      <table className="doc-table">
        <thead>
          <tr>
            <th>Layer</th>
            <th>Technology</th>
            <th>Purpose</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Frontend</td><td>React + Vite</td><td>Modern SPA with fast HMR</td></tr>
          <tr><td>Backend</td><td>FastAPI (Python)</td><td>High-performance REST API</td></tr>
          <tr><td>Database</td><td>AWS RDS MySQL</td><td>User data, chat history</td></tr>
          <tr><td>Vector DB</td><td>Pinecone</td><td>Semantic search for RAG</td></tr>
          <tr><td>AI Model</td><td>OpenAI GPT-3.5</td><td>Response generation</td></tr>
          <tr><td>Deployment</td><td>Docker + EC2</td><td>Containerized cloud hosting</td></tr>
        </tbody>
      </table>

      <h3>Key Features</h3>
      <ul className="doc-features">
        <li><strong>AI Chat</strong> - Context-aware responses grounded in university data</li>
        <li><strong>Voice Mode</strong> - Speech-to-text and text-to-speech</li>
        <li><strong>Curriculum Tracker</strong> - Visual degree progress</li>
        <li><strong>DegreeWorks Parser</strong> - Upload PDF transcripts</li>
        <li><strong>Multi-Session</strong> - Multiple conversation threads</li>
        <li><strong>Admin Dashboard</strong> - Knowledge base management</li>
      </ul>

      <h3>Knowledge Sources</h3>
      <p>The chatbot is trained on <strong>11 curated knowledge sources</strong> including:</p>
      <div className="doc-grid">
        <span>CS Course Catalog</span>
        <span>Degree Requirements</span>
        <span>Faculty Directory</span>
        <span>Career Resources</span>
        <span>Campus Facilities</span>
        <span>Academic Policies</span>
        <span>Student Organizations</span>
        <span>Research Opportunities</span>
        <span>Graduate Programs</span>
        <span>FAQ</span>
        <span>Contact Info</span>
      </div>
    </div>
  );

  const renderArchitecture = () => (
    <div className="doc-section">
      <h2>System Architecture</h2>
      <p>The system follows a modern microservices architecture with clear separation of concerns.</p>

      <div
        className="mermaid-diagram"
        data-diagram={`flowchart TB
    subgraph Client["Client Layer"]
        Browser["Web Browser"]
        React["React SPA"]
    end

    subgraph Server["Application Layer"]
        Nginx["Nginx Proxy"]
        FastAPI["FastAPI Backend"]
    end

    subgraph AI["AI/ML Layer"]
        LangChain["LangChain"]
        OpenAI["OpenAI GPT-3.5"]
    end

    subgraph Data["Data Layer"]
        MySQL[("AWS RDS MySQL")]
        Pinecone[("Pinecone Vector DB")]
    end

    Browser --> React
    React --> Nginx
    Nginx --> FastAPI
    FastAPI --> LangChain
    LangChain --> OpenAI
    LangChain --> Pinecone
    FastAPI --> MySQL`}
      />

      <h3>Layer Descriptions</h3>
      <table className="doc-table">
        <thead>
          <tr><th>Layer</th><th>Components</th><th>Responsibility</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Client</strong></td>
            <td>React, Vite, Tailwind</td>
            <td>User interface, state management, API calls</td>
          </tr>
          <tr>
            <td><strong>Application</strong></td>
            <td>Nginx, FastAPI, JWT</td>
            <td>Request routing, authentication, business logic</td>
          </tr>
          <tr>
            <td><strong>AI/ML</strong></td>
            <td>LangChain, OpenAI</td>
            <td>RAG pipeline, embeddings, response generation</td>
          </tr>
          <tr>
            <td><strong>Data</strong></td>
            <td>MySQL, Pinecone</td>
            <td>Persistent storage, vector similarity search</td>
          </tr>
        </tbody>
      </table>
    </div>
  );

  const renderWorkflow = () => (
    <div className="doc-section">
      <h2>RAG Pipeline Workflow</h2>
      <p>How questions are processed and answered using Retrieval-Augmented Generation.</p>

      <div
        className="mermaid-diagram"
        data-diagram={`sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant P as Pinecone
    participant O as OpenAI

    U->>F: Ask question
    F->>B: POST /chat
    B->>B: Embed query (1536 dims)
    B->>P: Vector similarity search
    P-->>B: Top 5 relevant docs
    B->>O: Query + Context
    O-->>B: Generated answer
    B-->>F: JSON response
    F-->>U: Display answer`}
      />

      <h3>RAG Process Steps</h3>
      <div className="workflow-steps">
        <div className="step">
          <div className="step-number">1</div>
          <div className="step-content">
            <h4>EMBED</h4>
            <p>Convert user question to a 1536-dimensional vector using OpenAI embeddings</p>
          </div>
        </div>
        <div className="step">
          <div className="step-number">2</div>
          <div className="step-content">
            <h4>RETRIEVE</h4>
            <p>Search Pinecone for semantically similar documents from knowledge base</p>
          </div>
        </div>
        <div className="step">
          <div className="step-number">3</div>
          <div className="step-content">
            <h4>AUGMENT</h4>
            <p>Combine retrieved context with the original question into a prompt</p>
          </div>
        </div>
        <div className="step">
          <div className="step-number">4</div>
          <div className="step-content">
            <h4>GENERATE</h4>
            <p>GPT-3.5 produces a grounded response based on actual university data</p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderAPI = () => (
    <div className="doc-section">
      <h2>API Documentation</h2>
      <p>REST API endpoints available in the FastAPI backend.</p>

      <h3>Authentication</h3>
      <table className="doc-table">
        <thead>
          <tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>/api/register</code></td><td>POST</td><td>Create new user account</td></tr>
          <tr><td><code>/api/login</code></td><td>POST</td><td>Authenticate, receive JWT token</td></tr>
          <tr><td><code>/api/profile</code></td><td>GET/PUT</td><td>View or update user profile</td></tr>
        </tbody>
      </table>

      <h3>Chat</h3>
      <table className="doc-table">
        <thead>
          <tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>/chat</code></td><td>POST</td><td>Send message, receive AI response</td></tr>
          <tr><td><code>/chat-history</code></td><td>GET</td><td>Retrieve conversation history</td></tr>
          <tr><td><code>/sessions</code></td><td>GET/POST/DELETE</td><td>Manage chat sessions</td></tr>
          <tr><td><code>/reset-history</code></td><td>POST</td><td>Clear chat history</td></tr>
        </tbody>
      </table>

      <h3>Academic</h3>
      <table className="doc-table">
        <thead>
          <tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>/api/curriculum</code></td><td>GET</td><td>Get CS curriculum data</td></tr>
          <tr><td><code>/api/degreeworks</code></td><td>GET</td><td>View degree audit data</td></tr>
          <tr><td><code>/api/degreeworks/upload-pdf</code></td><td>POST</td><td>Upload transcript PDF</td></tr>
        </tbody>
      </table>

      <h3>Admin</h3>
      <table className="doc-table">
        <thead>
          <tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>/api/admin/users</code></td><td>GET</td><td>List all users</td></tr>
          <tr><td><code>/api/admin/analytics</code></td><td>GET</td><td>View usage analytics</td></tr>
          <tr><td><code>/api/admin/tickets</code></td><td>GET</td><td>View support tickets</td></tr>
          <tr><td><code>/api/admin/knowledge-base</code></td><td>GET</td><td>Search knowledge base</td></tr>
        </tbody>
      </table>

      <h3>Request Example</h3>
      <pre className="code-block">
{`POST /chat
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "query": "What are the prerequisites for COSC 311?",
  "session_id": "default"
}`}
      </pre>

      <h3>Response Example</h3>
      <pre className="code-block">
{`{
  "response": "COSC 311 (Data Structures) requires COSC 211
              (Object-Oriented Programming) and MATH 241
              (Calculus I) as prerequisites."
}`}
      </pre>
    </div>
  );

  // ========== ROADMAP CONTENT ==========
  const renderCompleted = () => (
    <div className="doc-section">
      <h2>Phase 1: Core Platform (Completed)</h2>
      <p className="phase-desc">Foundation and essential features</p>

      <div className="roadmap-list">
        <div className="roadmap-item done">
          <FaCheckCircle className="item-icon" />
          <div><strong>RAG Chat Engine</strong> - Vector search + GPT responses grounded in MSU data</div>
        </div>
        <div className="roadmap-item done">
          <FaCheckCircle className="item-icon" />
          <div><strong>Auth & Sessions</strong> - JWT authentication, multi-conversation support</div>
        </div>
        <div className="roadmap-item done">
          <FaCheckCircle className="item-icon" />
          <div><strong>Curriculum Tracker</strong> - Visual degree progress with DegreeWorks parsing</div>
        </div>
        <div className="roadmap-item done">
          <FaCheckCircle className="item-icon" />
          <div><strong>Voice Mode</strong> - OpenAI TTS/STT for hands-free interaction</div>
        </div>
        <div className="roadmap-item done">
          <FaCheckCircle className="item-icon" />
          <div><strong>Admin Dashboard</strong> - User management, tickets, knowledge base editor</div>
        </div>
        <div className="roadmap-item done">
          <FaCheckCircle className="item-icon" />
          <div><strong>11 Knowledge Sources</strong> - Courses, faculty, careers, policies, FAQs</div>
        </div>
      </div>

      <h3>Proven Impact (Industry Research)</h3>
      <table className="doc-table">
        <thead>
          <tr><th>University</th><th>Chatbot</th><th>Result</th></tr>
        </thead>
        <tbody>
          <tr><td>Georgia State</td><td>Pounce</td><td>21.4% reduction in summer melt</td></tr>
          <tr><td>U. of Galway</td><td>Cara</td><td>80%+ inquiries handled autonomously</td></tr>
          <tr><td>Staffordshire</td><td>Beacon</td><td>Improved retention rates</td></tr>
        </tbody>
      </table>
    </div>
  );

  const renderCurrent = () => (
    <div className="doc-section">
      <h2>Phase 2: Optimization (In Progress)</h2>
      <p className="phase-desc">Performance improvements and quality assurance</p>

      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Response Time</span>
          <span className="metric-current">2.5s</span>
          <span className="metric-arrow">→</span>
          <span className="metric-target">&lt;1.5s</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Accuracy</span>
          <span className="metric-current">88%</span>
          <span className="metric-arrow">→</span>
          <span className="metric-target">92%</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Test Coverage</span>
          <span className="metric-current">40%</span>
          <span className="metric-arrow">→</span>
          <span className="metric-target">80%</span>
        </div>
      </div>

      <div className="roadmap-list">
        <div className="roadmap-item progress">
          <FaClock className="item-icon" />
          <div><strong>Hybrid Search</strong> - Combine vector + BM25 keyword search (+15-20% accuracy)</div>
        </div>
        <div className="roadmap-item progress">
          <FaClock className="item-icon" />
          <div><strong>Redis Caching</strong> - 40-60% faster responses for common queries</div>
        </div>
        <div className="roadmap-item progress">
          <FaClock className="item-icon" />
          <div><strong>CI/CD Pipeline</strong> - Automated testing and deployment</div>
        </div>
        <div className="roadmap-item progress">
          <FaClock className="item-icon" />
          <div><strong>Security Hardening</strong> - Audit and penetration testing</div>
        </div>
      </div>
    </div>
  );

  const renderPlanned = () => (
    <div className="doc-section">
      <h2>Phase 3-4: Scale & Commercialize</h2>
      <p className="phase-desc">University-wide expansion and revenue generation</p>

      <h3>Feature Expansion</h3>
      <div className="roadmap-list">
        <div className="roadmap-item planned">
          <FaRocket className="item-icon" />
          <div><strong>Multilingual Support</strong> - Spanish, Mandarin for diverse student body</div>
        </div>
        <div className="roadmap-item planned">
          <FaRocket className="item-icon" />
          <div><strong>Proactive Notifications</strong> - Deadline reminders, registration alerts</div>
        </div>
        <div className="roadmap-item planned">
          <FaRocket className="item-icon" />
          <div><strong>LMS Integration</strong> - Connect with Canvas and Banner SIS</div>
        </div>
        <div className="roadmap-item planned">
          <FaRocket className="item-icon" />
          <div><strong>Mobile App</strong> - React Native for iOS/Android</div>
        </div>
        <div className="roadmap-item planned">
          <FaRocket className="item-icon" />
          <div><strong>GraphRAG</strong> - Complex multi-hop queries across knowledge graph</div>
        </div>
      </div>

      <h3>Scale Targets</h3>
      <table className="doc-table">
        <thead>
          <tr><th>Metric</th><th>Current</th><th>12 Months</th></tr>
        </thead>
        <tbody>
          <tr><td>Active Users</td><td>500</td><td>10,000+</td></tr>
          <tr><td>Daily Messages</td><td>500</td><td>20,000+</td></tr>
          <tr><td>Knowledge Sources</td><td>11</td><td>200+</td></tr>
        </tbody>
      </table>

      <h3>Revenue Model</h3>
      <p>White-label SaaS for other universities: $1,500 - $7,500/month tiered pricing</p>
      <table className="doc-table">
        <thead>
          <tr><th>Year</th><th>Clients</th><th>Revenue</th></tr>
        </thead>
        <tbody>
          <tr><td>Year 1</td><td>5</td><td>$150K</td></tr>
          <tr><td>Year 2</td><td>15</td><td>$540K</td></tr>
          <tr><td>Year 3</td><td>40</td><td>$1.68M</td></tr>
        </tbody>
      </table>
    </div>
  );

  const renderContent = () => {
    if (mode === 'roadmap') {
      switch (activeTab) {
        case 'completed': return renderCompleted();
        case 'current': return renderCurrent();
        case 'planned': return renderPlanned();
        default: return renderCompleted();
      }
    }
    switch (activeTab) {
      case 'overview': return renderOverview();
      case 'architecture': return renderArchitecture();
      case 'workflow': return renderWorkflow();
      case 'api': return renderAPI();
      default: return renderOverview();
    }
  };

  return (
    <div className="doc-viewer-overlay" onClick={onClose}>
      <div
        className={`doc-viewer ${darkMode ? 'dark' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="doc-viewer-header">
          <h2>{mode === 'roadmap' ? 'Development Roadmap' : 'Technical Documentation'}</h2>
          <button className="doc-close-btn" onClick={onClose} title="Close">
            <FaTimes size={20} />
          </button>
        </div>

        <div className="doc-viewer-tabs">
          {tabs.map((tab) => {
            const IconComponent = tab.icon;
            return (
              <button
                key={tab.id}
                className={`doc-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <IconComponent size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <div className="doc-viewer-content" ref={mermaidRef}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
