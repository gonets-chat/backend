"""Определяет общие модели WebSocket-конвертов и их строгую конфигурацию."""

from pydantic import BaseModel, ConfigDict


class DTOBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        hide_input_in_errors=True,
    )


class WSServerEvent[DataT: BaseModel](DTOBase):
    data: DataT


class WSClientCommand[DataT: BaseModel](DTOBase):
    data: DataT
