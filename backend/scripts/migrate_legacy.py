"""One-off migration: imports the original single-tenant policies_docx/ + chroma_db/
into a new 'rag' project, so nothing already indexed under the old setup is lost.

Usage (from backend/, with DATABASE_URL/ENCRYPTION_KEY etc. set in the environment):
    python scripts/migrate_legacy.py --email you@example.com --password 'choose-one'

Reuses the existing chroma_db directory as-is (same embedding model, same chunk
metadata schema), so no re-embedding is needed — it's just copied into the new
per-project storage layout and its files are registered in the `documents` table.
"""
import argparse
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.core.crypto import encrypt_secret
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.document import Document
from app.models.project import Project
from app.models.rag_config import RagConfig
from app.models.user import User

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
LEGACY_POLICIES_DIR = REPO_ROOT / "policies_docx"
LEGACY_CHROMA_DIR = REPO_ROOT / "chroma_db"
LEGACY_TRACKER_FILE = LEGACY_CHROMA_DIR / "indexed_files.json"
LEGACY_ENV_FILE = REPO_ROOT / ".env"


def read_legacy_env() -> dict:
    values = {}
    if LEGACY_ENV_FILE.exists():
        for line in LEGACY_ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--project-name", default="Legacy Policy Bot")
    args = parser.parse_args()

    if not LEGACY_CHROMA_DIR.exists():
        print(f"No legacy chroma_db found at {LEGACY_CHROMA_DIR} — nothing to migrate.")
        return

    env = read_legacy_env()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if user is None:
            user = User(email=args.email, hashed_password=hash_password(args.password))
            db.add(user)
            db.flush()
            print(f"Created user {args.email}")
        else:
            print(f"Using existing user {args.email}")

        project = Project(owner_id=user.id, name=args.project_name, type="rag")
        db.add(project)
        db.flush()

        rag_config = RagConfig(
            project_id=project.id,
            provider="ibm_watsonx",
            api_key_encrypted=encrypt_secret(env["IBM_API_KEY"]) if env.get("IBM_API_KEY") else None,
            model_id="ibm-granite/granite-4.0-h-small",
            region=env.get("IBM_REGION"),
            project_id_external=env.get("PROJECT_ID"),
        )
        db.add(rag_config)

        from app.core.config import get_settings

        settings = get_settings()
        uploads_dir = settings.uploads_dir(str(project.id))
        chroma_dir = settings.chroma_dir(str(project.id))
        uploads_dir.mkdir(parents=True, exist_ok=True)

        if LEGACY_POLICIES_DIR.exists():
            for f in LEGACY_POLICIES_DIR.iterdir():
                if f.is_file():
                    shutil.copy2(f, uploads_dir / f.name)

        shutil.copytree(LEGACY_CHROMA_DIR, chroma_dir, dirs_exist_ok=True)
        # Remove the copied tracker file — replaced by the `documents` table below.
        (chroma_dir / "indexed_files.json").unlink(missing_ok=True)

        tracker = {}
        if LEGACY_TRACKER_FILE.exists():
            tracker = json.loads(LEGACY_TRACKER_FILE.read_text())

        for filename, file_hash in tracker.items():
            db.add(Document(project_id=project.id, filename=filename, file_hash=file_hash, status="indexed"))

        db.commit()
        print(f"Migrated legacy data into project '{project.name}' (id={project.id}).")
        print(f"  {len(tracker)} document(s) carried over without re-embedding.")
        print(f"Log in as {args.email} to manage it in the builder.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
