"""Валидирует WebSocket-команды и выполняет каждую в отдельной транзакции."""

from typing import Any
from uuid import UUID

from pydantic import ValidationError

from dto.websocket import (
    WS_COMMAND_ADAPTER,
    WSCommandError,
    WSCommandErrorCode,
    WSCommandErrorData,
)
from enums import WSCommandType
from exc import (
    BaseError,
    ChatNotFoundError,
    MessageNotFoundError,
    PermissionDeniedError,
)
from infrastructure.exceptions import UserNotFoundError
from logger import get_configured_logger
from logic.events.abc import BaseEvent, Delivery
from logic.events.handlers.message import MessageDelete, MessageSend, MessageUpdate
from types_alias import ServicesFactory

logger = get_configured_logger(__name__)

INVALID_COMMAND_MESSAGE = "Команда имеет неправильный формат."
INTERNAL_ERROR_MESSAGE = "Команду выполнить не удалось, попробуйте ещё раз."


def command_error(code: WSCommandErrorCode, message: str) -> WSCommandError:
    return WSCommandError(data=WSCommandErrorData(code=code, message=message))


class EventsManager:
    def __init__(self, services_factory: ServicesFactory) -> None:
        self._services_factory = services_factory
        self._events: dict[WSCommandType, BaseEvent[Any]] = {
            WSCommandType.MESSAGE_SEND: MessageSend(),
            WSCommandType.MESSAGE_UPDATE: MessageUpdate(),
            WSCommandType.MESSAGE_DELETE: MessageDelete(),
        }

    async def handle(self, sender_id: UUID, raw_json: str) -> Delivery | WSCommandError:
        """Выполняет команду и возвращает событие для рассылки или ошибку отправителю.

        Рассылку выполняет вызывающий код уже после commit, поэтому клиенты
        никогда не получают событие об изменении, которое откатилось.
        """
        try:
            command = WS_COMMAND_ADAPTER.validate_json(raw_json)
        except ValidationError:
            return command_error("invalid_command", INVALID_COMMAND_MESSAGE)

        event = self._events[command.type]

        try:
            async with self._services_factory() as services:
                return await event.execute(
                    services=services,
                    sender_id=sender_id,
                    data=command.data,
                )
        except PermissionDeniedError as exc:
            return command_error("permission_denied", exc.message)
        except (ChatNotFoundError, MessageNotFoundError, UserNotFoundError) as exc:
            return command_error("not_found", exc.message)
        except BaseError as exc:
            return command_error("bad_request", exc.message)
        except Exception:
            logger.exception(
                "Failed to handle WebSocket command %s from user %s.",
                command.type,
                sender_id,
            )
            return command_error("internal_error", INTERNAL_ERROR_MESSAGE)
