import sys
# Force unbuffered output so we see logs immediately
sys.stdout.reconfigure(line_buffering=True)

print("[OK] main.py loaded successfully")

import os
import re
import json
# import time  # Commented: currently unused, kept for potential future use
import shutil #  NEW: For file operations
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone

#  FIXED IMPORTS: Use 'pypdf' which you installed, not 'PyPDF2'
import pypdf 
import docx
from langchain.schema import SystemMessage, HumanMessage 

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from collections import Counter
import io
from dotenv import load_dotenv

# ==============================================================================
# 1. ENVIRONMENT LOADING (FIXED FOR ROOT FOLDER)
# ==============================================================================
# Get the absolute path of the backend folder
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root (one level up)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
# Path to .env file in the root
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

# Load course catalog for context injection
COURSE_CATALOG_TEXT = ""
_catalog_path = os.path.join(BACKEND_DIR, "data_sources", "classes.json")
if os.path.exists(_catalog_path):
    try:
        with open(_catalog_path) as _f:
            _catalog = json.load(_f)
        _lines = []
        for c in _catalog.get("courses", []):
            prereqs = ", ".join(c.get("prerequisites", [])) or "None"
            _lines.append(f"  {c['course_code']} - {c['course_name']} ({c.get('credits',3)} cr, {c.get('category','')}) Prereqs: {prereqs}")
        COURSE_CATALOG_TEXT = "AVAILABLE CS COURSES AT MORGAN STATE (from official catalog):\n" + "\n".join(_lines) + "\n"
    except Exception as _e:
        print(f"[WARN] Failed to load course catalog: {_e}")

print(f"[INFO] Looking for .env at: {ENV_PATH}")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print("[OK] .env file loaded!")
else:
    print("[ERROR] .env file NOT found at root. Checking backend folder...")
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))

print(f"[KEY] JWT_SECRET Check: {'FOUND' if os.getenv('JWT_SECRET') else 'MISSING'}")

# SQLAlchemy Imports
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, text

# Vertex AI Agent Engine (replaces Pinecone + OpenAI RAG pipeline)
from vertex_agent import query_agent, query_agent_stream, check_agent_health, reset_session

# Query caching for faster responses
from cache import query_cache, get_context_hash, log_cache_stats


# Legacy imports kept for /ingest endpoint and file analysis fallback
try:
    from langchain.text_splitter import TokenTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_pinecone import PineconeVectorStore
    from langchain_community.chat_models import ChatOpenAI
    from langchain.chains import RetrievalQA
    from pinecone import Pinecone
    LEGACY_RAG_AVAILABLE = True
except ImportError:
    LEGACY_RAG_AVAILABLE = False
    print("   Legacy RAG imports not available (Pinecone/LangChain not installed)")

# Local Imports (Auth & DB) - These must run AFTER load_dotenv
from db import SessionLocal, engine, Base
from models import User, DegreeWorksData, SupportTicket
from security import hash_password, verify_password, create_access_token
from jose import JWTError, jwt

# ==============================================================================
# 2. CONFIGURATION & CONSTANTS
# ==============================================================================
# Vertex AI Agent Engine config
USE_VERTEX_AGENT   = os.getenv("USE_VERTEX_AGENT", "true").lower() == "true"
ADK_BASE_URL       = os.getenv("ADK_BASE_URL", "http://127.0.0.1:8080")

# Legacy Pinecone + OpenAI config (kept for /ingest and TTS)
PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_ENV       = os.getenv("PINECONE_ENV")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "docs")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")  # Still needed for TTS
JWT_SECRET         = os.getenv("JWT_SECRET")
ALGORITHM          = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

# Upload configuration
UPLOAD_FOLDER = os.path.join(BACKEND_DIR, "uploads", "profile_pictures")
CHAT_FILES_FOLDER = os.path.join(BACKEND_DIR, "uploads", "chat_files") #  NEW: Chat files folder

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'docx', 'doc', 'mov', 'mp4'} #  NEW: Added Docs

# Create folders if not exist
for folder in [UPLOAD_FOLDER, CHAT_FILES_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        print(f"[OK] Created folder: {folder}")

# Safety check for keys
if USE_VERTEX_AGENT:
    print(f"[INFO] Using Vertex AI Agent Engine at {ADK_BASE_URL}")
elif not all([PINECONE_API_KEY, PINECONE_ENV, PINECONE_INDEX, OPENAI_API_KEY]):
    print("[WARN] WARNING: Some API keys are missing. Chatbot features will be limited.")

# ==============================================================================
# 3. DATABASE MODELS (UPDATED WITH SESSION_ID)
# ==============================================================================
class ChatHistory(Base):
    """
    Stores chat history in AWS RDS (or local DB).
    Linked to the User table via user_id.
    """
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(255), default="default") #  NEW: Support multiple threads
    user_query = Column(Text)
    bot_response = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Feedback(Base):
    """
     NEW: Stores user feedback on bot responses for improving the chatbot.
    """
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(255), default="default")
    message_text = Column(Text)  # The bot message that was rated
    feedback_type = Column(String(50))  # 'helpful', 'not_helpful', 'report'
    report_details = Column(Text, nullable=True)  # Additional details for reports
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def init_db():
    """Initializes the database tables and runs migrations."""
    # 1. Create tables if missing
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables checked/created.")
    except Exception as e:
        print(f"[WARN] DB Connection Error: {e}")

    # 2. Add session_id column if missing (For existing DBs)
    with engine.connect() as conn:
        try:
            # Check if column exists by selecting from it
            conn.execute(text("SELECT session_id FROM chat_history LIMIT 1"))
        except (OperationalError, ProgrammingError):
            print("[WARN] 'session_id' column missing. Adding it now...")
            try:
                conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_id VARCHAR(255) DEFAULT 'default'"))
                conn.commit()
                print("[OK] Successfully added 'session_id' column!")
            except Exception as e:
                print(f"[ERROR] Failed to add column: {e}")

        # 3. Add profile_picture_data column if missing (For base64 storage)
        try:
            conn.execute(text("SELECT profile_picture_data FROM users LIMIT 1"))
        except (OperationalError, ProgrammingError):
            print("[WARN] 'profile_picture_data' column missing. Adding it now...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN profile_picture_data LONGTEXT"))
                conn.commit()
                print("[OK] Successfully added 'profile_picture_data' column!")
            except Exception as e:
                print(f"[ERROR] Failed to add profile_picture_data column: {e}")

        # 4. Add morgan_connected_at column if missing
        try:
            conn.execute(text("SELECT morgan_connected_at FROM users LIMIT 1"))
        except (OperationalError, ProgrammingError):
            print("[WARN] 'morgan_connected_at' column missing. Adding it now...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN morgan_connected_at DATETIME"))
                conn.commit()
                print("[OK] Successfully added 'morgan_connected_at' column!")
            except Exception as e:
                print(f"[ERROR] Failed to add morgan_connected_at column: {e}")

        # 5. Check if degreeworks_data table exists
        try:
            conn.execute(text("SELECT id FROM degreeworks_data LIMIT 1"))
            print("[OK] degreeworks_data table exists")
        except (OperationalError, ProgrammingError):
            print("[WARN] 'degreeworks_data' table missing. Creating it now...")
            try:
                conn.execute(text("""
                    CREATE TABLE degreeworks_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT UNIQUE NOT NULL,
                        student_name VARCHAR(255),
                        student_id VARCHAR(50),
                        degree_program VARCHAR(255),
                        catalog_year VARCHAR(20),
                        classification VARCHAR(50),
                        advisor VARCHAR(255),
                        overall_gpa FLOAT,
                        major_gpa FLOAT,
                        total_credits_earned FLOAT,
                        credits_required FLOAT,
                        credits_remaining FLOAT,
                        courses_completed TEXT,
                        courses_in_progress TEXT,
                        courses_remaining TEXT,
                        requirements_status TEXT,
                        raw_data TEXT,
                        synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
                print("[OK] Successfully created 'degreeworks_data' table!")
            except Exception as e:
                print(f"[ERROR] Failed to create degreeworks_data table: {e}")

        # 6. Check if support_tickets table exists
        try:
            conn.execute(text("SELECT id FROM support_tickets LIMIT 1"))
            print("[OK] support_tickets table exists")
        except (OperationalError, ProgrammingError):
            print("[WARN] 'support_tickets' table missing. Creating it now...")
            try:
                conn.execute(text("""
                    CREATE TABLE support_tickets (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        subject VARCHAR(255) NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        description TEXT NOT NULL,
                        attachment_data LONGTEXT,
                        attachment_name VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'open',
                        priority VARCHAR(20) DEFAULT 'normal',
                        admin_notes TEXT,
                        resolved_by INT,
                        resolved_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
                conn.commit()
                print("[OK] Successfully created 'support_tickets' table!")
            except Exception as e:
                print(f"[ERROR] Failed to create support_tickets table: {e}")

    # 7. Create/Update admin account
    try:
        db = SessionLocal()
        admin_email = os.getenv("ADMIN_EMAIL", "admin@test.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "changeme")

        existing_admin = db.query(User).filter(User.email == admin_email).first()

        if existing_admin:
            # Update existing user to admin
            if existing_admin.role != "admin":
                existing_admin.role = "admin"
                db.commit()
                print(f"[OK] Updated {admin_email} to admin role!")
            else:
                print(f"[OK] Admin account {admin_email} already exists with admin role.")
        else:
            # Create new admin account
            from security import hash_password
            hashed = hash_password(admin_password)
            admin_user = User(
                email=admin_email,
                password_hash=hashed,
                role="admin",
                name="Admin"
            )
            db.add(admin_user)
            db.commit()
            print(f"[OK] Created admin account: {admin_email}")

        db.close()
    except Exception as e:
        print(f"[ERROR] Failed to create/update admin account: {e}")

init_db()

# ==============================================================================
# 4. FASTAPI APP SETUP
# ==============================================================================
# AI System globals (initialized in lifespan)
pc = None
retriever = None
qa = None
llm = None

def build_qa_chain():
    """Initialize legacy AI components on startup (only when not using Vertex AI)"""
    global retriever, qa, llm, pc
    if USE_VERTEX_AGENT:
        # Check Vertex AI Agent health
        health = check_agent_health()
        print(f" Vertex AI Agent: {health['status']} - {health['message']}")
        if health["status"] != "connected":
            print("[WARN] ADK server not running. Start it with:")
            print("   cd google-ai-engine-research/adk_deploy && python -m google.adk.cli web . --port 8080")
        return

    if not LEGACY_RAG_AVAILABLE:
        print("[WARN] Legacy RAG libraries not installed. Chatbot will be offline.")
        return
    if not all([PINECONE_API_KEY, OPENAI_API_KEY, PINECONE_INDEX]):
        print("[WARN] API Keys missing. Chatbot will be offline.")
        return
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=OPENAI_API_KEY)
        store = PineconeVectorStore.from_existing_index(
            index_name=PINECONE_INDEX,
            embedding=embeddings,
            namespace=PINECONE_NAMESPACE,
        )
        retriever = store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 10,
                "fetch_k": 30,
                "lambda_mult": 0.5
            }
        )
        llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model_name="gpt-3.5-turbo", temperature=0)
        qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)
        print("[OK] Legacy AI System Initialized (Pinecone + OpenAI)")
    except Exception as e:
        print(f"[ERROR] AI Init Failed: {e}")

@asynccontextmanager
async def lifespan(app):
    """Modern lifespan event handler for FastAPI"""
    # Startup
    build_qa_chain()
    yield
    # Shutdown (cleanup if needed)

