from pydantic import BaseModel


class RagConfigIn(BaseModel):
    provider: str
    api_key: str | None = None  # write-only; omit to keep existing key
    model_id: str
    base_url: str | None = None
    region: str | None = None
    project_id_external: str | None = None

    temperature: float = 0.0
    max_new_tokens: int = 150

    search_k: int = 5
    fetch_k: int = 20
    lambda_mult: float = 0.7
    chunk_size: int = 1000
    chunk_overlap: int = 150

    system_prompt: str | None = None


class RagConfigOut(BaseModel):
    provider: str
    api_key_masked: str | None
    model_id: str
    base_url: str | None
    region: str | None
    project_id_external: str | None

    temperature: float
    max_new_tokens: int

    search_k: int
    fetch_k: int
    lambda_mult: float
    chunk_size: int
    chunk_overlap: int

    system_prompt: str | None
