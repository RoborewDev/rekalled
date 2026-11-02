import uuid

from pydantic import BaseModel


class Me(BaseModel):
    id: uuid.UUID
    email: str | None
    display_name: str | None
    scopes: list[str]
