from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User, Field
from ..schemas import FieldCreate, FieldResponse
from ..auth import get_current_user

router = APIRouter(prefix="/api/fields", tags=["Fields"])


@router.post("/", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def create_field(
    field_data: FieldCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new field for the current user."""
    field = Field(
        user_id=current_user.id,
        name=field_data.name,
        location=field_data.location,
        area_hectares=field_data.area_hectares,
        soil_type=field_data.soil_type,
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return FieldResponse.model_validate(field)


@router.get("/", response_model=List[FieldResponse])
async def list_fields(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all fields for the current user."""
    fields = (
        db.query(Field)
        .filter(Field.user_id == current_user.id)
        .order_by(Field.created_at.desc())
        .all()
    )
    return [FieldResponse.model_validate(f) for f in fields]


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a field."""
    field = db.query(Field).filter(
        Field.id == field_id,
        Field.user_id == current_user.id
    ).first()

    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found"
        )

    db.delete(field)
    db.commit()
