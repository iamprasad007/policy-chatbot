import pathlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_owned_project
from app.core.config import get_settings
from app.core.db import get_db
from app.models.document import Document
from app.models.project import Project
from app.models.rag_config import RagConfig
from app.schemas.document import DocumentOut, ReloadResult
from app.services import ingestion, rag_engine

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])
settings = get_settings()


@router.get("", response_model=list[DocumentOut])
def list_documents(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.project_id == project.id).order_by(Document.created_at.desc()).all()


@router.post("", response_model=list[DocumentOut])
async def upload_documents(
    files: list[UploadFile],
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    if project.type != "rag":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a RAG project")

    uploads_dir = settings.uploads_dir(str(project.id))
    uploads_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Document] = []
    for upload in files:
        original_name = pathlib.Path(upload.filename or "").name  # strip any path components
        suffix = pathlib.Path(original_name).suffix.lower()
        if suffix not in ingestion.SUPPORTED_SUFFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {original_name}",
            )

        dest = uploads_dir / original_name
        content = await upload.read()
        dest.write_bytes(content)

        row = db.query(Document).filter(Document.project_id == project.id, Document.filename == original_name).first()
        if row is None:
            row = Document(project_id=project.id, filename=original_name, file_hash="", status="pending")
            db.add(row)
        else:
            row.status = "pending"
        saved.append(row)

    db.commit()
    for row in saved:
        db.refresh(row)
    return saved


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    row = db.get(Document, document_id)
    if row is None or row.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = settings.uploads_dir(str(project.id)) / row.filename
    if file_path.exists():
        file_path.unlink()

    vectorstore = rag_engine.get_vectorstore(project.id)
    ingestion.delete_chunks_for_source(vectorstore, row.filename)

    db.delete(row)
    db.commit()
    rag_engine.invalidate(project.id)
    return {"status": "deleted"}


@router.post("/reload", response_model=ReloadResult)
def reload_documents(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    if project.type != "rag":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a RAG project")

    config = db.query(RagConfig).filter(RagConfig.project_id == project.id).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG config not found")

    indexed, removed, errors = rag_engine.reindex_project(project.id, config, db)
    return ReloadResult(indexed=indexed, removed=removed, errors=errors)
