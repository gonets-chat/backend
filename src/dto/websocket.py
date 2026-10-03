"""Валидирует входящие WebSocket-команды и описывает безопасные ошибки."""

from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from dto.base import DTOBase, WSClientCommand, WSServerEvent
from dto.message import MessageCreate, MessageDeleteData, MessageUpdateDTO
from enums import WSCommandType, WSEventType


class MessageSendCommand(WSClientCommand[MessageCreate]):
    type: Literal[WSCommandType.MESSAGE_SEND] = WSCommandType.MESSAGE_SEND


class MessageUpdateCommand(WSClientCommand[MessageUpdateDTO]):
    type: Literal[WSCommandType.MESSAGE_UPDATE] = WSCommandType.MESSAGE_UPDATE


class MessageDeleteCommand(WSClientCommand[MessageDeleteData]):
    type: Literal[WSCommandType.MESSAGE_DELETE] = WSCommandType.MESSAGE_DELETE


type WSCommand = Annotated[
    MessageSendCommand | MessageUpdateCommand | MessageDeleteCommand,
    Field(discriminator="type"),
]


WS_COMMAND_ADAPTER = TypeAdapter(WSCommand)


type WSCommandErrorCode = Literal[
    "invalid_command",
    "permission_denied",
    "not_found",
    "bad_request",
    "internal_error",
]


class WSCommandErrorData(DTOBase):
    code: WSCommandErrorCode
    message: str


class WSCommandError(WSServerEvent[WSCommandErrorData]):
    type: WSEventType = WSEventType.COMMAND_ERROR
