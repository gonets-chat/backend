import logging
import sys


def get_configured_logger(name: str = __name__, level=logging.DEBUG) -> logging.Logger:
    """
    Настраивает и возвращает простой логгер для работы в консоли.
    """
    logger = logging.getLogger(name)

    # Если логгер уже настроен (например, при повторном вызове), возвращаем его
    if logger.hasHandlers():
        return logger

    logger.setLevel(level)

    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Задаем красивый формат: [Время] [Уровень] [Имя файла:Линия] -> Сообщение
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-5s [%(filename)s:%(lineno)d] -> %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    # Добавляем обработчик к логгеру
    logger.addHandler(console_handler)

    return logger


# === Пример использования ===
if __name__ == "__main__":
    # Получаем настроенный логгер
    log = get_configured_logger()

    log.info("Логгер успешно инициализирован!")
    log.debug("Это сообщение для отладки (debug)")
    log.warning("Предупреждение!")
    log.error("А тут что-то пошло не так...")
