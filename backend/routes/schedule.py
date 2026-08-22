from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.schema import User
from backend.services.auth_service import get_db, get_current_user
from backend.services.scheduling_engine import SchedulingEngine
from backend.schemas import OptimizeRequest, SimulationRequest

router = APIRouter(prefix="/api/schedule", tags=["Smart Scheduling Engine"])

@router.post("/optimize")
def optimize_schedule_slots(
    req: OptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    engine = SchedulingEngine(db)
    recommendations = engine.optimize_schedule(
        event_id=req.event_id,
        date_str=req.date,
        duration=req.duration,
        participant_ids=req.participant_ids,
        room_id=req.room_id,
        preferred_time=req.preferred_time,
        deadline=req.deadline,
        priority=req.priority or "MEDIUM",
        buffer_time=req.buffer_time or 15
    )

    return {
        "success": True,
        "recommendations": recommendations
    }

@router.post("/simulate")
def simulate_schedule_change(
    req: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    engine = SchedulingEngine(db)
    result = engine.simulate_schedule_change(
        event_id=req.event_id,
        proposed_date=req.proposed_date,
        proposed_start=req.proposed_start,
        proposed_end=req.proposed_end,
        proposed_room_id=req.proposed_room_id,
        proposed_participant_ids=req.proposed_participant_ids
    )

    return result
