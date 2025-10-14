# backend/security.py

import os
import bcrypt
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv

# load the .env just like in main.py
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Pull JWT_SECRET from environment
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("Missing JWT_SECRET in .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  

def hash_password(plain: str) -> str:
    # Truncate to 72 bytes for bcrypt compatibility
    truncated = plain.encode('utf-8')[:72]
    # Use bcrypt directly
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(truncated, salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    # Truncate to 72 bytes for bcrypt compatibility
    truncated = plain.encode('utf-8')[:72]
    # Use bcrypt directly
    return bcrypt.checkpw(truncated, hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
