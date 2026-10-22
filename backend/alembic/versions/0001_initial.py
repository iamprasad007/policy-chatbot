"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("public_widget_key", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("linked_rag_project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "rag_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider", sa.String(30), server_default="ibm_watsonx"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("model_id", sa.String(255), server_default="ibm-granite/granite-4.0-h-small"),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("region", sa.String(50), nullable=True),
        sa.Column("project_id_external", sa.String(255), nullable=True),
        sa.Column("temperature", sa.Float(), server_default="0.0"),
        sa.Column("max_new_tokens", sa.Integer(), server_default="150"),
        sa.Column("search_k", sa.Integer(), server_default="5"),
        sa.Column("fetch_k", sa.Integer(), server_default="20"),
        sa.Column("lambda_mult", sa.Float(), server_default="0.7"),
        sa.Column("chunk_size", sa.Integer(), server_default="1000"),
        sa.Column("chunk_overlap", sa.Integer(), server_default="150"),
        sa.Column("system_prompt", sa.Text(), nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("rag_configs")
    op.drop_table("projects")
    op.drop_table("users")
