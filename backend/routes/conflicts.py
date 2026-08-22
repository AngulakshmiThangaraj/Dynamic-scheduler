from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from backend.database.schema import Conflict, Event, User
from backend.services.auth_service import get_db, get_current_user
from backend.services.scheduling_engine import SchedulingEngine
from backend.schemas import ResolutionRequest

router = APIRouter(prefix="/api/conflicts", tags=["Conflict Resolver"])

@router.get("")
def list_conflicts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conflicts = db.query(Conflict).filter(Conflict.is_resolved == False).all()
    results = []

    for c in conflicts:
        ev = db.query(Event).filter(Event.id == c.event_id).first()
        c_ev = db.query(Event).filter(Event.id == c.conflicting_event_id).first() if c.conflicting_event_id else None

        results.append({
            "id": c.id,
            "eventId": c.event_id,
            "eventTitle": ev.title if ev else "Unknown Event",
            "conflictType": c.conflict_type,
            "severity": c.severity,
            "score": c.score,
            "explanation": c.explanation,
            "conflictingEventId": c.conflicting_event_id,
            "conflictingEventTitle": c_ev.title if c_ev else None,
            "affectedUsers": c.affected_users or [],
            "createdAt": c.created_at.isoformat() if c.created_at else None
        })

    return results

@router.post("/resolve")
def resolve_conflict(
    req: ResolutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    engine = SchedulingEngine(db)
    res = engine.resolve_conflict_auto(conflict_id=req.conflict_id, user_id=current_user.id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Resolution failed"))
    return res
