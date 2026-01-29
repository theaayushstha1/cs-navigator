# CS Navigator

**An AI-Powered Academic Assistant for University Students**

CS Navigator is a full-stack RAG (Retrieval-Augmented Generation) chatbot that helps Computer Science students at Morgan State University navigate their academic journey. It answers questions about courses, degree requirements, campus resources, and career guidance using AI-powered semantic search.

---

## Demo

**Live Application:** [http://100.48.56.24:3000](http://100.48.56.24:3000)

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
| **Voice Mode** | Speech-to-text input, text-to-speech output |
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
| `/api/register` | POST | No | Create user account |
| `/api/login` | POST | No | Authenticate, receive JWT |
| `/api/profile` | GET/PUT | Yes | User profile management |
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

## Contributors

- **Aayush Shrestha** - Cloud Architecture & Backend
- **Sakina Shrestha** - Core Development
- **Morgan State University** - Computer Science Department

---

## License

MIT License - See [LICENSE](./LICENSE) for details.
