"""Loads and validates application settings from environment variables."""

from pathlib import Path
from urllib.parse import quote, urlsplit

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from exc import SettingsValidationError

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "OpenVerse Messanger"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    DEFAULT_CACHE_LIFETIME: int = 300

    WS_ALLOWED_ORIGINS: frozenset[str] = Field(min_length=1)
    MAX_WS_PAYLOAD_BYTES: int = Field(default=65_536, ge=1_024)
    MAX_CONNECTIONS_PER_USER: int = Field(default=5, ge=1)
    WS_IDLE_TIMEOUT_SECONDS: int = Field(default=60, ge=10)

    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("WS_ALLOWED_ORIGINS")
    @classmethod
    def validate_ws_allowed_origins(
        cls,
        origins: frozenset[str],
    ) -> frozenset[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username is not None
                or parsed.password is not None
            ):
                msg = f"Invalid WebSocket origin: {origin!r}"
                raise ValueError(msg)

        return origins

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def database_url(self) -> str:
        user = quote(self.POSTGRES_USER, safe="")
        password = quote(self.POSTGRES_PASSWORD, safe="")
        database = quote(self.POSTGRES_DB, safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{database}"
        )


def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[reportCallIssue]
    except ValidationError as exc:
        raise SettingsValidationError from exc


settings = load_settings()
