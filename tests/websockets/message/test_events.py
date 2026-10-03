from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from conftest import WebsocketTestState, receive_websocket_event
from starlette.testclient import WebSocketTestSession


def test_message_send_broadcasts_created_event_to_online_chat_members(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])

    with websocket_connect(user_id) as sender:
        with websocket_connect(other_user_id) as receiver:
            sender.send_json(
                {
                    "type": "message.send",
                    "data": {
                        "chat_id": str(chat_id),
                        "text": "hello",
                    },
                }
            )

            sender_payload = receive_websocket_event(sender, "message.created")
            receiver_payload = receive_websocket_event(receiver, "message.created")

    assert sender_payload == receiver_payload
    assert sender_payload["type"] == "message.created"
    message_data = sender_payload["data"]["message"]
    assert message_data["chat_id"] == str(chat_id)
    assert message_data["sender_id"] == str(user_id)
    assert message_data["text"] == "hello"


def test_message_send_returns_permission_denied_for_non_member(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [other_user_id])

    with websocket_connect(user_id) as sender:
        sender.send_json(
            {
                "type": "message.send",
                "data": {
                    "chat_id": str(chat_id),
                    "text": "forbidden",
                },
            }
        )
        payload = sender.receive_json()

    assert payload == {
        "type": "command.error",
        "data": {
            "code": "permission_denied",
            "message": "У вас нет доступа к этому чату.",
        },
    }
    assert websocket_state.messages == {}


def test_message_update_broadcasts_updated_event_to_online_chat_members(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])
    message = websocket_state.add_message(chat_id=chat_id, sender_id=user_id)

    with websocket_connect(user_id) as sender:
        with websocket_connect(other_user_id) as receiver:
            sender.send_json(
                {
                    "type": "message.update",
                    "data": {
                        "message_id": str(message.id),
                        "text": "updated text",
                        "is_read": True,
                    },
                }
            )

            sender_payload = receive_websocket_event(sender, "message.updated")
            receiver_payload = receive_websocket_event(receiver, "message.updated")

    assert sender_payload == receiver_payload
    assert sender_payload["type"] == "message.updated"
    message_data = sender_payload["data"]["message"]
    assert message_data["id"] == str(message.id)
    assert message_data["text"] == "updated text"
    assert message_data["is_read"] is True


def test_message_delete_broadcasts_deleted_event_to_online_chat_members(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])
    message = websocket_state.add_message(chat_id=chat_id, sender_id=user_id)

    with websocket_connect(user_id) as sender:
        with websocket_connect(other_user_id) as receiver:
            sender.send_json(
                {
                    "type": "message.delete",
                    "data": {
                        "message_id": str(message.id),
                    },
                }
            )

            sender_payload = receive_websocket_event(sender, "message.deleted")
            receiver_payload = receive_websocket_event(receiver, "message.deleted")

    assert sender_payload == receiver_payload
    assert sender_payload["type"] == "message.deleted"
    assert sender_payload["data"]["message_id"] == str(message.id)
    assert sender_payload["data"]["chat_id"] == str(chat_id)
    assert message.id not in websocket_state.messages


def test_message_update_returns_permission_denied_to_sender(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])
    message = websocket_state.add_message(chat_id=chat_id, sender_id=other_user_id)

    with websocket_connect(user_id) as sender:
        sender.send_json(
            {
                "type": "message.update",
                "data": {
                    "message_id": str(message.id),
                    "text": "forbidden update",
                },
            }
        )
        payload = sender.receive_json()

    assert payload == {
        "type": "command.error",
        "data": {
            "code": "permission_denied",
            "message": "Вы не можете это сделать с чужим сообщением!",
        },
    }
    assert websocket_state.messages[message.id].text == "initial text"


def test_message_update_broadcasts_message_chat_id(
    websocket_connect: Callable[..., WebSocketTestSession],
    websocket_state: WebsocketTestState,
    user_id: UUID,
    other_user_id: UUID,
    chat_id: UUID,
) -> None:
    websocket_state.add_chat(chat_id, [user_id, other_user_id])
    message = websocket_state.add_message(chat_id=chat_id, sender_id=user_id)

    with websocket_connect(user_id) as sender:
        with websocket_connect(other_user_id) as receiver:
            sender.send_json(
                {
                    "type": "message.update",
                    "data": {
                        "message_id": str(message.id),
                        "text": "updated text",
                    },
                }
            )

            sender_payload = receive_websocket_event(sender, "message.updated")
            receiver_payload = receive_websocket_event(receiver, "message.updated")

    assert sender_payload == receiver_payload
    assert sender_payload["data"]["message"]["chat_id"] == str(chat_id)
