from dataclasses import dataclass

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from exc import (
    AccessTokenNotFoundError,
    BaseError,
    ChatAlreadyExistsError,
    ChatNotFoundError,
    DatabaseError,
    DatabaseWriteError,
    DirectChatSelfError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    MessageNotFoundError,
    PermissionDeniedError,
    TokenExpiredError,
    UsernameAlreadyExistsError,
)
from infrastructure.exceptions import UserNotFoundError
from logger import get_configured_logger

logger = get_configured_logger(__name__)


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    status_code: int
    detail: str | None = None


EXCEPTION_RESPONSES: dict[type[Exception], ErrorResponse] = {
    EmailAlreadyExistsError: ErrorResponse(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Пользователь \u0441 таким адресом электронной почты уже зарегистрирован."
        ),
    ),
    UsernameAlreadyExistsError: ErrorResponse(
        status_code=status.HTTP_409_CONFLICT,
        detail="Это имя пользователя уже занято.",
    ),
    AccessTokenNotFoundError: ErrorResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Access token not found.",
    ),
    InvalidCredentialsError: ErrorResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
    ),
    TokenExpiredError: ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED),
    InvalidTokenError: ErrorResponse(status_code=status.HTTP_401_UNAUTHORIZED),
    ChatAlreadyExistsError: ErrorResponse(status_code=status.HTTP_409_CONFLICT),
    DirectChatSelfError: ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST),
    ChatNotFoundError: ErrorResponse(status_code=status.HTTP_404_NOT_FOUND),
    MessageNotFoundError: ErrorResponse(status_code=status.HTTP_404_NOT_FOUND),
    PermissionDeniedError: ErrorResponse(status_code=status.HTTP_403_FORBIDDEN),
    UserNotFoundError: ErrorResponse(status_code=status.HTTP_404_NOT_FOUND),
    DatabaseWriteError: ErrorResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database write error.",
    ),
    DatabaseError: ErrorResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database error.",
    ),
}


async def application_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    response = next(
        (
            EXCEPTION_RESPONSES[exception_class]
            for exception_class in type(exc).__mro__
            if exception_class in EXCEPTION_RESPONSES
        ),
        ErrorResponse(status_code=status.HTTP_400_BAD_REQUEST),
    )

    if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error(
            "Application exception while processing %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

    return JSONResponse(
        status_code=response.status_code,
        content={"detail": response.detail or str(exc) or "Unexpected error."},
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "Unhandled exception while processing %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


def setup_exception_handlers(app: FastAPI) -> None:
    for exception_class in EXCEPTION_RESPONSES:
        app.add_exception_handler(exception_class, application_exception_handler)

    app.add_exception_handler(BaseError, application_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
