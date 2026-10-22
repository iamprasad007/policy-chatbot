from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_owned_project
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.core.db import get_db
from app.models.project import Project
from app.models.rag_config import RagConfig
from app.schemas.rag_config import RagConfigIn, RagConfigOut
from app.services import rag_engine

router = APIRouter(prefix="/api/projects/{project_id}/rag-config", tags=["rag-config"])


def _get_config_or_404(project: Project, db: Session) -> RagConfig:
    if project.type != "rag":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a RAG project")
    config = db.query(RagConfig).filter(RagConfig.project_id == project.id).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG config not found")
    return config


def _to_out(config: RagConfig) -> RagConfigOut:
    masked = mask_secret(decrypt_secret(config.api_key_encrypted)) if config.api_key_encrypted else None
    return RagConfigOut(
        provider=config.provider,
        api_key_masked=masked,
        model_id=config.model_id,
        base_url=config.base_url,
        region=config.region,
        project_id_external=config.project_id_external,
        temperature=config.temperature,
        max_new_tokens=config.max_new_tokens,
        search_k=config.search_k,
        fetch_k=config.fetch_k,
        lambda_mult=config.lambda_mult,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        system_prompt=config.system_prompt,
    )


@router.get("", response_model=RagConfigOut)
def get_rag_config(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    config = _get_config_or_404(project, db)
    return _to_out(config)


@router.put("", response_model=RagConfigOut)
def update_rag_config(
    payload: RagConfigIn,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    config = _get_config_or_404(project, db)

    config.provider = payload.provider
    if payload.api_key:  # omit to keep the existing stored key
        config.api_key_encrypted = encrypt_secret(payload.api_key)
    config.model_id = payload.model_id
    config.base_url = payload.base_url
    config.region = payload.region
    config.project_id_external = payload.project_id_external
    config.temperature = payload.temperature
    config.max_new_tokens = payload.max_new_tokens
    config.search_k = payload.search_k
    config.fetch_k = payload.fetch_k
    config.lambda_mult = payload.lambda_mult
    config.chunk_size = payload.chunk_size
    config.chunk_overlap = payload.chunk_overlap
    config.system_prompt = payload.system_prompt

    db.commit()
    db.refresh(config)
    rag_engine.invalidate(project.id)

    return _to_out(config)
