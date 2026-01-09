# backend/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="student")  # "admin" or "student"

    # 🔥 Profile fields
    name = Column(String(255), nullable=True)
    student_id = Column(String(50), nullable=True)
    major = Column(String(100), nullable=True, default="Computer Science")
    profile_picture = Column(String(500), nullable=True, default="/user_icon.jpg")
    profile_picture_data = Column(Text, nullable=True)  # Store base64 image data
    morgan_connected = Column(Boolean, nullable=False, default=False)
    morgan_connected_at = Column(DateTime, nullable=True)  # When DegreeWorks was synced
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to DegreeWorks data
    degreeworks = relationship("DegreeWorksData", back_populates="user", uselist=False)


class DegreeWorksData(Base):
    """Stores parsed DegreeWorks academic data for personalized chatbot responses"""
    __tablename__ = "degreeworks_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Student Info
    student_name = Column(String(255), nullable=True)
    student_id = Column(String(50), nullable=True)
    degree_program = Column(String(255), nullable=True)  # e.g., "Bachelor of Science in Computer Science"
    catalog_year = Column(String(20), nullable=True)  # e.g., "2022-2023"
    classification = Column(String(50), nullable=True)  # e.g., "Senior", "Junior"
    advisor = Column(String(255), nullable=True)

    # Academic Progress
    overall_gpa = Column(Float, nullable=True)
    major_gpa = Column(Float, nullable=True)
    total_credits_earned = Column(Float, nullable=True)
    credits_required = Column(Float, nullable=True)
    credits_remaining = Column(Float, nullable=True)

    # Course Data (stored as JSON strings)
    courses_completed = Column(Text, nullable=True)  # JSON: [{code, name, credits, grade, semester}]
    courses_in_progress = Column(Text, nullable=True)  # JSON: [{code, name, credits, semester}]
    courses_remaining = Column(Text, nullable=True)  # JSON: [{code, name, credits, category}]
    requirements_status = Column(Text, nullable=True)  # JSON: [{category, status, details}]

    # Raw data backup
    raw_data = Column(Text, nullable=True)  # Full JSON dump for reference

    # Metadata
    synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="degreeworks")


class SupportTicket(Base):
    """Support tickets submitted by users for bug reports and feedback"""
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Ticket Details
    subject = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # "bug", "feature", "question", "other"
    description = Column(Text, nullable=False)
    attachment_data = Column(Text, nullable=True)  # Base64 encoded file or screenshot
    attachment_name = Column(String(255), nullable=True)

    # Status tracking
    status = Column(String(50), nullable=False, default="open")  # "open", "in_progress", "resolved", "closed"
    priority = Column(String(20), nullable=False, default="normal")  # "low", "normal", "high", "urgent"

    # Admin response
    admin_notes = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="tickets")