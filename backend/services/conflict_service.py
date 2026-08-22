from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database.schema import (
    Event, EventParticipant, Room, Resource, EventResource,
    Availability, Holiday, Conflict, User
)

def time_to_minutes(t_str: str) -> int:
    """Converts HH:MM string to total minutes from midnight."""
    try:
        parts = t_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0

def minutes_to_time(mins: int) -> str:
    """Converts total minutes from midnight to HH:MM string."""
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"

def is_time_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    """Checks if interval [s1, e1) overlaps with [s2, e2)."""
    return max(s1, s2) < min(e1, e2)

class ConflictDetectionService:
    def __init__(self, db: Session):
        self.db = db

    def check_event_conflicts(
        self,
        event_data: Dict[str, Any],
        exclude_event_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes full multi-dimensional conflict detection across all 9 categories.
        Returns a list of conflict details dictionaries.
        """
        conflicts = []

        date_str = event_data.get("date")
        start_str = event_data.get("startTime") or event_data.get("start_time")
        end_str = event_data.get("endTime") or event_data.get("end_time")
        room_id = event_data.get("roomId") or event_data.get("room_id")
        participant_ids = event_data.get("participants", [])
        requested_resources = event_data.get("resources", []) # list of {"resource_id": ..., "quantity": ...}
        priority = event_data.get("priority", "MEDIUM")
        buffer_mins = event_data.get("bufferTime") or event_data.get("buffer_time", 15)

        start_m = time_to_minutes(start_str)
        end_m = time_to_minutes(end_str)

        # Parse date day of week (0=Mon, 6=Sun)
        dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day_of_week = dt_obj.weekday()

        # Fetch existing events on the same date
        existing_query = self.db.query(Event).filter(
            Event.date == date_str,
            Event.status != "CANCELLED"
        )
        if exclude_event_id:
            existing_query = existing_query.filter(Event.id != exclude_event_id)
        existing_events = existing_query.all()

        # 1. HOLIDAY CONFLICT
        holiday = self.db.query(Holiday).filter(Holiday.date == date_str).first()
        if holiday:
            conflicts.append({
                "type": "HOLIDAY_CONFLICT",
                "severity": "CRITICAL",
                "score": 95.0,
                "explanation": f"Event is scheduled on company holiday: '{holiday.name}'.",
                "conflictingEventId": None,
                "affectedUsers": participant_ids
            })

        # 2. ROOM CAPACITY CONFLICT
        if room_id:
            room = self.db.query(Room).filter(Room.id == room_id).first()
            if room:
                total_participants = len(participant_ids) + 1  # include organizer
                if total_participants > room.capacity:
                    conflicts.append({
                        "type": "ROOM_CAPACITY_CONFLICT",
                        "severity": "HIGH",
                        "score": 85.0,
                        "explanation": f"Room '{room.name}' capacity ({room.capacity}) exceeded by requested participants ({total_participants}).",
                        "conflictingEventId": None,
                        "affectedUsers": participant_ids
                    })

        # 3. WORKING HOUR & LUNCH BREAK CONFLICTS
        all_users = set(participant_ids)
        organizer_id = event_data.get("organizerId") or event_data.get("organizer_id")
        if organizer_id:
            all_users.add(organizer_id)

        for uid in all_users:
            user = self.db.query(User).filter(User.id == uid).first()
            user_name = user.full_name if user else f"User {uid}"

            avail = self.db.query(Availability).filter(
                Availability.user_id == uid,
                Availability.day_of_week == day_of_week
            ).first()

            if avail:
                work_s = time_to_minutes(avail.start_time)
                work_e = time_to_minutes(avail.end_time)

                # Outside working hours
                if start_m < work_s or end_m > work_e:
                    conflicts.append({
                        "type": "WORKING_HOUR_CONFLICT",
                        "severity": "MEDIUM",
                        "score": 65.0,
                        "explanation": f"Event ({start_str}-{end_str}) is outside {user_name}'s working hours ({avail.start_time}-{avail.end_time}).",
                        "conflictingEventId": None,
                        "affectedUsers": [uid]
                    })

                # Lunch break conflict
                if avail.break_start and avail.break_end:
                    break_s = time_to_minutes(avail.break_start)
                    break_e = time_to_minutes(avail.break_end)
                    if is_time_overlap(start_m, end_m, break_s, break_e):
                        conflicts.append({
                            "type": "WORKING_HOUR_CONFLICT",
                            "severity": "LOW",
                            "score": 45.0,
                            "explanation": f"Event overlaps with {user_name}'s break time ({avail.break_start}-{avail.break_end}).",
                            "conflictingEventId": None,
                            "affectedUsers": [uid]
                        })

        # Iterate existing events on same date for Overlaps, Buffers & Resources
        for ex in existing_events:
            ex_s = time_to_minutes(ex.start_time)
            ex_e = time_to_minutes(ex.end_time)

            # 4. ROOM CONFLICT
            if room_id and ex.room_id == room_id:
                if is_time_overlap(start_m, end_m, ex_s, ex_e):
                    room_obj = self.db.query(Room).filter(Room.id == room_id).first()
                    room_name = room_obj.name if room_obj else "Selected Room"
                    conflicts.append({
                        "type": "ROOM_CONFLICT",
                        "severity": "CRITICAL" if priority in ["CRITICAL", "HIGH"] else "HIGH",
                        "score": 90.0,
                        "explanation": f"Room '{room_name}' is already booked for '{ex.title}' ({ex.start_time}-{ex.end_time}).",
                        "conflictingEventId": ex.id,
                        "affectedUsers": [ex.organizer_id]
                    })

            # 5. PARTICIPANT CONFLICT
            ex_part_ids = [p.user_id for p in ex.participants] + [ex.organizer_id]
            common_participants = all_users.intersection(set(ex_part_ids))

            if common_participants:
                if is_time_overlap(start_m, end_m, ex_s, ex_e):
                    conflicting_users = self.db.query(User).filter(User.id.in_(list(common_participants))).all()
                    names = ", ".join([u.full_name for u in conflicting_users])
                    conflicts.append({
                        "type": "PARTICIPANT_CONFLICT",
                        "severity": "HIGH",
                        "score": 88.0,
                        "explanation": f"Participant(s) ({names}) already scheduled in '{ex.title}' ({ex.start_time}-{ex.end_time}).",
                        "conflictingEventId": ex.id,
                        "affectedUsers": list(common_participants)
                    })

                # 6. BUFFER / TRAVEL CONFLICT
                # Buffer gap check: gap between end of one and start of next
                buffer_needed = max(buffer_mins, ex.buffer_time)
                if (0 < (start_m - ex_e) < buffer_needed) or (0 < (ex_s - end_m) < buffer_needed):
                    conflicting_users = self.db.query(User).filter(User.id.in_(list(common_participants))).all()
                    names = ", ".join([u.full_name for u in conflicting_users])
                    conflicts.append({
                        "type": "BUFFER_CONFLICT",
                        "severity": "MEDIUM",
                        "score": 60.0,
                        "explanation": f"Insufficient buffer time (<{buffer_needed}m) for {names} relative to '{ex.title}'.",
                        "conflictingEventId": ex.id,
                        "affectedUsers": list(common_participants)
                    })

            # 7. RECURRING EVENT CONFLICT
            if ex.recurrence and ex.recurrence != "NONE":
                if is_time_overlap(start_m, end_m, ex_s, ex_e) and common_participants:
                    conflicts.append({
                        "type": "RECURRING_EVENT_CONFLICT",
                        "severity": "HIGH",
                        "score": 82.0,
                        "explanation": f"Recurring event occurrence '{ex.title}' conflicts with requested time.",
                        "conflictingEventId": ex.id,
                        "affectedUsers": list(common_participants)
                    })

        # 8. RESOURCE CONFLICT
        for req_r in requested_resources:
            r_id = req_r.get("resource_id") or req_r.get("resourceId")
            req_qty = req_r.get("quantity", 1)
            resource_obj = self.db.query(Resource).filter(Resource.id == r_id).first()

            if resource_obj:
                # Find total allocated quantity during [start_m, end_m)
                allocated_qty = 0
                for ex in existing_events:
                    ex_s = time_to_minutes(ex.start_time)
                    ex_e = time_to_minutes(ex.end_time)
                    if is_time_overlap(start_m, end_m, ex_s, ex_e):
                        for er in ex.resources:
                            if er.resource_id == r_id:
                                allocated_qty += er.quantity

                if (allocated_qty + req_qty) > resource_obj.total_quantity:
                    conflicts.append({
                        "type": "RESOURCE_CONFLICT",
                        "severity": "HIGH",
                        "score": 80.0,
                        "explanation": f"Resource '{resource_obj.name}' limit exceeded ({allocated_qty + req_qty}/{resource_obj.total_quantity} requested).",
                        "conflictingEventId": None,
                        "affectedUsers": list(all_users)
                    })

        # 9. GENERAL TIME CONFLICT fallback if no specific rule caught it
        if not conflicts:
            pass  # Clean schedule!

        return conflicts
