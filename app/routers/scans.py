import os
import uuid
import mimetypes
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from ..database import get_db
from ..models import User, Scan, ApiUsage
from ..schemas import ScanResponse, ScanListResponse, StatsResponse
from ..auth import get_current_user
from ..config import settings
from ..services.ai_service import analyze_crop_image

router = APIRouter(prefix="/api/scans", tags=["Crop Scans"])


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/analyze", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def analyze_scan(
    image: UploadFile = File(...),
    crop_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a crop image and get AI-powered disease/deficiency analysis."""

    # Validate file extension
    ext = os.path.splitext(image.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read image data
    image_data = await image.read()
    if len(image_data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB."
        )

    # Save image to uploads directory
    upload_dir = os.path.join(settings.UPLOAD_DIR, current_user.id)
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(image_data)

    # Determine MIME type
    media_type = mimetypes.guess_type(filename)[0] or "image/jpeg"

    # Call AI service
    diagnosis = await analyze_crop_image(image_data, crop_type, media_type)

    # Build a relative URL path for the image (served by the static file mount)
    # Convert OS path to URL format: uploads/{user_id}/{filename}
    relative_url = "/uploads/" + current_user.id + "/" + filename

    # Create scan record
    scan = Scan(
        user_id=current_user.id,
        image_path=relative_url,
        crop_type=crop_type,
        diagnosis=diagnosis.diagnosis,
        diagnosis_type=diagnosis.type,
        severity=diagnosis.severity,
        confidence=diagnosis.confidence,
        symptoms=diagnosis.symptoms,
        cause=diagnosis.cause,
        treatment=diagnosis.treatment,
        prevention=diagnosis.prevention,
        spray_recommendation=diagnosis.spray_recommendation,
        soil_fertilizer=diagnosis.soil_fertilizer,
        organic_alternative=diagnosis.organic_alternative,
    )
    db.add(scan)

    # Log API usage
    api_log = ApiUsage(
        user_id=current_user.id,
        endpoint="/api/scans/analyze",
        tokens_used=1024,
    )
    db.add(api_log)

    db.commit()
    db.refresh(scan)

    return ScanResponse.model_validate(scan)


@router.get("/", response_model=ScanListResponse)
async def list_scans(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    crop_type: Optional[str] = Query(None),
    diagnosis_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of user's scan history."""
    query = db.query(Scan).filter(Scan.user_id == current_user.id)

    if crop_type:
        query = query.filter(Scan.crop_type == crop_type)
    if diagnosis_type:
        query = query.filter(Scan.diagnosis_type == diagnosis_type)

    total = query.count()
    scans = (
        query
        .order_by(Scan.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return ScanListResponse(
        scans=[ScanResponse.model_validate(s) for s in scans],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats/summary", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get aggregate scan statistics for the current user."""
    base_query = db.query(Scan).filter(Scan.user_id == current_user.id)

    total_scans = base_query.count()
    diseases = base_query.filter(Scan.diagnosis_type == "disease").count()
    deficiencies = base_query.filter(Scan.diagnosis_type == "deficiency").count()
    healthy = base_query.filter(Scan.diagnosis_type == "healthy").count()

    # Average confidence
    avg_conf = db.query(func.avg(Scan.confidence)).filter(
        Scan.user_id == current_user.id,
        Scan.confidence.isnot(None)
    ).scalar() or 0.0

    # Most common crop
    most_crop = (
        db.query(Scan.crop_type, func.count(Scan.crop_type).label("cnt"))
        .filter(Scan.user_id == current_user.id)
        .group_by(Scan.crop_type)
        .order_by(func.count(Scan.crop_type).desc())
        .first()
    )

    # Most common disease
    most_disease = (
        db.query(Scan.diagnosis, func.count(Scan.diagnosis).label("cnt"))
        .filter(
            Scan.user_id == current_user.id,
            Scan.diagnosis_type == "disease"
        )
        .group_by(Scan.diagnosis)
        .order_by(func.count(Scan.diagnosis).desc())
        .first()
    )

    # Scans this month
    now = datetime.utcnow()
    scans_month = base_query.filter(
        extract("year", Scan.created_at) == now.year,
        extract("month", Scan.created_at) == now.month,
    ).count()

    return StatsResponse(
        total_scans=total_scans,
        diseases_detected=diseases,
        deficiencies_detected=deficiencies,
        healthy_plants=healthy,
        crops_saved=diseases + deficiencies,
        avg_confidence=round(float(avg_conf), 1),
        most_common_crop=most_crop[0] if most_crop else None,
        most_common_disease=most_disease[0] if most_disease else None,
        scans_this_month=scans_month,
    )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific scan by ID."""
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    return ScanResponse.model_validate(scan)


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scan and its associated image."""
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    # Delete image file - image_path may be a URL like '/uploads/...' or a legacy OS path
    if scan.image_path:
        if scan.image_path.startswith('/uploads/'):
            # Convert URL path to filesystem path
            img_filepath = scan.image_path.lstrip('/')
        else:
            img_filepath = scan.image_path
        if os.path.exists(img_filepath):
            try:
                os.remove(img_filepath)
            except OSError:
                pass

    db.delete(scan)
    db.commit()
