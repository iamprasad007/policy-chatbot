from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_owned_project
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.project import Project
from app.models.rag_config import RagConfig
from app.models.user import User
from app.schemas.project import EmbedSnippetOut, ProjectCreate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])
settings = get_settings()


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Project).filter(Project.owner_id == user.id).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = Project(owner_id=user.id, name=payload.name, type=payload.type)
    db.add(project)
    db.flush()

    if payload.type == "rag":
        db.add(RagConfig(project_id=project.id))

    db.commit()
    db.refresh(project)

    settings.uploads_dir(str(project.id)).mkdir(parents=True, exist_ok=True)
    settings.chroma_dir(str(project.id)).mkdir(parents=True, exist_ok=True)

    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: Project = Depends(get_owned_project)):
    return project


@router.delete("/{project_id}")
def delete_project(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    db.delete(project)
    db.commit()
    return {"status": "deleted"}


@router.get("/{project_id}/embed-snippet", response_model=EmbedSnippetOut)
def embed_snippet(project: Project = Depends(get_owned_project)):
    widget_url = "/widget/widget.js"
    snippet = (
        f'<script src="{widget_url}" data-project="{project.public_widget_key}" async></script>'
    )
    return EmbedSnippetOut(snippet=snippet, widget_js_url=widget_url, public_widget_key=project.public_widget_key)
