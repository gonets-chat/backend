from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

import jwt
from jwt.exceptions import (
    ExpiredSignatureError as JWTExpiredSignatureError,
)
from jwt.exceptions import (
    InvalidTokenError as JWTInvalidTokenError,
)

from config import settings
from enums import TokenType
from exc import InvalidTokenError as AppInvalidTokenError
from exc import TokenExpiredError

if TYPE_CHECKING:
    from types_alias import UserID


from dataclasses import dataclass, field

from utils import generate_uuid_str, get_current_timestamp


@dataclass(frozen=True, slots=True)
class AccessTokenPayload:
    sub: str
    exp: float
    jti: str = field(default_factory=generate_uuid_str)
    token_type: Literal["access"] = "access"
    iat: float = field(default_factory=get_current_timestamp)


@dataclass(frozen=True, slots=True)
class RefreshTokenPayload:
    sub: str
    exp: float
    jti: str = field(default_factory=generate_uuid_str)
    token_type: Literal["refresh"] = "refresh"
    iat: float = field(default_factory=get_current_timestamp)


@dataclass
class AccessToken:
    payload: AccessTokenPayload


@dataclass
class RefreshToken:
    payload: RefreshTokenPayload


@dataclass
class JwtTokens:
    access_token: str
    refresh_token: str


def create_access_token(exp: timedelta, sub: UserID) -> str:
    """Создает строковый JWT Access Token."""
    access_token_payload = AccessTokenPayload(
        exp=(datetime.now(UTC) + exp).timestamp(), sub=str(sub)
    )
    access_token = AccessToken(payload=access_token_payload)

    return jwt.encode(
        key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        payload=asdict(access_token.payload),
    )


def create_refresh_token(exp: timedelta, sub: UserID) -> str:
    """Создает строковый JWT Refresh Token."""
    refresh_token_payload = RefreshTokenPayload(
        exp=(datetime.now(UTC) + exp).timestamp(), sub=str(sub)
    )
    refresh_token = RefreshToken(payload=refresh_token_payload)

    return jwt.encode(
        key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        payload=asdict(refresh_token.payload),
    )


def verify_access_token(token: str) -> AccessToken:
    """
    Проверяет валидность Access Token.
    Возвращает объект AccessToken с payload в случае успеха.
    """
    try:
        payload_dict = jwt.decode(
            token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_type = payload_dict.get("token_type")
        if token_type != TokenType.ACCESS:
            raise AppInvalidTokenError

        payload = AccessTokenPayload(
            sub=payload_dict["sub"],
            exp=payload_dict["exp"],
            jti=payload_dict["jti"],
            token_type=payload_dict["token_type"],
            iat=payload_dict["iat"],
        )

        if payload.exp < datetime.now(UTC).timestamp():
            raise TokenExpiredError
        return AccessToken(payload=payload)

    except JWTExpiredSignatureError as exc:
        raise TokenExpiredError from exc
    except (JWTInvalidTokenError, KeyError) as exc:
        raise AppInvalidTokenError from exc


def verify_refresh_token(token: str) -> RefreshToken:
    """
    Проверяет валидность Refresh Token.
    Возвращает объект RefreshToken с payload в случае успеха.
    """
    try:
        payload_dict = jwt.decode(
            token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        token_type = payload_dict.get("token_type")
        if token_type != TokenType.REFRESH:
            raise AppInvalidTokenError

        payload = RefreshTokenPayload(
            sub=payload_dict["sub"],
            exp=payload_dict["exp"],
            jti=payload_dict["jti"],
            token_type=payload_dict["token_type"],
            iat=payload_dict["iat"],
        )
        if payload.exp < datetime.now(UTC).timestamp():
            raise TokenExpiredError
        return RefreshToken(payload=payload)

    except JWTExpiredSignatureError as exc:
        raise TokenExpiredError from exc
    except (JWTInvalidTokenError, KeyError) as exc:
        raise AppInvalidTokenError from exc
