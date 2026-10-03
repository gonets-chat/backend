"""Определяет перечисления публичных и внутренних контрактов приложения."""

import enum


class ChatType(enum.Enum):
    DIRECT = "direct"
    GROUP = "group"


class ChatRole(enum.Enum):
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


class PublicRole(enum.Enum):
    MEMBER = "member"
    MODERATOR = "moderator"
    ADMIN = "admin"
    OWNER = "owner"


class RelationStatus(enum.Enum):
    FRIEND = "friend"
    BLOCKED = "blocked"
    PENDING = "pending"
    REJECTED = "rejected"


class NotificationType(enum.Enum):
    LIKE = "like"
    COMMENT = "comment"
    REPOST = "repost"
    MENTION = "mention"
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    SYSTEM = "system"


class PostVisibility(enum.Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


class MediaType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"


class WSCommandType(enum.StrEnum):
    MESSAGE_SEND = "message.send"
    MESSAGE_UPDATE = "message.update"
    MESSAGE_DELETE = "message.delete"


class WSEventType(enum.StrEnum):
    MESSAGE_CREATED = "message.created"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_DELETED = "message.deleted"
    PRESENCE_UPDATED = "presence.updated"
    COMMAND_ERROR = "command.error"


class TokenType(enum.StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"
