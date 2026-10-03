"""Описывает серверное WebSocket-событие изменения присутствия пользователя."""

from uuid import UUID

from dto.base import DTOBase, WSServerEvent
from enums import WSEventType


class PresenceEventData(DTOBase):
    user_id: UUID
    is_online: bool


class WSPresenceEvent(WSServerEvent[PresenceEventData]):
    type: WSEventType = WSEventType.PRESENCE_UPDATED
