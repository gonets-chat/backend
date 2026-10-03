# ruff: noqa

from datetime import timedelta
from typing import Self

from redis import asyncio as aioredis

from logger import get_configured_logger
from config import settings
from types_alias import Seconds

logger = get_configured_logger(__name__)


class RedisTTLCache:
    def __init__(self) -> None:
        self.redis: aioredis.Redis | None = None

    async def connect(self) -> Self:
        logger.info(
            f"Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}..."
        )
        self.redis = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        logger.info("Redis connection established successfully.")
        return self

    async def set(
        self, key: str, value: str, time: Seconds | timedelta | None = None
    ) -> None:
        if not self.redis:
            logger.error(
                "Redis client is not initialized! Call .connect() first.", exc_info=True
            )
            raise ConnectionError(
                "Redis client is not initialized. Cannot perform 'set' operation."
            )

        try:
            lifetime = time or settings.DEFAULT_CACHE_LIFETIME

            await self.redis.set(
                name=key,
                value=value,
                ex=lifetime,
            )
            logger.debug(f"Set cache value with key: {key}")
        except Exception as e:
            logger.warning(f"Failed to set cache for key '{key}': {e}", exc_info=True)

    async def get(self, key: str) -> str | None:
        if not self.redis:
            logger.error(
                "Redis client is not initialized! Call .connect() first.", exc_info=True
            )
            raise ConnectionError(
                "Redis client is not initialized. Cannot perform 'get' operation."
            )

        try:
            cached_value = await self.redis.get(name=key)
            logger.debug(f"Get value by key: {key}")
            return cached_value.decode() if cached_value else None
        except Exception as e:
            logger.warning(f"Failed to get cache for key '{key}': {e}", exc_info=True)
            return None

    async def del_key(self, key: str) -> None:
        if not self.redis:
            logger.error(
                "Redis client is not initialized! Call .connect() first.", exc_info=True
            )
            raise ConnectionError(
                "Redis client is not initialized. Cannot perform 'del_key' operation."
            )

        try:
            await self.redis.delete(key)
            logger.debug(f"Deleted cache key: {key}")
        except Exception as e:
            logger.warning(f"Failed to delete cache key '{key}': {e}", exc_info=True)

    async def close(self) -> None:
        if not self.redis:
            logger.warning(
                "Attempted to close Redis connection, but it was never initialized."
            )
            return

        try:
            await self.redis.aclose()
            logger.info("Redis connection closed.")
        except Exception as e:
            logger.error(f"Error while closing Redis connection: {e}", exc_info=True)
        finally:
            self.redis = None
