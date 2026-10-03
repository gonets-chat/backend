from uuid import UUID

from pydantic import BaseModel, Field


class FriendRequestSent(BaseModel):
    sender_id: UUID = Field(..., description="ID отправителя заявки (user_id в БД)")
    target_user_id: UUID = Field(
        ..., description="ID получателя заявки (target_user_id в БД)"
    )


class FriendRequestAccept(BaseModel):
    # Для принятия заявки обычно нужен ID самой связи (UserRelation.id)
    # либо ID того, чью заявку мы принимаем.
    relation_id: UUID = Field(..., description="ID записи из таблицы user_relations")


class FriendRequestReject(BaseModel):
    # Тот, кто отклоняет, обычно уже авторизован (его ID берем из токена/сессии)
    # Нам нужен ID записи, которую мы отклоняем
    relation_id: UUID


class UserBlockRequest(BaseModel):
    # ID пользователя, которого мы хотим отправить в ЧС
    target_user_id: UUID


class UserUnblockRequest(BaseModel):
    # ID пользователя, которого мы хотим убрать из ЧС
    target_user_id: UUID
