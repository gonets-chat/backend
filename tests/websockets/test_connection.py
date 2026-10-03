from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from config import settings
from socket_app.connection_manager import (
    CONNECTION_LIMIT_CLOSE_CODE,
    CONNECTION_LIMIT_CLOSE_REASON,
    connection_manager,
)
from socket_app.security import AUTH_FAILED_CLOSE_CODE
from tokens import create_access_token


@contextmanager
def open_connections(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
    count: int,
) -> Iterator[list[WebSocketTestSession]]:
    with ExitStack() as stack:
        sockets = [
            stack.enter_context(websocket_connect(user_id)) for _ in range(count)
        ]
        yield sockets


def test_connects_with_valid_access_token(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    with websocket_connect(user_id):
        assert connection_manager.is_online(user_id)


def test_rejects_connection_without_access_token(
    client: TestClient,
    user_id: UUID,
) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws",
            headers={"origin": "http://localhost:8000"},
        ) as websocket:
            websocket.receive_text()

    assert exc_info.value.code == AUTH_FAILED_CLOSE_CODE
    assert exc_info.value.reason == "Access token not found."


def test_rejects_connection_with_invalid_access_token(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with websocket_connect(user_id, token="not-a-jwt-token") as websocket:
            websocket.receive_text()

    assert exc_info.value.code == AUTH_FAILED_CLOSE_CODE
    assert exc_info.value.reason == "Invalid token."


def test_rejects_connection_with_expired_access_token(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    token = create_access_token(exp=timedelta(seconds=-1), sub=user_id)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with websocket_connect(user_id, token=token) as websocket:
            websocket.receive_text()

    assert exc_info.value.code == AUTH_FAILED_CLOSE_CODE
    assert exc_info.value.reason == "Access token has expired."


def test_disconnects_only_closed_tab(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    with websocket_connect(user_id):
        with websocket_connect(user_id):
            assert len(connection_manager.connections[user_id]) == 2

        assert connection_manager.is_online(user_id)
        assert len(connection_manager.connections[user_id]) == 1

    assert not connection_manager.is_online(user_id)


def test_rejects_connection_above_per_user_limit(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    with open_connections(
        websocket_connect,
        user_id,
        settings.MAX_CONNECTIONS_PER_USER,
    ):
        assert (
            len(connection_manager.connections[user_id])
            == settings.MAX_CONNECTIONS_PER_USER
        )

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect(user_id) as websocket:
                websocket.receive_text()

        assert exc_info.value.code == CONNECTION_LIMIT_CLOSE_CODE
        assert exc_info.value.reason == CONNECTION_LIMIT_CLOSE_REASON
        assert (
            len(connection_manager.connections[user_id])
            == settings.MAX_CONNECTIONS_PER_USER
        )

    assert not connection_manager.is_online(user_id)


def test_rejects_binary_frame(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    with websocket_connect(user_id) as websocket:
        websocket.send_bytes(b"not-json")

        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()

    assert exc_info.value.code == 1003
    assert exc_info.value.reason == "Only text JSON frames are supported."


def test_rejects_oversized_text_frame(
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    payload = "я" * (settings.MAX_WS_PAYLOAD_BYTES // 2 + 1)

    with websocket_connect(user_id) as websocket:
        websocket.send_text(payload)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()

    assert exc_info.value.code == 1009
    assert exc_info.value.reason == "WebSocket message is too large."


def test_event_manager_failure_does_not_register_connection(
    monkeypatch: pytest.MonkeyPatch,
    websocket_connect: Callable[..., WebSocketTestSession],
    user_id: UUID,
) -> None:
    class FailingEventsManager:
        def __init__(self, **_services: object) -> None:
            raise RuntimeError("Event manager setup failed.")

    monkeypatch.setattr(
        "socket_app.endpoint.EventsManager",
        FailingEventsManager,
    )

    with pytest.raises(RuntimeError, match="Event manager setup failed"):
        with websocket_connect(user_id):
            pass

    assert not connection_manager.is_online(user_id)
