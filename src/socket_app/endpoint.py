"""Принимает, проверяет и маршрутизирует WebSocket-соединения приложения."""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.dependencies import ServicesFactoryDep
from dto.websocket import WSCommandError
from logic.events.manager import EventsManager
from socket_app.connection_manager import connection_manager
from socket_app.presence_manager import presence_manager
from socket_app.security import authenticate_websocket, require_allowed_origin
from socket_app.transport import receive_command

websocket_router = APIRouter(tags=["WebSockets"])


@websocket_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    services_factory: ServicesFactoryDep,
) -> None:
    require_allowed_origin(websocket)
    access_token = await authenticate_websocket(websocket)
    if access_token is None:
        return

    user_id = UUID(access_token.payload.sub)
    event_manager = EventsManager(services_factory=services_factory)

    was_online = connection_manager.is_online(user_id)
    is_connected = await connection_manager.connect(
        user_id=user_id, websocket=websocket
    )
    if not is_connected:
        return

    try:
        if not was_online:
            await presence_manager.connected(
                user_id=user_id,
                services_factory=services_factory,
            )

        token_expires_at = access_token.payload.exp
        while (
            raw_text := await receive_command(websocket, token_expires_at)
        ) is not None:
            result = await event_manager.handle(sender_id=user_id, raw_json=raw_text)

            if isinstance(result, WSCommandError):
                await websocket.send_text(result.model_dump_json())
                continue

            await connection_manager.send_to_users(
                result.recipient_ids,
                result.payload,
            )
    except WebSocketDisconnect:
        pass
    finally:
        became_offline = await connection_manager.disconnect(
            user_id=user_id,
            socket=websocket,
        )
        if became_offline:
            presence_manager.disconnected(
                user_id=user_id,
                services_factory=services_factory,
            )
