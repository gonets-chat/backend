from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from conftest import WebsocketTestState, receive_websocket_event
from fastapi import FastAPI
from starlette.testclient import WebSocketTestSession

from api.dependencies import get_services_factory
from dto.message import MessageCreate, MessageResponse
from types_alias import Services


def send_message(websocket: WebSocketTestSession, chat_id: UUID, text: str) -> None:
    websocket.send_json(
        {
            "type": "message.send",
            "data": {"chat_id": str(chat_id), "text": text},
        }
    )


def test_invalid_command_returns_error_and_keeps_connection(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id])

    with websocket_connect(user_id) as websocket:
        websocket.send_json({"type": "message.send", "data": {}})
        error = receive_websocket_event(websocket, "command.error")

        send_message(websocket, chat_id, "still alive")
        created = receive_websocket_event(websocket, "message.created")

    assert error["data"]["code"] == "invalid_command"
    assert created["data"]["message"]["text"] == "still alive"


def test_missing_message_returns_not_found(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    with websocket_connect(user_id) as websocket:
        websocket.send_json(
            {
                "type": "message.update",
                "data": {"message_id": str(uuid4()), "text": "edited"},
            }
        )
        payload = receive_websocket_event(websocket, "command.error")

    assert payload["data"]["code"] == "not_found"


def test_unexpected_error_returns_internal_error_and_keeps_connection(
    monkeypatch: pytest.MonkeyPatch,
    services: Services,
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id])
    create_message = services.message.create_message_in_db

    async def flaky_create(obj: MessageCreate, sender_id: UUID) -> MessageResponse:
        if obj.text == "boom":
            msg = "database is down"
            raise RuntimeError(msg)
        return await create_message(obj=obj, sender_id=sender_id)

    monkeypatch.setattr(services.message, "create_message_in_db", flaky_create)

    with websocket_connect(user_id) as websocket:
        send_message(websocket, chat_id, "boom")
        error = receive_websocket_event(websocket, "command.error")

        send_message(websocket, chat_id, "second")
        created = receive_websocket_event(websocket, "message.created")

    assert error["data"]["code"] == "internal_error"
    assert "database" not in error["data"]["message"]
    assert created["data"]["message"]["text"] == "second"


def test_event_is_not_broadcast_when_commit_fails(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    services: Services,
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])
    open_services = app.dependency_overrides[get_services_factory]()
    create_message = services.message.create_message_in_db
    fail_commit = False

    async def create_then_fail_commit(
        obj: MessageCreate,
        sender_id: UUID,
    ) -> MessageResponse:
        nonlocal fail_commit
        fail_commit = obj.text == "lost"
        return await create_message(obj=obj, sender_id=sender_id)

    @asynccontextmanager
    async def failing_commit() -> AsyncIterator[Services]:
        nonlocal fail_commit
        async with open_services() as opened:
            yield opened
        if fail_commit:
            fail_commit = False
            msg = "commit failed"
            raise RuntimeError(msg)

    monkeypatch.setattr(services.message, "create_message_in_db", create_then_fail_commit)
    app.dependency_overrides[get_services_factory] = lambda: failing_commit

    with websocket_connect(other_user_id) as receiver:
        with websocket_connect(user_id) as sender:
            send_message(sender, chat_id, "lost")
            error = receive_websocket_event(sender, "command.error")

            send_message(sender, chat_id, "delivered")
            received = receive_websocket_event(receiver, "message.created")

    assert error["data"]["code"] == "internal_error"
    assert received["data"]["message"]["text"] == "delivered"
