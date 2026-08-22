from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database.schema import Event, Conflict, Resolution, Room, User, EventParticipant
from backend.services.auth_service import get_db, get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics Dashboard"])

@router.get("")
def get_analytics_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_events = db.query(Event).count()
    total_conflicts = db.query(Conflict).count()
    resolved_conflicts = db.query(Conflict).filter(Conflict.is_resolved == True).count()
    
    resolution_rate = round((resolved_conflicts / total_conflicts * 100), 1) if total_conflicts > 0 else 100.0

    # Most common conflict type
    type_counts = db.query(
        Conflict.conflict_type, func.count(Conflict.id)
    ).group_by(Conflict.conflict_type).order_by(func.count(Conflict.id).desc()).all()

    most_common_type = type_counts[0][0] if type_counts else "None"
    conflict_distribution = {tc[0]: tc[1] for tc in type_counts}

    # Room Utilization
    total_rooms = db.query(Room).filter(Room.is_active == True).count()
    booked_rooms = db.query(Event.room_id).filter(Event.room_id.isnot(None), Event.status == "SCHEDULED").distinct().count()
    room_utilization = round((booked_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0.0

    # Automatic vs Manual Resolutions
    auto_resolutions = db.query(Resolution).filter(Resolution.resolution_strategy == "AUTOMATIC").count()

    # Participant Utilization
    total_users = db.query(User).count()
    active_participants = db.query(EventParticipant.user_id).distinct().count()
    participant_utilization = round((active_participants / total_users * 100), 1) if total_users > 0 else 0.0

    return {
        "success": True,
        "totalEvents": total_events,
        "totalConflicts": total_conflicts,
        "resolvedConflicts": resolved_conflicts,
        "resolutionRate": resolution_rate,
        "mostCommonConflictType": most_common_type,
        "conflictDistribution": conflict_distribution,
        "roomUtilization": room_utilization,
        "autoResolutions": auto_resolutions,
        "participantUtilization": participant_utilization
    }
