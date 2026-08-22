from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.schema import ScheduleHistory, AuditLog, User, Event
from backend.services.auth_service import get_db, get_current_user, require_role

router = APIRouter(tags=["History and Audit Logs"])

@router.get("/api/schedule-history")
def get_schedule_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    history = db.query(ScheduleHistory).order_by(ScheduleHistory.timestamp.desc()).all()
    results = []
    for h in history:
        ev = db.query(Event).filter(Event.id == h.event_id).first()
        usr = db.query(User).filter(User.id == h.changed_by).first()
        results.append({
            "id": h.id,
            "eventId": h.event_id,
            "eventTitle": ev.title if ev else "Deleted Event",
            "oldValues": h.old_values,
            "newValues": h.new_values,
            "reason": h.reason,
            "changedBy": usr.full_name if usr else "System",
            "timestamp": h.timestamp.isoformat()
        })
    return results

@router.get("/api/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    results = []
    for l in logs:
        usr = db.query(User).filter(User.id == l.user_id).first() if l.user_id else None
        results.append({
            "id": l.id,
            "action": l.action,
            "user": usr.full_name if usr else "System/Anonymous",
            "details": l.details,
            "ipAddress": l.ip_address,
            "timestamp": l.timestamp.isoformat()
        })
    return results
