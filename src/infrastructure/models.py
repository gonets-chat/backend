from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from bcrypt import checkpw
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from enums import (
    ChatRole,
    ChatType,
    MediaType,
    NotificationType,
    PostVisibility,
    PublicRole,
    RelationStatus,
)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    second_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    memberships: Mapped[list[ChatMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="sender", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    outgoing_relations: Mapped[list[UserRelation]] = relationship(
        foreign_keys="UserRelation.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    incoming_relations: Mapped[list[UserRelation]] = relationship(
        foreign_keys="UserRelation.target_user_id",
        back_populates="target_user",
        cascade="all, delete-orphan",
    )

    posts: Mapped[list[Post]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    owned_publics: Mapped[list[Public]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    public_memberships: Mapped[list[PublicMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    post_likes: Mapped[list[PostLike]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    post_comments: Mapped[list[PostComment]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    post_reposts: Mapped[list[PostRepost]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    notifications_received: Mapped[list[Notification]] = relationship(
        foreign_keys="Notification.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications_sent: Mapped[list[Notification]] = relationship(
        foreign_keys="Notification.actor_id",
        back_populates="actor",
        cascade="all, delete-orphan",
    )

    notification_preference: Mapped[NotificationPreference | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def verify_password(self, plain_password: str) -> bool:
        return checkpw(
            plain_password.encode("utf-8"), self.hashed_password.encode("utf-8")
        )


class Chat(TimestampMixin, Base):
    __tablename__ = "chats"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    type: Mapped[ChatType] = mapped_column(
        Enum(ChatType), default=ChatType.DIRECT, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    members: Mapped[list[ChatMember]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )


class ChatMember(TimestampMixin, Base):
    __tablename__ = "chat_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatRole] = mapped_column(
        Enum(ChatRole), default=ChatRole.MEMBER, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    chat: Mapped[Chat] = relationship(back_populates="members")


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    chat_id: Mapped[UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    chat: Mapped[Chat] = relationship(back_populates="messages")
    sender: Mapped[User] = relationship(back_populates="messages")

    # Курсорная пагинация истории и последнее сообщение чата.
    __table_args__ = (Index("ix_messages_chat_id_id", "chat_id", "id"),)


class UserSession(TimestampMixin, Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class UserRelation(TimestampMixin, Base):
    __tablename__ = "user_relations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[RelationStatus] = mapped_column(
        Enum(RelationStatus), default=RelationStatus.PENDING, nullable=False
    )

    user: Mapped[User] = relationship(
        foreign_keys=[user_id], back_populates="outgoing_relations"
    )
    target_user: Mapped[User] = relationship(
        foreign_keys=[target_user_id], back_populates="incoming_relations"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "target_user_id", name="uq_user_relation_pair"),
    )


class Public(TimestampMixin, Base):
    __tablename__ = "publics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    members_count: Mapped[int] = mapped_column(default=0, nullable=False)
    posts_count: Mapped[int] = mapped_column(default=0, nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner: Mapped[User] = relationship(back_populates="owned_publics")
    members: Mapped[list[PublicMember]] = relationship(
        back_populates="public", cascade="all, delete-orphan"
    )
    posts: Mapped[list[Post]] = relationship(back_populates="public")


class PublicMember(TimestampMixin, Base):
    __tablename__ = "public_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        ForeignKey("publics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[PublicRole] = mapped_column(
        Enum(PublicRole), default=PublicRole.MEMBER, nullable=False
    )

    public: Mapped[Public] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="public_memberships")

    __table_args__ = (
        UniqueConstraint("public_id", "user_id", name="uq_public_member_user"),
    )


class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    public_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("publics.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[PostVisibility] = mapped_column(
        Enum(PostVisibility), default=PostVisibility.PUBLIC, nullable=False
    )

    likes_count: Mapped[int] = mapped_column(default=0, nullable=False)
    comments_count: Mapped[int] = mapped_column(default=0, nullable=False)
    reposts_count: Mapped[int] = mapped_column(default=0, nullable=False)

    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    author: Mapped[User] = relationship(back_populates="posts")
    public: Mapped[Public | None] = relationship(back_populates="posts")
    media_items: Mapped[list[PostMedia]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    likes: Mapped[list[PostLike]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    comments: Mapped[list[PostComment]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    reposts: Mapped[list[PostRepost]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class PostMedia(TimestampMixin, Base):
    __tablename__ = "post_media"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType), nullable=False, default=MediaType.IMAGE
    )
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    preview_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    position: Mapped[int] = mapped_column(default=0, nullable=False)
    metadata_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    post: Mapped[Post] = relationship(back_populates="media_items")

    __table_args__ = (Index("ix_post_media_post_position", "post_id", "position"),)


class PostLike(TimestampMixin, Base):
    __tablename__ = "post_likes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    post: Mapped[Post] = relationship(back_populates="likes")
    user: Mapped[User] = relationship(back_populates="post_likes")

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_like_user_post"),
    )


class PostComment(TimestampMixin, Base):
    __tablename__ = "post_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_comment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=True, index=True
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    post: Mapped[Post] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(back_populates="post_comments")

    parent: Mapped[PostComment | None] = relationship(
        remote_side="PostComment.id", back_populates="replies"
    )
    replies: Mapped[list[PostComment]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )


class PostRepost(TimestampMixin, Base):
    __tablename__ = "post_reposts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    post: Mapped[Post] = relationship(back_populates="reposts")
    user: Mapped[User] = relationship(back_populates="post_reposts")

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_repost_user_post"),
    )


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    post_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(
        foreign_keys=[user_id], back_populates="notifications_received"
    )
    actor: Mapped[User | None] = relationship(
        foreign_keys=[actor_id], back_populates="notifications_sent"
    )
    post: Mapped[Post | None] = relationship(back_populates="notifications")


class NotificationPreference(TimestampMixin, Base):
    __tablename__ = "notification_preferences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    likes_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    comments_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    reposts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mentions_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    friend_requests_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    system_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="notification_preference")
