import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship
from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    fields = relationship("Field", back_populates="user", cascade="all, delete-orphan")
    api_usage = relationship("ApiUsage", back_populates="user", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    crop_type = Column(String(100), nullable=False)
    diagnosis = Column(String(255), nullable=True)
    diagnosis_type = Column(String(50), nullable=True)  # disease, deficiency, healthy, unknown
    severity = Column(String(20), nullable=True)  # low, medium, high
    confidence = Column(Float, nullable=True)
    symptoms = Column(Text, nullable=True)
    cause = Column(Text, nullable=True)
    treatment = Column(JSON, nullable=True)  # List of treatment strings
    prevention = Column(Text, nullable=True)
    spray_recommendation = Column(Text, nullable=True)
    soil_fertilizer = Column(Text, nullable=True)
    organic_alternative = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="scans")


class Field(Base):
    __tablename__ = "fields"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    area_hectares = Column(Float, nullable=True)
    soil_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="fields")


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_usage")
