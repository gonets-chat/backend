"""Проверяет право клиента на WebSocket-соединение: Origin и access-токен.

Чужой Origin отклоняется до accept (1008): переподключаться бессмысленно.
Ошибка токена закрывает соединение уже после accept с кодом 4401 — только так
браузер увидит код и сможет обновить токен и переподключиться.
"""

from uuid import UUID

from fastapi import WebSocket, WebSocketException, status

from config import settings
from exc import AccessTokenNotFoundError, InvalidTokenError, TokenExpiredError
from tokens import AccessToken, verify_access_token

AUTH_FAILED_CLOSE_CODE = 4401


def require_allowed_origin(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    if origin is None or origin not in settings.WS_ALLOWED_ORIGINS:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="WebSocket origin is not allowed.",
        )


def _verify_cookie_token(token: str | None) -> AccessToken:
    if token is None:
        raise AccessTokenNotFoundError

    access_token = verify_access_token(token)
    try:
        UUID(access_token.payload.sub)
    except ValueError as exc:
        raise InvalidTokenError from exc

    return access_token


async def authenticate_websocket(websocket: WebSocket) -> AccessToken | None:
    """Возвращает токен; None — соединение уже закрыто с кодом 4401."""
    try:
        return _verify_cookie_token(websocket.cookies.get("access_token"))
    except (AccessTokenNotFoundError, TokenExpiredError, InvalidTokenError) as exc:
        await websocket.accept()
        await websocket.close(code=AUTH_FAILED_CLOSE_CODE, reason=exc.message)
        return None
