# CS Navigator

**An AI-Powered Academic Assistant for University Students**

CS Navigator is a full-stack RAG (Retrieval-Augmented Generation) chatbot that helps Computer Science students at Morgan State University navigate their academic journey. It answers questions about courses, degree requirements, campus resources, and career guidance using AI-powered semantic search.

> **Current Version:** 3.0 | **Latest:** Optimized multi-agent architecture with security hardening

---

## Demo

**Live Application:** [https://inavigator.ai](https://inavigator.ai)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  ┌─────────────┐                                                   │
│  │   React     │  Single Page Application (Vite + Tailwind CSS)    │
│  │   Frontend  │  Voice input/output, Multi-session chat           │
│  └──────┬──────┘                                                   │
└─────────┼───────────────────────────────────────────────────────────┘
          │ HTTPS
┌─────────┼───────────────────────────────────────────────────────────┐
│         ▼              APPLICATION LAYER                            │
│  ┌─────────────┐     ┌─────────────────────────────────────────┐   │
│  │   Nginx     │────▶│          FastAPI Backend                │   │
│  │   Proxy     │     │  - JWT Authentication                   │   │
│  └─────────────┘     │  - REST API (25+ endpoints)             │   │
│                      │  - File upload handling                 │   │
│                      └──────────────┬──────────────────────────┘   │
└─────────────────────────────────────┼───────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────┐
│                        AI/ML LAYER  │                               │
│  ┌──────────────────────────────────▼─────────────────────────┐    │
│  │                    LangChain RAG Pipeline                   │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │    │
│  │  │   Query     │───▶│   Vector    │───▶│   Context   │     │    │
│  │  │   Embedding │    │   Search    │    │   Assembly  │     │    │
│  │  └─────────────┘    └─────────────┘    └──────┬──────┘     │    │
│  │                                               │             │    │
│  │                                        ┌──────▼──────┐      │    │
│  │                                        │   OpenAI    │      │    │
│  │                                        │   GPT-3.5   │      │    │
│  │                                        └─────────────┘      │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         CACHING LAYER                               │
│  ┌─────────────────┐          ┌─────────────────┐                  │
│  │  L1: In-Memory  │          │  L2: Redis      │                  │
│  │  - LRU Cache    │   miss   │  Cloud          │                  │
│  │  - 500 entries  │─────────▶│  - Distributed  │                  │
│  │  - ~0.001ms     │          │  - 24hr TTL     │                  │
│  │  - 1hr TTL      │◀─────────│  - ~1-2ms       │                  │
│  └─────────────────┘  promote └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                 │
│  ┌─────────────────┐          ┌─────────────────┐                  │
│  │  AWS RDS MySQL  │          │ Pinecone Vector │                  │
│  │  - Users        │          │ Database        │                  │
│  │  - Chat History │          │ - 11 Knowledge  │                  │
│  │  - Sessions     │          │   Sources       │                  │
│  │  - DegreeWorks  │          │ - Semantic      │                  │
│  └─────────────────┘          │   Embeddings    │                  │
│                               └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## How RAG Works

```
User Question: "What are the prerequisites for COSC 311?"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. EMBED: Convert question to 1536-dimensional vector       │
│    using OpenAI text-embedding-3-small                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. RETRIEVE: Search Pinecone for semantically similar       │
│    documents (top 5 matches from knowledge base)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AUGMENT: Combine retrieved context with user question    │
│    into a structured prompt                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. GENERATE: Send to GPT-3.5 to produce grounded response   │
│    based on actual university data                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
Answer: "COSC 311 (Data Structures) requires COSC 211
        (Object-Oriented Programming) and MATH 241..."
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React 19 + Vite | Fast, modern SPA |
| Styling | Tailwind CSS | Utility-first CSS |
| Backend | FastAPI (Python 3.11) | High-performance API |
| Database | AWS RDS MySQL | User data, chat history |
| Cache L1 | In-Memory LRU | Ultra-fast query cache (~0.001ms) |
| Cache L2 | Redis Cloud | Distributed cache (~1-2ms) |
| Vector DB | Pinecone | Semantic search |
| AI Model | OpenAI GPT-3.5-turbo | Response generation |
| Embeddings | text-embedding-3-small | Vector conversion |
| Auth | JWT + bcrypt | Secure authentication |
| Deployment | Docker + AWS EC2 | Containerized hosting |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **AI Chat** | Context-aware responses grounded in university data |
| **Multi-Tier Cache** | 56x faster responses with L1 + L2 caching (14s → 0.25s) |
| **Voice Mode** | Speech-to-text input, text-to-speech output |
| **SSE Streaming** | Real-time response streaming with status updates |
| **Curriculum Tracker** | Visual progress through CS degree requirements |
| **DegreeWorks Parser** | Upload PDF transcripts for automatic grade import |
| **Multi-Session** | Create and manage multiple conversation threads |
| **Admin Dashboard** | Manage knowledge base, view analytics, handle tickets |

---

## Project Structure

```
cs-chatbot-morganstate/
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/       # UI components
│   │   ├── pages/            # Route pages
│   │   └── App.jsx           # Main app entry
│   └── Dockerfile
│
├── backend/                  # FastAPI application
│   ├── main.py               # API endpoints (~3000 lines)
│   ├── security.py           # JWT authentication
│   ├── ingestion.py          # Vector DB ingestion
│   ├── datasource/           # Knowledge base JSON files
│   └── Dockerfile
│
├── docker-compose.yml        # Container orchestration
├── deploy.sh                 # One-command deployment
└── README.md
```

---

## Quick Start

### Prerequisites
- Docker Desktop
- OpenAI API Key
- Pinecone API Key

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/theaayushstha1/cs-chatbot-morganstate.git
cd cs-chatbot-morganstate

# 2. Create .env file in backend/
OPENAI_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX=your_index
JWT_SECRET=your_secret
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db

# Redis Cache (optional - falls back to in-memory only)
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# 3. Run with Docker
docker-compose up --build

# 4. Access application
# Frontend: http://localhost:3000
# Backend:  http://localhost:5000
```

### Production Deployment

```bash
# One-command deploy to EC2
bash deploy.sh
```

---

## API Overview

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/chat` | POST | Yes | Send message, receive AI response |
| `/chat/stream` | POST | Yes | SSE streaming chat response |
| `/api/register` | POST | No | Create user account |
| `/api/login` | POST | No | Authenticate, receive JWT |
| `/api/profile` | GET/PUT | Yes | User profile management |
| `/api/cache/stats` | GET | No | Cache hit rates and statistics |
| `/chat-history` | GET | Yes | Retrieve conversation history |
| `/sessions` | GET/POST/DELETE | Yes | Manage chat sessions |
| `/api/curriculum` | GET | Yes | CS curriculum data |
| `/api/degreeworks/upload-pdf` | POST | Yes | Upload transcript PDF |

---

## Knowledge Base

The chatbot is trained on 11 curated knowledge sources:

1. **CS Courses** - All 45+ CS course descriptions
2. **Curriculum Requirements** - 120 credit hour breakdown
3. **Faculty Directory** - Professors and office hours
4. **Career Resources** - Internships, jobs, resume tips
5. **Campus Facilities** - Labs, library, study spaces
6. **Academic Policies** - Grading, registration, deadlines
7. **Student Organizations** - CS clubs and events
8. **Research Opportunities** - Labs and projects
9. **Graduate Programs** - MS/PhD pathways
10. **FAQ** - Common student questions
11. **Contact Information** - Department contacts

---

## Version History

| Version | Release | Highlights |
|---------|---------|------------|
| **v3.0** | Mar 2026 | Optimized multi-agent architecture, 4 specialized datastores, security hardening |
| **v2.2** | Mar 2026 | Multi-tier caching (L1 + Redis Cloud), 56x faster responses |
| **v2.1** | Mar 2026 | SSE streaming, cache warmup, data cleanup |
| **v2.0** | Feb 2026 | Google ADK AI Agent, voice mode, admin dashboard |
| **v1.0** | Jan 2026 | Initial RAG pipeline with Pinecone + OpenAI |

---

## v3.0 Changelog (March 9, 2026)

### Agent Architecture Optimization
- **4 specialized datastores** replacing 1 shared datastore for better retrieval precision
  - `academic-kb` (13 docs): courses, prerequisites, degree requirements, faculty
  - `career-kb` (5 docs): career paths, internships, job resources
  - `financial-kb` (14 docs): scholarships, FAFSA, tuition, financial aid
  - `general-kb` (12 docs): department info, contacts, student orgs
- **Dual-model strategy**: `gemini-2.0-flash` for routing, `gemini-2.5-flash` for specialists
- **Smart routing**: Router handles greetings/trivial queries directly (1 LLM hop instead of 3)
- **Enriched specialist prompts** with domain-specific facts and strict grounding rules
- **Response format rules**: concise, under 300 words, bullet points, bold key info

### Performance
- Greeting latency: ~6s to **1.7s** (72% faster)
- Simple factual queries: ~10% faster
- Benchmark across all 7 specialists: average 12.6s

### Security Hardening (Promptfoo Red-Teaming)
- 23 automated test cases across 6 categories
- **3 critical vulnerabilities found and patched:**
  - Prompt injection (agent complied with "ignore instructions" attacks)
  - System prompt leakage (dumped full system prompt when asked)
  - Instruction smuggling (accepted fake "SYSTEM UPDATE" commands)
- Added 5 strict security rules to router system prompt
- Final score: 23/23 (100% effective pass rate)

### Agent Files
- Agent code: `adk_agent/cs_navigator_unified/agent.py`
- Security eval config: `adk_agent/cs_navigator_unified/promptfooconfig.yaml`
- Deploy scripts: `adk_agent/cs_navigator_unified/deploy.py`

---

## Contributors

- **Aayush Shrestha** - Cloud Architecture & Backend
- **Sakina Shrestha** - Core Development
- **Morgan State University** - Computer Science Department

---

## License

MIT License - See [LICENSE](./LICENSE) for details.
