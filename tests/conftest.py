from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Generator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from api.dependencies import get_services_factory
from dto.message import MessageCreate, MessageResponse, MessageUpdateDTO
from exc import (
    ChatAccessDeniedError,
    MessageNotFoundError,
    PermissionDeniedError,
)
from types_alias import Services
from socket_app.connection_manager import connection_manager
from socket_app.endpoint import websocket_router
from socket_app.presence_manager import presence_manager
from tokens import create_access_token


@dataclass
class WebsocketTestState:
    chat_members: dict[UUID, list[UUID]] = field(default_factory=dict)
    messages: dict[UUID, MessageResponse] = field(default_factory=dict)

    def add_chat(self, chat_id: UUID, member_ids: list[UUID]) -> None:
        self.chat_members[chat_id] = member_ids

    def add_message(
        self,
        *,
        chat_id: UUID,
        sender_id: UUID,
        text: str = "initial text",
    ) -> MessageResponse:
        message = MessageResponse(
            id=uuid4(),
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            is_read=False,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        self.messages[message.id] = message
        return message


class InMemoryChatService:
    def __init__(self, state: WebsocketTestState) -> None:
        self._state = state

    async def get_member_ids(self, chat_id: UUID) -> set[UUID]:
        return set(self._state.chat_members.get(chat_id, []))

    async def get_shared_chat_user_ids(self, user_id: UUID) -> set[UUID]:
        shared_users: set[UUID] = set()
        for member_ids in self._state.chat_members.values():
            if user_id in member_ids:
                shared_users.update(member_ids)

        shared_users.discard(user_id)
        return shared_users


class InMemoryMessageService:
    def __init__(self, state: WebsocketTestState) -> None:
        self._state = state

    async def create_message_in_db(
        self,
        obj: MessageCreate,
        sender_id: UUID,
    ) -> MessageResponse:
        if sender_id not in self._state.chat_members.get(obj.chat_id, []):
            raise ChatAccessDeniedError(
                user_id=sender_id,
                chat_id=obj.chat_id,
            )

        message = MessageResponse(
            id=uuid4(),
            chat_id=obj.chat_id,
            sender_id=sender_id,
            text=obj.text,
            is_read=False,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        self._state.messages[message.id] = message
        return message

    async def update_message(
        self,
        message_id: UUID,
        obj_in: MessageUpdateDTO,
        user_id: UUID,
    ) -> MessageResponse:
        message = self._state.messages.get(message_id)
        if message is None:
            raise MessageNotFoundError(message_id=message_id)
        if user_id not in self._state.chat_members.get(message.chat_id, []):
            raise ChatAccessDeniedError(
                user_id=user_id,
                chat_id=message.chat_id,
            )
        if message.sender_id != user_id:
            raise PermissionDeniedError(user_id=user_id)

        updated = message.model_copy(
            update={
                "text": obj_in.text if obj_in.text is not None else message.text,
                "is_read": obj_in.is_read
                if obj_in.is_read is not None
                else message.is_read,
                "updated_at": datetime.now(UTC),
            }
        )
        self._state.messages[message_id] = updated
        return updated

    async def delete_message(
        self,
        message_id: UUID,
        user_id: UUID,
    ) -> MessageResponse:
        message = self._state.messages.get(message_id)
        if message is None:
            raise MessageNotFoundError(message_id=message_id)
        if user_id not in self._state.chat_members.get(message.chat_id, []):
            raise ChatAccessDeniedError(
                user_id=user_id,
                chat_id=message.chat_id,
            )
        if message.sender_id != user_id:
            raise PermissionDeniedError(user_id=user_id)

        del self._state.messages[message_id]
        return message


@pytest.fixture(autouse=True)
def clear_websocket_connections() -> Generator[None]:
    original_grace_period = presence_manager.offline_grace_seconds
    presence_manager.offline_grace_seconds = 0.01
    connection_manager.connections.clear()
    presence_manager.pending_offline.clear()
    yield
    connection_manager.connections.clear()
    presence_manager.pending_offline.clear()
    presence_manager.offline_grace_seconds = original_grace_period


@pytest.fixture
def websocket_state() -> WebsocketTestState:
    return WebsocketTestState()


@pytest.fixture
def services(websocket_state: WebsocketTestState) -> Services:
    return Services(
        user=object(),
        auth=object(),
        chat=InMemoryChatService(websocket_state),
        message=InMemoryMessageService(websocket_state),
    )


@pytest.fixture
def app(services: Services) -> FastAPI:
    app = FastAPI()
    app.include_router(websocket_router)

    @asynccontextmanager
    async def open_services() -> AsyncIterator[Services]:
        yield services

    app.dependency_overrides[get_services_factory] = lambda: open_services

    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def chat_id() -> UUID:
    return uuid4()


@pytest.fixture
def access_token() -> Callable[[UUID], str]:
    def create_token(user_id: UUID) -> str:
        return create_access_token(exp=timedelta(minutes=15), sub=user_id)

    return create_token


@pytest.fixture
def websocket_connect(
    client: TestClient,
    access_token: Callable[[UUID], str],
) -> Callable[..., WebSocketTestSession]:
    def connect(user_id: UUID, token: str | None = None) -> WebSocketTestSession:
        cookie_token = token or access_token(user_id)
        return client.websocket_connect(
            "/ws",
            headers={
                "cookie": f"access_token={cookie_token}",
                "origin": "http://localhost:8000",
            },
        )

    return connect


def receive_websocket_event(
    websocket: WebSocketTestSession,
    event_type: str,
) -> dict[str, Any]:
    while True:
        payload = websocket.receive_json()
        if payload.get("type") == event_type:
            return payload
