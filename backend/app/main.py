from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, chat, documents, projects, rag
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Chatbot Builder API")

# Wildcard CORS: the embeddable widget and /public/* chat endpoint are called
# from arbitrary third-party sites. Auth uses a Bearer token (not cookies), so
# a wildcard origin without credentials is safe here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(rag.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "Chatbot builder API running fine"}


if settings.widget_dist_dir.exists():
    app.mount("/widget", StaticFiles(directory=str(settings.widget_dist_dir)), name="widget")

if settings.frontend_dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(settings.frontend_dist_dir), html=True), name="frontend")
