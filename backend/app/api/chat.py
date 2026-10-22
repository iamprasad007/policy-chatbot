from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_owned_project
from app.core.db import get_db
from app.models.project import Project
from app.models.rag_config import RagConfig
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import rag_engine

router = APIRouter(tags=["chat"])


def _answer_for_project(project: Project, question: str, db: Session) -> ChatResponse:
    if project.type != "rag":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chatbot flows are not available yet")

    config = db.query(RagConfig).filter(RagConfig.project_id == project.id).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG config not found")

    answer, sources = rag_engine.generate_answer(project.id, config, question)
    return ChatResponse(response=answer, sources=sources)


@router.post("/api/projects/{project_id}/chat", response_model=ChatResponse)
def chat_authenticated(
    payload: ChatRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    """Authenticated 'test in builder' endpoint."""
    return _answer_for_project(project, payload.text, db)


@router.post("/public/{widget_key}/chat", response_model=ChatResponse)
def chat_public(widget_key: str, payload: ChatRequest, db: Session = Depends(get_db)):
    """Unauthenticated endpoint the embedded widget calls, identified by the
    project's public widget key rather than the owner's JWT."""
    project = db.query(Project).filter(Project.public_widget_key == widget_key).first()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown widget")

    return _answer_for_project(project, payload.text, db)
