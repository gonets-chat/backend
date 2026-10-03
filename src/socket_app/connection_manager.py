import asyncio
from collections.abc import Iterable
from typing import ClassVar
from uuid import UUID

from fastapi import WebSocket

from config import settings
from logger import get_configured_logger
from types_alias import SingletonMeta

logger = get_configured_logger(__name__)

CONNECTION_LIMIT_CLOSE_CODE = 1013
CONNECTION_LIMIT_CLOSE_REASON = "Maximum WebSocket connections exceeded."


class ConnectionManager(metaclass=SingletonMeta):
    connections: ClassVar[dict[UUID, set[WebSocket]]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket) -> bool:
        await websocket.accept()

        sockets = self.connections.get(user_id)
        if sockets is not None and len(sockets) >= settings.MAX_CONNECTIONS_PER_USER:
            await websocket.close(
                code=CONNECTION_LIMIT_CLOSE_CODE,
                reason=CONNECTION_LIMIT_CLOSE_REASON,
            )
            return False

        if sockets is None:
            sockets = set()
            self.connections[user_id] = sockets

        sockets.add(websocket)
        return True

    async def disconnect(self, user_id: UUID, socket: WebSocket) -> bool:
        sockets = self.connections.get(user_id)

        if not sockets:
            return False

        sockets.discard(socket)

        if sockets:
            return False

        del self.connections[user_id]
        return True

    def is_online(self, user_id: UUID) -> bool:
        return user_id in self.connections

    def get_connections(self) -> dict[UUID, set[WebSocket]]:
        return self.connections

    async def send_to_users(self, user_ids: Iterable[UUID], payload: str) -> None:
        """Отправляет payload во все вкладки пользователей.

        Ошибка одного сокета не прерывает доставку остальным: оборванное
        соединение уберёт его собственный endpoint.
        """
        sockets = [
            socket
            for user_id in user_ids
            for socket in tuple(self.connections.get(user_id, ()))
        ]
        if not sockets:
            return

        results = await asyncio.gather(
            *(socket.send_text(payload) for socket in sockets),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Failed to deliver WebSocket event: %r", result)


connection_manager = ConnectionManager()
