import sys
# Force unbuffered output so we see logs immediately
sys.stdout.reconfigure(line_buffering=True)

print("✅✅✅ main.py loaded successfully")

import os
import re
import json
# import time  # Commented: currently unused, kept for potential future use
import shutil # 🔥 NEW: For file operations
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# 🔥 FIXED IMPORTS: Use 'pypdf' which you installed, not 'PyPDF2'
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

print(f"🔍 Looking for .env at: {ENV_PATH}")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print("✅ .env file loaded!")
else:
    print("❌ .env file NOT found at root. Checking backend folder...")
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))

print(f"🔑 JWT_SECRET Check: {'FOUND' if os.getenv('JWT_SECRET') else 'MISSING'}")

# SQLAlchemy Imports
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, text

# Vertex AI Agent Engine (replaces Pinecone + OpenAI RAG pipeline)
from vertex_agent import query_agent, check_agent_health, reset_session

# Text extraction service (PDF, DOCX, images via OCR)
from text_extractor import extract_text as extract_text_api, is_healthy as is_extract_healthy

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
CHAT_FILES_FOLDER = os.path.join(BACKEND_DIR, "uploads", "chat_files") # 🔥 NEW: Chat files folder

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'docx', 'doc', 'mov', 'mp4'} # 🔥 NEW: Added Docs

