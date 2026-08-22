from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from backend.database.schema import Availability, User
from backend.services.auth_service import get_db, get_current_user
from backend.schemas import AvailabilityCreate, AvailabilityResponse

router = APIRouter(prefix="/api/availability", tags=["User Availability"])

@router.get("", response_model=List[AvailabilityResponse])
def get_user_availabilities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    avail = db.query(Availability).filter(Availability.user_id == current_user.id).all()
    return [AvailabilityResponse.model_validate(a) for a in avail]

@router.post("", response_model=AvailabilityResponse)
def set_user_availability(
    data: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Availability).filter(
        Availability.user_id == current_user.id,
        Availability.day_of_week == data.day_of_week
    ).first()

    if existing:
        existing.start_time = data.start_time
        existing.end_time = data.end_time
        existing.break_start = data.break_start
        existing.break_end = data.break_end
        db.commit()
        db.refresh(existing)
        return AvailabilityResponse.model_validate(existing)
    else:
        new_avail = Availability(
            user_id=current_user.id,
            day_of_week=data.day_of_week,
            start_time=data.start_time,
            end_time=data.end_time,
            break_start=data.break_start,
            break_end=data.break_end,
            is_recurring=True
        )
        db.add(new_avail)
        db.commit()
        db.refresh(new_avail)
        return AvailabilityResponse.model_validate(new_avail)
