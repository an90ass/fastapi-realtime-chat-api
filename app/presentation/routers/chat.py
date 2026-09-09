"""
Chat router — thin HTTP + WebSocket controller.

HTTP endpoint: cursor-paginated message history.
WebSocket endpoint: authenticated real-time chat connection.

All business rules (membership check, message persistence, broadcasting)
are delegated to Application Use Cases via Dependency Injection.
"""

import json
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import ValidationError

from app.application.services.auth_service import AuthService
from app.application.services.chat_service import ChatService
from app.application.services.room_service import RoomService
from app.core.exceptions import AppException
from app.domain.entities.user import UserEntity
from app.presentation.dependencies import (
    get_auth_service,
    get_chat_service,
    get_current_user,
    get_room_service,
)
from app.presentation.schemas.message import (
    MessageCursorPageSchema,
    MessageResponseSchema,
    WebSocketInSchema,
)
from app.presentation.websocket.connection_manager import connection_manager
from app.presentation.websocket.pubsub_manager import pubsub_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


# ──────────────────────────────────────────────
# HTTP endpoint
# ──────────────────────────────────────────────

@router.get("/{room_id}/messages", response_model=MessageCursorPageSchema)
async def get_messages(
    room_id: int,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None, description="Cursor: fetch messages older than this ID"),
    current_user: UserEntity = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> MessageCursorPageSchema:
    """Return cursor-paginated message history for a room."""
    result = await chat_service.get_messages(
        room_id=room_id,
        user_id=current_user.id,
        limit=limit,
        before_id=before_id,
    )
    items = [
        MessageResponseSchema(
            id=msg.id,
            content=msg.content,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            username=msg.sender_username,
            created_at=msg.created_at,
        )
        for msg in result.items
    ]
    return MessageCursorPageSchema(
        items=items,
        next_cursor=result.next_cursor,
        has_more=result.has_more,
    )


# ──────────────────────────────────────────────
# Shared WebSocket handler
# ──────────────────────────────────────────────

async def _handle_ws(
    websocket: WebSocket,
    room_id: int,
    token: str,
    auth_service: AuthService,
    room_service: RoomService,
    chat_service: ChatService,
) -> None:
    """Core WebSocket connection lifecycle. Reused by both endpoint variants."""

    # 1. Authenticate (before accepting the socket to save resources)
    try:
        user = await auth_service.get_user_from_token(token)
    except AppException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Verify room membership
    try:
        await room_service.check_membership(room_id, user.id)
    except AppException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 3. Register connection and start Redis listener (if not already running)
    await connection_manager.connect(room_id, websocket)
    await pubsub_manager.add_listener_if_needed(room_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                in_msg = WebSocketInSchema(**json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                await websocket.send_text(
                    json.dumps({"error": "Invalid payload", "details": str(exc)})
                )
                continue

            # Delegate entirely to Application layer — no business logic here
            await chat_service.send_message(
                content=in_msg.content,
                room_id=room_id,
                sender_id=user.id,
                sender_username=user.username,
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: user=%s room=%s", user.id, room_id)
    except Exception as exc:
        logger.error("Unexpected WS error user=%s room=%s: %s", user.id, room_id, exc)
    finally:
        # 4. Guaranteed cleanup — no resource leaks
        connection_manager.disconnect(room_id, websocket)
        await pubsub_manager.remove_listener_if_empty(room_id)


# ──────────────────────────────────────────────
# WebSocket endpoints
# ──────────────────────────────────────────────

@router.websocket("/ws/{room_id}")
async def ws_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(..., description="JWT access token"),
    auth_service: AuthService = Depends(get_auth_service),
    room_service: RoomService = Depends(get_room_service),
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    """Secure WebSocket endpoint — token via query parameter (preferred)."""
    await _handle_ws(websocket, room_id, token, auth_service, room_service, chat_service)


@router.websocket("/ws/{room_id}/{token}")
async def ws_endpoint_compat(
    websocket: WebSocket,
    room_id: int,
    token: str,
    auth_service: AuthService = Depends(get_auth_service),
    room_service: RoomService = Depends(get_room_service),
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    """Backward-compatible WebSocket endpoint — token via path segment."""
    await _handle_ws(websocket, room_id, token, auth_service, room_service, chat_service)