app = FastAPI(title="CS Chatbot API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Mount Static Files (Profile Pictures AND Chat Files)
UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")
if os.path.exists(UPLOADS_DIR):
    try:
        app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
        print(f"[OK] Static files mounted: /uploads -> {UPLOADS_DIR}")
    except Exception as e:
        print(f"[ERROR] Error mounting static files: {e}")
else:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print(f"[OK] Created uploads directory: {UPLOADS_DIR}")

# ==============================================================================
# 5. AUTHENTICATION HELPERS
# ==============================================================================
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str,Any]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_email = payload.get("email")
        if not user_email:
            raise HTTPException(status_code=403, detail="Invalid token")

        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=403, detail="User not found")

        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role
        }
    except JWTError as e:
        print(f"JWT decode error: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================================================================
# 6. PYDANTIC SCHEMAS
# ==============================================================================
class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class QueryRequest(BaseModel):
    query: str
    session_id: str = "default" #  NEW: Accept session ID

class GuestQueryRequest(BaseModel):
    query: str
    guestProfile: Optional[dict] = None

# ==============================================================================
# GUEST RATE LIMITING (Simple In-Memory)
# ==============================================================================
from collections import defaultdict
import time as time_module

guest_rate_limits = defaultdict(list)  # IP -> list of timestamps
GUEST_RATE_LIMIT = 15  # requests per minute (time-based session provides natural limiting)
GUEST_RATE_WINDOW = 60  # seconds

def check_guest_rate_limit(ip: str) -> bool:
    """Check if IP is within rate limit. Returns True if allowed, False if blocked."""
    current_time = time_module.time()
    # Clean old entries
    guest_rate_limits[ip] = [t for t in guest_rate_limits[ip] if current_time - t < GUEST_RATE_WINDOW]
    # Check limit
    if len(guest_rate_limits[ip]) >= GUEST_RATE_LIMIT:
        return False
    # Add new request
    guest_rate_limits[ip].append(current_time)
    return True

class Course(BaseModel):
    course_code: str
    course_name: str
    credits: int
    prerequisites: List[str] = []
    offered: List[str] = []

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    studentId: Optional[str] = None
    major: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    currentPassword: str
    newPassword: str

class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer

#  DegreeWorks Data Schema
class DegreeWorksRequest(BaseModel):
    student_name: Optional[str] = None
    student_id: Optional[str] = None
    degree_program: Optional[str] = None
    catalog_year: Optional[str] = None
    classification: Optional[str] = None
    advisor: Optional[str] = None
    overall_gpa: Optional[float] = None
    major_gpa: Optional[float] = None
    total_credits_earned: Optional[float] = None
    credits_required: Optional[float] = None
    credits_remaining: Optional[float] = None
    courses_completed: Optional[List[Dict[str, Any]]] = None  # [{code, name, credits, grade, semester}]
    courses_in_progress: Optional[List[Dict[str, Any]]] = None  # [{code, name, credits, semester}]
    courses_remaining: Optional[List[Dict[str, Any]]] = None  # [{code, name, credits, category}]
    requirements_status: Optional[List[Dict[str, Any]]] = None  # [{category, status, details}]
    raw_data: Optional[str] = None

# ==============================================================================
# 7. STATIC DATA & RESOURCES
# ==============================================================================
DATA_DIR       = os.path.join(BACKEND_DIR, "data_sources")
CLASSES_FILE   = os.path.join(DATA_DIR, "classes.json")
RESOURCES_FILE = os.path.join(DATA_DIR, "academic_resources.json")

helpful_links = {}
if os.path.exists(RESOURCES_FILE):
    try:
        with open(RESOURCES_FILE, "r", encoding="utf-8") as f:
            res_data = json.load(f)
        helpful_links = res_data.get("academic_and_student_support", {}).get("helpful_links", {})
    except:
        pass

def load_json_documents(paths: List[str]) -> List[Dict[str,Any]]:
    docs: List[Dict[str,Any]] = []
    for p in paths:
        try:
            data = json.load(open(p, encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        parts = [f"{subk}: {subv}" for subk, subv in v.items()]
                        docs.append({"text": f"{k} – " + "; ".join(parts), "source": p})
                    else:
                        docs.append({"text": f"{k}: {v}", "source": p})
            elif isinstance(data, list):
                for obj in data:
                    text = "\n".join(f"{kk}: {vv}" for kk, vv in obj.items())
                    docs.append({"text": text, "source": p})
        except Exception:
            pass
    return docs

# ==============================================================================
# 8. API ENDPOINTS
# ==============================================================================

# --- Auth ---
@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(req.password)
    student = User(email=req.email, password_hash=hashed, role="student")
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"message": "Account created", "user_id": student.id}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({
        "user_id": user.id,
        "role": user.role,
        "email": user.email
    })
    return {"access_token": token, "token_type": "bearer"}

# --- Profile Management ---
@app.get("/api/profile")
async def get_profile(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prefer base64 data (persistent) over file URL
    profile_pic = getattr(db_user, 'profile_picture_data', None)
    if not profile_pic:
        profile_pic = getattr(db_user, 'profile_picture', None)

    return {
        "email": db_user.email,
        "name": getattr(db_user, 'name', None),
        "studentId": getattr(db_user, 'student_id', None),
        "major": getattr(db_user, 'major', "Computer Science"),
        "profilePicture": profile_pic,
        "morganConnected": getattr(db_user, 'morgan_connected', False),
        "role": getattr(db_user, 'role', "student")
    }

@app.put("/api/profile")
async def update_profile(req: ProfileUpdateRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if not db_user: raise HTTPException(404, "User not found")
    
    if req.name is not None and hasattr(db_user, 'name'): db_user.name = req.name
    if req.studentId is not None and hasattr(db_user, 'student_id'): db_user.student_id = req.studentId
    if req.major is not None and hasattr(db_user, 'major'): db_user.major = req.major
    
    db.commit()
    return {"message": "Profile updated"}

@app.post("/api/change-password")
async def change_password(req: PasswordChangeRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if not db_user: raise HTTPException(404, "User not found")
    
    if not verify_password(req.currentPassword, db_user.password_hash):
        raise HTTPException(401, "Current password incorrect")
    
    db_user.password_hash = hash_password(req.newPassword)
    db.commit()
    return {"message": "Password changed"}

@app.post("/api/upload-profile-picture")
async def upload_profile_picture(profilePicture: UploadFile = File(...), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not allowed_file(profilePicture.filename):
        raise HTTPException(400, "Invalid file type")

    # Read file content
    file_content = await profilePicture.read()

    # Get file extension and mime type
    ext = profilePicture.filename.rsplit('.', 1)[1].lower()
    mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif'
    }
    mime_type = mime_types.get(ext, 'image/jpeg')

    # Convert to base64 data URL
    import base64
    base64_data = base64.b64encode(file_content).decode('utf-8')
    data_url = f"data:{mime_type};base64,{base64_data}"

    # Also save to filesystem as backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"user_{user['user_id']}_{timestamp}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(file_content)

    file_url = f"/uploads/profile_pictures/{filename}"

    # Save base64 to database (persistent) and file URL as fallback
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if db_user:
        db_user.profile_picture = file_url  # File path as fallback
        if hasattr(db_user, 'profile_picture_data'):
            db_user.profile_picture_data = data_url  # Base64 for persistence
        db.commit()

    # Return base64 data URL for immediate display
    return {"url": data_url}

#  NEW: Chat File Upload Endpoint
@app.post("/api/upload-file")
async def upload_chat_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    # 1. Validate File Type
    if not allowed_file(file.filename): 
        raise HTTPException(400, "File type not allowed")
    
    # 2. Create Unique Filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Sanitize filename
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    filename = f"chat_{user['user_id']}_{timestamp}_{clean_name}"
    filepath = os.path.join(CHAT_FILES_FOLDER, filename)

    # 3. Save the File
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        print(f"[ERROR] File Save Error: {e}")
        raise HTTPException(500, "Could not save file")

    # 4. Return the public URL
    url = f"/uploads/chat_files/{filename}"
    return {"url": url, "filename": file.filename}

@app.post("/api/connect-morgan")
async def connect_morgan(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if hasattr(db_user, 'morgan_connected'):
        db_user.morgan_connected = True
        db.commit()
    return {"message": "Morgan Connected", "morganConnected": True}

# ==============================================================================
# DegreeWorks Integration Endpoints
# ==============================================================================

@app.post("/api/degreeworks/sync")
async def sync_degreeworks(
    req: DegreeWorksRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Receives DegreeWorks data from the bookmarklet and saves it to the database.
    Creates or updates the user's DegreeWorks record.
    """
    try:
        db_user = db.query(User).filter(User.id == user["user_id"]).first()
        if not db_user:
            raise HTTPException(404, "User not found")

        # Check if user already has DegreeWorks data
        existing = db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).first()

        if existing:
            # Update existing record
            existing.student_name = req.student_name
            existing.student_id = req.student_id
            existing.degree_program = req.degree_program
            existing.catalog_year = req.catalog_year
            existing.classification = req.classification
            existing.advisor = req.advisor
            existing.overall_gpa = req.overall_gpa
            existing.major_gpa = req.major_gpa
            existing.total_credits_earned = req.total_credits_earned
            existing.credits_required = req.credits_required
            existing.credits_remaining = req.credits_remaining
            existing.courses_completed = json.dumps(req.courses_completed) if req.courses_completed else None
            existing.courses_in_progress = json.dumps(req.courses_in_progress) if req.courses_in_progress else None
            existing.courses_remaining = json.dumps(req.courses_remaining) if req.courses_remaining else None
            existing.requirements_status = json.dumps(req.requirements_status) if req.requirements_status else None
            existing.raw_data = req.raw_data
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Create new record
            new_data = DegreeWorksData(
                user_id=user["user_id"],
                student_name=req.student_name,
                student_id=req.student_id,
                degree_program=req.degree_program,
                catalog_year=req.catalog_year,
                classification=req.classification,
                advisor=req.advisor,
                overall_gpa=req.overall_gpa,
                major_gpa=req.major_gpa,
                total_credits_earned=req.total_credits_earned,
                credits_required=req.credits_required,
                credits_remaining=req.credits_remaining,
                courses_completed=json.dumps(req.courses_completed) if req.courses_completed else None,
                courses_in_progress=json.dumps(req.courses_in_progress) if req.courses_in_progress else None,
                courses_remaining=json.dumps(req.courses_remaining) if req.courses_remaining else None,
                requirements_status=json.dumps(req.requirements_status) if req.requirements_status else None,
                raw_data=req.raw_data
            )
            db.add(new_data)

        # Update user's morgan_connected status
        db_user.morgan_connected = True
        db_user.morgan_connected_at = datetime.now(timezone.utc)

        # Update name if provided and not already set
        if req.student_name and not db_user.name:
            db_user.name = req.student_name
        if req.student_id and not db_user.student_id:
            db_user.student_id = req.student_id

        db.commit()

        return {
            "success": True,
            "message": "DegreeWorks data synced successfully!",
            "data": {
                "student_name": req.student_name,
                "degree_program": req.degree_program,
                "classification": req.classification,
                "gpa": req.overall_gpa,
                "credits_earned": req.total_credits_earned
            }
        }

    except Exception as e:
        print(f"[ERROR] DegreeWorks Sync Error: {e}")
        raise HTTPException(500, f"Failed to sync DegreeWorks data: {str(e)}")


@app.get("/api/degreeworks")
async def get_degreeworks(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves the user's DegreeWorks data.
    """
    dw_data = db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).first()

    if not dw_data:
        return {"connected": False, "data": None}

    return {
        "connected": True,
        "data": {
            "student_name": dw_data.student_name,
            "student_id": dw_data.student_id,
            "degree_program": dw_data.degree_program,
            "catalog_year": dw_data.catalog_year,
            "classification": dw_data.classification,
            "advisor": dw_data.advisor,
            "overall_gpa": dw_data.overall_gpa,
            "major_gpa": dw_data.major_gpa,
            "total_credits_earned": dw_data.total_credits_earned,
            "credits_required": dw_data.credits_required,
            "credits_remaining": dw_data.credits_remaining,
            "courses_completed": json.loads(dw_data.courses_completed) if dw_data.courses_completed else [],
            "courses_in_progress": json.loads(dw_data.courses_in_progress) if dw_data.courses_in_progress else [],
            "courses_remaining": json.loads(dw_data.courses_remaining) if dw_data.courses_remaining else [],
            "requirements_status": json.loads(dw_data.requirements_status) if dw_data.requirements_status else [],
            "synced_at": dw_data.synced_at.isoformat() if dw_data.synced_at else None,
            "updated_at": dw_data.updated_at.isoformat() if dw_data.updated_at else None
        }
    }


@app.get("/api/degreeworks/debug")
async def debug_degreeworks(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Debug endpoint to see ALL extracted DegreeWorks data including raw_data preview.
    """
    dw_data = db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).first()

    if not dw_data:
        return {"connected": False, "message": "No DegreeWorks data found for this user"}

    return {
        "connected": True,
        "all_fields": {
            "student_name": dw_data.student_name,
            "student_id": dw_data.student_id,
            "degree_program": dw_data.degree_program,
            "catalog_year": dw_data.catalog_year,
            "classification": dw_data.classification,
            "advisor": dw_data.advisor,
            "overall_gpa": dw_data.overall_gpa,
            "major_gpa": dw_data.major_gpa,
            "total_credits_earned": dw_data.total_credits_earned,
            "credits_required": dw_data.credits_required,
            "credits_remaining": dw_data.credits_remaining,
        },
        "courses_completed_count": len(json.loads(dw_data.courses_completed)) if dw_data.courses_completed else 0,
        "courses_completed": json.loads(dw_data.courses_completed) if dw_data.courses_completed else [],
        "raw_data_preview": dw_data.raw_data[:2000] if dw_data.raw_data else "No raw data",
        "raw_data_full": dw_data.raw_data[:10000] if dw_data.raw_data else "No raw data",
        "synced_at": dw_data.synced_at.isoformat() if dw_data.synced_at else None,
    }


@app.post("/api/degreeworks/test-pdf-parse")
async def test_pdf_parse(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Test endpoint that parses a DegreeWorks PDF and returns what was extracted
    WITHOUT saving to database. Useful for debugging.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Please upload a PDF file")

    try:
        # Save temporarily
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"test_dw_{user['user_id']}_{timestamp}.pdf"
        temp_filepath = os.path.join(CHAT_FILES_FOLDER, temp_filename)

        with open(temp_filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Extract text from PDF
        pdf_text = ""
        try:
            reader = pypdf.PdfReader(temp_filepath)
            for page in reader.pages:
                pdf_text += page.extract_text() + "\n"
        except Exception as e:
            return {"error": f"Could not read PDF: {e}"}

        # Parse the PDF
        data = parse_degreeworks_pdf(pdf_text)

        # Clean up temp file
        try:
            os.remove(temp_filepath)
        except:
            pass

        return {
            "success": True,
            "pdf_text_length": len(pdf_text),
            "pdf_text_preview": pdf_text[:3000],
            "extracted_data": {
                "student_name": data.get('student_name'),
                "student_id": data.get('student_id'),
                "classification": data.get('classification'),
                "degree_program": data.get('degree_program'),
                "overall_gpa": data.get('overall_gpa'),
                "major_gpa": data.get('major_gpa'),
                "total_credits_earned": data.get('total_credits_earned'),
                "credits_required": data.get('credits_required'),
                "credits_remaining": data.get('credits_remaining'),
                "advisor": data.get('advisor'),
                "catalog_year": data.get('catalog_year'),
                "courses_count": len(json.loads(data.get('courses_completed', '[]'))) if data.get('courses_completed') else 0
            },
            "message": "Test parse complete - data NOT saved to database"
        }

    except Exception as e:
        return {"error": f"Failed to process PDF: {str(e)}"}


@app.delete("/api/degreeworks/disconnect")
async def disconnect_degreeworks(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Removes the user's DegreeWorks data and disconnects their Morgan account.
    """
    try:
        # Delete DegreeWorks data
        db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).delete()

        # Update user's morgan_connected status
        db_user = db.query(User).filter(User.id == user["user_id"]).first()
        if db_user:
            db_user.morgan_connected = False
            db_user.morgan_connected_at = None

        db.commit()

        return {"success": True, "message": "DegreeWorks data disconnected"}
    except Exception as e:
        print(f"[ERROR] DegreeWorks Disconnect Error: {e}")
        raise HTTPException(500, f"Failed to disconnect: {str(e)}")


@app.post("/api/degreeworks/upload-pdf")
async def upload_degreeworks_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads DegreeWorks document (PDF or DOCX) and stores the extracted
    text for chat context injection.
    """
    ALLOWED_DW_EXTENSIONS = {'pdf', 'docx', 'doc'}

    print("=" * 60)
    print("DEGREEWORKS UPLOAD ENDPOINT HIT!")
    print(f"File received: {file.filename if file else 'NO FILE'}")
    print(f"User: {user}")
    print("=" * 60)

    if not file or not file.filename:
        raise HTTPException(400, "No file provided")

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_DW_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type. Please upload: {', '.join(ALLOWED_DW_EXTENSIONS)}")

    try:
        # Save the uploaded file temporarily
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"degreeworks_{user['user_id']}_{timestamp}.{ext}"
        temp_filepath = os.path.join(CHAT_FILES_FOLDER, temp_filename)

        content = await file.read()
        print(f"Received file: {file.filename}, size: {len(content)} bytes")

        with open(temp_filepath, "wb") as buffer:
            buffer.write(content)

        # Extract text - try fast local methods first, OCR API only when needed
        pdf_text = ""

        # Method 1: Local pypdf for PDFs (instant for text-based PDFs)
        if ext == 'pdf':
            try:
                print("Trying local pypdf extraction (fast)...")
                reader = pypdf.PdfReader(temp_filepath)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pdf_text += page_text + "\n"
                print(f"pypdf extracted {len(pdf_text)} chars")
            except Exception as e:
                print(f"pypdf extraction failed: {e}")

        # Method 2: Local python-docx for DOCX (instant)
        if ext in ('docx', 'doc'):
            try:
                print("Trying local docx extraction (fast)...")
                doc_file = docx.Document(temp_filepath)
                for para in doc_file.paragraphs:
                    pdf_text += para.text + "\n"
                print(f"docx extracted {len(pdf_text)} chars")
            except Exception as e:
                print(f"docx extraction failed: {e}")

        print(f"Total extracted text: {len(pdf_text)} characters")

        if len(pdf_text.strip()) < 20:
            raise HTTPException(
                400,
                f"Could not extract text from this file ({len(pdf_text)} chars). "
                "Please upload a text-based PDF or DOCX file."
            )

        # Try to parse specific fields (best effort)
        data = parse_degreeworks_pdf(pdf_text)

        # CRITICAL: Always store the raw PDF text - this is used for chat context injection
        data['raw_data'] = pdf_text[:50000]  # Store up to 50k chars

        # Get or create DegreeWorks record
        db_user = db.query(User).filter(User.id == user["user_id"]).first()
        existing = db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).first()

        if existing:
            # Update existing - ALWAYS update raw_data
            existing.raw_data = data['raw_data']
            for key, value in data.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            new_data = DegreeWorksData(user_id=user["user_id"], **data)
            db.add(new_data)

        # Update user's morgan_connected status
        db_user.morgan_connected = True
        db_user.morgan_connected_at = datetime.now(timezone.utc)

        # Update user name if found
        if data.get('student_name') and not db_user.name:
            db_user.name = data['student_name']

        db.commit()

        # Clean up temp file
        try:
            os.remove(temp_filepath)
        except:
            pass

        return {
            "success": True,
            "message": "DegreeWorks PDF uploaded successfully! Your academic data is now available for personalized chat.",
            "data": {
                "student_name": data.get('student_name'),
                "classification": data.get('classification'),
                "degree_program": data.get('degree_program'),
                "overall_gpa": data.get('overall_gpa'),
                "total_credits_earned": data.get('total_credits_earned'),
                "pdf_text_length": len(pdf_text),
                "pdf_stored": True
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] DegreeWorks PDF Upload Error: {e}")
        raise HTTPException(500, f"Failed to process PDF: {str(e)}")


@app.post("/api/degreeworks/scrape-html")
async def scrape_degreeworks_html(
    request: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Receives raw HTML from DegreeWorks page (via bookmarklet) and extracts academic data.
    This is the preferred method - more accurate than PDF parsing.
    """
    html_content = request.get("html", "")

    if not html_content or len(html_content) < 100:
        raise HTTPException(400, "No HTML content provided")

    try:
        # Parse the HTML and extract data
        data = parse_degreeworks_html(html_content)

        if not data or (not data.get('overall_gpa') and not data.get('classification')):
            raise HTTPException(400, "Could not extract academic data from this page. Make sure you're on the DegreeWorks audit page.")

        # Get or create DegreeWorks record
        db_user = db.query(User).filter(User.id == user["user_id"]).first()
        existing = db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).first()

        if existing:
            # Update existing
            for key, value in data.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            new_data = DegreeWorksData(user_id=user["user_id"], **data)
            db.add(new_data)

        # Update user's morgan_connected status
        db_user.morgan_connected = True
        db_user.morgan_connected_at = datetime.now(timezone.utc)

        # Update user name if found
        if data.get('student_name') and not db_user.name:
            db_user.name = data['student_name']
        if data.get('student_id') and not db_user.student_id:
            db_user.student_id = data['student_id']

        db.commit()

        return {
            "success": True,
            "message": "DegreeWorks data synced successfully!",
            "data": {
                "student_name": data.get('student_name'),
                "classification": data.get('classification'),
                "degree_program": data.get('degree_program'),
                "overall_gpa": data.get('overall_gpa'),
                "major_gpa": data.get('major_gpa'),
                "total_credits_earned": data.get('total_credits_earned'),
                "courses_count": len(json.loads(data.get('courses_completed', '[]'))) if data.get('courses_completed') else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] DegreeWorks HTML Scrape Error: {e}")
        raise HTTPException(500, f"Failed to process DegreeWorks data: {str(e)}")


def parse_degreeworks_html(html: str) -> dict:
    """
    Parses DegreeWorks HTML and extracts academic data.
    Based on the DegreeWorks HTML structure.
    """
    data = {}

    # First, extract all text content from HTML
    # Remove script and style tags
    html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags but keep text
    text = re.sub(r'<[^>]+>', ' ', html_clean)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    text_lower = text.lower()

    # Also keep original HTML for pattern matching
    html_lower = html.lower()

    # Extract Student Name - look in multiple places
    name_patterns = [
        r'student[:\s]+name[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
        r'name[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
        r'>([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)</(?:h1|h2|div|span)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, html)
        if match:
            name = match.group(1).strip()
            if len(name) > 3 and len(name) < 50:
                data['student_name'] = name
                break

    # Student ID
    id_patterns = [
        r'(?:student\s*)?id[:\s#]*["\']?(\d{7,9})["\']?',
        r'>\s*(\d{7,9})\s*<',
    ]
    for pattern in id_patterns:
        match = re.search(pattern, html_lower)
        if match:
            data['student_id'] = match.group(1)
            break

    # Overall GPA - this is critical
    gpa_patterns = [
        r'overall\s*gpa[:\s]*(\d\.\d{1,2})',
        r'cumulative\s*gpa[:\s]*(\d\.\d{1,2})',
        r'gpa[:\s]+(\d\.\d{1,2})',
        r'gpa\s*:\s*(\d\.\d{1,2})',
        r'gpa\s+(\d\.\d{1,2})',
        r'total\s*gpa[:\s]*(\d\.\d{1,2})',
        r'career\s*gpa[:\s]*(\d\.\d{1,2})',
        r'>(\d\.\d{2})<.*?gpa',
        r'gpa.*?>(\d\.\d{2})<',
    ]
    for pattern in gpa_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                gpa = float(match.group(1))
                if 0 <= gpa <= 4.0:
                    data['overall_gpa'] = gpa
                    break
            except:
                pass

    # Fallback: Find any decimal that looks like GPA
    if not data.get('overall_gpa'):
        # Look near GPA keyword
        gpa_area = re.search(r'gpa.{0,30}', text_lower)
        if gpa_area:
            gpa_match = re.search(r'(\d\.\d{1,2})', gpa_area.group())
            if gpa_match:
                gpa = float(gpa_match.group(1))
                if 1.0 <= gpa <= 4.0:
                    data['overall_gpa'] = gpa

    # Major GPA
    major_gpa_patterns = [
        r'major\s*gpa[:\s]*(\d\.\d{1,2})',
        r'program\s*gpa[:\s]*(\d\.\d{1,2})',
    ]
    for pattern in major_gpa_patterns:
        match = re.search(pattern, text_lower)
        if match:
            data['major_gpa'] = float(match.group(1))
            break

    # Classification
    class_patterns = [
        r'classification[:\s]*(freshman|sophomore|junior|senior|graduate)',
        r'class[:\s]*(freshman|sophomore|junior|senior|graduate)',
        r'standing[:\s]*(freshman|sophomore|junior|senior|graduate)',
        r'level[:\s]*(freshman|sophomore|junior|senior|graduate)',
        r'student\s*level[:\s]*(freshman|sophomore|junior|senior|graduate)',
        r'>(freshman|sophomore|junior|senior|graduate)<',
    ]
    for pattern in class_patterns:
        match = re.search(pattern, text_lower)
        if match:
            data['classification'] = match.group(1).title()
            break

    # If classification not found, try to determine from credits
    if not data.get('classification') and data.get('total_credits_earned'):
        credits = data['total_credits_earned']
        if credits >= 90:
            data['classification'] = 'Senior'
        elif credits >= 60:
            data['classification'] = 'Junior'
        elif credits >= 30:
            data['classification'] = 'Sophomore'
        else:
            data['classification'] = 'Freshman'

    # Degree/Program/Major
    degree_patterns = [
        r'(bachelor\s+of\s+science\s+in\s+[a-z\s]+?)(?:\s|<|$)',
        r'(master\s+of\s+science\s+in\s+[a-z\s]+?)(?:\s|<|$)',
        r'major[:\s]*(computer\s+science|information\s+(?:systems|science)|cybersecurity|software\s+engineering)',
        r'program[:\s]*(computer\s+science|information\s+(?:systems|science)|cybersecurity)',
        r'>(computer\s+science|information\s+systems)<',
    ]
    for pattern in degree_patterns:
        match = re.search(pattern, text_lower)
        if match:
            program = match.group(1).strip().title()
            if len(program) > 5:
                data['degree_program'] = program
                break

    # Credits - look for various patterns
    credits_patterns = [
        r'(?:total|earned|completed)\s*(?:credits|hours)[:\s]*(\d{2,3}(?:\.\d)?)',
        r'(\d{2,3}(?:\.\d)?)\s*(?:credits|hours)\s*(?:earned|completed|total)',
        r'credits\s*(?:earned|applied)[:\s]*(\d{2,3}(?:\.\d)?)',
        r'hours\s*earned[:\s]*(\d{2,3}(?:\.\d)?)',
        r'credits\s*:\s*(\d{2,3}(?:\.\d)?)',
        r'total\s*credits[:\s]*(\d{2,3}(?:\.\d)?)',
    ]
    for pattern in credits_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                credits = float(match.group(1))
                # Valid range for student credits (20-200), avoid 100 (often percentage)
                if 20 < credits <= 200 and credits != 100:
                    data['total_credits_earned'] = credits
                    break
            except:
                pass

    # Credits Required
    req_patterns = [
        r'(?:credits|hours)\s*required[:\s]*(\d{2,3})',
        r'required[:\s]*(\d{2,3})\s*(?:credits|hours)',
        r'total\s*(?:credits|hours)[:\s]*(\d{2,3})',
    ]
    for pattern in req_patterns:
        match = re.search(pattern, text_lower)
        if match:
            req = float(match.group(1))
            if 60 <= req <= 180:
                data['credits_required'] = req
                break

    # Credits Remaining
    remain_patterns = [
        r'(?:remaining|still\s*need|left)[:\s]*(\d{1,3}(?:\.\d)?)\s*(?:credits|hours)?',
        r'(\d{1,3}(?:\.\d)?)\s*(?:credits|hours)\s*(?:remaining|left|needed)',
    ]
    for pattern in remain_patterns:
        match = re.search(pattern, text_lower)
        if match:
            remain = float(match.group(1))
            if 0 <= remain <= 150:
                data['credits_remaining'] = remain
                break

    # Catalog Year
    catalog_match = re.search(r'(?:catalog|requirement)[:\s]*(\d{4}[-–]\d{4}|\d{4})', text_lower)
    if catalog_match:
        data['catalog_year'] = catalog_match.group(1)

    # Advisor
    advisor_patterns = [
        r'advisor[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)*)',
        r'advised\s+by[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    ]
    for pattern in advisor_patterns:
        match = re.search(pattern, text)
        if match:
            advisor = match.group(1).strip()
            if len(advisor) > 3:
                data['advisor'] = advisor
                break

    # Extract completed courses - look for course patterns
    # Pattern: DEPT 123 Course Title Grade Credits Term
    courses_completed = []
    course_patterns = [
        # Standard format: COSC 111 Intro to CS A 3.00 Fall 2024
        r'([A-Z]{2,4})\s*(\d{3}[A-Z]?)\s+([A-Za-z][A-Za-z\s&\-,]+?)\s+([ABCDF][+-]?)\s+(\d(?:\.\d{1,2})?)\s+((?:Fall|Spring|Summer|Winter)\s*\d{4})',
        # Without term: COSC 111 Intro to CS A 3.00
        r'([A-Z]{2,4})\s*(\d{3}[A-Z]?)\s+([A-Za-z][A-Za-z\s&\-,]{3,30}?)\s+([ABCDF][+-]?)\s+(\d(?:\.\d{1,2})?)',
        # Minimal: COSC 111 A 3.00
        r'([A-Z]{2,4})\s*(\d{3}[A-Z]?)\s+([ABCDF][+-]?)\s+(\d(?:\.\d{1,2})?)',
    ]

    seen_courses = set()
    for pattern in course_patterns:
        for match in re.finditer(pattern, text):
            groups = match.groups()
            if len(groups) >= 4:
                dept = groups[0]
                num = groups[1]
                code = f"{dept} {num}"

                if code in seen_courses:
                    continue
                seen_courses.add(code)

                course = {'code': code}

                if len(groups) == 6:  # Full format with term
                    course['name'] = groups[2].strip()[:50]
                    course['grade'] = groups[3]
                    course['credits'] = float(groups[4])
                    course['term'] = groups[5]
                elif len(groups) == 5:  # Without term
                    course['name'] = groups[2].strip()[:50]
                    course['grade'] = groups[3]
                    course['credits'] = float(groups[4])
                elif len(groups) == 4:  # Minimal
                    course['grade'] = groups[2]
                    course['credits'] = float(groups[3])

                if course.get('grade') in ['A', 'A-', 'A+', 'B', 'B-', 'B+', 'C', 'C-', 'C+', 'D', 'D-', 'D+', 'F']:
                    courses_completed.append(course)

    if courses_completed:
        data['courses_completed'] = json.dumps(courses_completed[:50])  # Limit to 50 courses

    # Extract remaining/needed courses
    remaining_courses = []
    still_needed_pattern = r'still\s+need(?:ed)?[:\s]+(.+?)(?:\.|$)'
    for match in re.finditer(still_needed_pattern, text_lower):
        req = match.group(1).strip()
        if len(req) > 5 and len(req) < 200:
            remaining_courses.append({'requirement': req})

    if remaining_courses:
        data['courses_remaining'] = json.dumps(remaining_courses[:20])

    # Store raw text for reference (truncated)
    data['raw_data'] = text[:30000]

    return data


def parse_degreeworks_pdf(text: str) -> dict:
    """
    Parses DegreeWorks PDF text using pure text processing.
    No LLM needed - cleans the text first, then extracts structured data with regex.
    Fast, deterministic, and free (no API call).
    """
    data = {}

    # Store raw text for the "chat with PDF" feature
    data['raw_data'] = text[:30000]

    # =====================================================
    # STEP 1: Clean the raw PDF text
    # Remove noise, collapse multi-line entries, keep only useful lines
    # =====================================================
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip noise lines
        if stripped.startswith('Satisfied by:'):
            continue
        if stripped.startswith('Exception by:'):
            continue
        if stripped.startswith('Morgan State University') and '- *****' in stripped:
            continue
        if stripped.startswith('Disclaimer'):
            break
        if stripped.startswith('Legend'):
            break
        if stripped.startswith('Ellucian Degree'):
            break
        clean_lines.append(stripped)

    clean_text = '\n'.join(clean_lines)
    # Also make a single-line version for multi-line course matching
    collapsed = ' '.join(clean_lines)

    print("=" * 60)
    print(f"PDF: {len(text)} chars raw -> {len(clean_text)} chars cleaned")
    print("=" * 60)

    # =====================================================
    # STEP 2: Extract header fields (GPA, name, classification, etc.)
    # =====================================================

    # Student name: "Student name Last, First"
    name_match = re.search(r'Student\s+name\s+(\w[\w\'-]+),\s+(\w[\w\'-]+)', text)
    if name_match:
        data['student_name'] = f"{name_match.group(2)} {name_match.group(1)}"

    # Overall GPA: "Overall GPA\n3.953" or "GPA: 3.953"
    gpa_match = re.search(r'Overall\s+GPA\s*[:\n]?\s*(\d\.\d{1,3})', text)
    if gpa_match:
        gpa = float(gpa_match.group(1))
        if 0.0 <= gpa <= 4.0:
            data['overall_gpa'] = gpa

    # Major GPA: "Your GPA in these classes is 4.000"
    major_gpa_match = re.search(r'Your\s+GPA\s+in\s+these\s+classes\s+is\s+(\d\.\d{1,3})', text)
    if major_gpa_match:
        mgpa = float(major_gpa_match.group(1))
        if 0.0 <= mgpa <= 4.0:
            data['major_gpa'] = mgpa

    # Classification: "Classification 4-Senior" or "Classification Senior"
    class_match = re.search(r'Classification\s+(?:\d-)?(Freshman|Sophomore|Junior|Senior|Graduate)', text, re.IGNORECASE)
    if class_match:
        data['classification'] = class_match.group(1).title()

    # Credits applied: "Credits applied:  128.5"
    credits_match = re.search(r'Credits\s+applied:\s*(\d+\.?\d*)', text)
    if credits_match:
        creds = float(credits_match.group(1))
        if 0 <= creds <= 300:
            data['total_credits_earned'] = creds

    # Credits required: "Credits required: 120"
    creq_match = re.search(r'Credits\s+required:\s*(\d+\.?\d*)', text)
    if creq_match:
        creq = float(creq_match.group(1))
        if 30 <= creq <= 300:
            data['credits_required'] = creq
            if data.get('total_credits_earned'):
                remaining = max(0, creq - data['total_credits_earned'])
                data['credits_remaining'] = remaining

    # Degree program: "Degree Bachelor of Science" + "Major Computer Science"
    degree_match = re.search(r'Degree\s+(Bachelor\s+of\s+\w+|Master\s+of\s+\w+)', text)
    major_match = re.search(r'Major\s+([A-Za-z ]+?)(?:\s{2,}|Program)', text)
    if degree_match and major_match:
        data['degree_program'] = f"{degree_match.group(1)} in {major_match.group(1).strip()}"
    elif degree_match:
        data['degree_program'] = degree_match.group(1)

    # Advisor: "Advisor Vojislav Stojkovic" (stop at double-space or end of line)
    advisor_match = re.search(r'Advisor\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text)
    if advisor_match:
        data['advisor'] = advisor_match.group(1).strip()

    # Catalog year: "Catalog year:  SPRING 2024"
    catalog_match = re.search(r'Catalog\s+year:\s*(\w+\s+\d{4})', text)
    if catalog_match:
        data['catalog_year'] = catalog_match.group(1)

    # Transfer hours (extracted but not stored in DB - kept in raw_data only)
    # transfer_match = re.search(r'Transfer\s*Hours\s+(\d+\.?\d*)', text)

    # =====================================================
    # STEP 3: Extract ALL courses from cleaned collapsed text
    # Pattern: DEPT CODE  COURSE NAME  GRADE  CREDITS  TERM
    # Handles multi-line names because text is collapsed
    # =====================================================

    # Course code prefixes we care about (add more as needed)
    DEPT_PREFIXES = r'(?:COSC|MATH|CLCO|EEGR|INSS|PHYS|BIOL|CHEM|ENGL|HIST|PSYC|PHIL|HLTH|WGST|FIN|ORTR|THEA|PHEC)'

    # Letter grades, transfer grades, pass/fail, and in-progress
    VALID_GRADES = r'(?:A\+?|A-|B\+?|B-|C\+?|C-|D\+?|D-|F|TRA|TRB|TRC|TRD|PT|IP|W)'

    # Main course extraction pattern on collapsed text
    # Course name: up to ~60 chars of letters/digits/spaces/punctuation, but NOT containing
    # another course code or grade-like pattern (prevents runaway matching)
    course_pattern = re.compile(
        r'(' + DEPT_PREFIXES + r'\s+\d{3}(?:TR)?)\s+'  # course code (e.g., COSC 470, PHYS 116TR)
        r'([A-Z][A-Za-z0-9 &/\',\.\-\(\)]{2,55}?)\s+'  # course name (2-55 chars, starts with uppercase)
        r'\b(' + VALID_GRADES + r')\b\s+'                 # grade with word boundary
        r'(\d+\.?\d*)\s+'                                  # credits
        r'((?:FALL|SPRING|SUMMER)\s+\d{4})',              # term
        re.IGNORECASE
    )

    # In-progress pattern: "COSC 458 SOFTWARE ENGINEERING IP (3) SPRING 2026"
    # Course name limited to 55 chars max to prevent runaway across multiple entries
    ip_pattern = re.compile(
        r'(' + DEPT_PREFIXES + r'\s+\d{3})\s+'
        r'([A-Z][A-Za-z0-9 &/\',\.\-\(\)]{2,55}?)\s+'
        r'IP\s+\((\d+)\)\s+'
        r'((?:FALL|SPRING|SUMMER)\s+\d{4})',
        re.IGNORECASE
    )

    completed_courses = []
    ip_courses = []
    seen_codes = set()

    # First pass: extract in-progress courses (IP pattern is more specific)
    for match in ip_pattern.finditer(collapsed):
        code = match.group(1).upper().strip()
        name = match.group(2).strip()
        credits = int(match.group(3))
        term = match.group(4).strip()
        if code not in seen_codes:
            seen_codes.add(code)
            ip_courses.append({
                "code": code,
                "name": name,
                "credits": credits,
                "status": "in_progress",
                "term": term
            })

    # Second pass: extract completed courses
    for match in course_pattern.finditer(collapsed):
        code = match.group(1).upper().strip()
        name = match.group(2).strip()
        grade = match.group(3).upper().strip()
        credits = float(match.group(4))
        term = match.group(5).strip()

        if code in seen_codes:
            continue
        seen_codes.add(code)

        if grade == 'IP':
            ip_courses.append({
                "code": code,
                "name": name,
                "credits": int(credits),
                "status": "in_progress",
                "term": term
            })
        else:
            completed_courses.append({
                "code": code,
                "name": name,
                "grade": grade,
                "credits": credits,
                "term": term
            })

    if completed_courses:
        data['courses_completed'] = json.dumps(completed_courses)
    if ip_courses:
        data['courses_in_progress'] = json.dumps(ip_courses)

    # Derive classification from credits if not found in header
    if not data.get("classification") and data.get("total_credits_earned"):
        credits = data["total_credits_earned"]
        if credits >= 90:
            data["classification"] = "Senior"
        elif credits >= 60:
            data["classification"] = "Junior"
        elif credits >= 30:
            data["classification"] = "Sophomore"
        else:
            data["classification"] = "Freshman"

    print("=" * 60)
    print("EXTRACTION SUMMARY:")
    print(f"   Name: {data.get('student_name', 'NOT FOUND')}")
    print(f"   GPA: {data.get('overall_gpa', 'NOT FOUND')}")
    print(f"   Major GPA: {data.get('major_gpa', 'NOT FOUND')}")
    print(f"   Credits: {data.get('total_credits_earned', 'NOT FOUND')}")
    print(f"   Classification: {data.get('classification', 'NOT FOUND')}")
    print(f"   Program: {data.get('degree_program', 'NOT FOUND')}")
    print(f"   Advisor: {data.get('advisor', 'NOT FOUND')}")
    print(f"   Courses Completed: {len(completed_courses)}")
    print(f"   Courses In Progress: {len(ip_courses)}")
    if completed_courses:
        print(f"   Completed codes: {[c['code'] for c in completed_courses]}")
    if ip_courses:
        print(f"   In-progress codes: {[c['code'] for c in ip_courses]}")
    print("=" * 60)

    return data




def extract_file_content(filepath: str) -> str:
    """Reads text from PDF, DOCX, or TXT files."""
    ext = filepath.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'pdf':
            #  UPDATED: Uses pypdf instead of PyPDF2
            reader = pypdf.PdfReader(filepath)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif ext in ['docx', 'doc']:
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            return "[Image or unsupported file type - Text extraction skipped]"
    except Exception as e:
        print(f"Error reading file: {e}")
        return f"[Error reading file content: {e}]"
    
    # Limit content to ~15k chars to fit context window
    return text[:15000]

# --- CHAT ROUTES (WITH CONVERSATION MEMORY + PERSONALIZATION) ---
@app.post("/chat")
async def chat_with_bot(req: QueryRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user: raise HTTPException(401, "Unauthorized")

    user_q = req.query.strip()
    session_id = req.session_id or "default"

    # Fetch user's DegreeWorks data for personalization
    student_context = ""
    has_student_data = False
    has_raw_pdf_data = False
    dw_data = db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).first()
    if dw_data:
        has_student_data = True
        student_context = "\n" + "="*60 + "\n"
        student_context += "THIS STUDENT'S DEGREEWORKS ACADEMIC RECORD:\n"
        student_context += "="*60 + "\n\n"

        # Student profile summary
        student_context += "STUDENT PROFILE:\n"
        if dw_data.student_name:
            student_context += f"- Name: {dw_data.student_name}\n"
        if dw_data.student_id:
            student_context += f"- Student ID: {dw_data.student_id}\n"
        if dw_data.classification:
            student_context += f"- Classification: {dw_data.classification}\n"
        if dw_data.degree_program:
            student_context += f"- Degree Program: {dw_data.degree_program}\n"
        if dw_data.overall_gpa:
            student_context += f"- Overall GPA: {dw_data.overall_gpa}\n"
        if dw_data.major_gpa:
            student_context += f"- Major GPA: {dw_data.major_gpa}\n"
        if dw_data.total_credits_earned:
            student_context += f"- Credits Earned: {dw_data.total_credits_earned}\n"
        if dw_data.credits_required:
            student_context += f"- Credits Required: {dw_data.credits_required}\n"
        if dw_data.credits_remaining:
            student_context += f"- Credits Remaining: {dw_data.credits_remaining}\n"
        if dw_data.advisor:
            student_context += f"- Academic Advisor: {dw_data.advisor}\n"
        if dw_data.catalog_year:
            student_context += f"- Catalog Year: {dw_data.catalog_year}\n"
        student_context += "\n"

        # Completed courses - clearly labeled DO NOT RECOMMEND
        completed_codes = []
        if dw_data.courses_completed:
            try:
                completed = json.loads(dw_data.courses_completed)
                if completed:
                    completed_codes = [c.get('code', '') for c in completed]
                    student_context += f"ALREADY COMPLETED COURSES (DO NOT RECOMMEND THESE):\n"
                    for c in completed:
                        student_context += f"  - {c.get('code', '')} {c.get('name', '')} (Grade: {c.get('grade', '')})\n"
                    student_context += "\n"
            except: pass

        # In-progress courses - clearly labeled DO NOT RECOMMEND
        if dw_data.courses_in_progress:
            try:
                in_progress = json.loads(dw_data.courses_in_progress)
                if in_progress:
                    for c in in_progress:
                        completed_codes.append(c.get('code', ''))
                    student_context += f"CURRENTLY ENROLLED (DO NOT RECOMMEND THESE EITHER):\n"
                    for c in in_progress:
                        student_context += f"  - {c.get('code', '')} {c.get('name', '')}\n"
                    student_context += "\n"
            except: pass

        # Remaining requirements
        if dw_data.courses_remaining:
            try:
                remaining = json.loads(dw_data.courses_remaining)
                if remaining:
                    student_context += f"STILL NEEDS TO COMPLETE (PRIORITIZE THESE FOR RECOMMENDATIONS):\n"
                    for c in remaining[:10]:
                        req = c.get('requirement', c.get('code', ''))
                        student_context += f"  - {req}\n"
                    student_context += "\n"
            except: pass

        student_context += "INSTRUCTION: When recommending courses, ONLY recommend from the AVAILABLE COURSES list below. NEVER recommend courses from the completed or enrolled lists above.\n"
        if COURSE_CATALOG_TEXT:
            student_context += "\n" + COURSE_CATALOG_TEXT + "\n"
        student_context += "="*60 + "\n\n"

        # Store raw data flag but don't dump the full PDF text into context
        if dw_data.raw_data and len(dw_data.raw_data) > 100:
            has_raw_pdf_data = True

    # Fetch recent conversation history for context (last 6 exchanges)
    recent_history = db.query(ChatHistory)\
        .filter(ChatHistory.user_id == user["user_id"])\
        .filter(ChatHistory.session_id == session_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(10)\
        .all()

    recent_history = list(reversed(recent_history))

    conversation_context = ""
    if recent_history:
        conversation_context = "Previous conversation:\n"
        for chat in recent_history:
            conversation_context += f"User: {chat.user_query}\n"
            conversation_context += f"Assistant: {chat.bot_response}\n"
        conversation_context += "\n"

    # 1. Check for File Upload in Message (Markdown link)
    file_match = re.search(r'uploads/chat_files/([^\)]+)', user_q)

    if file_match and USE_VERTEX_AGENT:
        # File uploaded -> include file content as context for the agent
        filename = file_match.group(1)
        filepath = os.path.join(CHAT_FILES_FOLDER, filename)

        if os.path.exists(filepath):
            file_content = extract_file_content(filepath)
            clean_query = re.sub(r'\[.*?\]\(.*?\)', '', user_q).strip()
            if not clean_query: clean_query = "Summarize this file."

            file_context = f"{student_context}{conversation_context}File Content:\n{file_content}\n"
            answer = query_agent(
                query=clean_query,
                user_id=str(user["user_id"]),
                context=file_context,
            )
        else:
            answer = "I received the file link, but I cannot find the file on the server to read it."

    elif file_match and llm:
        # Legacy: File uploaded with old LLM pipeline
        filename = file_match.group(1)
        filepath = os.path.join(CHAT_FILES_FOLDER, filename)

        if os.path.exists(filepath):
            file_content = extract_file_content(filepath)
            system_msg = f"""You are a helpful academic assistant for Morgan State University's Computer Science department.
Use the provided file content and conversation history to answer the user's question.
{student_context}"""

            clean_query = re.sub(r'\[.*?\]\(.*?\)', '', user_q).strip()
            if not clean_query: clean_query = "Summarize this file."

            user_msg = f"{conversation_context}File Content:\n{file_content}\n\nCurrent Question: {clean_query}"

            try:
                response = llm([
                    SystemMessage(content=system_msg),
                    HumanMessage(content=user_msg)
                ])
                answer = response.content
            except Exception as e:
                answer = f"I read the file, but had trouble analyzing it: {e}"
        else:
            answer = "I received the file link, but I cannot find the file on the server to read it."

    elif USE_VERTEX_AGENT:
        # Vertex AI Agent Engine path - send everything to the agent
        try:
            agent_context = ""
            if student_context:
                agent_context += student_context
            if conversation_context:
                agent_context += conversation_context

            print(f" Vertex AI query: '{user_q[:50]}...' (user={user['user_id']}, context={len(agent_context)} chars)")
            answer = query_agent(
                query=user_q,
                user_id=str(user["user_id"]),
                context=agent_context,
            )
        except Exception as e:
            print(f"   Vertex AI Chat Error: {e}")
            answer = "I'm having trouble processing your request. Please try again."
    elif llm and retriever:
        # Legacy Pinecone + OpenAI RAG path (fallback)
        norm = re.sub(r'[\s\W]+', '', user_q.lower())
        if re.match(r'^(hi|hello|hey)\b', user_q.lower()):
            answer = "Hello! How can I help you today?"
        elif re.match(r'^(bye|goodbye|see you)\b', user_q.lower()):
            answer = "Goodbye! Have a great day."
        elif re.search(r'\b(thankyou|thanks|thanx|thx|ty)\b', norm):
            answer = "You're welcome! Let me know if you have any other questions."
        else:
            try:
                docs = retriever.get_relevant_documents(user_q)
                context_docs = "\n\n".join([doc.page_content for doc in docs[:8]])
                system_prompt = f"""You are CS Navigator, an academic assistant for Morgan State University's CS department.
{student_context}
ONLY answer based on the KNOWLEDGE BASE CONTEXT provided. If info is not found, say so honestly."""
                full_message = f"{conversation_context}Knowledge base:\n{context_docs}\n\nQuestion: {user_q}"
                response = llm([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=full_message)
                ])
                answer = response.content.strip()
            except Exception as e:
                print(f"   Legacy Chat Error: {e}")
                answer = "I'm having trouble processing your request."
    else:
        answer = "AI system is initializing. Please try again in a moment."

    # 3. SAVE to RDS (User-Specific)
    try:
        new_chat = ChatHistory(
            user_id=user["user_id"],
            session_id=session_id,
            user_query=user_q,
            bot_response=answer
        )
        db.add(new_chat)
        db.commit()
    except Exception as e:
        print(f"[ERROR] Failed to save chat history: {e}")

    return {"response": answer}


# ==============================================================================
# STREAMING CHAT ENDPOINT (Server-Sent Events)
# ==============================================================================
@app.post("/chat/stream")
async def chat_stream(req: QueryRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    Returns text chunks as they arrive from the AI agent for faster perceived response time.
    """
    if not user:
        raise HTTPException(401, "Unauthorized")

    user_q = req.query.strip()
    session_id = req.session_id or "default"

    # Build context (same as regular /chat endpoint)
    student_context = ""
    dw_data = db.query(DegreeWorksData).filter(DegreeWorksData.user_id == user["user_id"]).first()
    if dw_data:
        student_context = "\n" + "="*60 + "\n"
        student_context += "THIS STUDENT'S DEGREEWORKS ACADEMIC RECORD:\n"
        student_context += "="*60 + "\n\n"
        student_context += "STUDENT PROFILE:\n"
        if dw_data.student_name:
            student_context += f"- Name: {dw_data.student_name}\n"
        if dw_data.student_id:
            student_context += f"- Student ID: {dw_data.student_id}\n"
        if dw_data.classification:
            student_context += f"- Classification: {dw_data.classification}\n"
        if dw_data.degree_program:
            student_context += f"- Degree Program: {dw_data.degree_program}\n"
        if dw_data.overall_gpa:
            student_context += f"- Overall GPA: {dw_data.overall_gpa}\n"
        if dw_data.major_gpa:
            student_context += f"- Major GPA: {dw_data.major_gpa}\n"
        if dw_data.total_credits_earned:
            student_context += f"- Credits Earned: {dw_data.total_credits_earned}\n"
        if dw_data.credits_required:
            student_context += f"- Credits Required: {dw_data.credits_required}\n"
        if dw_data.credits_remaining:
            student_context += f"- Credits Remaining: {dw_data.credits_remaining}\n"
        if dw_data.advisor:
            student_context += f"- Academic Advisor: {dw_data.advisor}\n"
        if dw_data.catalog_year:
            student_context += f"- Catalog Year: {dw_data.catalog_year}\n"
        student_context += "\n"

        # Completed courses
        if dw_data.courses_completed:
            try:
                completed = json.loads(dw_data.courses_completed)
                if completed:
                    student_context += "ALREADY COMPLETED COURSES (DO NOT RECOMMEND THESE):\n"
                    for c in completed[:15]:
                        student_context += f"  - {c.get('code', '')} {c.get('name', '')} (Grade: {c.get('grade', '')})\n"
                    student_context += "\n"
            except: pass

        # Remaining requirements
        if dw_data.courses_remaining:
            try:
                remaining = json.loads(dw_data.courses_remaining)
                if remaining:
                    student_context += "STILL NEEDS TO COMPLETE (PRIORITIZE THESE FOR RECOMMENDATIONS):\n"
                    for c in remaining[:10]:
                        req_text = c.get('requirement', c.get('code', ''))
                        student_context += f"  - {req_text}\n"
                    student_context += "\n"
            except: pass

        student_context += "INSTRUCTION: When recommending courses, ONLY recommend from the AVAILABLE COURSES list below.\n"
        if COURSE_CATALOG_TEXT:
            student_context += "\n" + COURSE_CATALOG_TEXT + "\n"
        student_context += "="*60 + "\n\n"

    # Conversation history
    recent_history = db.query(ChatHistory)\
        .filter(ChatHistory.user_id == user["user_id"])\
        .filter(ChatHistory.session_id == session_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(6)\
        .all()
    recent_history = list(reversed(recent_history))

    conversation_context = ""
    if recent_history:
        conversation_context = "Previous conversation:\n"
        for chat in recent_history:
            conversation_context += f"User: {chat.user_query}\n"
            conversation_context += f"Assistant: {chat.bot_response}\n"
        conversation_context += "\n"

    agent_context = student_context + conversation_context

    # Store user_id and session_id for saving history after stream completes
    user_id = user["user_id"]

    # =========================================================================
    # CACHE CHECK - Return cached response instantly if available
    # =========================================================================
    context_hash = get_context_hash(user_id, has_degreeworks=bool(dw_data))
    cached_response = query_cache.get(user_q, context_hash)

    if cached_response:
        print(f"[CACHE] HIT for query: {user_q[:50]}...")

        async def generate_cached_sse():
            """Return cached response as SSE."""
            # Send status to show it's from cache
            yield f"data: {json.dumps({'type': 'status', 'content': 'Retrieved from cache'})}\n\n"
            # Send the full response immediately
            yield f"data: {json.dumps({'type': 'done', 'content': cached_response})}\n\n"

            # Still save to chat history
            try:
                with SessionLocal() as save_db:
                    new_chat = ChatHistory(
                        user_id=user_id,
                        session_id=session_id,
                        user_query=user_q,
                        bot_response=cached_response
                    )
                    save_db.add(new_chat)
                    save_db.commit()
            except Exception as e:
                print(f"[ERROR] Failed to save cached chat history: {e}")

        return StreamingResponse(
            generate_cached_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # =========================================================================
    # CACHE MISS - Stream from AI agent and cache the result
    # =========================================================================
    print(f"[CACHE] MISS for query: {user_q[:50]}...")

    async def generate_sse():
        """SSE generator that streams text chunks from the agent."""
        full_response = ""
        try:
            for event in query_agent_stream(
                query=user_q,
                user_id=str(user_id),
                context=agent_context
            ):
                event_type = event.get("type", "")
                content = event.get("content", "")

                if event_type == "status":
                    yield f"data: {json.dumps({'type': 'status', 'content': content})}\n\n"

                elif event_type == "chunk":
                    full_response += content
                    # Send SSE event
                    yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"

                elif event_type == "done":
                    full_response = content or full_response
                    yield f"data: {json.dumps({'type': 'done', 'content': full_response})}\n\n"

                elif event_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': content})}\n\n"
                    full_response = content
                    break

        except Exception as e:
            print(f"[ERROR] Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred during streaming.'})}\n\n"
            full_response = "An error occurred during streaming."

        # Cache the successful response
        if full_response and "error" not in full_response.lower()[:50]:
            if query_cache.set(user_q, full_response, context_hash):
                print(f"[CACHE] Stored response for: {user_q[:50]}...")

        # Save to chat history after stream completes
        try:
            with SessionLocal() as save_db:
                new_chat = ChatHistory(
                    user_id=user_id,
                    session_id=session_id,
                    user_query=user_q,
                    bot_response=full_response
                )
                save_db.add(new_chat)
                save_db.commit()
        except Exception as e:
            print(f"[ERROR] Failed to save streamed chat history: {e}")

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==============================================================================
# GUEST CHAT ENDPOINT (No Authentication Required)
# ==============================================================================
@app.post("/chat/guest")
async def chat_guest(req: GuestQueryRequest, request: Request):
    """
    Guest chat endpoint - NO authentication required.
    - No personalization (no DegreeWorks)
    - No history persistence
    - Rate limited: 10 requests/minute per IP
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    if not check_guest_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again in a minute or sign up for unlimited access!"
        )

    user_q = req.query.strip()
    if not user_q:
        return {"response": "Please enter a question."}

    # #11 - Limit query length (500 chars max)
    if len(user_q) > 500:
        user_q = user_q[:500]

    # Small talk override - handle greetings, acknowledgments, and non-questions
    lower_q = user_q.lower().strip()
    norm = re.sub(r'[\s\W]+', '', lower_q)
    word_count = len(lower_q.split())

    # #9 FIX: Only match greetings if it's JUST a greeting (1-2 words max)
    # Greetings (including typos) - only if short message
    greeting_patterns = ['hi', 'hey', 'heyt', 'hii', 'heyy', 'hello', 'helo', 'howdy', 'sup', 'yo', 'hola', 'greetings']
    if word_count <= 2 and (norm in greeting_patterns or re.match(r'^(hi+|hey+t?|hello+)$', norm)):
        return {"response": "Hello! I'm CS Navigator. How can I help you learn about Morgan State's Computer Science program today?"}

    # #8 FIX: "what's up", "how are you" patterns
    elif norm in ['whatsup', 'wassup', 'wazzup', 'whatsgood', 'howareyou', 'howru', 'howreyou', 'howyoudoing']:
        return {"response": "I'm doing great, thanks for asking! How can I help you with Morgan State's CS program today?"}

    # Goodbyes - only if short
    elif word_count <= 3 and re.match(r'^(bye|goodbye|see you|later|cya|peace|gotta go|gtg)', lower_q):
        return {"response": "Goodbye! Sign up for a free account to save your chat history and get personalized advice!"}

    # Thank you
    elif re.search(r'\b(thank|thanks|thanx|thx|ty|appreciate)\b', lower_q):
        return {"response": "You're welcome! Feel free to ask more questions. Sign up to unlock personalized features!"}

    # #8 FIX: Reactions and fillers (lol, haha, test, etc.)
    elif norm in ['lol', 'lmao', 'rofl', 'haha', 'hahaha', 'hehe', 'lolol', 'xd', 'test', 'testing', 'testtest', 'asdf', 'aaa', 'zzz', 'idk', 'idc', 'nvm', 'nevermind', 'bruh', 'bro', 'dude', 'wow', 'omg', 'wtf', 'wth']:
        return {"response": "I'm here whenever you're ready! Ask me anything about Morgan State's CS program - courses, professors, requirements, or career paths."}

    # Acknowledgments (ok, sure, cool, etc.)
    elif norm in ['ok', 'okay', 'okk', 'okok', 'k', 'kk', 'sure', 'alright', 'aight', 'cool', 'nice', 'great', 'good', 'gotit', 'understood', 'isee', 'ah', 'oh', 'ohh', 'hmm', 'hm', 'mhm', 'yep', 'yup', 'yes', 'yeah', 'ya', 'no', 'nope', 'nah', 'fine', 'bet', 'word', 'facts', 'true', 'right', 'correct']:
        return {"response": "Got it! Feel free to ask me anything about Morgan State's CS program - courses, professors, requirements, or career opportunities!"}

    # Very short inputs (1-2 chars) or just punctuation/emojis
    elif len(norm) <= 2 or not any(c.isalpha() for c in user_q):
        return {"response": "I'm here to help! Ask me about CS courses, professors, degree requirements, or anything else about Morgan State's Computer Science program."}

    # =========================================================================
    # CACHE CHECK - Return cached response instantly for guest queries
    # =========================================================================
    # Guest queries share cache (no user-specific context)
    cached_response = query_cache.get(user_q, context_hash="")
    if cached_response:
        print(f"[CACHE] HIT (guest) for: {user_q[:50]}...")
        return {"response": cached_response, "cached": True}

    # Use Vertex AI Agent for real questions
    if USE_VERTEX_AGENT:
        try:
            # Build light guest context
            guest_profile = req.guestProfile or {}
            guest_context = ""
            guest_classification = guest_profile.get("classification", "")
            guest_gpa = guest_profile.get("gpa", "")
            if guest_classification or guest_gpa:
                parts = []
                if guest_classification: parts.append(f"a {guest_classification} student")
                if guest_gpa: parts.append(f"with ~{guest_gpa} GPA")
                guest_context = f"[Guest user info: {' '.join(parts)}]\n"

            # Use a guest-specific user_id based on IP for session management
            guest_user_id = f"guest_{client_ip.replace('.', '_')}"
            print(f"[CACHE] MISS (guest) for: '{user_q[:50]}...'")
            answer = query_agent(
                query=user_q,
                user_id=guest_user_id,
                context=guest_context,
            )

            # Cache the successful response
            if answer and "error" not in answer.lower()[:50]:
                query_cache.set(user_q, answer, context_hash="")

        except Exception as e:
            print(f"   Guest Vertex AI Error: {e}")
            answer = "I'm having trouble processing your request. Please try again."
    elif llm and retriever:
        # Legacy Pinecone + OpenAI RAG path (fallback)
        try:
            docs = retriever.get_relevant_documents(user_q)
            context_docs = "\n\n".join([doc.page_content for doc in docs[:8]])
            if not context_docs.strip():
                answer = "I don't have specific information about that. Contact the CS department at compsci@morgan.edu or (443) 885-3962."
            else:
                response = llm([
                    SystemMessage(content="You are CS Navigator for Morgan State University's CS department. ONLY answer from the provided context."),
                    HumanMessage(content=f"Context:\n{context_docs}\n\nQuestion: {user_q}")
                ])
                answer = response.content.strip()
        except Exception as e:
            print(f"   Guest Legacy Error: {e}")
            answer = "I'm having trouble processing your request. Please try again."
    else:
        answer = "AI system is initializing. Please try again in a moment."

    return {"response": answer}

@app.get("/chat-history")
async def get_chat_history(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch chat history for the logged-in user from RDS"""
    chats = db.query(ChatHistory)\
              .filter(ChatHistory.user_id == user["user_id"])\
              .order_by(ChatHistory.timestamp.asc())\
              .all()
    
    # Format for frontend
    history = []
    for c in chats:
        history.append({
            "session_id": c.session_id or "default",
            "user": c.user_query,
            "bot": c.bot_response,
            "time": c.timestamp.isoformat()
        })
        
    return {"history": history}

@app.post("/reset-history")
async def reset_chat_history(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete history only for this user"""
    db.query(ChatHistory).filter(ChatHistory.user_id == user["user_id"]).delete()
    db.commit()
    return {"message": "Chat history reset."}

# --- Voice Mode Endpoints ---
@app.post("/api/tts")
async def text_to_speech(req: TTSRequest, _user=Depends(get_current_user)):
    """Convert text to speech using OpenAI TTS API"""
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OpenAI API key not configured")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Use TTS-1 for speed (tts-1-hd for quality but slower)
        response = client.audio.speech.create(
            model="tts-1",
            voice=req.voice,
            input=req.text[:4096],  # Limit to 4096 chars
            response_format="mp3"
        )

        # Stream the audio response
        audio_data = io.BytesIO(response.content)
        return StreamingResponse(
            audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=response.mp3"}
        )
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(500, f"TTS generation failed: {str(e)}")

@app.get("/api/popular-questions")
async def get_popular_questions():
    """Returns 8 randomly selected questions from a curated pool."""
    import random

    QUESTION_POOL = [
        # Course & curriculum
        "What courses should I take next semester if I'm interested in AI/ML?",
        "Can you recommend a study plan for the cybersecurity track?",
        "What are the prerequisites for COSC 450 Operating Systems?",
        "What electives count toward the CS degree?",
        "What math courses are required for the CS major?",
        "What is the recommended course sequence for freshmen CS students?",
        "Which courses cover data structures and algorithms?",
        # Department & faculty
        "Who are the professors in the CS department and what do they teach?",
        "Who is the chair of the Computer Science department?",
        "What research areas do CS faculty specialize in?",
        "How do I find a faculty mentor for my capstone project?",
        # Career & opportunities
        "What internship and co-op opportunities are available for CS majors?",
        "What career paths can I pursue with a CS degree from Morgan State?",
        "How can I prepare for technical interviews?",
        "What companies recruit CS students from Morgan State?",
        # Academic advising & graduation
        "How do I apply for graduation and what requirements do I need?",
        "How many credits do I need to graduate with a CS degree?",
        "What is the difference between a B.S. and B.A. in Computer Science?",
        "What is the minimum GPA required to stay in the CS program?",
        # Research & extracurricular
        "What research labs and projects can I join in the CS department?",
        "Are there any CS student organizations or clubs at Morgan State?",
        "How can I get involved in undergraduate research?",
        "What programming competitions can Morgan State students participate in?",
        # Frequently asked
        "How do I contact my academic advisor?",
        "Where is the Computer Science department located?",
        "How do I register for CS courses?",
    ]

    return {"questions": random.sample(QUESTION_POOL, 8)}

# --- Admin / Ingest Routes ---
@app.post("/ingest")
async def ingest_data_endpoint(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    files = [os.path.join(DATA_DIR, fn) for fn in sorted(os.listdir(DATA_DIR)) if fn.lower().endswith(".json")]
    raw = []
    for p in files:
        raw.extend(load_json_documents([p]))

    splitter = TokenTextSplitter(chunk_size=800, chunk_overlap=160, model_name="gpt-3.5-turbo")
    texts, metas = [], []
    for doc in raw:
        for chunk in splitter.split_text(doc["text"]):
            texts.append(chunk)
            metas.append({"source": os.path.basename(doc["source"])})

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=OPENAI_API_KEY)
    PineconeVectorStore.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metas,
        index_name=PINECONE_INDEX,
        namespace=PINECONE_NAMESPACE,
    )
    return {"message": f"Ingested into {PINECONE_INDEX}:{PINECONE_NAMESPACE}", "chunks": len(texts)}

@app.delete("/clear-index")
async def clear_index(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    if not pc:
        raise HTTPException(status_code=500, detail="Pinecone not initialized")
    idx = pc.Index(PINECONE_INDEX)
    idx.delete(delete_all=True, namespace=PINECONE_NAMESPACE)
    return {"message": f"Cleared namespace '{PINECONE_NAMESPACE}' in index {PINECONE_INDEX}"}

# --- Curriculum Routes ---
@app.post("/api/curriculum/add")
async def add_course(course: Course, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    arr = json.load(open(CLASSES_FILE, encoding="utf-8"))
    arr.append(course.model_dump())
    json.dump(arr, open(CLASSES_FILE, "w", encoding="utf-8"), indent=2)
    return {"message": "Course added", "course": course}

@app.delete("/api/curriculum/delete/{code}")
async def delete_course(code: str, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    arr = json.load(open(CLASSES_FILE, encoding="utf-8"))
    filtered = [c for c in arr if c.get("course_code") != code]
    json.dump(filtered, open(CLASSES_FILE, "w", encoding="utf-8"), indent=2)
    return {"message": f"{code} deleted"}

@app.get("/api/curriculum")
async def get_curriculum():
    """Returns full curriculum data including degree info, courses, and elective requirements"""
    try:
        data = json.load(open(CLASSES_FILE, encoding="utf-8"))

        # New structure with degree_info, courses, and elective_requirements
        if isinstance(data, dict) and "courses" in data:
            return {
                "degree_info": data.get("degree_info", {}),
                "courses": data.get("courses", []),
                "elective_requirements": data.get("elective_requirements", {})
            }

        # Legacy support for old structure
        if isinstance(data, list):
            return {"degree_info": {}, "courses": data, "elective_requirements": {}}

        for key in ("computer_science_courses", "classes"):
            arr = data.get(key)
            if isinstance(arr, list):
                return {"degree_info": {}, "courses": arr, "elective_requirements": {}}

        cs = data.get("computer_science_courses")
        if isinstance(cs, dict) and isinstance(cs.get("computer_science_courses"), list):
            return {"degree_info": {}, "courses": cs["computer_science_courses"], "elective_requirements": {}}

        return {"degree_info": {}, "courses": [], "elective_requirements": {}}
    except FileNotFoundError:
        return {"degree_info": {}, "courses": [], "elective_requirements": {}}

@app.get("/health")
def health():
    return {"status": "ok", "db": "connected", "ai": "ready" if qa else "offline"}

# ==============================================================================
# ADMIN DASHBOARD ENDPOINTS
# ==============================================================================

# --- Admin: User Management ---
@app.get("/api/admin/users")
async def get_all_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(User).order_by(User.created_at.desc())

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) |
            (User.name.ilike(search_term)) |
            (User.student_id.ilike(search_term))
        )

    if role and role != "all":
        query = query.filter(User.role == role)

    users = query.all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "student_id": u.student_id,
                "major": u.major,
                "morgan_connected": u.morgan_connected,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ],
        "total": len(users)
    }

@app.get("/api/admin/users/stats")
async def get_user_stats(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user statistics (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from datetime import timedelta
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = db.query(User).count()
    total_students = db.query(User).filter(User.role == "student").count()
    total_admins = db.query(User).filter(User.role == "admin").count()
    new_this_week = db.query(User).filter(User.created_at >= week_ago).count()
    new_this_month = db.query(User).filter(User.created_at >= month_ago).count()
    morgan_connected = db.query(User).filter(User.morgan_connected == True).count()

    return {
        "total": total_users,
        "students": total_students,
        "admins": total_admins,
        "new_this_week": new_this_week,
        "new_this_month": new_this_month,
        "morgan_connected": morgan_connected
    }

@app.put("/api/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if new_role not in ["student", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'student' or 'admin'")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.role = new_role
    db.commit()

    return {"message": f"User {target_user.email} role updated to {new_role}"}

# --- Admin: System Health ---
@app.get("/api/admin/health")
async def get_system_health(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get detailed system health (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    health_status = {
        "database": {"status": "unknown", "message": ""},
        "vertex_agent": {"status": "unknown", "message": ""},
        "openai_tts": {"status": "unknown", "message": ""},
        "mode": "vertex_ai" if USE_VERTEX_AGENT else "legacy_rag",
        "last_check": datetime.now(timezone.utc).isoformat()
    }

    # Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = {"status": "connected", "message": "Database connection OK"}
    except Exception as e:
        health_status["database"] = {"status": "error", "message": str(e)[:100]}

    # Check Vertex AI Agent
    if USE_VERTEX_AGENT:
        health_status["vertex_agent"] = check_agent_health()
    else:
        # Legacy: check Pinecone
        try:
            if PINECONE_API_KEY and PINECONE_INDEX and LEGACY_RAG_AVAILABLE:
                pc_check = Pinecone(api_key=PINECONE_API_KEY)
                idx = pc_check.Index(PINECONE_INDEX)
                stats = idx.describe_index_stats()
                vector_count = stats.get("total_vector_count", 0)
                health_status["vertex_agent"] = {"status": "n/a (legacy mode)", "message": f"Pinecone: {vector_count} vectors"}
            else:
                health_status["vertex_agent"] = {"status": "not_configured", "message": "Legacy mode, keys missing"}
        except Exception as e:
            health_status["vertex_agent"] = {"status": "error", "message": str(e)[:100]}

    # Check OpenAI TTS
    try:
        if OPENAI_API_KEY:
            health_status["openai_tts"] = {"status": "configured", "message": "TTS API key present"}
        else:
            health_status["openai_tts"] = {"status": "not_configured", "message": "TTS unavailable (no OpenAI key)"}
    except Exception as e:
        health_status["openai_tts"] = {"status": "error", "message": str(e)[:100]}

    return health_status

# --- Admin: Course Edit ---
@app.put("/api/curriculum/{code}")
async def update_course(code: str, course: Course, user=Depends(get_current_user)):
    """Update an existing course (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    arr = json.load(open(CLASSES_FILE, encoding="utf-8"))
    found = False
    for i, c in enumerate(arr):
        if c.get("course_code") == code:
            arr[i] = course.model_dump()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail=f"Course {code} not found")

    json.dump(arr, open(CLASSES_FILE, "w", encoding="utf-8"), indent=2)
    return {"message": f"Course {code} updated", "course": course}

# --- Admin: Knowledge Base Management ---
DATA_SOURCES_DIR = os.path.join(BACKEND_DIR, "data_sources")

@app.get("/api/admin/knowledge-base/files")
async def list_kb_files(user: dict = Depends(get_current_user)):
    """List all knowledge base JSON files (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    files = []
    if os.path.exists(DATA_SOURCES_DIR):
        for f in os.listdir(DATA_SOURCES_DIR):
            if f.endswith(".json"):
                filepath = os.path.join(DATA_SOURCES_DIR, f)
                size = os.path.getsize(filepath)
                modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                files.append({
                    "filename": f,
                    "size": size,
                    "modified": modified.isoformat()
                })

    return {"files": sorted(files, key=lambda x: x["filename"])}

@app.get("/api/admin/knowledge-base/search")
async def search_kb_files(q: str, user: dict = Depends(get_current_user)):
    """Search across all knowledge base files (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not q or len(q) < 2:
        return {"results": []}

    results = []
    search_term = q.lower()

    if os.path.exists(DATA_SOURCES_DIR):
        for filename in os.listdir(DATA_SOURCES_DIR):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(DATA_SOURCES_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                content_lower = content.lower()

                # Find ALL matches in this file
                idx = 0
                match_count = 0
                while True:
                    idx = content_lower.find(search_term, idx)
                    if idx == -1:
                        break

                    match_count += 1

                    # Get context around match (80 chars before and after)
                    start = max(0, idx - 80)
                    end = min(len(content), idx + len(q) + 80)
                    context = content[start:end]

                    # Clean up context (remove newlines for display)
                    context = context.replace('\n', ' ').replace('\r', '')

                    # Find the match in context and highlight it
                    match_start_in_context = idx - start
                    actual_match = content[idx:idx+len(q)]

                    # Build highlighted context
                    highlighted = (
                        context[:match_start_in_context] +
                        f"<mark>{actual_match}</mark>" +
                        context[match_start_in_context + len(q):]
                    )

                    results.append({
                        "filename": filename,
                        "context": "..." + highlighted.strip() + "...",
                        "position": idx,
                        "match_number": match_count
                    })

                    idx += len(q)

                    # Limit matches per file to 10
                    if match_count >= 10:
                        break

            except Exception:
                continue

    # Sort by filename, then position
    results.sort(key=lambda x: (x["filename"], x.get("position", 0)))

    return {"results": results[:50], "total_matches": len(results)}

@app.get("/api/admin/knowledge-base/{filename}")
async def get_kb_file(filename: str, user: dict = Depends(get_current_user)):
    """Get content of a knowledge base file (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files allowed")

    filepath = os.path.join(DATA_SOURCES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = json.load(f)
        return {"filename": filename, "content": content}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON: {str(e)}")

@app.put("/api/admin/knowledge-base/{filename}")
async def update_kb_file(filename: str, content: dict, user: dict = Depends(get_current_user)):
    """Update a knowledge base file (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files allowed")

    filepath = os.path.join(DATA_SOURCES_DIR, filename)

    # Create backup
    if os.path.exists(filepath):
        backup_path = filepath + ".backup"
        shutil.copy(filepath, backup_path)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        return {"message": f"File {filename} updated successfully"}
    except Exception as e:
        # Restore backup on failure
        if os.path.exists(filepath + ".backup"):
            shutil.copy(filepath + ".backup", filepath)
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")

@app.post("/api/admin/knowledge-base/ingest")
async def trigger_ingestion(user: dict = Depends(get_current_user)):
    """Trigger knowledge base re-ingestion (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Import and run ingestion
        from ingestion import ingest_data
        await ingest_data()
        return {"message": "Ingestion completed successfully", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

# --- Admin: Cloud Knowledge Base (Vertex AI Datastore) ---
from datastore_manager import (
    list_datastore_documents,
    get_document_content,
    upload_document,
    delete_document,
    update_document,
    sync_datastore,
    search_documents as search_cloud_kb,
)

@app.get("/api/admin/cloud-kb/documents")
async def list_cloud_kb_docs(user: dict = Depends(get_current_user)):
    """List all documents in the Vertex AI Search datastore"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        docs = list_datastore_documents()
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {e}")

@app.get("/api/admin/cloud-kb/documents/{doc_id}/content")
async def read_cloud_kb_doc(doc_id: str, uri: str = "", user: dict = Depends(get_current_user)):
    """Read content of a document from the cloud KB"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if not uri:
        raise HTTPException(status_code=400, detail="URI parameter required")
    try:
        content = get_document_content(uri)
        return {"content": content, "doc_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read document: {e}")

@app.post("/api/admin/cloud-kb/upload")
async def upload_cloud_kb_doc(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload a new document to the cloud KB"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    allowed_exts = {'txt', 'pdf', 'html', 'csv', 'json'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Allowed types: {', '.join(allowed_exts)}")

    content = await file.read()
    content_type = file.content_type or "text/plain"

    result = upload_document(file.filename, content, content_type)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.put("/api/admin/cloud-kb/documents/{doc_id}")
async def update_cloud_kb_doc(
    doc_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Update content of an existing document in the cloud KB"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    body = await request.json()
    uri = body.get("uri", "")
    content = body.get("content", "")
    if not uri or not content:
        raise HTTPException(status_code=400, detail="URI and content required")

    result = update_document(uri, content.encode("utf-8"))
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.delete("/api/admin/cloud-kb/documents/{doc_id}")
async def delete_cloud_kb_doc(doc_id: str, uri: str = "", user: dict = Depends(get_current_user)):
    """Delete a document from the cloud KB"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = delete_document(doc_id, uri)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/admin/cloud-kb/sync")
async def sync_cloud_kb(user: dict = Depends(get_current_user)):
    """Re-sync all GCS documents into the datastore"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = sync_datastore()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# ==============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ==============================================================================

@app.get("/api/admin/cache/stats")
async def get_cache_stats(user: dict = Depends(get_current_user)):
    """Get cache statistics - hits, misses, hit rate, etc."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    stats = query_cache.get_stats()
    return {
        "success": True,
        "cache_stats": stats
    }

@app.post("/api/admin/cache/clear")
async def clear_cache(user: dict = Depends(get_current_user)):
    """Clear all cached responses"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    cleared_count = query_cache.clear()
    return {
        "success": True,
        "message": f"Cleared {cleared_count} cached items"
    }

@app.get("/api/admin/cloud-kb/search")
async def search_cloud_kb_docs(q: str, user: dict = Depends(get_current_user)):
    """Search across all cloud KB documents"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if not q or len(q) < 2:
        return {"results": []}
    try:
        results = search_cloud_kb(q)
        return {"results": results, "query": q, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

# --- Admin: Analytics ---
@app.get("/api/admin/analytics")
async def get_analytics(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get usage analytics (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from datetime import timedelta
    now = datetime.now(timezone.utc)

    # User signups by day (last 7 days)
    signups_by_day = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(User).filter(
            User.created_at >= day_start,
            User.created_at < day_end
        ).count()
        signups_by_day.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "day": day_start.strftime("%a"),
            "count": count
        })

    # Ticket stats
    total_tickets = db.query(SupportTicket).count()
    open_tickets = db.query(SupportTicket).filter(SupportTicket.status == "open").count()

    return {
        "signups_by_day": signups_by_day,
        "total_users": db.query(User).count(),
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "timestamp": now.isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)