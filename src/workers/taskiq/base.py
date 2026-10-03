from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from config import settings
from logger import get_configured_logger

logger = get_configured_logger(__name__)

# 1. Настраиваем хранилище результатов (Result Backend)
# Здесь будут лежать ответы от функций после их выполнения
result_backend = RedisAsyncResultBackend(
    redis_url=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
)

# 2. Настраиваем брокер сообщений (Broker)
# ListQueueBroker — это встроенный в taskiq_redis быстрый брокер на основе списков Redis
broker = ListQueueBroker(
    url=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"  # 0-я БД для очереди задач  # noqa: E501
).with_result_backend(result_backend)
