"""Управляет серверными событиями подключения и отключения пользователей."""

import asyncio
from typing import ClassVar
from uuid import UUID

from dto.presence import PresenceEventData, WSPresenceEvent
from logger import get_configured_logger
from socket_app.connection_manager import connection_manager
from types_alias import ServicesFactory, SingletonMeta

logger = get_configured_logger(__name__)


class PresenceManager(metaclass=SingletonMeta):
    pending_offline: ClassVar[dict[UUID, asyncio.Task[None]]] = {}
    offline_grace_seconds: float = 3.0

    async def connected(self, user_id: UUID, services_factory: ServicesFactory) -> None:
        pending = self.pending_offline.pop(user_id, None)
        if pending is not None and not pending.done():
            pending.cancel()
            return

        await self._broadcast_safe(
            user_id=user_id,
            is_online=True,
            services_factory=services_factory,
        )

    def disconnected(self, user_id: UUID, services_factory: ServicesFactory) -> None:
        pending = self.pending_offline.get(user_id)
        if pending is not None and not pending.done():
            pending.cancel()

        self.pending_offline[user_id] = asyncio.create_task(
            self._announce_offline(user_id=user_id, services_factory=services_factory)
        )

    async def shutdown(self) -> None:
        pending = list(self.pending_offline.values())
        self.pending_offline.clear()

        for task in pending:
            task.cancel()

        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def _announce_offline(
        self,
        user_id: UUID,
        services_factory: ServicesFactory,
    ) -> None:
        task = asyncio.current_task()

        try:
            await asyncio.sleep(self.offline_grace_seconds)
            if connection_manager.is_online(user_id):
                return

            await self._broadcast_safe(
                user_id=user_id,
                is_online=False,
                services_factory=services_factory,
            )
        finally:
            if self.pending_offline.get(user_id) is task:
                del self.pending_offline[user_id]

    async def _broadcast_safe(
        self,
        *,
        user_id: UUID,
        is_online: bool,
        services_factory: ServicesFactory,
    ) -> None:
        try:
            await self._broadcast(
                user_id=user_id,
                is_online=is_online,
                services_factory=services_factory,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Failed to broadcast presence for user %s.",
                user_id,
            )

    async def _broadcast(
        self,
        *,
        user_id: UUID,
        is_online: bool,
        services_factory: ServicesFactory,
    ) -> None:
        async with services_factory() as services:
            recipients = await services.chat.get_shared_chat_user_ids(user_id)

        payload = WSPresenceEvent(
            data=PresenceEventData(
                user_id=user_id,
                is_online=is_online,
            ),
        ).model_dump_json()
        await connection_manager.send_to_users(recipients, payload)


presence_manager = PresenceManager()