# Create folders if not exist
for folder in [UPLOAD_FOLDER, CHAT_FILES_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Created folder: {folder}")

# Safety check for keys
if USE_VERTEX_AGENT:
    print(f"🚀 Using Vertex AI Agent Engine at {ADK_BASE_URL}")
elif not all([PINECONE_API_KEY, PINECONE_ENV, PINECONE_INDEX, OPENAI_API_KEY]):
    print("⚠️ WARNING: Some API keys are missing. Chatbot features will be limited.")

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
    session_id = Column(String(255), default="default") # 🔥 NEW: Support multiple threads
    user_query = Column(Text)
    bot_response = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Feedback(Base):
    """
    🔥 NEW: Stores user feedback on bot responses for improving the chatbot.
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
        print("✅ Database tables checked/created.")
    except Exception as e:
        print(f"⚠️ DB Connection Error: {e}")

    # 2. Add session_id column if missing (For existing DBs)
    with engine.connect() as conn:
        try:
            # Check if column exists by selecting from it
            conn.execute(text("SELECT session_id FROM chat_history LIMIT 1"))
        except (OperationalError, ProgrammingError):
            print("⚠️ 'session_id' column missing. Adding it now...")
            try:
                conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_id VARCHAR(255) DEFAULT 'default'"))
                conn.commit()
                print("✅ Successfully added 'session_id' column!")
            except Exception as e:
                print(f"❌ Failed to add column: {e}")

        # 3. Add profile_picture_data column if missing (For base64 storage)
        try:
            conn.execute(text("SELECT profile_picture_data FROM users LIMIT 1"))
        except (OperationalError, ProgrammingError):
            print("⚠️ 'profile_picture_data' column missing. Adding it now...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN profile_picture_data LONGTEXT"))
                conn.commit()
                print("✅ Successfully added 'profile_picture_data' column!")
            except Exception as e:
                print(f"❌ Failed to add profile_picture_data column: {e}")

        # 4. Add morgan_connected_at column if missing
        try:
            conn.execute(text("SELECT morgan_connected_at FROM users LIMIT 1"))
        except (OperationalError, ProgrammingError):
            print("⚠️ 'morgan_connected_at' column missing. Adding it now...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN morgan_connected_at DATETIME"))
                conn.commit()
                print("✅ Successfully added 'morgan_connected_at' column!")
            except Exception as e:
                print(f"❌ Failed to add morgan_connected_at column: {e}")

        # 5. Check if degreeworks_data table exists
        try:
            conn.execute(text("SELECT id FROM degreeworks_data LIMIT 1"))
            print("✅ degreeworks_data table exists")
        except (OperationalError, ProgrammingError):
            print("⚠️ 'degreeworks_data' table missing. Creating it now...")
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
                print("✅ Successfully created 'degreeworks_data' table!")
            except Exception as e:
                print(f"❌ Failed to create degreeworks_data table: {e}")

        # 6. Check if support_tickets table exists
        try:
            conn.execute(text("SELECT id FROM support_tickets LIMIT 1"))
            print("✅ support_tickets table exists")
        except (OperationalError, ProgrammingError):
            print("⚠️ 'support_tickets' table missing. Creating it now...")
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
                print("✅ Successfully created 'support_tickets' table!")
            except Exception as e:
                print(f"❌ Failed to create support_tickets table: {e}")

    # 7. Create/Update admin account
    try:
        db = SessionLocal()
        admin_email = "admin@test.com"
        admin_password = "admin"

        existing_admin = db.query(User).filter(User.email == admin_email).first()

        if existing_admin:
            # Update existing user to admin
            if existing_admin.role != "admin":
                existing_admin.role = "admin"
                db.commit()
                print(f"✅ Updated {admin_email} to admin role!")
            else:
                print(f"✅ Admin account {admin_email} already exists with admin role.")
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
            print(f"✅ Created admin account: {admin_email}")

        db.close()
    except Exception as e:
        print(f"❌ Failed to create/update admin account: {e}")

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
        print(f"🤖 Vertex AI Agent: {health['status']} - {health['message']}")
        if health["status"] != "connected":
            print("⚠️ ADK server not running. Start it with:")
            print("   cd google-ai-engine-research/adk_deploy && python -m google.adk.cli web . --port 8080")
        return

    if not LEGACY_RAG_AVAILABLE:
        print("⚠️ Legacy RAG libraries not installed. Chatbot will be offline.")
        return
    if not all([PINECONE_API_KEY, OPENAI_API_KEY, PINECONE_INDEX]):
        print("⚠️ API Keys missing. Chatbot will be offline.")
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
        print("✅ Legacy AI System Initialized (Pinecone + OpenAI)")
    except Exception as e:
        print(f"❌ AI Init Failed: {e}")

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
        print(f"✅ Static files mounted: /uploads -> {UPLOADS_DIR}")
    except Exception as e:
        print(f"❌ Error mounting static files: {e}")
else:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print(f"✅ Created uploads directory: {UPLOADS_DIR}")

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
    except JWTError:
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
    session_id: str = "default" # 🔥 NEW: Accept session ID

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

# 🔥 DegreeWorks Data Schema
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

# 🔥 NEW: Chat File Upload Endpoint
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
        print(f"❌ File Save Error: {e}")
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
        print(f"❌ DegreeWorks Sync Error: {e}")
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
        print(f"❌ DegreeWorks Disconnect Error: {e}")
        raise HTTPException(500, f"Failed to disconnect: {str(e)}")


@app.post("/api/degreeworks/upload-pdf")
async def upload_degreeworks_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads DegreeWorks document (PDF, DOCX, or image) and stores the extracted
    text for chat context injection. Uses text-extract-api for high-quality
    extraction with OCR support. Falls back to local pypdf for PDFs.
    """
    ALLOWED_DW_EXTENSIONS = {'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif'}

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

        # Method 3: text-extract-api with OCR (for images, or if local extraction got < 50 chars)
        if len(pdf_text.strip()) < 50:
            try:
                print("Local extraction insufficient, trying text-extract-api (OCR)...")
                pdf_text = extract_text_api(temp_filepath, timeout=120)
                print(f"text-extract-api extracted {len(pdf_text)} chars")
            except RuntimeError as e:
                print(f"text-extract-api unavailable: {e}")

        print(f"Total extracted text: {len(pdf_text)} characters")

        if len(pdf_text.strip()) < 20:
            raise HTTPException(
                400,
                f"Could not extract text from this file ({len(pdf_text)} chars). "
                "The file may be image-based. Make sure the text-extract-api Docker service is running for OCR support."
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
        print(f"❌ DegreeWorks PDF Upload Error: {e}")
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
        print(f"❌ DegreeWorks HTML Scrape Error: {e}")
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
    Parses DegreeWorks PDF text and extracts academic data.
    Super enhanced to handle Morgan State DegreeWorks PDF formats.
    """
    data = {}
    # Clean up text - remove extra whitespace but preserve structure
    text_clean = re.sub(r'[ \t]+', ' ', text)
    text_lower_clean = text_clean.lower()

    # Debug: print first 1000 chars to see format
    print("=" * 60)
    print("📄 PDF TEXT PREVIEW (first 1000 chars):")
    print("=" * 60)
    print(text[:1000])
    print("=" * 60)

    # ============ MORGAN STATE DEGREEWORKS HEADER PARSER ============
    # Parse the structured header lines first - these are the most reliable source.
    # Line 1: "Level ... Classification N-Word ... Major ... Program ... Transfer Hours N ... Advisor Name"
    # Line 2: "Credits required: NNN Credits applied: NNN Catalog year: XXXX GPA: N.NNN"
    # Line 3: "Student name Last, First"

    # Header line: Classification (e.g., "Classification 4-Senior")
    header_class = re.search(r'classification\s+\d-(senior|junior|sophomore|freshman|graduate)', text_lower_clean)
    if header_class:
        data['classification'] = header_class.group(1).title()
        print(f"Found classification (header): {data['classification']}")

    # Header line: Major / Program (e.g., "Major Computer Science   Program")
    header_major = re.search(r'major\s+([\w\s]+?)\s{2,}', text_clean, re.IGNORECASE)
    if header_major:
        major = header_major.group(1).strip().title()
        if len(major) > 3:
            data['degree_program'] = major
            print(f"Found program (header): {data['degree_program']}")

    # Header line: Transfer Hours (e.g., "Transfer Hours 56")
    header_transfer = re.search(r'transfer\s*hours\s+(\d+)', text_lower_clean)
    if header_transfer:
        data['transfer_hours'] = float(header_transfer.group(1))
        print(f"Found transfer hours (header): {data['transfer_hours']}")

    # Header line: Advisor (e.g., "Advisor Amjad Ali")
    header_advisor = re.search(r'advisor\s+([\w]+\s+[\w]+)', text_clean, re.IGNORECASE)
    if header_advisor:
        advisor = header_advisor.group(1).strip()
        if advisor.lower() not in ['information', 'prerequisite', 'required', 'course']:
            data['advisor'] = advisor
            print(f"Found advisor (header): {data['advisor']}")

    # Degree summary: "Credits applied: NNN" (e.g., "Credits applied:  139")
    applied_match = re.search(r'credits\s*applied[:\s]+(\d{2,3})', text_lower_clean)
    if applied_match:
        credits_val = float(applied_match.group(1))
        if 10 <= credits_val <= 300:
            data['total_credits_earned'] = credits_val
            print(f"Found credits applied (header): {data['total_credits_earned']}")

    # Degree summary: Inline "GPA: N.NNN" (from the degree summary line, NOT progress bar)
    # The progress bar shows "Overall GPA\n0.000" on separate lines.
    # The degree summary has "GPA: 3.943" inline after "Catalog year" or "Credits applied".
    summary_gpa = re.search(r'(?:catalog\s*year|credits\s*applied).*?gpa[:\s]+(\d\.\d{1,3})', text_lower_clean)
    if summary_gpa:
        gpa = float(summary_gpa.group(1))
        if 0.0 < gpa <= 4.0:
            data['overall_gpa'] = gpa
            print(f"Found GPA (header): {data['overall_gpa']}")

    # Student name: "Student name Last, First" -> "First Last"
    name_match = re.search(r'student\s+name\s+([\w\'\-]+),\s*([\w\'\-]+)', text_clean, re.IGNORECASE)
    if name_match:
        data['student_name'] = f"{name_match.group(2)} {name_match.group(1)}"
        print(f"Found name (header): {data['student_name']}")

    # Catalog year from summary line (e.g., "Catalog year:  FALL 2023")
    cat_match = re.search(r'catalog\s*year[:\s]+((?:fall|spring|summer)\s+\d{4})', text_lower_clean)
    if cat_match:
        data['catalog_year'] = cat_match.group(1).upper()
        print(f"Found catalog year (header): {data['catalog_year']}")

    # ============ GPA EXTRACTION (Most Important) ============
    # Try many different patterns to find GPA (skip if header parser already found it)
    gpa_found = bool(data.get('overall_gpa'))

    # Pattern group 1: Explicit GPA labels (most reliable)
    gpa_patterns_explicit = [
        r'overall\s*gpa[:\s]*(\d\.\d{1,2})',
        r'cumulative\s*gpa[:\s]*(\d\.\d{1,2})',
        r'gpa[:\s]+(\d\.\d{1,2})',
        r'overall[:\s]+(\d\.\d{1,2})',
        r'cumulative[:\s]+(\d\.\d{1,2})',
        r'grade\s*point\s*average[:\s]*(\d\.\d{1,2})',
        r'cum\s*gpa[:\s]*(\d\.\d{1,2})',
        r'inst\s*gpa[:\s]*(\d\.\d{1,2})',  # Institutional GPA
        r'ovr\s*gpa[:\s]*(\d\.\d{1,2})',   # Abbreviated
        r'total\s*gpa[:\s]*(\d\.\d{1,2})',
        r'current\s*gpa[:\s]*(\d\.\d{1,2})',
        r'career\s*gpa[:\s]*(\d\.\d{1,2})',  # Banner/DegreeWorks terminology
        r'gpa\s*:\s*(\d\.\d{1,2})',  # GPA : 3.50
        r'gpa\s+(\d\.\d{1,2})',  # GPA 3.50 (no colon)
    ]

    for pattern in gpa_patterns_explicit:
        match = re.search(pattern, text_lower_clean)
        if match:
            try:
                gpa = float(match.group(1))
                if 0.0 <= gpa <= 4.0:
                    data['overall_gpa'] = gpa
                    print(f"✅ Found GPA (explicit): {gpa}")
                    gpa_found = True
                    break
            except: pass

    # Pattern group 2: GPA near keyword (within 30 chars)
    if not gpa_found:
        gpa_keywords = ['gpa', 'overall', 'cumulative', 'average', 'grade point']
        for keyword in gpa_keywords:
            if keyword in text_lower_clean:
                # Find position of keyword
                pos = text_lower_clean.find(keyword)
                # Look for decimal in nearby text (30 chars before and after)
                nearby = text_lower_clean[max(0, pos-30):pos+40]
                decimal_match = re.search(r'(\d\.\d{2})', nearby)
                if decimal_match:
                    gpa = float(decimal_match.group(1))
                    if 0.0 <= gpa <= 4.0:
                        data['overall_gpa'] = gpa
                        print(f"✅ Found GPA (near '{keyword}'): {gpa}")
                        gpa_found = True
                        break

    # Pattern group 3: Look for X.XX X.XX pattern (often GPA and credits together)
    if not gpa_found:
        double_decimal = re.search(r'(\d\.\d{2})\s+(\d{1,3}\.\d{2})', text)
        if double_decimal:
            first = float(double_decimal.group(1))
            if 0.0 <= first <= 4.0:
                data['overall_gpa'] = first
                print(f"✅ Found GPA (double pattern): {first}")
                gpa_found = True

    # Pattern group 4: Find ANY decimal between 1.0 and 4.0 (last resort)
    if not gpa_found:
        all_decimals = re.findall(r'(?<!\d)(\d\.\d{2})(?!\d)', text)
        for dec in all_decimals:
            val = float(dec)
            # GPA is typically between 1.0 and 4.0
            if 1.5 <= val <= 4.0:
                data['overall_gpa'] = val
                print(f"✅ Found likely GPA (fallback): {val}")
                gpa_found = True
                break

    # ============ CLASSIFICATION ============
    # BEST APPROACH: Use credits to determine classification (most reliable)
    # Credits thresholds: Freshman (0-29), Sophomore (30-59), Junior (60-89), Senior (90+)

    # First, try to get credits if we don't have them yet
    if not data.get('total_credits_earned'):
        # Quick credits search - allow 2-3 digit numbers (e.g., 45, 124)
        credits_match = re.search(r'(\d{2,3}(?:\.\d)?)\s*(?:credits|hours)', text_lower_clean)
        if credits_match:
            try:
                cred_val = float(credits_match.group(1))
                if 20 <= cred_val <= 200:  # Valid credit range
                    data['total_credits_earned'] = cred_val
            except:
                pass

    # Now determine classification from credits (skip if header parser already found it)
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
        print(f"✅ Classification from credits ({credits}): {data['classification']}")

    # If classification not set yet, try multiple fallback patterns
    if not data.get('classification'):
        # Pattern 1: Look for explicit "Classification: Senior" format
        class_patterns = [
            r'classification[:\s]*(senior|junior|sophomore|freshman|graduate)',
            r'class[:\s]*(senior|junior|sophomore|freshman|graduate)',
            r'standing[:\s]*(senior|junior|sophomore|freshman|graduate)',
            r'level[:\s]*(senior|junior|sophomore|freshman|graduate)',
            r'student\s+level[:\s]*(senior|junior|sophomore|freshman|graduate)',
            r'academic\s+level[:\s]*(senior|junior|sophomore|freshman|graduate)',
        ]
        for pattern in class_patterns:
            class_match = re.search(pattern, text_lower_clean)
            if class_match:
                data['classification'] = class_match.group(1).title()
                print(f"✅ Classification from label: {data['classification']}")
                break

        # Pattern 2: Look for standalone classification words with context clues
        if not data.get('classification'):
            # Check if "Senior" appears more than once (likely classification not course)
            for cls in ['Senior', 'Junior', 'Sophomore', 'Freshman', 'Graduate']:
                cls_lower = cls.lower()
                # Count occurrences
                count = len(re.findall(rf'\b{cls_lower}\b', text_lower_clean))
                # If it appears multiple times or near key words, it's likely classification
                if count >= 2:
                    data['classification'] = cls
                    print(f"✅ Classification from frequency ({cls} appeared {count} times): {cls}")
                    break
                # Check if near classification-related keywords
                context_match = re.search(rf'(level|status|standing|class|year).*?\b{cls_lower}\b|\b{cls_lower}\b.*?(level|status|standing|class|year)', text_lower_clean)
                if context_match:
                    data['classification'] = cls
                    print(f"✅ Classification from context: {cls}")
                    break

    # ============ CREDITS ============
    # Skip if header parser already found credits
    credits_found = bool(data.get('total_credits_earned'))

    # IMPORTANT: Look for LABELED credits first (e.g., "Credits applied: 124")
    # Avoid picking up "100%" or "100 %" which is percentage, not credits
    credits_patterns = [
        # DegreeWorks specific patterns - applied/earned FIRST, required LAST
        r'credits\s*applied[:\s]*(\d{2,3}(?:\.\d{1,2})?)',  # "Credits applied: 124.0"
        r'credits\s*earned[:\s]*(\d{2,3}(?:\.\d{1,2})?)',   # "Credits earned: 124"
        r'total\s*credits[:\s]*(\d{2,3}(?:\.\d{1,2})?)',     # "Total credits: 124"
        r'hours\s*earned[:\s]*(\d{2,3}(?:\.\d{1,2})?)',      # "Hours earned: 124"
        r'transfer\s*hours[:\s]*(\d{2,3}(?:\.\d{1,2})?)',    # "Transfer Hours: 41"
        # More general patterns
        r'(\d{2,3}(?:\.\d{1,2})?)\s*credits?\s*(?:applied|earned|completed)',
        r'(\d{2,3}(?:\.\d{1,2})?)\s*(?:credit\s*)?hours?\s*(?:earned|completed)',
        # Required is LAST (fallback - prefer applied/earned over required)
        r'credits\s*required[:\s]*(\d{2,3}(?:\.\d{1,2})?)',  # "Credits required: 120"
    ]

    for pattern in credits_patterns:
        match = re.search(pattern, text_lower_clean)
        if match:
            try:
                credits = float(match.group(1))
                # Must be between 30-200 and NOT be 100 (which is often percentage)
                if 30 <= credits <= 200 and credits != 100:
                    data['total_credits_earned'] = credits
                    print(f"✅ Found Credits (explicit): {credits}")
                    credits_found = True
                    break
            except: pass

    # If we found 100, double-check it's not from "100%" - look for a different number
    if not credits_found:
        # Look specifically for numbers > 100 or numbers like 124, 120, etc.
        credit_match = re.search(r'(?:credits?|hours?)\s*(?:applied|earned|required)[:\s]*(\d{3}(?:\.\d)?)', text_lower_clean)
        if credit_match:
            credits = float(credit_match.group(1))
            if 100 < credits <= 200:
                data['total_credits_earned'] = credits
                print(f"✅ Found Credits (3-digit): {credits}")
                credits_found = True

    # Fallback: Look for "124.0" or "120.0" pattern (common credit amounts)
    if not credits_found:
        common_credits = re.findall(r'(\d{3}\.\d)\b', text)
        for c in common_credits:
            val = float(c)
            if 100 < val <= 150:  # Typical total credits range
                data['total_credits_earned'] = val
                print(f"✅ Found Credits (common pattern): {val}")
                credits_found = True
                break

    # Pattern group 3: Look for standalone numbers that could be credits (last resort)
    if not credits_found:
        # Find 2-3 digit numbers
        all_numbers = re.findall(r'(?<!\d)(\d{2,3})(?:\.\d{1,2})?(?!\d)', text)
        for num in all_numbers:
            val = int(num)
            # Credits typically between 30 and 150 for enrolled students
            if 30 <= val <= 150:
                data['total_credits_earned'] = float(val)
                print(f"✅ Found likely Credits (fallback): {val}")
                credits_found = True
                break

    # ============ DEGREE PROGRAM ============
    if not data.get('degree_program'):
        degree_patterns = [
            r'(bachelor\s+of\s+science\s+in\s+[a-z\s]+)',
            r'(master\s+of\s+science\s+in\s+[a-z\s]+)',
            r'(b\.?s\.?\s+(?:in\s+)?computer\s+science)',
            r'(computer\s+science)',
            r'(information\s+(?:systems?|science))',
            r'(cybersecurity)',
            r'(software\s+engineering)',
            r'(electrical\s+engineering)',
            r'major[:\s]*([a-z\s]+?)(?:\n|$)',
            r'program[:\s]*([a-z\s]+?)(?:\n|$)',
            r'degree[:\s]*([a-z\s]+?)(?:\n|$)',
        ]
        for pattern in degree_patterns:
            match = re.search(pattern, text_lower_clean)
            if match:
                program = match.group(1).strip().title()
                if len(program) > 3 and len(program) < 60:
                    data['degree_program'] = program
                    print(f"✅ Found Program: {program}")
                    break

    # ============ STUDENT NAME ============
    if not data.get('student_name'):
        # Look for patterns like "Name: John Smith" or just capitalized names at start
        name_patterns = [
            r'(?:student|name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'^([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',  # At start of text
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text_clean, re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if 3 < len(name) < 50:
                    data['student_name'] = name
                    print(f"✅ Found Name: {name}")
                    break

    # ============ STUDENT ID ============
    id_match = re.search(r'(?:id|student)[:\s#]*(\d{7,9})', text_lower_clean)
    if id_match:
        data['student_id'] = id_match.group(1)
        print(f"✅ Found Student ID: {data['student_id']}")
    else:
        # Just look for any 7-9 digit number
        id_match = re.search(r'(?<!\d)(\d{7,9})(?!\d)', text)
        if id_match:
            data['student_id'] = id_match.group(1)

    # ============ ADVISOR ============
    if not data.get('advisor'):
        # Look for advisor name in DegreeWorks format
        # Example formats: "Advisor Md/dr Blakeley", "Advisor: Dr. Smith", "Advisor Walden Blakeley"

        # Words that are NOT advisor names
        not_advisor_words = [
            'prerequisite', 'prerequsite', 'required', 'complete', 'incomplete',
            'pending', 'satisfied', 'unsatisfied', 'needed', 'met', 'unmet',
            'information', 'course', 'credit', 'hours', 'gpa', 'grade'
        ]

        # Try multiple patterns
        advisor_found = False

        # Pattern 1: "Advisor" followed by title and name (e.g., "Advisor Md/dr Blakeley")
        advisor_match = re.search(r'advisor[:\s]+(?:md/?dr\.?|dr\.?|mr\.?|ms\.?|mrs\.?|prof\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text_clean, re.IGNORECASE)
        if advisor_match:
            advisor = advisor_match.group(1).strip()
            if advisor.lower() not in not_advisor_words and len(advisor) > 2:
                data['advisor'] = advisor
                advisor_found = True
                print(f"✅ Found Advisor: {advisor}")

        # Pattern 2: Look for name after "Advisor" with more flexible matching
        if not advisor_found:
            # Find the word "Advisor" and grab the next 2-3 words
            advisor_pos = text_clean.lower().find('advisor')
            if advisor_pos != -1:
                # Get text after "Advisor"
                after_advisor = text_clean[advisor_pos + 7:advisor_pos + 50].strip()
                # Split into words and take first 1-2 capitalized words
                words = after_advisor.split()
                name_parts = []
                for word in words[:3]:
                    # Skip titles and non-names
                    clean_word = re.sub(r'[^a-zA-Z]', '', word)
                    if clean_word and clean_word.lower() not in not_advisor_words:
                        if clean_word[0].isupper() and len(clean_word) > 2:
                            name_parts.append(clean_word)
                            if len(name_parts) >= 2:
                                break
                if name_parts:
                    data['advisor'] = ' '.join(name_parts)
                    print(f"✅ Found Advisor (parsed): {data['advisor']}")

    # ============ CATALOG YEAR ============
    if not data.get('catalog_year'):
        catalog_match = re.search(r'(?:catalog|requirement|year)[:\s]*(\d{4}[-–]\d{4}|\d{4})', text_lower_clean)
        if catalog_match:
            data['catalog_year'] = catalog_match.group(1)
            print(f"✅ Found Catalog Year: {data['catalog_year']}")

    # ============ IN-PROGRESS COURSES (Parse FIRST) ============
    # Parse IP courses BEFORE completed courses so they don't get incorrectly categorized
    # DegreeWorks format: "COSC 458 SOFTWARE ENGINEERING IP (3) SPRING 2026"
    courses_in_progress = []
    seen_in_progress = set()

    print("=" * 40)
    print("PARSING IN-PROGRESS COURSES...")

    # Pattern 1: DegreeWorks format - Course with IP grade and credits in parentheses
    # Format: COSC 458 SOFTWARE ENGINEERING IP (3) SPRING 2026
    ip_patterns = [
        # Full format with course name: COSC 458 SOFTWARE ENGINEERING IP (3)
        r'([A-Z]{2,4})\s+(\d{3}[A-Z]?)\s+([A-Z][A-Za-z\s&\-,\./]+?)\s+IP\s+\((\d)\)',
        # Short format: COSC 458 IP (3)
        r'([A-Z]{2,4})\s+(\d{3}[A-Z]?)\s+IP\s+\((\d)\)',
    ]

    for pattern in ip_patterns:
        for match in re.finditer(pattern, text_clean):
            groups = match.groups()
            dept = groups[0]
            num = groups[1]
            code = f"{dept} {num}"

            if code in seen_in_progress:
                continue
            seen_in_progress.add(code)

            course = {'code': code, 'status': 'in_progress'}
            if len(groups) >= 4:
                course['name'] = groups[2].strip()[:50]
                course['credits'] = int(groups[3])
            elif len(groups) >= 3:
                try:
                    course['credits'] = int(groups[2])
                except:
                    pass

            courses_in_progress.append(course)
            print(f"   Found IP course: {code}")

    # Pattern 2: Look for "Preregistered" section (DegreeWorks specific)
    preregistered_match = re.search(r'Preregistered[:\s]*Credits[:\s]*\d+', text_clean, re.IGNORECASE)
    if preregistered_match:
        start_pos = preregistered_match.end()
        preregistered_text = text_clean[start_pos:start_pos+2000]

        # Find courses in preregistered section
        ip_courses = re.findall(r'([A-Z]{2,4})\s+(\d{3}[A-Z]?)\s+([A-Z][A-Za-z\s&\-,\./]+?)\s+IP\s+\((\d)\)', preregistered_text)
        for dept, num, name, credits in ip_courses:
            code = f"{dept} {num}"
            if code not in seen_in_progress:
                seen_in_progress.add(code)
                courses_in_progress.append({
                    'code': code,
                    'name': name.strip()[:50],
                    'credits': int(credits),
                    'status': 'in_progress'
                })
                print(f"   Found IP course (preregistered): {code}")

    if courses_in_progress:
        data['courses_in_progress'] = json.dumps(courses_in_progress[:20])
        print(f"Found {len(courses_in_progress)} in-progress courses")
    else:
        print("No in-progress courses found")

    # ============ COMPLETED COURSES ============
    print("=" * 40)
    print("PARSING COMPLETED COURSES...")
    courses_completed = []
    seen_courses = set()

    # Only match courses with actual letter grades (A, B, C, D, F) or transfer grades (TRA, TRB)
    # DO NOT use broad patterns that match all course codes
    course_patterns = [
        # Format: COSC 111 INTRO TO COMPUTER SCI I A 4 SPRING 2024
        r'([A-Z]{2,4})\s+(\d{3}[A-Z]?)\s+([A-Za-z][A-Za-z\s&\-,\.]+?)\s+(A[+-]?|B[+-]?|C[+-]?|D[+-]?|F|TRA|TRB|TR[A-Z]?|PT)\s+(\d(?:\.\d{1,2})?)',
        # Format: COSC 111 A 4
        r'([A-Z]{2,4})\s+(\d{3}[A-Z]?)\s+(A[+-]?|B[+-]?|C[+-]?|D[+-]?|F|TRA|TRB|TR[A-Z]?|PT)\s+(\d(?:\.\d{1,2})?)',
    ]

    for pattern in course_patterns:
        for match in re.finditer(pattern, text_clean):
            groups = match.groups()
            dept = groups[0]
            num = groups[1]
            code = f"{dept} {num}"

            # Skip if already seen as completed OR if it's an in-progress course
            if code in seen_courses or code in seen_in_progress:
                continue
            seen_courses.add(code)

            course = {'code': code}
            if len(groups) >= 5:
                course['name'] = groups[2].strip()[:50]
                course['grade'] = groups[3]
                course['credits'] = float(groups[4])
            elif len(groups) >= 4:
                course['grade'] = groups[2]
                course['credits'] = float(groups[3])

            courses_completed.append(course)

    if courses_completed:
        data['courses_completed'] = json.dumps(courses_completed[:50])
        print(f"Found {len(courses_completed)} completed courses")

    # Store raw text for debugging
    data['raw_data'] = text[:30000]

    print("=" * 60)
    print("EXTRACTION SUMMARY:")
    print(f"   GPA: {data.get('overall_gpa', 'NOT FOUND')}")
    print(f"   Credits: {data.get('total_credits_earned', 'NOT FOUND')}")
    print(f"   Classification: {data.get('classification', 'NOT FOUND')}")
    print(f"   Program: {data.get('degree_program', 'NOT FOUND')}")
    print(f"   Completed Courses: {len(courses_completed)}")
    print(f"   In-Progress Courses: {len(courses_in_progress)}")
    print("=" * 60)

    return data


# ==============================================================================
# SUPPORT TICKETS API
# ==============================================================================

class TicketCreate(BaseModel):
    subject: str
    category: str  # "bug", "feature", "question", "other"
    description: str
    attachment_data: Optional[str] = None  # Base64 encoded
    attachment_name: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    admin_notes: Optional[str] = None


@app.post("/api/tickets")
async def create_ticket(
    ticket: TicketCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new support ticket"""
    try:
        new_ticket = SupportTicket(
            user_id=user["user_id"],
            subject=ticket.subject,
            category=ticket.category,
            description=ticket.description,
            attachment_data=ticket.attachment_data,
            attachment_name=ticket.attachment_name,
            status="open",
            priority="normal"
        )
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)

        print(f"📩 New support ticket #{new_ticket.id} from user {user['email']}: {ticket.subject}")

        return {
            "success": True,
            "message": "Ticket submitted successfully! We'll review it soon.",
            "ticket_id": new_ticket.id
        }
    except Exception as e:
        print(f"❌ Ticket creation error: {e}")
        raise HTTPException(500, f"Failed to create ticket: {str(e)}")


@app.get("/api/tickets/my")
async def get_my_tickets(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's tickets"""
    tickets = db.query(SupportTicket).filter(
        SupportTicket.user_id == user["user_id"]
    ).order_by(SupportTicket.created_at.desc()).all()

    return {
        "tickets": [
            {
                "id": t.id,
                "subject": t.subject,
                "category": t.category,
                "status": t.status,
                "priority": t.priority,
                "created_at": t.created_at.isoformat(),
                "admin_notes": t.admin_notes
            }
            for t in tickets
        ]
    }


@app.get("/api/tickets")
async def get_all_tickets(
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tickets (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    query = db.query(SupportTicket).order_by(SupportTicket.created_at.desc())

    if status:
        query = query.filter(SupportTicket.status == status)

    tickets = query.all()

    return {
        "tickets": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "user_email": db.query(User).filter(User.id == t.user_id).first().email if t.user_id else None,
                "subject": t.subject,
                "category": t.category,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "admin_notes": t.admin_notes,
                "attachment_name": t.attachment_name,
                "has_attachment": bool(t.attachment_data),
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            }
            for t in tickets
        ],
        "total": len(tickets)
    }


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific ticket"""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    # Users can only view their own tickets, admins can view all
    if user.get("role") != "admin" and ticket.user_id != user["user_id"]:
        raise HTTPException(403, "Not authorized to view this ticket")

    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "subject": ticket.subject,
        "category": ticket.category,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "admin_notes": ticket.admin_notes,
        "attachment_data": ticket.attachment_data,
        "attachment_name": ticket.attachment_name,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None
    }


@app.put("/api/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    update: TicketUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a ticket (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if update.status:
        ticket.status = update.status
        if update.status == "resolved":
            ticket.resolved_by = user["user_id"]
            ticket.resolved_at = datetime.now(timezone.utc)

    if update.priority:
        ticket.priority = update.priority

    if update.admin_notes is not None:
        ticket.admin_notes = update.admin_notes

    db.commit()

    return {"success": True, "message": "Ticket updated successfully"}


@app.get("/api/tickets/stats/summary")
async def get_ticket_stats(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ticket statistics (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    total = db.query(SupportTicket).count()
    open_count = db.query(SupportTicket).filter(SupportTicket.status == "open").count()
    in_progress = db.query(SupportTicket).filter(SupportTicket.status == "in_progress").count()
    resolved = db.query(SupportTicket).filter(SupportTicket.status == "resolved").count()

    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "resolved": resolved
    }


# ==============================================================================
# 🔥 FEEDBACK ENDPOINT - Rate & Report Bot Responses
# ==============================================================================
class FeedbackCreate(BaseModel):
    message_text: str
    feedback_type: str  # 'helpful', 'not_helpful', 'report'
    report_details: Optional[str] = None
    session_id: Optional[str] = "default"


@app.post("/api/feedback")
async def submit_feedback(
    feedback: FeedbackCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback on a bot response to help improve the chatbot"""
    try:
        new_feedback = Feedback(
            user_id=user["user_id"],
            session_id=feedback.session_id,
            message_text=feedback.message_text[:2000],  # Limit to 2000 chars
            feedback_type=feedback.feedback_type,
            report_details=feedback.report_details[:1000] if feedback.report_details else None
        )
        db.add(new_feedback)
        db.commit()

        # Log for analytics
        emoji = "👍" if feedback.feedback_type == "helpful" else "👎" if feedback.feedback_type == "not_helpful" else "🚩"
        print(f"{emoji} Feedback received: {feedback.feedback_type} from user {user['email']}")

        return {"success": True, "message": "Thank you for your feedback!"}

    except Exception as e:
        print(f"❌ Feedback error: {e}")
        raise HTTPException(500, f"Failed to save feedback: {str(e)}")


@app.get("/api/feedback/stats")
async def get_feedback_stats(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback statistics (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    total = db.query(Feedback).count()
    helpful = db.query(Feedback).filter(Feedback.feedback_type == "helpful").count()
    not_helpful = db.query(Feedback).filter(Feedback.feedback_type == "not_helpful").count()
    reports = db.query(Feedback).filter(Feedback.feedback_type == "report").count()

    # Get recent reports for review
    recent_reports = db.query(Feedback).filter(
        Feedback.feedback_type == "report"
    ).order_by(Feedback.timestamp.desc()).limit(10).all()

    return {
        "total": total,
        "helpful": helpful,
        "not_helpful": not_helpful,
        "reports": reports,
        "satisfaction_rate": round((helpful / total * 100), 1) if total > 0 else 0,
        "recent_reports": [
            {
                "id": r.id,
                "message_preview": r.message_text[:100] + "..." if len(r.message_text) > 100 else r.message_text,
                "details": r.report_details,
                "timestamp": r.timestamp.isoformat()
            }
            for r in recent_reports
        ]
    }


# 🔥 NEW HELPER: Extract Text from Files (Updated to use 'pypdf')
def extract_file_content(filepath: str) -> str:
    """Reads text from PDF, DOCX, or TXT files."""
    ext = filepath.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'pdf':
            # 🔥 UPDATED: Uses pypdf instead of PyPDF2
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

        if dw_data.raw_data and len(dw_data.raw_data) > 100:
            has_raw_pdf_data = True
            student_context += "FULL DEGREEWORKS DOCUMENT CONTENT:\n"
            student_context += "-"*40 + "\n"
            student_context += dw_data.raw_data[:15000] + "\n"
            student_context += "-"*40 + "\n\n"

        student_context += "PARSED SUMMARY (if available):\n"
        if dw_data.student_name:
            student_context += f"- Student Name: {dw_data.student_name}\n"
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
        if dw_data.courses_completed:
            try:
                completed = json.loads(dw_data.courses_completed)
                if completed:
                    student_context += f"- Courses Completed ({len(completed)} total):\n"
                    for c in completed[:20]:
                        grade = c.get('grade', '')
                        name = c.get('name', '')
                        student_context += f"  - {c.get('code', '')} {name} (Grade: {grade})\n"
            except: pass
        if dw_data.courses_in_progress:
            try:
                in_progress = json.loads(dw_data.courses_in_progress)
                if in_progress:
                    student_context += f"- Currently Enrolled In:\n"
                    for c in in_progress:
                        student_context += f"  - {c.get('code', '')} {c.get('name', '')}\n"
            except: pass
        if dw_data.courses_remaining:
            try:
                remaining = json.loads(dw_data.courses_remaining)
                if remaining:
                    student_context += f"- Still Needs to Complete:\n"
                    for c in remaining[:10]:
                        req = c.get('requirement', c.get('code', ''))
                        student_context += f"  - {req}\n"
            except: pass
        student_context += "="*60 + "\n\n"

    # Fetch recent conversation history for context (last 6 exchanges)
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
        # Vertex AI Agent Engine path
        norm = re.sub(r'[\s\W]+', '', user_q.lower())
        if re.match(r'^(hi|hello|hey)\b', user_q.lower()):
            answer = "Hello! How can I help you today?"
        elif re.match(r'^(bye|goodbye|see you)\b', user_q.lower()):
            answer = "Goodbye! Have a great day."
        elif re.search(r'\b(thankyou|thanks|thanx|thx|ty)\b', norm):
            answer = "You're welcome! Let me know if you have any other questions."
        else:
            try:
                # Build context for the agent (DegreeWorks + conversation history)
                agent_context = ""
                if student_context:
                    agent_context += student_context
                if conversation_context:
                    agent_context += conversation_context

                print(f"🤖 Vertex AI query: '{user_q[:50]}...' (user={user['user_id']}, context={len(agent_context)} chars)")
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
        print(f"❌ Failed to save chat history: {e}")

    return {"response": answer}

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
            print(f"🤖 [Guest] Vertex AI query: '{user_q[:50]}...'")
            answer = query_agent(
                query=user_q,
                user_id=guest_user_id,
                context=guest_context,
            )
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
async def get_popular_questions(db: Session = Depends(get_db)):
    """
    Returns 6 questions:
    - 2 most frequently asked (from user data)
    - 2 trending (recent popular questions)
    - 2 general questions (hardcoded)
    """
    try:
        # 2 General questions (always shown)
        general_questions = [
            "What internship opportunities are available?",
            "How do I contact my academic advisor?"
        ]

        # Query ALL user questions to find most frequent and trending
        queries = db.query(ChatHistory.user_query)\
            .filter(ChatHistory.user_query.isnot(None))\
            .filter(ChatHistory.user_query != "")\
            .order_by(ChatHistory.timestamp.desc())\
            .limit(1000)\
            .all()

        # Clean and normalize questions
        def normalize_question(q):
            if not q:
                return None
            original = q.strip()
            normalized = re.sub(r'[^\w\s?]', '', q.lower().strip())
            # Skip greetings and short phrases
            skip_words = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'bye', 'goodbye',
                          'ok', 'okay', 'yes', 'no', 'sure', 'great']
            if normalized in skip_words or len(normalized) < 15:
                return None
            # Skip file uploads and follow-ups
            if 'uploads' in normalized or 'chat_files' in normalized:
                return None
            if any(fu in normalized for fu in ['tell me more', 'what about', 'explain more']):
                return None
            # Skip outdated semester-specific questions (past semesters)
            outdated_patterns = ['fall 2024', 'fall 2025', 'spring 2024', 'spring 2025',
                                 'summer 2024', 'summer 2025', 'did i take', 'have i taken']
            if any(op in normalized for op in outdated_patterns):
                return None
            return original

        # Count question frequencies
        question_counts = Counter()
        for (query,) in queries:
            normalized = normalize_question(query)
            if normalized:
                question_counts[normalized] += 1

        # Get 2 MOST FREQUENTLY asked (highest count overall)
        frequent_questions = []
        for question, count in question_counts.most_common(20):
            if count >= 2 and len(question) > 15:  # Asked at least twice
                formatted = question[0].upper() + question[1:]
                if not formatted.endswith('?'):
                    formatted += '?'
                frequent_questions.append(formatted)
                if len(frequent_questions) >= 2:
                    break

        # Get 2 TRENDING questions (recent but different from frequent)
        recent_queries = db.query(ChatHistory.user_query)\
            .filter(ChatHistory.user_query.isnot(None))\
            .order_by(ChatHistory.timestamp.desc())\
            .limit(100)\
            .all()

        recent_counts = Counter()
        for (query,) in recent_queries:
            normalized = normalize_question(query)
            if normalized:
                recent_counts[normalized] += 1

        trending_questions = []
        for question, count in recent_counts.most_common(20):
            # Skip if already in frequent
            if any(question.lower() in fq.lower() or fq.lower() in question.lower()
                   for fq in frequent_questions):
                continue
            if len(question) > 15:
                formatted = question[0].upper() + question[1:]
                if not formatted.endswith('?'):
                    formatted += '?'
                trending_questions.append(formatted)
                if len(trending_questions) >= 2:
                    break

        # Fallback questions if we don't have enough data
        fallback_frequent = [
            "Who is the chair of Computer Science department?",
            "What are the degree requirements for CS major?"
        ]
        fallback_trending = [
            "What programming languages should I learn?",
            "When is the deadline for course registration?"
        ]

        # Fill in with fallbacks if needed
        while len(frequent_questions) < 2:
            for fb in fallback_frequent:
                if fb not in frequent_questions:
                    frequent_questions.append(fb)
                    break

        while len(trending_questions) < 2:
            for fb in fallback_trending:
                if fb not in trending_questions and fb not in frequent_questions:
                    trending_questions.append(fb)
                    break

        # Combine and deduplicate: 2 frequent + 2 trending + 2 general = 6 total
        seen = set()
        all_questions = []

        def add_if_unique(question):
            key = question.lower().strip()
            if key not in seen:
                seen.add(key)
                all_questions.append(question)
                return True
            return False

        # Add frequent questions first
        for q in frequent_questions[:2]:
            add_if_unique(q)

        # Add trending questions
        for q in trending_questions[:2]:
            add_if_unique(q)

        # Add general questions
        for q in general_questions:
            add_if_unique(q)

        # If we still don't have 6, add more fallbacks
        extra_fallbacks = [
            "What courses should I take for cybersecurity?",
            "What research opportunities exist in CS?",
            "Who is the chair of Computer Science?"
        ]
        for q in extra_fallbacks:
            if len(all_questions) >= 6:
                break
            add_if_unique(q)

        return {"questions": all_questions[:6]}

    except Exception as e:
        print(f"Error fetching popular questions: {e}")
        return {
            "questions": [
                "Who is the chair of Computer Science?",
                "What are the prerequisites for COSC 311?",
                "What internship opportunities are available?",
                "How do I contact my academic advisor?",
                "What courses should I take for cybersecurity?",
                "What research opportunities exist in CS?"
            ]
        }

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