from datetime import UTC, datetime
from uuid import uuid4

import bcrypt


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def get_current_timestamp() -> float:
    return datetime.now(UTC).timestamp()


def generate_uuid_str() -> str:
    return str(uuid4())
