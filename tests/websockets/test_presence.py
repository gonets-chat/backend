from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from conftest import WebsocketTestState, receive_websocket_event
from starlette.testclient import WebSocketTestSession

from socket_app.connection_manager import connection_manager
from socket_app.presence_manager import presence_manager


def test_presence_broadcasts_online_and_offline_to_shared_chat_member(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])

    with websocket_connect(other_user_id) as observer:
        with websocket_connect(user_id):
            online = receive_websocket_event(observer, "presence.updated")

        offline = receive_websocket_event(observer, "presence.updated")

    assert online == {
        "type": "presence.updated",
        "data": {
            "user_id": str(user_id),
            "is_online": True,
        },
    }
    assert offline == {
        "type": "presence.updated",
        "data": {
            "user_id": str(user_id),
            "is_online": False,
        },
    }


def test_presence_stays_online_while_another_tab_is_connected(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])

    with websocket_connect(other_user_id) as observer:
        with websocket_connect(user_id):
            online = receive_websocket_event(observer, "presence.updated")

            with websocket_connect(user_id):
                assert len(connection_manager.connections[user_id]) == 2

            assert connection_manager.is_online(user_id)
            assert len(connection_manager.connections[user_id]) == 1

        offline = receive_websocket_event(observer, "presence.updated")

    assert online["data"]["is_online"] is True
    assert offline["data"]["is_online"] is False


def test_presence_cancels_offline_when_user_reconnects_during_grace_period(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    presence_manager.offline_grace_seconds = 0.1
    websocket_state.add_chat(chat_id, [user_id, other_user_id])

    with websocket_connect(other_user_id) as observer:
        with websocket_connect(user_id):
            online = receive_websocket_event(observer, "presence.updated")

        with websocket_connect(user_id):
            assert connection_manager.is_online(user_id)

        next_presence = receive_websocket_event(observer, "presence.updated")

    assert online["data"]["is_online"] is True
    assert next_presence["data"]["is_online"] is False
