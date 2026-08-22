from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any

# User & Auth Schemas
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    role: Optional[str] = "PARTICIPANT"

class UserLogin(BaseModel):
    email: str
    password: str

class SocialLoginRequest(BaseModel):
    provider: str  # google or microsoft
    email: str
    full_name: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Event Schemas
class ParticipantInput(BaseModel):
    user_id: str
    is_required: Optional[bool] = True

class ResourceInput(BaseModel):
    resource_id: str
    quantity: Optional[int] = 1

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    date: str
    start_time: str
    end_time: str
    duration: int
    priority: Optional[str] = "MEDIUM"
    location: Optional[str] = "Online"
    room_id: Optional[str] = None
    deadline: Optional[str] = None
    preferred_time: Optional[str] = None
    flexible_time_window: Optional[int] = 60
    buffer_time: Optional[int] = 15
    auto_reschedule: Optional[bool] = True
    recurrence: Optional[str] = "NONE"
    participants: Optional[List[ParticipantInput]] = []
    resources: Optional[List[ResourceInput]] = []

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[int] = None
    priority: Optional[str] = None
    location: Optional[str] = None
    room_id: Optional[str] = None
    status: Optional[str] = None
    buffer_time: Optional[int] = None

class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: Optional[str] = ""
    date: str
    start_time: str
    end_time: str
    duration: int
    priority: str
    organizer_id: str
    location: str
    room_id: Optional[str] = None
    deadline: Optional[str] = None
    preferred_time: Optional[str] = None
    buffer_time: int
    auto_reschedule: bool
    recurrence: str
    status: str
    participants: List[Dict[str, Any]] = []
    resources: List[Dict[str, Any]] = []

# Availability Schemas
class AvailabilityCreate(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    break_start: Optional[str] = "13:00"
    break_end: Optional[str] = "14:00"

class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    day_of_week: int
    start_time: str
    end_time: str
    break_start: Optional[str]
    break_end: Optional[str]

# Room & Resource Schemas
class RoomCreate(BaseModel):
    name: str
    capacity: int
    location: str
    features: Optional[List[str]] = []

class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    capacity: int
    location: str
    features: List[str] = []
    is_active: bool

class ResourceCreate(BaseModel):
    name: str
    resource_type: Optional[str] = "EQUIPMENT"
    total_quantity: int

class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    resource_type: str
    total_quantity: int
    is_active: bool

# Scheduling & Simulation Schemas
class OptimizeRequest(BaseModel):
    event_id: Optional[str] = None
    date: str
    duration: int
    participant_ids: List[str]
    room_id: Optional[str] = None
    preferred_time: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    buffer_time: Optional[int] = 15

class SimulationRequest(BaseModel):
    event_id: Optional[str] = None
    proposed_date: str
    proposed_start: str
    proposed_end: str
    proposed_room_id: Optional[str] = None
    proposed_participant_ids: Optional[List[str]] = None

class ResolutionRequest(BaseModel):
    conflict_id: str
