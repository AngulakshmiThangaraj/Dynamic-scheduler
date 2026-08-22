import hashlib
from datetime import datetime, timedelta
from backend.database.schema import (
    SessionLocal, init_db, User, Role, Room, Resource, Availability, Holiday, Event, EventParticipant, EventResource
)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def seed_database():
    init_db()
    db = SessionLocal()

    # Check if already seeded
    if db.query(User).first():
        print("Database already seeded.")
        db.close()
        return

    print("Seeding database...")

    # Roles
    admin_role = Role(name="ADMIN", description="System Administrator")
    organizer_role = Role(name="ORGANIZER", description="Event Organizer")
    participant_role = Role(name="PARTICIPANT", description="Regular Participant")
    db.add_all([admin_role, organizer_role, participant_role])

    # Users
    admin = User(
        email="admin@company.com",
        password_hash=hash_password("admin123"),
        full_name="Sarah Jenkins (Admin)",
        role="ADMIN",
        is_active=True
    )
    organizer1 = User(
        email="organizer@company.com",
        password_hash=hash_password("org123"),
        full_name="Alex Rivera (Lead Organizer)",
        role="ORGANIZER",
        is_active=True
    )
    dev1 = User(
        email="dev1@company.com",
        password_hash=hash_password("dev123"),
        full_name="David Chen (Senior Dev)",
        role="PARTICIPANT",
        is_active=True
    )
    dev2 = User(
        email="dev2@company.com",
        password_hash=hash_password("dev123"),
        full_name="Elena Rostova (UI/UX Lead)",
        role="PARTICIPANT",
        is_active=True
    )
    pm1 = User(
        email="pm1@company.com",
        password_hash=hash_password("pm123"),
        full_name="Marcus Vance (Product Manager)",
        role="PARTICIPANT",
        is_active=True
    )
    db.add_all([admin, organizer1, dev1, dev2, pm1])
    db.commit()

    # Rooms
    boardroom = Room(
        name="Apollo Boardroom",
        capacity=15,
        location="Floor 4 - Executive Wing",
        features=["Projector", "VideoConf", "Whiteboard", "Catering"],
        is_active=True
    )
    sync_room = Room(
        name="Zeus Sync Room",
        capacity=6,
        location="Floor 2 - Engineering Wing",
        features=["TV Screen", "Whiteboard"],
        is_active=True
    )
    auditorium = Room(
        name="Titan Auditorium",
        capacity=50,
        location="Ground Floor",
        features=["Stage", "PA System", "Projector", "LiveStream"],
        is_active=True
    )
    db.add_all([boardroom, sync_room, auditorium])

    # Resources
    proj = Resource(name="4K Wireless Projector", resource_type="EQUIPMENT", total_quantity=3)
    mic = Resource(name="Podcast Microphone Set", resource_type="AUDIO", total_quantity=2)
    laptop = Resource(name="Demo Macbook Pro", resource_type="HARDWARE", total_quantity=5)
    db.add_all([proj, mic, laptop])

    # Company Holidays
    today = datetime.now().date()
    labor_day = Holiday(date=f"{today.year}-09-07", name="Labor Day", is_company_wide=True)
    thanksgiving = Holiday(date=f"{today.year}-11-26", name="Thanksgiving Day", is_company_wide=True)
    db.add_all([labor_day, thanksgiving])

    # Default Availability for users (Mon-Fri 09:00-17:00, lunch 13:00-14:00)
    users = [admin, organizer1, dev1, dev2, pm1]
    for u in users:
        for day in range(5):  # 0 to 4 (Mon to Fri)
            avail = Availability(
                user_id=u.id,
                day_of_week=day,
                start_time="09:00",
                end_time="17:00",
                break_start="13:00",
                break_end="14:00",
                is_recurring=True
            )
            db.add(avail)
    db.commit()

    # Sample Events
    today_str = today.strftime("%Y-%m-%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    next_day_str = (today + timedelta(days=2)).strftime("%Y-%m-%d")

    ev1 = Event(
        title="Q3 Product Strategy Alignment",
        description="Quarterly review of product roadmap and engineering milestones.",
        date=today_str,
        start_time="10:00",
        end_time="11:30",
        duration=90,
        priority="HIGH",
        organizer_id=organizer1.id,
        location="Apollo Boardroom",
        room_id=boardroom.id,
        preferred_time="10:00",
        buffer_time=15,
        status="SCHEDULED"
    )
    ev2 = Event(
        title="Sprint Planning & Architecture Sync",
        description="Detailed review of incoming sprint backlog items and schema updates.",
        date=today_str,
        start_time="14:00",
        end_time="15:00",
        duration=60,
        priority="CRITICAL",
        organizer_id=pm1.id,
        location="Zeus Sync Room",
        room_id=sync_room.id,
        preferred_time="14:00",
        buffer_time=15,
        status="SCHEDULED"
    )
    ev3 = Event(
        title="UI/UX Design Critique",
        description="Review wireframes for event conflict drawer.",
        date=tomorrow_str,
        start_time="11:00",
        end_time="12:00",
        duration=60,
        priority="MEDIUM",
        organizer_id=dev2.id,
        location="Zeus Sync Room",
        room_id=sync_room.id,
        preferred_time="11:00",
        buffer_time=15,
        status="SCHEDULED"
    )
    db.add_all([ev1, ev2, ev3])
    db.commit()

    # Participants
    p1 = EventParticipant(event_id=ev1.id, user_id=organizer1.id, is_required=True, status="ACCEPTED")
    p2 = EventParticipant(event_id=ev1.id, user_id=pm1.id, is_required=True, status="ACCEPTED")
    p3 = EventParticipant(event_id=ev1.id, user_id=dev1.id, is_required=False, status="ACCEPTED")

    p4 = EventParticipant(event_id=ev2.id, user_id=pm1.id, is_required=True, status="ACCEPTED")
    p5 = EventParticipant(event_id=ev2.id, user_id=dev1.id, is_required=True, status="ACCEPTED")
    p6 = EventParticipant(event_id=ev2.id, user_id=dev2.id, is_required=True, status="ACCEPTED")

    p7 = EventParticipant(event_id=ev3.id, user_id=dev2.id, is_required=True, status="ACCEPTED")
    p8 = EventParticipant(event_id=ev3.id, user_id=dev1.id, is_required=True, status="ACCEPTED")
    db.add_all([p1, p2, p3, p4, p5, p6, p7, p8])

    # Event Resources
    er1 = EventResource(event_id=ev1.id, resource_id=proj.id, quantity=1)
    er2 = EventResource(event_id=ev2.id, resource_id=laptop.id, quantity=2)
    db.add_all([er1, er2])

    db.commit()
    print("Database successfully seeded!")
    db.close()

if __name__ == "__main__":
    seed_database()
