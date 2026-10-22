from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    type: Literal["rag", "chatbot"]


class ProjectOut(BaseModel):
    id: int
    name: str
    type: str
    public_widget_key: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EmbedSnippetOut(BaseModel):
    snippet: str
    widget_js_url: str
    public_widget_key: str
