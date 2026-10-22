from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    status: str
    error_message: str | None
    indexed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReloadResult(BaseModel):
    indexed: int
    removed: int
    errors: list[str]
