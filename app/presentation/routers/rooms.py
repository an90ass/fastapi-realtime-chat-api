"""
Rooms router — thin HTTP controller.
Responsibility: HTTP boundary only. Maps HTTP ↔ Application Commands ↔ Domain Entities.
"""

from typing import List

from fastapi import APIRouter, Depends, Query, status

from app.application.commands import CreateRoomCommand
from app.application.services.room_service import RoomService
from app.domain.entities.room import RoomEntity, RoomMemberEntity
from app.domain.entities.user import UserEntity
from app.presentation.dependencies import get_current_user, get_room_service
from app.presentation.schemas.room import (
    RoomCreateSchema,
    RoomMemberResponseSchema,
    RoomResponseSchema,
)

router = APIRouter(prefix="/rooms", tags=["Rooms"])


def _room_to_response(entity: RoomEntity) -> RoomResponseSchema:
    return RoomResponseSchema(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        is_private=entity.is_private,
        created_at=entity.created_at,
    )


def _member_to_response(entity: RoomMemberEntity) -> RoomMemberResponseSchema:
    return RoomMemberResponseSchema(
        id=entity.id,
        room_id=entity.room_id,
        user_id=entity.user_id,
        joined_at=entity.joined_at,
    )


@router.post("/", response_model=RoomResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_room(
    body: RoomCreateSchema,
    current_user: UserEntity = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
) -> RoomResponseSchema:
    """Create a new chat room (creator is auto-joined)."""
    cmd = CreateRoomCommand(
        name=body.name,
        description=body.description,
        is_private=body.is_private,
        creator_id=current_user.id,
    )
    entity = await room_service.create_room(cmd)
    return _room_to_response(entity)


@router.get("/", response_model=List[RoomResponseSchema])
async def list_public_rooms(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserEntity = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
) -> List[RoomResponseSchema]:
    """List all public rooms with offset pagination."""
    entities = await room_service.list_public_rooms(skip=skip, limit=limit)
    return [_room_to_response(e) for e in entities]


@router.get("/{room_id}", response_model=RoomResponseSchema)
async def get_room(
    room_id: int,
    current_user: UserEntity = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
) -> RoomResponseSchema:
    """Fetch details of a specific room."""
    entity = await room_service.get_room(room_id)
    return _room_to_response(entity)


@router.post("/{room_id}/join", response_model=RoomMemberResponseSchema)
async def join_room(
    room_id: int,
    current_user: UserEntity = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
) -> RoomMemberResponseSchema:
    """Join the authenticated user to a room."""
    entity = await room_service.join_room(room_id=room_id, user_id=current_user.id)
    return _member_to_response(entity)


@router.get("/{room_id}/members", response_model=List[RoomMemberResponseSchema])
async def get_room_members(
    room_id: int,
    current_user: UserEntity = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
) -> List[RoomMemberResponseSchema]:
    """Return all members enrolled in a room."""
    entities = await room_service.get_room_members(room_id)
    return [_member_to_response(e) for e in entities]
