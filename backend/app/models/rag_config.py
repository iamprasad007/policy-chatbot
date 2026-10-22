from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class RagConfig(Base):
    __tablename__ = "rag_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # LLM provider settings — "any LLM API key" abstraction
    provider: Mapped[str] = mapped_column(String(30), default="ibm_watsonx")
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[str] = mapped_column(String(255), default="ibm-granite/granite-4.0-h-small")
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_id_external: Mapped[str | None] = mapped_column(String(255), nullable=True)  # IBM project_id

    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    max_new_tokens: Mapped[int] = mapped_column(Integer, default=150)

    # Retriever settings
    search_k: Mapped[int] = mapped_column(Integer, default=5)
    fetch_k: Mapped[int] = mapped_column(Integer, default=20)
    lambda_mult: Mapped[float] = mapped_column(Float, default=0.7)
    chunk_size: Mapped[int] = mapped_column(Integer, default=1000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=150)

    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    project = relationship("Project", back_populates="rag_config")
