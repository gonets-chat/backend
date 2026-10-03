import asyncio

from logger import get_configured_logger
from workers.taskiq.base import broker

logger = get_configured_logger(__name__)


@broker.task
async def send_welcome_email(user_email: str, username: str) -> bool:
    """Имитация долгой отправки письма"""
    logger.info(f"Начало отправки письма для {user_email}")

    # Здесь могла бы быть логика отправки через aiosmtplib

    await asyncio.sleep(3)

    logger.info(f"Письмо успешно отправлено {username}!")
    return True
