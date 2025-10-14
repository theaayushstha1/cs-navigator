# backend/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Get values
DB_USER = os.getenv("DB_USER", "chatuser").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_HOST = os.getenv("DB_HOST", "localhost").strip()
DB_PORT = int(os.getenv("DB_PORT", "3306").strip())
DB_NAME = os.getenv("DB_NAME", "chatbot").strip()

# Safe connection string creation
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
