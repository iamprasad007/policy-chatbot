import secrets
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _generate_widget_key() -> str:
    return f"wk_{secrets.token_urlsafe(24)}"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # "rag" | "chatbot"
    public_widget_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, default=_generate_widget_key
    )
    # Phase 2: a chatbot-type project may delegate answers to a rag-type project.
    linked_rag_project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="projects")
    rag_config = relationship(
        "RagConfig", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
