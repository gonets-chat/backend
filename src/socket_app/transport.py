"""Читает WebSocket-кадры: транспортные ограничения, heartbeat и срок жизни токена.

Heartbeat: клиент шлёт текстовый кадр `ping` (~каждые 25 с), сервер отвечает `pong`.
Нет ни одного кадра дольше WS_IDLE_TIMEOUT_SECONDS — соединение потеряно (4408).
Истёк access-токен, с которым открыто соединение, — закрытие 4401.
"""

import asyncio
import time

from fastapi import WebSocket, status

from config import settings
from socket_app.security import AUTH_FAILED_CLOSE_CODE

PING = "ping"
PONG = "pong"
IDLE_TIMEOUT_CLOSE_CODE = 4408


async def receive_command(websocket: WebSocket, token_expires_at: float) -> str | None:
    """Следующая команда клиента; None — соединение закрыто."""
    while True:
        seconds_left = token_expires_at - time.time()
        if seconds_left <= 0:
            await websocket.close(
                code=AUTH_FAILED_CLOSE_CODE,
                reason="Access token has expired.",
            )
            return None

        try:
            async with asyncio.timeout(
                min(settings.WS_IDLE_TIMEOUT_SECONDS, seconds_left)
            ):
                frame = await websocket.receive()
        except TimeoutError:
            if time.time() >= token_expires_at:
                continue
            await websocket.close(
                code=IDLE_TIMEOUT_CLOSE_CODE,
                reason="Heartbeat timeout.",
            )
            return None

        if frame["type"] == "websocket.disconnect":
            return None

        raw_text = frame.get("text")
        if raw_text is None:
            await websocket.close(
                code=status.WS_1003_UNSUPPORTED_DATA,
                reason="Only text JSON frames are supported.",
            )
            return None

        if len(raw_text.encode("utf-8")) > settings.MAX_WS_PAYLOAD_BYTES:
            await websocket.close(
                code=status.WS_1009_MESSAGE_TOO_BIG,
                reason="WebSocket message is too large.",
            )
            return None

        if raw_text == PING:
            await websocket.send_text(PONG)
            continue

        return raw_text
