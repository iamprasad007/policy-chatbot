import pathlib
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_builder"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 1 week

    encryption_key: str = "vSg1t8v4x5Zt3xk8u9m8N9YV3sQvJXZ9k9dQe1yF8bY="  # dev-only default

    storage_root: pathlib.Path = pathlib.Path("/app/storage")

    frontend_dist_dir: pathlib.Path = pathlib.Path("/app/frontend_dist")
    widget_dist_dir: pathlib.Path = pathlib.Path("/app/widget_dist")

    def project_dir(self, project_id: str) -> pathlib.Path:
        return self.storage_root / "projects" / project_id

    def uploads_dir(self, project_id: str) -> pathlib.Path:
        return self.project_dir(project_id) / "uploads"

    def chroma_dir(self, project_id: str) -> pathlib.Path:
        return self.project_dir(project_id) / "chroma_db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
