from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(eq=False)
class RepositoryError(Exception, ABC):
    @property
    @abstractmethod
    def message(self) -> str: ...

    def __str__(self) -> str:
        return self.message


@dataclass
class UserNotFoundError(RepositoryError):
    user_id: UUID

    @property
    def message(self) -> str:
        return f"User with id {self.user_id} not found."
