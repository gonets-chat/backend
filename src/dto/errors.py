from pydantic import BaseModel


class PermissionDenied(BaseModel):
    status_code: int
    error: str
