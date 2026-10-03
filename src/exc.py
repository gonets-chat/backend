"""Defines application-specific exceptions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(eq=False)
class BaseError(Exception, ABC):
    @property
    @abstractmethod
    def message(self) -> str: ...

    def __str__(self) -> str:
        return self.message


class DatabaseError(Exception): ...


@dataclass(eq=False)
class DatabaseWriteError(BaseError):
    @property
    def message(self) -> str:
        return "Modifications are not allowed in read-only session"


class UsernameAlreadyExistsError(DatabaseError): ...


class EmailAlreadyExistsError(DatabaseError): ...


class RequiredUserFieldError(DatabaseError): ...


@dataclass(eq=False)
class TokenExpiredError(BaseError):
    @property
    def message(self) -> str:
        return "Access token has expired."


@dataclass(eq=False)
class InvalidTokenError(BaseError):
    @property
    def message(self) -> str:
        return "Invalid token."


@dataclass(eq=False)
class AccessTokenNotFoundError(BaseError):
    @property
    def message(self) -> str:
        return "Access token not found."


@dataclass(eq=False)
class InvalidCredentialsError(BaseError):
    @property
    def message(self) -> str:
        return "Invalid username or password"


@dataclass(eq=False)
class ChatAlreadyExistsError(BaseError):
    user_id: str
    received_id: str

    @property
    def message(self) -> str:
        return (
            f"Direct chat between user '{self.user_id}' and "
            f"'{self.received_id}' already exists."
        )


@dataclass(eq=False)
class DirectChatSelfError(BaseError):
    user_id: UUID

    @property
    def message(self) -> str:
        return "Нельзя создать личный чат \u0441 самим собой."


@dataclass(eq=False)
class ChatNotFoundError(BaseError):
    chat_id: UUID

    @property
    def message(self) -> str:
        return f"Chat with id '{self.chat_id}' not found."


@dataclass(eq=False)
class MessageNotFoundError(BaseError):
    message_id: UUID

    @property
    def message(self) -> str:
        return f"Message with id '{self.message_id}' not found."


@dataclass(eq=False)
class PermissionDeniedError(BaseError):
    # Identifier reserved for future access-violation statistics.
    user_id: UUID

    @property
    def message(self) -> str:
        return "Вы не можете это сделать \u0441 чужим сообщением!"


@dataclass(eq=False)
class ChatAccessDeniedError(PermissionDeniedError):
    chat_id: UUID

    @property
    def message(self) -> str:
        return "\u0423 вас нет доступа к этому чату."


@dataclass(eq=False)
class LoginMethodRequiredError(BaseError, ValueError):
    @property
    def message(self) -> str:
        return "Необходимо указать либо имя пользователя, либо электронную почту"


@dataclass(eq=False)
class LoginMethodAmbiguousError(BaseError, ValueError):
    @property
    def message(self) -> str:
        return "Нельзя указывать одновременно имя пользователя и электронную почту"


@dataclass(eq=False)
class SettingsValidationError(BaseError):
    @property
    def message(self) -> str:
        return "Application settings are invalid."
