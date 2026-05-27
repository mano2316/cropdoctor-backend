from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ─── Auth Schemas ───────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str
    phone: Optional[str] = None
    location: Optional[str] = None


class UserLogin(BaseModel):
    full_name: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Scan Schemas ───────────────────────────────────────────

class DiagnosisResult(BaseModel):
    diagnosis: str = "Unknown"
    type: str = "unknown"
    severity: str = "low"
    confidence: float = 0.0
    symptoms: str = ""
    cause: str = ""
    treatment: List[str] = []
    prevention: str = ""


class ScanResponse(BaseModel):
    id: str
    user_id: str
    image_path: str
    crop_type: str
    diagnosis: Optional[str] = None
    diagnosis_type: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None
    symptoms: Optional[str] = None
    cause: Optional[str] = None
    treatment: Optional[List[str]] = None
    prevention: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    scans: List[ScanResponse]
    total: int
    page: int
    per_page: int


class StatsResponse(BaseModel):
    total_scans: int = 0
    diseases_detected: int = 0
    deficiencies_detected: int = 0
    healthy_plants: int = 0
    crops_saved: int = 0
    avg_confidence: float = 0.0
    most_common_crop: Optional[str] = None
    most_common_disease: Optional[str] = None
    scans_this_month: int = 0


# ─── Field Schemas ──────────────────────────────────────────

class FieldCreate(BaseModel):
    name: str
    location: Optional[str] = None
    area_hectares: Optional[float] = None
    soil_type: Optional[str] = None


class FieldResponse(BaseModel):
    id: str
    user_id: str
    name: str
    location: Optional[str] = None
    area_hectares: Optional[float] = None
    soil_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
