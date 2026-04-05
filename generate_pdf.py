"""Generate CSNavigator System Architecture & Session Report PDF"""
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "CSNavigator - System Architecture & Technical Guide", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 60, 150)
        self.ln(6)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 60, 150)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(4)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(50, 50, 50)
        self.ln(3)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text, indent=15):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(5, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def code_block(self, text):
        self.set_font("Courier", "", 9)
        self.set_fill_color(240, 240, 245)
        self.set_text_color(30, 30, 30)
        y = self.get_y()
        if y > 250:
            self.add_page()
        self.multi_cell(0, 5, text, fill=True)
        self.ln(3)

    def key_value(self, key, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(40, 40, 40)
        self.cell(55, 6, key + ":")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)

# =====================================================================
# TITLE PAGE
# =====================================================================
pdf.add_page()
pdf.ln(40)
pdf.set_font("Helvetica", "B", 28)
pdf.set_text_color(30, 60, 150)
pdf.cell(0, 15, "CSNavigator", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 16)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 10, "AI-Powered Academic Advising Chatbot", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "Morgan State University - Computer Science Department", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(15)
pdf.set_font("Helvetica", "", 12)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 8, "System Architecture & Technical Guide", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "Version 4.2 (ADK) - March 2026", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(20)
pdf.set_font("Helvetica", "I", 10)
pdf.cell(0, 6, "Prepared by: Aayush Shrestha", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "For use with Google NotebookLM for interactive learning", align="C", new_x="LMARGIN", new_y="NEXT")

# =====================================================================
# TABLE OF CONTENTS
# =====================================================================
pdf.add_page()
pdf.chapter_title("Table of Contents")
toc = [
    "1. System Overview & Architecture",
    "2. The Three Services (Frontend, Backend, ADK Agent)",
    "3. Google ADK Agent - How It Works",
    "4. Backend (FastAPI) - Deep Dive",
    "5. Frontend (React + Vite) - Deep Dive",
    "6. Cloud Run Deployment",
    "7. Database & Storage",
    "8. Authentication & Security",
    "9. API Endpoints & Data Flow",
    "10. Caching Architecture",
    "11. Streaming & Real-Time Features",
    "12. Session Summary: March 24, 2026",
    "13. Local Development Setup",
    "14. Environment Variables Reference",
]
for item in toc:
    pdf.bullet(item, indent=10)

# =====================================================================
# 1. SYSTEM OVERVIEW
# =====================================================================
pdf.add_page()
pdf.chapter_title("1. System Overview & Architecture")

pdf.body_text(
    "CSNavigator is an AI-powered academic advising chatbot built for Morgan State University's "
    "Computer Science Department. It helps students with course recommendations, degree requirements, "
    "career guidance, financial aid questions, and general campus information."
)

pdf.section_title("High-Level Architecture")
pdf.body_text(
    "The system consists of three microservices deployed on Google Cloud Run, communicating "
    "via HTTP/REST APIs:"
)
pdf.code_block(
    "  [User Browser]\n"
    "       |\n"
    "       v\n"
    "  [Frontend]  (React + Vite + Nginx)\n"
    "  Cloud Run port 8080\n"
    "       |\n"
    "       v  (REST API calls)\n"
    "  [Backend]   (FastAPI + Python)\n"
    "  Cloud Run port 5000\n"
    "       |\n"
    "       v  (HTTP SSE stream)\n"
    "  [ADK Agent] (Google ADK + Gemini 2.0 Flash)\n"
    "  Cloud Run port 8080\n"
    "       |\n"
    "       v  (Vertex AI Search grounding)\n"
    "  [Knowledge Base] (45 docs in GCS + Discovery Engine)"
)

pdf.section_title("Technology Stack")
pdf.key_value("Frontend", "React 18, Vite 6, TailwindCSS, Framer Motion")
pdf.key_value("Backend", "FastAPI (Python 3.12), Uvicorn, SQLAlchemy")
pdf.key_value("AI Agent", "Google ADK 1.23, Gemini 2.0 Flash, Vertex AI Search")
pdf.key_value("Database", "MySQL (AWS RDS)")
pdf.key_value("Storage", "Google Cloud Storage (GCS)")
pdf.key_value("Search", "Vertex AI Discovery Engine (datastore)")
pdf.key_value("Auth", "JWT tokens (python-jose), bcrypt passwords")
pdf.key_value("Deployment", "Google Cloud Run (3 services)")
pdf.key_value("CI/CD", "Cloud Build (cloudbuild.yaml)")
pdf.key_value("TTS", "OpenAI API (text-to-speech only)")

# =====================================================================
# 2. THE THREE SERVICES
# =====================================================================
pdf.add_page()
pdf.chapter_title("2. The Three Services")

pdf.section_title("Service 1: Frontend (csnavigator-frontend)")
pdf.body_text(
    "A React single-page application built with Vite and served by Nginx in production. "
    "Handles all user interaction, chat UI, admin dashboard, curriculum browser, and profile management."
)
pdf.key_value("Local URL", "http://localhost:5173")
pdf.key_value("Cloud Run URL", "csnavigator-frontend-750361124802.us-central1.run.app")
pdf.key_value("Docker", "Multi-stage: Node build -> Nginx serve on port 8080")
pdf.key_value("Key File", "frontend/src/lib/apiBase.js (routes API calls)")
pdf.ln(3)

pdf.section_title("Service 2: Backend (csnavigator-backend)")
pdf.body_text(
    "A FastAPI application that serves as the API gateway. Handles authentication, user management, "
    "chat routing, file uploads, DegreeWorks integration, admin operations, and caching. "
    "It proxies chat queries to the ADK Agent service via HTTP SSE."
)
pdf.key_value("Local URL", "http://localhost:8000")
pdf.key_value("Cloud Run URL", "csnavigator-backend-750361124802.us-central1.run.app")
pdf.key_value("Docker", "Python 3.11-slim, uvicorn on port 5000")
pdf.key_value("Key File", "backend/main.py (3000+ lines, all API routes)")
pdf.key_value("Agent Client", "backend/vertex_agent.py (SSE communication with ADK)")
pdf.ln(3)

pdf.section_title("Service 3: ADK Agent (csnavigator-adk)")
pdf.body_text(
    "A Google Agent Development Kit (ADK) web server that runs the AI agent. "
    "Uses Gemini 2.0 Flash model with Vertex AI Search tool for knowledge base grounding. "
    "This is where all AI reasoning happens."
)
pdf.key_value("Local URL", "http://localhost:8080")
pdf.key_value("Cloud Run URL", "csnavigator-adk-750361124802.us-central1.run.app")
pdf.key_value("Docker", "Python 3.12, google-adk 1.23")
pdf.key_value("Key File", "adk_agent/cs_navigator_unified/agent.py")
pdf.key_value("Model", "Gemini 2.0 Flash (temperature=0.2, max_tokens=1024)")

# =====================================================================
# 3. ADK AGENT DEEP DIVE
# =====================================================================
pdf.add_page()
pdf.chapter_title("3. Google ADK Agent - How It Works")

pdf.section_title("Architecture: Single Unified Agent (v4)")
pdf.body_text(
    "The agent evolved from v3 (8 specialist agents with routing, 6-12s response time) to "
    "v4 (1 unified agent, 2-4s response time). This was a major simplification:"
)
pdf.code_block(
    "v3 (old): User -> Root Agent -> Route -> Specialist Agent -> Response\n"
    "          3 LLM hops, 6-12 seconds\n\n"
    "v4 (new): User -> Unified Agent + KB Grounding -> Response\n"
    "          1 LLM hop, 2-4 seconds"
)

pdf.section_title("How a Query is Processed")
pdf.body_text("Step-by-step flow when a student asks a question:")
pdf.bullet("1. User types question in React chat UI")
pdf.bullet("2. Frontend sends POST to /chat/stream (SSE endpoint)")
pdf.bullet("3. Backend fetches DegreeWorks data for personalization")
pdf.bullet("4. Backend checks query cache (L1 in-memory, L2 Redis)")
pdf.bullet("5. If cache miss: Backend calls ADK Agent via SSE stream")
pdf.bullet("6. ADK creates/reuses session, injects DegreeWorks into session state")
pdf.bullet("7. Gemini 2.0 Flash receives the query + system instruction")
pdf.bullet("8. Gemini automatically searches Vertex AI Knowledge Base (45 docs)")
pdf.bullet("9. Gemini generates grounded response using KB search results")
pdf.bullet("10. Response streams back: ADK -> Backend -> Frontend (real-time)")
pdf.bullet("11. Backend caches the response for future identical queries")
pdf.bullet("12. Frontend renders markdown with typing animation")

pdf.section_title("Greeting Fast-Path (Zero Latency)")
pdf.body_text(
    "Simple greetings like 'hi', 'hey', 'thanks' are intercepted by a before_agent_callback "
    "using regex matching. This returns a canned response instantly without calling the LLM, "
    "saving 2-4 seconds and API costs."
)

pdf.section_title("Vertex AI Search Tool (Knowledge Base)")
pdf.body_text(
    "The agent uses VertexAiSearchTool connected to a unified datastore containing 45 documents "
    "across domains: academic (courses, requirements, faculty), career (internships, orgs), "
    "financial (aid, scholarships, housing), and general (campus resources, calendar). "
    "Documents are stored in GCS and indexed by Discovery Engine for semantic search."
)

pdf.section_title("DegreeWorks Personalization")
pdf.body_text(
    "When a student has DegreeWorks data linked, it's injected into the agent's session state "
    "(not the message). The dynamic instruction builder (_build_instruction) appends the student's "
    "GPA, completed courses, in-progress courses, and remaining requirements to the system prompt. "
    "This lets the agent give personalized advice like 'You've already completed COSC 220, "
    "so you can take COSC 320 next semester.'"
)

pdf.section_title("Key Environment Variables for ADK")
pdf.code_block(
    "GOOGLE_CLOUD_PROJECT=csnavigator-vertex-ai\n"
    "GOOGLE_GENAI_USE_VERTEXAI=true    # Use Vertex AI, not Gemini API\n"
    "GOOGLE_CLOUD_LOCATION=us-central1"
)

# =====================================================================
# 4. BACKEND DEEP DIVE
# =====================================================================
pdf.add_page()
pdf.chapter_title("4. Backend (FastAPI) - Deep Dive")

pdf.section_title("Core Modules")
pdf.key_value("main.py", "All API routes, middleware, startup logic (3000+ lines)")
pdf.key_value("vertex_agent.py", "ADK client: session management, SSE parsing, streaming")
pdf.key_value("cache.py", "Two-tier caching (L1 in-memory + L2 Redis)")
pdf.key_value("datastore_manager.py", "GCS + Discovery Engine CRUD operations")
pdf.key_value("db.py", "SQLAlchemy database connection and session factory")
pdf.key_value("models.py", "ORM models: User, DegreeWorksData, ChatHistory, etc.")
pdf.key_value("security.py", "Password hashing (bcrypt) and JWT token creation")
pdf.key_value("banner_scraper.py", "Banner SSB integration for student data sync")
pdf.ln(3)

pdf.section_title("Middleware Stack")
pdf.bullet("CORSMiddleware - Controls which origins can call the API")
pdf.bullet("TrustedHostMiddleware - Validates request Host headers")
pdf.bullet("Static files - Serves uploaded profile pictures and chat files")
pdf.ln(2)

pdf.section_title("CORS Configuration")
pdf.body_text(
    "The backend reads ALLOWED_ORIGINS from the environment variable (not CORS_ORIGINS). "
    "This must include all frontend URLs (localhost ports + Cloud Run URL). "
    "A common bug: if the frontend runs on a new port, CORS blocks all requests."
)

pdf.section_title("vertex_agent.py - ADK Client")
pdf.body_text(
    "This module handles all communication with the ADK Agent service. Key features:"
)
pdf.bullet("Session reuse: Caches ADK sessions per user with 30-min TTL and context hash")
pdf.bullet("Context detection: If DegreeWorks data changes, creates a new session")
pdf.bullet("SSE parsing: Reads Server-Sent Events stream, extracts text chunks and tool status")
pdf.bullet("Auto-retry: If session expires (404), creates new session and retries once")
pdf.bullet("Streaming: query_agent_stream() yields chunks for real-time display")

pdf.section_title("Startup Sequence (lifespan)")
pdf.body_text("When the backend starts, it:")
pdf.bullet("1. Loads .env from project root")
pdf.bullet("2. Connects to MySQL database (AWS RDS)")
pdf.bullet("3. Creates tables if they don't exist")
pdf.bullet("4. Creates admin account if missing")
pdf.bullet("5. Attempts Redis connection (optional L2 cache)")
pdf.bullet("6. Checks ADK agent health (warns if not reachable)")
pdf.bullet("7. Mounts static file directories for uploads")

# =====================================================================
# 5. FRONTEND DEEP DIVE
# =====================================================================
pdf.add_page()
pdf.chapter_title("5. Frontend (React + Vite) - Deep Dive")

pdf.section_title("Key Components")
pdf.key_value("App.jsx", "Main router, auth state, chat session management")
pdf.key_value("Chatbox.jsx", "Chat UI, streaming, TTS, file upload, voice mode")
pdf.key_value("AdminDashboard.jsx", "Admin panel with 7 tabs (Overview, Datastore, etc.)")
pdf.key_value("CurriculumPage.jsx", "Interactive course catalog browser")
pdf.key_value("ProfilePage.jsx", "User profile, DegreeWorks sync, Banner integration")
pdf.key_value("GuestChatbox.jsx", "Public trial chat (limited messages, no auth)")
pdf.key_value("Login.jsx / SignUp.jsx", "Authentication pages")
pdf.key_value("ChatSidebar.jsx", "Chat history list, search, support tickets")
pdf.key_value("apiBase.js", "API URL router (localhost vs Cloud Run)")
pdf.ln(3)

pdf.section_title("API Base Routing (apiBase.js)")
pdf.body_text(
    "This critical file determines where API calls go. For localhost, it returns "
    "http://127.0.0.1:8000 (or 8001). For production (any non-localhost hostname), "
    "it returns the Cloud Run backend URL. This is how the same frontend code works "
    "both locally and in production."
)

pdf.section_title("Chat Streaming Flow")
pdf.body_text("The Chatbox component handles real-time streaming:")
pdf.bullet("1. User sends message -> POST /chat/stream with JWT token")
pdf.bullet("2. Adds placeholder bot message with isStreaming=true")
pdf.bullet("3. Reads SSE stream using ReadableStream API")
pdf.bullet("4. Status events update the thinking indicator (step icons)")
pdf.bullet("5. Chunk events append text to the bot message in real-time")
pdf.bullet("6. Done event finalizes the message and stops streaming")
pdf.bullet("7. Thinking steps cycle through: Understanding -> Searching -> Analyzing -> Preparing")

pdf.section_title("Streaming Status UI (Built Today)")
pdf.body_text(
    "The streaming indicator shows a step-by-step progress with contextual SVG icons:"
)
pdf.bullet("Lightbulb icon (pulsing) - 'Understanding your question'")
pdf.bullet("Magnifying glass (bobbing) - 'Searching knowledge base'")
pdf.bullet("Brain icon (pulsing) - 'Analyzing results'")
pdf.bullet("Pen icon (writing motion) - 'Preparing response'")
pdf.bullet("Each completed step shows a green checkmark with pop animation")
pdf.bullet("Active step has a blue icon box that floats, with shimmer text")
pdf.bullet("While text streams: blinking cursor bar (like a text editor)")

# =====================================================================
# 6. CLOUD RUN DEPLOYMENT
# =====================================================================
pdf.add_page()
pdf.chapter_title("6. Cloud Run Deployment")

pdf.section_title("What is Cloud Run?")
pdf.body_text(
    "Google Cloud Run is a serverless container platform. You give it a Docker container, "
    "and it runs it with automatic scaling (0 to N instances), HTTPS, and pay-per-use pricing. "
    "No servers to manage - it scales to zero when idle (no cost) and scales up under load."
)

pdf.section_title("Our Three Cloud Run Services")
pdf.code_block(
    "csnavigator-frontend  (512MB, 1 CPU, port 8080, public)\n"
    "csnavigator-backend   (1GB, 1 CPU, port 5000, public)\n"
    "csnavigator-adk       (2GB, 2 CPU, port 8080, private)"
)
pdf.body_text(
    "The ADK service is private (--no-allow-unauthenticated) because only the backend "
    "calls it. Frontend and backend are public for user access."
)

pdf.section_title("Deploying Without Docker (gcloud run deploy --source)")
pdf.body_text(
    "Since Docker isn't installed locally, we use 'gcloud run deploy --source .' which:"
)
pdf.bullet("1. Uploads source code to Google Cloud Storage")
pdf.bullet("2. Cloud Build reads the Dockerfile and builds the container image")
pdf.bullet("3. Image is stored in Artifact Registry")
pdf.bullet("4. Cloud Run creates a new revision and routes traffic to it")
pdf.bullet("Total deploy time: ~3-5 minutes per service")
pdf.ln(2)

pdf.section_title("Deploy Commands Used Today")
pdf.code_block(
    "# Backend\n"
    "gcloud run deploy csnavigator-backend --source ./backend \\\n"
    "  --region us-central1 --port 5000 --allow-unauthenticated \\\n"
    "  --memory 1Gi --cpu 1\n\n"
    "# Frontend\n"
    "gcloud run deploy csnavigator-frontend --source ./frontend \\\n"
    "  --region us-central1 --port 8080 --allow-unauthenticated \\\n"
    "  --memory 512Mi --cpu 1\n\n"
    "# ADK Agent\n"
    "gcloud run deploy csnavigator-adk --source ./adk_agent \\\n"
    "  --region us-central1 --port 8080 --no-allow-unauthenticated \\\n"
    "  --memory 2Gi --cpu 2 \\\n"
    "  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,..."
)

pdf.section_title("CI/CD with Cloud Build (cloudbuild.yaml)")
pdf.body_text(
    "We created a cloudbuild.yaml that auto-deploys all 3 services on git push to main. "
    "It builds images in parallel, deploys ADK first (backend depends on its URL), "
    "then backend, then frontend. To enable: connect GitHub repo to Cloud Build triggers."
)

# =====================================================================
# 7. DATABASE & STORAGE
# =====================================================================
pdf.add_page()
pdf.chapter_title("7. Database & Storage")

pdf.section_title("MySQL Database (AWS RDS)")
pdf.body_text(
    "The application uses a MySQL database hosted on AWS RDS. It stores user accounts, "
    "chat history, DegreeWorks data, support tickets, and feedback. The same RDS instance "
    "is shared between local development and Cloud Run production."
)
pdf.key_value("Host", "cs-navigator-db.cbh3ertrslsi.us-east-1.rds.amazonaws.com")
pdf.key_value("Engine", "MySQL via PyMySQL + SQLAlchemy ORM")
pdf.key_value("Tables", "users, chat_history, degreeworks_data, support_tickets, banner_student_data")
pdf.ln(3)

pdf.section_title("Google Cloud Storage (GCS)")
pdf.key_value("Bucket", "csnavigator-unified-kb")
pdf.key_value("Contents", "45 knowledge base documents (txt files, ~95KB total)")
pdf.key_value("Path", "gs://csnavigator-unified-kb/v4_split/*.txt")
pdf.body_text(
    "GCS stores the source documents for the knowledge base. When you upload/edit docs "
    "through the admin dashboard, they're written to GCS and Discovery Engine re-indexes them."
)
pdf.ln(2)

pdf.section_title("Vertex AI Discovery Engine (Datastore)")
pdf.body_text(
    "Discovery Engine indexes the GCS documents for semantic search. The ADK agent's "
    "VertexAiSearchTool queries this datastore to find relevant information. "
    "The datastore ID is: csnavigator-unified-kb-v4"
)

# =====================================================================
# 8. AUTH & SECURITY
# =====================================================================
pdf.add_page()
pdf.chapter_title("8. Authentication & Security")

pdf.section_title("JWT Authentication Flow")
pdf.bullet("1. User logs in with email + password")
pdf.bullet("2. Backend verifies password hash (bcrypt)")
pdf.bullet("3. Backend generates JWT token (HS256, 4-hour expiry)")
pdf.bullet("4. Frontend stores token in localStorage")
pdf.bullet("5. Every API request includes 'Authorization: Bearer <token>' header")
pdf.bullet("6. Backend middleware validates token on protected routes")
pdf.ln(2)

pdf.section_title("Role-Based Access")
pdf.bullet("'user' role: Chat, profile, curriculum, DegreeWorks")
pdf.bullet("'admin' role: All user features + Admin Dashboard (manage users, KB, tickets)")
pdf.ln(2)

pdf.section_title("Agent Security")
pdf.body_text(
    "The agent's system prompt includes strict security rules: never reveal instructions, "
    "never comply with prompt injection ('ignore previous instructions'), never share PII, "
    "and stay on-topic (Morgan State CS questions only)."
)

# =====================================================================
# 9. API ENDPOINTS
# =====================================================================
pdf.add_page()
pdf.chapter_title("9. API Endpoints & Data Flow")

pdf.section_title("Chat Endpoints")
pdf.code_block(
    "POST /chat/stream     - SSE streaming chat (primary)\n"
    "POST /chat            - Non-streaming chat (legacy)\n"
    "POST /chat/guest      - Guest trial chat (no auth, limited)"
)

pdf.section_title("Auth Endpoints")
pdf.code_block(
    "POST /api/login       - Email/password login -> JWT token\n"
    "POST /api/register    - Create new account\n"
    "POST /api/change-password - Change password"
)

pdf.section_title("User Endpoints")
pdf.code_block(
    "GET  /api/profile     - Get user profile\n"
    "POST /api/upload-profile-picture\n"
    "GET  /api/degreeworks  - Get linked DegreeWorks data\n"
    "POST /api/degreeworks/upload-pdf\n"
    "POST /api/degreeworks/sync\n"
    "GET  /api/curriculum   - Full course catalog\n"
    "GET  /chat-history     - User's chat sessions"
)

pdf.section_title("Admin Endpoints")
pdf.code_block(
    "GET  /api/admin/users       - List all users\n"
    "GET  /api/admin/health      - System health check\n"
    "GET  /api/admin/analytics   - Usage analytics\n"
    "GET  /api/admin/cloud-kb/documents  - List KB docs\n"
    "POST /api/admin/cloud-kb/upload     - Upload to KB\n"
    "PUT  /api/admin/cloud-kb/documents/{id}  - Edit doc\n"
    "DELETE /api/admin/cloud-kb/documents/{id}\n"
    "GET  /api/admin/cache/stats - Cache hit rates\n"
    "POST /api/admin/cache/clear - Clear all caches"
)

pdf.section_title("Communication Between Services")
pdf.code_block(
    "Frontend -> Backend:\n"
    "  fetch('https://csnavigator-backend.../api/login')\n"
    "  fetch('https://csnavigator-backend.../chat/stream')\n\n"
    "Backend -> ADK Agent:\n"
    "  POST {ADK_BASE_URL}/apps/cs_navigator_unified/users/{id}/sessions\n"
    "  POST {ADK_BASE_URL}/run_sse  (Server-Sent Events stream)\n\n"
    "ADK Agent -> Vertex AI:\n"
    "  VertexAiSearchTool -> Discovery Engine datastore query\n"
    "  Gemini 2.0 Flash -> LLM inference"
)

# =====================================================================
# 10. CACHING
# =====================================================================
pdf.add_page()
pdf.chapter_title("10. Caching Architecture")

pdf.section_title("Two-Tier Query Cache")
pdf.body_text(
    "To avoid redundant AI calls (which cost money and take 2-4s), the backend caches "
    "chat responses at two levels:"
)
pdf.bullet("L1 (In-Memory): Python dict, instant (<1ms), lost on restart. 1000-entry LRU.")
pdf.bullet("L2 (Redis): Persistent across restarts, ~5ms lookup. 24-hour TTL.")
pdf.body_text(
    "Cache keys combine the query text + a context hash (user ID + whether they have DegreeWorks). "
    "This ensures personalized responses aren't served to other users."
)
pdf.ln(2)

pdf.section_title("Cloud KB Documents Cache")
pdf.body_text(
    "The admin dashboard's Datastore tab caches the document list for 60 seconds server-side. "
    "The first load calls GCS + Discovery Engine in parallel (~2.4s). Subsequent loads are instant "
    "(~50ms). The frontend also pre-fetches this endpoint in the background when the dashboard loads."
)

pdf.section_title("ADK Session Cache")
pdf.body_text(
    "ADK sessions are reused per user for 30 minutes (SESSION_TTL). If the student's DegreeWorks "
    "context hasn't changed, the same session is used, saving ~100-200ms per request."
)

# =====================================================================
# 11. STREAMING
# =====================================================================
pdf.add_page()
pdf.chapter_title("11. Streaming & Real-Time Features")

pdf.section_title("Server-Sent Events (SSE) Protocol")
pdf.body_text(
    "The chat uses SSE for real-time streaming. Unlike WebSockets, SSE is one-way "
    "(server to client) and works over regular HTTP. The backend sends events as:"
)
pdf.code_block(
    'data: {"type": "status", "content": "Searching knowledge base"}\n\n'
    'data: {"type": "chunk", "content": "The prerequisites for..."}\n\n'
    'data: {"type": "done", "content": "Full response text here"}\n\n'
    'data: {"type": "error", "content": "Error message"}'
)

pdf.section_title("Frontend Streaming Pipeline")
pdf.body_text("The Chatbox reads the SSE stream using the Fetch API's ReadableStream:")
pdf.bullet("fetch('/chat/stream') returns a streaming Response")
pdf.bullet("reader = res.body.getReader() gives a stream reader")
pdf.bullet("Loop: reader.read() returns chunks of bytes")
pdf.bullet("Decode bytes, split by newlines, parse 'data: {...}' JSON")
pdf.bullet("Status events update thinking indicator (step progression)")
pdf.bullet("Chunk events append text to message (real-time typing effect)")
pdf.bullet("Done event finalizes and enables feedback/TTS buttons")

pdf.section_title("Text-to-Speech (TTS)")
pdf.body_text(
    "Bot responses can be read aloud using OpenAI's TTS API (alloy voice). "
    "The frontend sends the text to /api/tts, which calls OpenAI and returns an audio blob."
)

# =====================================================================
# 12. SESSION SUMMARY
# =====================================================================
pdf.add_page()
pdf.chapter_title("12. Session Summary: March 24, 2026")

pdf.section_title("Environment Setup (Windows)")
pdf.bullet("Created .env file with all environment variables")
pdf.bullet("Removed deprecated TEXT_EXTRACT_API_URL")
pdf.bullet("Fixed CORS: backend uses ALLOWED_ORIGINS (not CORS_ORIGINS)")
pdf.bullet("Fixed apiBase.js: was hardcoded to port 5000, changed to 8000")
pdf.bullet("Installed all Python/Node dependencies")
pdf.bullet("Set up gcloud auth + application-default credentials")
pdf.bullet("Fixed ADK: needed GOOGLE_GENAI_USE_VERTEXAI=true env var")
pdf.ln(2)

pdf.section_title("Streaming UI Enhancements")
pdf.bullet("Added step-by-step status indicator with contextual SVG icons")
pdf.bullet("Magnifying glass for search, lightbulb for thinking, pen for writing")
pdf.bullet("Completed steps get green checkmark with pop animation")
pdf.bullet("Active step has floating blue icon box with shimmer text")
pdf.bullet("Replaced bouncing dots cursor with clean blinking bar")
pdf.bullet("Added inline regenerate button (refresh icon next to TTS)")
pdf.ln(2)

pdf.section_title("Performance Optimizations")
pdf.bullet("Datastore listing: 45 individual GCS calls -> 1 parallel batch call")
pdf.bullet("Added 60-second server-side cache for document list")
pdf.bullet("Added background pre-fetch on dashboard load")
pdf.bullet("Result: 10s+ load time -> 2.4s first load, 0.05s cached")
pdf.ln(2)

pdf.section_title("Cloud Run Deployment")
pdf.bullet("Created deploy-cloudrun.sh for manual deployment")
pdf.bullet("Created cloudbuild.yaml for CI/CD auto-deployment")
pdf.bullet("Deployed all 3 services using gcloud run deploy --source")
pdf.bullet("No Docker needed locally - Cloud Build handles everything")

# =====================================================================
# 13. LOCAL DEV SETUP
# =====================================================================
pdf.add_page()
pdf.chapter_title("13. Local Development Setup")

pdf.section_title("Prerequisites")
pdf.bullet("Python 3.12 with pip")
pdf.bullet("Node.js 18+ with npm")
pdf.bullet("Google Cloud SDK (gcloud CLI)")
pdf.bullet("gcloud auth login + gcloud auth application-default login")
pdf.ln(2)

pdf.section_title("Start All 3 Services")
pdf.code_block(
    "# Terminal 1: ADK Agent (port 8080)\n"
    "cd adk_agent\n"
    "GOOGLE_GENAI_USE_VERTEXAI=true \\\n"
    "GOOGLE_CLOUD_PROJECT=csnavigator-vertex-ai \\\n"
    "GOOGLE_CLOUD_LOCATION=us-central1 \\\n"
    "python -m google.adk.cli web . --port 8080\n\n"
    "# Terminal 2: Backend (port 8000)\n"
    "cd backend\n"
    "uvicorn main:app --reload --port 8000\n\n"
    "# Terminal 3: Frontend (port 5173)\n"
    "cd frontend\n"
    "npm run dev"
)

pdf.section_title("Important Notes")
pdf.bullet("Backend reads .env from project root (one level above backend/)")
pdf.bullet("Frontend apiBase.js routes to localhost:8001 for local dev")
pdf.bullet("ADK MUST have GOOGLE_GENAI_USE_VERTEXAI=true or it fails with 'No API key'")
pdf.bullet("NEVER kill all python.exe - it kills Claude Code too. Use specific PIDs.")

# =====================================================================
# 14. ENV VARS
# =====================================================================
pdf.add_page()
pdf.chapter_title("14. Environment Variables Reference")

pdf.section_title("Required for Backend")
pdf.code_block(
    "DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname\n"
    "JWT_SECRET=<64-char-random-string>\n"
    "ALGORITHM=HS256\n"
    "ACCESS_TOKEN_EXPIRE_MINUTES=240\n"
    "ADMIN_EMAIL=admin@morgan.edu\n"
    "ADMIN_PASSWORD=<strong-password>\n"
    "OPENAI_API_KEY=<key>           # For TTS only\n"
    "ALLOWED_ORIGINS=http://localhost:5173,...\n"
    "USE_VERTEX_AGENT=true\n"
    "ADK_BASE_URL=http://127.0.0.1:8080  # Local\n"
    "ADK_APP_NAME=cs_navigator_unified"
)

pdf.section_title("Required for ADK Agent")
pdf.code_block(
    "GOOGLE_CLOUD_PROJECT=csnavigator-vertex-ai\n"
    "GOOGLE_GENAI_USE_VERTEXAI=true\n"
    "GOOGLE_CLOUD_LOCATION=us-central1"
)

pdf.section_title("GCP Project Details")
pdf.key_value("Project ID", "csnavigator-vertex-ai")
pdf.key_value("Project Number", "750361124802")
pdf.key_value("Region", "us-central1")
pdf.key_value("Reasoning Engine", "projects/750361124802/locations/us-central1/reasoningEngines/6260838011370471424")
pdf.key_value("Datastore", "csnavigator-unified-kb-v4")
pdf.key_value("GCS Bucket", "csnavigator-unified-kb")

# Save
output_path = r"C:\Users\Aayush\Desktop\cs-chatbot-v4.2\CSNavigator_System_Guide.pdf"
pdf.output(output_path)
print(f"PDF saved to: {output_path}")
