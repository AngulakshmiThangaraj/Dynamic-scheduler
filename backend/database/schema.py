import os
import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

is_vercel = os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV") is not None
default_db_url = "sqlite:////tmp/scheduler.db" if is_vercel else "sqlite:///./scheduler.db"
DATABASE_URL = os.environ.get("DATABASE_URL", default_db_url)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="PARTICIPANT", nullable=False)  # ADMIN, ORGANIZER, PARTICIPANT
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organized_events = relationship("Event", back_populates="organizer", foreign_keys="Event.organizer_id")
    participations = relationship("EventParticipant", back_populates="user", cascade="all, delete-orphan")
    availabilities = relationship("Availability", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    capacity = Column(Integer, nullable=False, default=10)
    location = Column(String, nullable=False, default="Main Office")
    features = Column(JSON, default=list)  # ["Projector", "Whiteboard", "VideoConf"]
    is_active = Column(Boolean, default=True, nullable=False)

    events = relationship("Event", back_populates="room")

class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    resource_type = Column(String, nullable=False, default="EQUIPMENT")
    total_quantity = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True, nullable=False)

    event_resources = relationship("EventResource", back_populates="resource", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True, default="")
    date = Column(String, nullable=False, index=True)  # YYYY-MM-DD
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)    # HH:MM
    duration = Column(Integer, nullable=False)   # minutes
    priority = Column(String, default="MEDIUM", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    organizer_id = Column(String, ForeignKey("users.id"), nullable=False)
    location = Column(String, default="Online")
    room_id = Column(String, ForeignKey("rooms.id"), nullable=True)
    deadline = Column(String, nullable=True)  # YYYY-MM-DD HH:MM
    preferred_time = Column(String, nullable=True)  # HH:MM
    flexible_time_window = Column(Integer, default=60)  # minutes +/-
    buffer_time = Column(Integer, default=15)  # minutes
    auto_reschedule = Column(Boolean, default=True)
    recurrence = Column(String, default="NONE")  # NONE, DAILY, WEEKLY, MONTHLY
    recurrence_parent_id = Column(String, ForeignKey("events.id"), nullable=True)
    status = Column(String, default="SCHEDULED")  # SCHEDULED, CONFLICTED, RESCHEDULED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organizer = relationship("User", back_populates="organized_events", foreign_keys=[organizer_id])
    room = relationship("Room", back_populates="events")
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    resources = relationship("EventResource", back_populates="event", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="event", cascade="all, delete-orphan", foreign_keys="Conflict.event_id")

class EventParticipant(Base):
    __tablename__ = "event_participants"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    is_required = Column(Boolean, default=True)
    status = Column(String, default="ACCEPTED")  # PENDING, ACCEPTED, DECLINED

    event = relationship("Event", back_populates="participants")
    user = relationship("User", back_populates="participations")

class EventResource(Base):
    __tablename__ = "event_resources"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    resource_id = Column(String, ForeignKey("resources.id"), nullable=False)
    quantity = Column(Integer, default=1)

    event = relationship("Event", back_populates="resources")
    resource = relationship("Resource", back_populates="event_resources")

class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = Column(String, nullable=False, default="09:00")
    end_time = Column(String, nullable=False, default="17:00")
    break_start = Column(String, nullable=True, default="13:00")
    break_end = Column(String, nullable=True, default="14:00")
    is_recurring = Column(Boolean, default=True)

    user = relationship("User", back_populates="availabilities")

class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(String, primary_key=True, default=generate_uuid)
    date = Column(String, unique=True, nullable=False)  # YYYY-MM-DD
    name = Column(String, nullable=False)
    is_company_wide = Column(Boolean, default=True)

class Conflict(Base):
    __tablename__ = "conflicts"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    conflict_type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    score = Column(Float, default=75.0)
    explanation = Column(Text, nullable=False)
    conflicting_event_id = Column(String, ForeignKey("events.id"), nullable=True)
    affected_users = Column(JSON, default=list)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", foreign_keys=[event_id], back_populates="conflicts")
    conflicting_event = relationship("Event", foreign_keys=[conflicting_event_id])

class Resolution(Base):
    __tablename__ = "resolutions"

    id = Column(String, primary_key=True, default=generate_uuid)
    conflict_id = Column(String, ForeignKey("conflicts.id"), nullable=False)
    resolution_strategy = Column(String, nullable=False)  # AUTOMATIC, MANUAL, SIMULATED
    proposed_start_time = Column(String, nullable=True)
    proposed_end_time = Column(String, nullable=True)
    proposed_room_id = Column(String, nullable=True)
    score = Column(Float, default=90.0)
    status = Column(String, default="PROPOSED")  # PROPOSED, APPLIED, REJECTED
    executed_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, default="INFO")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

class ScheduleHistory(Base):
    __tablename__ = "schedule_histories"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    old_values = Column(JSON, nullable=False)
    new_values = Column(JSON, nullable=False)
    reason = Column(String, nullable=False)
    changed_by = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    action = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, default="127.0.0.1")
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
