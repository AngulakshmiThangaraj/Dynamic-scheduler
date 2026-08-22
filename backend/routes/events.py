from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.database.schema import Event, EventParticipant, EventResource, User, Room, Conflict
from backend.services.auth_service import get_db, get_current_user
from backend.services.conflict_service import ConflictDetectionService
from backend.schemas import EventCreate, EventUpdate, EventResponse

router = APIRouter(prefix="/api/events", tags=["Events"])

def format_event_dict(event: Event) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description or "",
        "date": event.date,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "duration": event.duration,
        "priority": event.priority,
        "organizer_id": event.organizer_id,
        "organizer_name": event.organizer.full_name if event.organizer else "Unknown",
        "location": event.location,
        "room_id": event.room_id,
        "room_name": event.room.name if event.room else "No Room",
        "deadline": event.deadline,
        "preferred_time": event.preferred_time,
        "buffer_time": event.buffer_time,
        "auto_reschedule": event.auto_reschedule,
        "recurrence": event.recurrence,
        "status": event.status,
        "participants": [
            {
                "user_id": p.user_id,
                "full_name": p.user.full_name if p.user else "User",
                "email": p.user.email if p.user else "",
                "is_required": p.is_required,
                "status": p.status
            }
            for p in event.participants
        ],
        "resources": [
            {
                "resource_id": r.resource_id,
                "name": r.resource.name if r.resource else "Resource",
                "quantity": r.quantity
            }
            for r in event.resources
        ]
    }

@router.get("", response_model=List[dict])
def list_events(
    date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Event)
    if date:
        query = query.filter(Event.date == date)
    if status:
        query = query.filter(Event.status == status)

    events = query.all()
    return [format_event_dict(e) for e in events]

@router.get("/{event_id}")
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return format_event_dict(event)

@router.post("")
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate participants
    participant_ids = [p.user_id for p in data.participants] if data.participants else []
    if current_user.id not in participant_ids:
        participant_ids.append(current_user.id)

    # Execute backend conflict detection FIRST
    detector = ConflictDetectionService(db)
    check_payload = {
        "date": data.date,
        "startTime": data.start_time,
        "endTime": data.end_time,
        "duration": data.duration,
        "priority": data.priority,
        "roomId": data.room_id,
        "participants": participant_ids,
        "resources": [r.model_dump() for r in data.resources] if data.resources else [],
        "bufferTime": data.buffer_time,
        "organizerId": current_user.id
    }
    conflicts = detector.check_event_conflicts(check_payload)

    # Determine status based on conflict severity
    has_critical = any(c["severity"] in ["CRITICAL", "HIGH"] for c in conflicts)
    event_status = "CONFLICTED" if has_critical else "SCHEDULED"

    # Transactional DB Creation
    event = Event(
        title=data.title,
        description=data.description,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        duration=data.duration,
        priority=data.priority or "MEDIUM",
        organizer_id=current_user.id,
        location=data.location or "Online",
        room_id=data.room_id,
        deadline=data.deadline,
        preferred_time=data.preferred_time,
        flexible_time_window=data.flexible_time_window or 60,
        buffer_time=data.buffer_time or 15,
        auto_reschedule=data.auto_reschedule if data.auto_reschedule is not None else True,
        recurrence=data.recurrence or "NONE",
        status=event_status
    )
    db.add(event)
    db.flush()

    # Add participants
    for pid in participant_ids:
        req = True
        if data.participants:
            found = next((p for p in data.participants if p.user_id == pid), None)
            if found:
                req = found.is_required
        ep = EventParticipant(event_id=event.id, user_id=pid, is_required=req, status="ACCEPTED")
        db.add(ep)

    # Add resources
    if data.resources:
        for r in data.resources:
            er = EventResource(event_id=event.id, resource_id=r.resource_id, quantity=r.quantity)
            db.add(er)

    # Record persistent conflict entries if conflicts exist
    recorded_conflicts = []
    for c in conflicts:
        db_c = Conflict(
            event_id=event.id,
            conflict_type=c["type"],
            severity=c["severity"],
            score=c["score"],
            explanation=c["explanation"],
            conflicting_event_id=c.get("conflictingEventId"),
            affected_users=c.get("affectedUsers", []),
            is_resolved=False
        )
        db.add(db_c)
        recorded_conflicts.append(c)

    db.commit()
    db.refresh(event)

    return {
        "success": True,
        "status": event_status,
        "event": format_event_dict(event),
        "conflicts": recorded_conflicts
    }

@router.put("/{event_id}")
def update_event(
    event_id: str,
    data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if data.title is not None:
        event.title = data.title
    if data.description is not None:
        event.description = data.description
    if data.date is not None:
        event.date = data.date
    if data.start_time is not None:
        event.start_time = data.start_time
    if data.end_time is not None:
        event.end_time = data.end_time
    if data.duration is not None:
        event.duration = data.duration
    if data.priority is not None:
        event.priority = data.priority
    if data.location is not None:
        event.location = data.location
    if data.room_id is not None:
        event.room_id = data.room_id
    if data.status is not None:
        event.status = data.status

    db.commit()
    db.refresh(event)
    return format_event_dict(event)

@router.delete("/{event_id}")
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()
    return {"success": True, "message": "Event deleted successfully"}
