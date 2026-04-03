# CS Navigator

**An AI-Powered Academic Assistant for University Students**

CS Navigator is a full-stack AI chatbot built on Google ADK (Agent Development Kit) that helps Computer Science students at Morgan State University navigate their academic journey. It uses a multi-agent architecture with RAG retrieval, DegreeWorks integration, and multi-tier caching to deliver fast, personalized academic advising.

> **Current Version:** 2.2 | **Live:** [https://cs.inavigator.ai](https://cs.inavigator.ai) | **Deployed on:** Google Cloud Run

---

## System Architecture

```
CLIENT LAYER
  React 19 + Vite SPA
  PWA-enabled, Voice I/O, Multi-session Chat
          |
          | HTTPS
          v
APPLICATION LAYER
  Nginx Reverse Proxy (Cloud Run)
          |
          v
  FastAPI Backend (Python 3.11)
  - JWT Authentication (bcrypt + JOSE)
  - REST API (30+ endpoints)
  - SSE Streaming Chat
  - File Upload / DegreeWorks PDF Parser
  - Multi-tier Cache (L1 In-Memory + L2 Redis Cloud + Semantic)
          |
          v
AI / AGENT LAYER
  Google ADK Agent Engine
  - cs_navigator_unified agent
  - Tool-based architecture (search, curriculum, advising)
  - Pinecone RAG retrieval (text-embedding-004)
  - Session-aware conversation memory
          |
          v
DATA LAYER
  AWS RDS MySQL        Pinecone Vector DB       Redis Cloud
  - Users/Auth         - 13 Knowledge Sources   - Distributed Cache
  - Chat History       - Semantic Embeddings    - 24hr TTL
  - DegreeWorks        - text-embedding-004     - Semantic Similarity
  - Support Tickets
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React 19 + Vite | PWA-enabled SPA with SSE streaming |
| Backend | FastAPI (Python 3.11) | High-performance async API server |
| AI Engine | Google ADK | Multi-agent orchestration |
| Database | AWS RDS MySQL | User data, chat history, DegreeWorks |
| Cache L1 | In-Memory TTLCache | Ultra-fast query cache (~0.001ms) |
| Cache L2 | Redis Cloud | Distributed cache with 24hr TTL (~1-2ms) |
| Cache L3 | Semantic Cache | Embedding similarity matching (0.78 threshold) |
| Vector DB | Pinecone | RAG semantic search |
| Embeddings | Google text-embedding-004 | 256-dim vector conversion |
| Auth | JWT + bcrypt | Stateless token authentication |
| Deployment | Google Cloud Run | Auto-scaling containerized hosting |
| CI/CD | gcloud CLI | Source-based deploys with min-instances warmth |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **AI Chat with Streaming** | Real-time SSE streaming with thinking status updates |
| **Multi-Tier Cache** | L1 + L2 + Semantic cache, 56x faster repeat responses |
| **Regenerate Response** | Cache-bypass regeneration for fresh, detailed answers |
| **Voice Mode** | Speech-to-text input + text-to-speech output |
| **DegreeWorks Integration** | Upload PDF transcripts, auto-parse courses and GPA |
| **Curriculum Tracker** | Visual progress through CS degree requirements |
| **Multi-Session Chat** | Create, rename, delete conversation threads with date grouping |
| **Guest Trial** | 15-minute free trial with timer, no account required |
| **Admin Dashboard** | Knowledge base management, analytics, support tickets |
| **PWA Support** | Installable app with offline caching via Workbox |
| **File Uploads** | Drag-and-drop with type/size validation (10MB max) |
| **Code Highlighting** | Syntax-highlighted code blocks with copy button |
| **Dark Mode** | Full dark theme with smooth transitions |

---

## Project Structure

```
cs-chatbot/
├── frontend/                    # React 19 + Vite application
│   ├── src/
│   │   ├── components/          # Chat, Sidebar, Profile, Curriculum, Admin
│   │   ├── lib/                 # API base URL config
│   │   ├── App.jsx              # Router + session management
│   │   └── index.css            # CSS variables + dark mode
│   ├── public/                  # Static assets (WebP optimized)
│   ├── nginx.cloudrun.conf      # Cloud Run nginx config
│   ├── Dockerfile.cloudrun      # Cloud Run frontend container
│   └── vite.config.js           # Build config + PWA + console stripping
│
├── backend/                     # FastAPI application
│   ├── main.py                  # API server (~3000 lines, 30+ endpoints)
│   ├── cache.py                 # Multi-tier cache (L1 + L2 + Semantic)
│   ├── security.py              # JWT creation + verification
│   ├── models.py                # SQLAlchemy ORM models
│   ├── db.py                    # Database connection
│   ├── data_sources/            # 13 JSON knowledge base files
│   ├── ingestion.py             # Pinecone vector ingestion
│   └── Dockerfile               # Backend container
│
├── adk_agent/                   # Google ADK Agent
│   ├── cs_navigator_unified/    # Unified agent with tools
│   │   └── agent.py             # Agent definition + tool config
│   └── Dockerfile               # ADK container
│
├── CLAUDE.md                    # AI assistant context
├── STARTUP.md                   # Local development instructions
└── README.md
```

---

## Quick Start

### Prerequisites
- Python 3.11+, Node.js 18+
- Google Cloud SDK (for ADK + deployment)
- API Keys: OpenAI, Pinecone, Google Cloud

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/theaayushstha1/cs-chatbot-morganstate.git
cd cs-chatbot-morganstate

# 2. Create .env file in project root
OPENAI_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX=your_index
JWT_SECRET=your_secret
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your_secure_password

# 3. Start ADK Engine (Terminal 1)
cd adk_agent && python -m google.adk.cli web . --port 8080

# 4. Start Backend (Terminal 2)
cd backend && uvicorn main:app --reload --port 8000

# 5. Start Frontend (Terminal 3)
cd frontend && npm install && npm run dev

# 6. Open http://localhost:5173
```

### Cloud Run Deployment

```bash
# Deploy all three services
gcloud run deploy csnavigator-frontend --source frontend/ --region=us-central1 --min-instances=1
gcloud run deploy csnavigator-backend --source backend/ --region=us-central1 --min-instances=1
gcloud run deploy csnavigator-adk --source adk_agent/ --region=us-central1 --min-instances=1
```

---

## API Overview

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/chat/stream` | POST | JWT | SSE streaming chat (supports `skip_cache`) |
| `/chat/guest` | POST | No | Rate-limited guest chat |
| `/api/register` | POST | No | Create account (email + 8-char password) |
| `/api/login` | POST | No | Authenticate, receive JWT |
| `/api/profile` | GET/PUT | JWT | User profile + picture upload |
| `/api/curriculum` | GET | JWT | Full CS curriculum data |
| `/api/degreeworks/upload-pdf` | POST | JWT | Parse DegreeWorks transcript |
| `/api/degreeworks/sync` | POST | JWT | Sync parsed data to profile |
| `/sessions` | GET/POST/DELETE | JWT | Chat session management |
| `/chat-history` | GET | JWT | Retrieve conversation history |
| `/api/cache/stats` | GET | No | Cache hit rates and performance |
| `/api/tts` | POST | JWT | Text-to-speech generation |

---

## Knowledge Base

13 curated JSON knowledge sources covering:

| Source | Content |
|--------|---------|
| CS Courses | 45+ course descriptions with prerequisites |
| Degree Programs | B.S. CS, B.S. Cloud Computing, M.S., Ph.D. requirements |
| Faculty Directory | 16+ professors with specializations and contact info |
| Academic Advising | Advisor assignments, forms, override process |
| Tutoring & Support | CASA, AEP, CS tutoring, NetTutor, Writing Center |
| Registration | Credit limits, forms, add/drop, grade appeals |
| Financial Aid | Scholarships, FAFSA, SAP requirements, deadlines |
| Academic Calendar | Fall/Spring/Summer dates, finals, commencement |
| Library Services | Richardson Library, databases, research access |
| University Leadership | President, Provost, Dean, Department Chair |
| Career Resources | Internships, career development |
| Honors Programs | SCMNS Honors, Adams Honors College |
| 4+1 Program | Accelerated B.S./M.S. pathway |

---

## Security

- CORS restricted to known origins (not wildcard)
- JWT tokens with bcrypt password hashing
- Email format + password strength validation on registration
- File upload validation (type whitelist + 10MB size limit)
- No hardcoded credentials (all via environment variables)
- Database connection strings masked in logs
- Console logs stripped from production builds
- Input length limits on all user-facing text fields
- TrustedHost middleware with explicit allowed hosts

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| **v2.2** | Mar 2026 | Visual polish, security hardening, Cloud Run warm instances, regenerate cache bypass, WebP assets, knowledge-base-aligned suggestions |
| **v2.1** | Mar 2026 | SSE streaming, cache warmup, data cleanup |
| **v2.0** | Feb 2026 | Google ADK AI Agent, voice mode, admin dashboard |
| **v1.0** | Jan 2026 | Initial RAG pipeline with Pinecone + OpenAI |

---

## Contributors

- **Aayush Shrestha** - Cloud Architecture, Backend, AI Agent
- **Sakina Shrestha** - Core Development
- **Morgan State University** - Computer Science Department

---

## License

MIT License - See [LICENSE](./LICENSE) for details.
