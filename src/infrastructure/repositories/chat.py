from infrastructure.base import BaseRepository
from infrastructure.models import Chat


class ChatRepository(BaseRepository[Chat]):
    model = Chat
