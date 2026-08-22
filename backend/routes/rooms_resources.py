from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from backend.database.schema import Room, Resource, User
from backend.services.auth_service import get_db, get_current_user, require_role
from backend.schemas import RoomCreate, RoomResponse, ResourceCreate, ResourceResponse

router = APIRouter(tags=["Rooms and Resources"])

# Rooms APIs
@router.get("/api/rooms", response_model=List[RoomResponse])
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rooms = db.query(Room).filter(Room.is_active == True).all()
    return [RoomResponse.model_validate(r) for r in rooms]

@router.post("/api/rooms", response_model=RoomResponse)
def create_room(
    data: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "ORGANIZER"]))
):
    room = Room(
        name=data.name,
        capacity=data.capacity,
        location=data.location,
        features=data.features or [],
        is_active=True
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return RoomResponse.model_validate(room)

@router.delete("/api/rooms/{room_id}")
def delete_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room.is_active = False
    db.commit()
    return {"success": True, "message": "Room deactivated"}

# Resources APIs
@router.get("/api/resources", response_model=List[ResourceResponse])
def list_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resources = db.query(Resource).filter(Resource.is_active == True).all()
    return [ResourceResponse.model_validate(r) for r in resources]

@router.post("/api/resources", response_model=ResourceResponse)
def create_resource(
    data: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "ORGANIZER"]))
):
    resource = Resource(
        name=data.name,
        resource_type=data.resource_type or "EQUIPMENT",
        total_quantity=data.total_quantity,
        is_active=True
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return ResourceResponse.model_validate(resource)
