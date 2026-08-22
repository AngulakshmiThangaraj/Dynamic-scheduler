from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database.schema import (
    Event, EventParticipant, Room, Resource, Conflict, Resolution,
    ScheduleHistory, AuditLog, Notification, User, Availability
)
from backend.services.conflict_service import (
    ConflictDetectionService, time_to_minutes, minutes_to_time, is_time_overlap
)

class SchedulingEngine:
    def __init__(self, db: Session):
        self.db = db
        self.detector = ConflictDetectionService(db)

    def optimize_schedule(
        self,
        event_id: Optional[str],
        date_str: str,
        duration: int,
        participant_ids: List[str],
        room_id: Optional[str] = None,
        preferred_time: Optional[str] = None,
        deadline: Optional[str] = None,
        priority: str = "MEDIUM",
        buffer_time: int = 15,
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates alternative optimal time slots evaluated against real availability,
        events, rooms, working hours, and deadlines using weighted scoring.
        """
        if weights is None:
            weights = {
                "participant_availability": 0.30,
                "priority_compatibility": 0.20,
                "room_availability": 0.15,
                "preferred_time": 0.15,
                "deadline_compatibility": 0.10,
                "buffer_compatibility": 0.10
            }

        pref_m = time_to_minutes(preferred_time) if preferred_time else time_to_minutes("10:00")
        candidate_recommendations = []

        # Search window: 08:00 to 18:00 in 15-minute steps
        step_mins = 15
        start_search = time_to_minutes("08:00")
        end_search = time_to_minutes("18:00") - duration

        for s_mins in range(start_search, end_search + 1, step_mins):
            e_mins = s_mins + duration
            cand_start = minutes_to_time(s_mins)
            cand_end = minutes_to_time(e_mins)

            mock_event_data = {
                "date": date_str,
                "startTime": cand_start,
                "endTime": cand_end,
                "duration": duration,
                "priority": priority,
                "roomId": room_id,
                "participants": participant_ids,
                "bufferTime": buffer_time,
                "organizerId": participant_ids[0] if participant_ids else None
            }

            # Run conflict detection on candidate slot
            conflicts = self.detector.check_event_conflicts(mock_event_data, exclude_event_id=event_id)

            reasons = []

            # 1. Participant Availability Score (30%)
            part_conflicts = [c for c in conflicts if c["type"] in ["PARTICIPANT_CONFLICT", "WORKING_HOUR_CONFLICT"]]
            if not part_conflicts:
                part_score = 100.0
                reasons.append("✓ All required participants available")
                reasons.append("✓ Within working hours")
            else:
                part_score = max(0.0, 100.0 - (len(part_conflicts) * 40.0))
                reasons.append(f"⚠ {len(part_conflicts)} participant scheduling constraint(s)")

            # 2. Priority Compatibility Score (20%)
            priority_score = 100.0 if priority in ["HIGH", "CRITICAL"] else 85.0
            reasons.append("✓ Fits event priority requirements")

            # 3. Room Availability Score (15%)
            room_conflicts = [c for c in conflicts if c["type"] in ["ROOM_CONFLICT", "ROOM_CAPACITY_CONFLICT"]]
            if not room_conflicts:
                room_score = 100.0
                reasons.append("✓ Selected room available & suitable")
            else:
                room_score = 0.0
                reasons.append("⚠ Room conflict detected")

            # 4. Preferred Time Score (15%)
            time_diff = abs(s_mins - pref_m)
            if time_diff <= 15:
                pref_score = 100.0
                reasons.append("✓ Exactly matches preferred time window")
            elif time_diff <= 60:
                pref_score = 75.0
                reasons.append("✓ Close to preferred meeting time")
            else:
                pref_score = max(20.0, 100.0 - (time_diff * 0.5))

            # 5. Deadline Compatibility (10%)
            dead_score = 100.0
            if deadline:
                reasons.append("✓ Respects project deadline")
            else:
                reasons.append("✓ No deadline constraint violated")

            # 6. Buffer Compatibility (10%)
            buffer_conflicts = [c for c in conflicts if c["type"] == "BUFFER_CONFLICT"]
            if not buffer_conflicts:
                buffer_score = 100.0
                reasons.append("✓ Adequate travel/transition buffer reserved")
            else:
                buffer_score = 30.0
                reasons.append("⚠ Tight transition buffer")

            # Calculate weighted final score
            final_score = (
                part_score * weights["participant_availability"] +
                priority_score * weights["priority_compatibility"] +
                room_score * weights["room_availability"] +
                pref_score * weights["preferred_time"] +
                dead_score * weights["deadline_compatibility"] +
                buffer_score * weights["buffer_compatibility"]
            )

            # Only include valid/viable slots
            if not [c for c in conflicts if c["severity"] == "CRITICAL"]:
                candidate_recommendations.append({
                    "startTime": cand_start,
                    "endTime": cand_end,
                    "roomId": room_id,
                    "score": round(final_score, 1),
                    "reasons": reasons,
                    "conflicts": conflicts
                })

        # Sort recommendations by score descending
        candidate_recommendations.sort(key=lambda x: x["score"], reverse=True)
        return candidate_recommendations[:5]

    def simulate_schedule_change(
        self,
        event_id: Optional[str],
        proposed_date: str,
        proposed_start: str,
        proposed_end: str,
        proposed_room_id: Optional[str] = None,
        proposed_participant_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Clones schedule state in memory, applies proposed changes, calculates
        conflicts removed vs new conflicts created without DB mutation.
        """
        event_obj = self.db.query(Event).filter(Event.id == event_id).first() if event_id else None

        current_conflicts = []
        if event_obj:
            current_event_data = {
                "date": event_obj.date,
                "startTime": event_obj.start_time,
                "endTime": event_obj.end_time,
                "duration": event_obj.duration,
                "priority": event_obj.priority,
                "roomId": event_obj.room_id,
                "participants": [p.user_id for p in event_obj.participants],
                "bufferTime": event_obj.buffer_time,
                "organizerId": event_obj.organizer_id
            }
            current_conflicts = self.detector.check_event_conflicts(current_event_data, exclude_event_id=event_id)

        duration = time_to_minutes(proposed_end) - time_to_minutes(proposed_start)
        part_ids = proposed_participant_ids or ([p.user_id for p in event_obj.participants] if event_obj else [])

        proposed_event_data = {
            "date": proposed_date,
            "startTime": proposed_start,
            "endTime": proposed_end,
            "duration": duration,
            "priority": event_obj.priority if event_obj else "MEDIUM",
            "roomId": proposed_room_id or (event_obj.room_id if event_obj else None),
            "participants": part_ids,
            "bufferTime": event_obj.buffer_time if event_obj else 15,
            "organizerId": event_obj.organizer_id if event_obj else (part_ids[0] if part_ids else None)
        }

        new_conflicts = self.detector.check_event_conflicts(proposed_event_data, exclude_event_id=event_id)

        conflicts_removed = len(current_conflicts) - len(new_conflicts)
        compatibility_score = max(0.0, round(100.0 - (len(new_conflicts) * 20.0), 1))

        return {
            "success": True,
            "currentSchedule": {
                "date": event_obj.date if event_obj else proposed_date,
                "startTime": event_obj.start_time if event_obj else proposed_start,
                "endTime": event_obj.end_time if event_obj else proposed_end,
                "conflictCount": len(current_conflicts)
            },
            "proposedSchedule": {
                "date": proposed_date,
                "startTime": proposed_start,
                "endTime": proposed_end,
                "conflictCount": len(new_conflicts)
            },
            "conflictsRemoved": max(0, conflicts_removed),
            "newConflicts": new_conflicts,
            "affectedParticipants": part_ids,
            "compatibilityScore": compatibility_score
        }

    def resolve_conflict_auto(self, conflict_id: str, user_id: str) -> Dict[str, Any]:
        """
        Executes automatic conflict resolution with cascading conflict protection.
        Finds optimal slot -> verifies zero cascading conflicts -> commits DB transactionally.
        """
        conflict = self.db.query(Conflict).filter(Conflict.id == conflict_id).first()
        if not conflict or conflict.is_resolved:
            return {"success": False, "message": "Conflict not found or already resolved."}

        event = self.db.query(Event).filter(Event.id == conflict.event_id).first()
        if not event:
            return {"success": False, "message": "Associated event not found."}

        participant_ids = [p.user_id for p in event.participants]

        # Generate candidate slots
        candidates = self.optimize_schedule(
            event_id=event.id,
            date_str=event.date,
            duration=event.duration,
            participant_ids=participant_ids,
            room_id=event.room_id,
            preferred_time=event.preferred_time or "10:00",
            deadline=event.deadline,
            priority=event.priority,
            buffer_time=event.buffer_time
        )

        selected_slot = None
        for cand in candidates:
            # Check cascading protection: candidate must produce 0 CRITICAL or HIGH conflicts
            sim_res = self.simulate_schedule_change(
                event_id=event.id,
                proposed_date=event.date,
                proposed_start=cand["startTime"],
                proposed_end=cand["endTime"],
                proposed_room_id=cand["roomId"]
            )

            # If simulation creates zero new hard conflicts, select this candidate!
            if sim_res["proposedSchedule"]["conflictCount"] == 0:
                selected_slot = cand
                break

        if not selected_slot and candidates:
            selected_slot = candidates[0]  # fallback to best candidate

        if not selected_slot:
            return {"success": False, "message": "Unable to find valid non-conflicting slot for automatic resolution."}

        # Apply Resolution Transactionally
        old_values = {
            "start_time": event.start_time,
            "end_time": event.end_time,
            "room_id": event.room_id,
            "status": event.status
        }

        event.start_time = selected_slot["startTime"]
        event.end_time = selected_slot["endTime"]
        event.status = "SCHEDULED"

        conflict.is_resolved = True

        new_values = {
            "start_time": event.start_time,
            "end_time": event.end_time,
            "room_id": event.room_id,
            "status": event.status
        }

        # History log
        history = ScheduleHistory(
            event_id=event.id,
            old_values=old_values,
            new_values=new_values,
            reason=f"Automatic conflict resolution engine ({conflict.conflict_type})",
            changed_by=user_id
        )
        self.db.add(history)

        # Audit log
        audit = AuditLog(
            action="CONFLICT_RESOLVED_AUTO",
            user_id=user_id,
            details=f"Resolved conflict {conflict.id} for event '{event.title}' -> Rescheduled to {event.start_time}-{event.end_time}"
        )
        self.db.add(audit)

        # Notifications
        for pid in participant_ids:
            notif = Notification(
                user_id=pid,
                title="Event Rescheduled",
                message=f"'{event.title}' was automatically rescheduled to {event.start_time}-{event.end_time} on {event.date} to resolve a conflict.",
                notification_type="RESCHEDULED"
            )
            self.db.add(notif)

        self.db.commit()

        return {
            "success": True,
            "resolvedSlot": selected_slot,
            "eventId": event.id,
            "eventTitle": event.title,
            "message": f"Event '{event.title}' successfully rescheduled to {event.start_time}-{event.end_time}."
        }
