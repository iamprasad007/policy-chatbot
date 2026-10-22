"""Multi-format document loading: docx, pdf (+ OCR fallback for scanned pages),
jpeg/png (OCR), and the existing OpenAPI-aware json/yaml/md/txt handling.

Ported and generalized from the original watsonx_client.py so the same
skip-unchanged-file indexing behavior is preserved per project.
"""
import hashlib
import io
import pathlib

from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document as LCDocument

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SUPPORTED_SUFFIXES = {".docx", ".pdf", ".jpg", ".jpeg", ".png", ".json", ".yaml", ".yml", ".md", ".txt"}

# A page/image with fewer real characters than this is treated as "no extractable text"
# and falls back to OCR.
MIN_TEXT_CHARS = 20


def get_file_hash(filepath: pathlib.Path) -> str:
    return hashlib.md5(filepath.read_bytes()).hexdigest()


def extract_openapi_metadata(file_path: pathlib.Path) -> dict:
    if file_path.suffix.lower() not in {".json", ".yaml", ".yml"}:
        return {}

    try:
        text = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() == ".json":
            import json

            data = json.loads(text)
        elif yaml is not None:
            data = yaml.safe_load(text)
        else:
            return {}
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    info = data.get("info", {}) if isinstance(data.get("info"), dict) else {}
    metadata = {}
    if info.get("title"):
        metadata["api_title"] = info["title"]
    if info.get("version"):
        metadata["version"] = info["version"]

    for path, methods in (data.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"} and isinstance(operation, dict):
                metadata["path"] = path
                metadata["http_method"] = method.upper()
                tags = operation.get("tags")
                if isinstance(tags, list) and tags:
                    metadata["tag"] = tags[0]
                break
        if "path" in metadata:
            break

    return metadata


def _ocr_image_bytes(image_bytes: bytes) -> str:
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)


def _load_image(file_path: pathlib.Path) -> list[LCDocument]:
    text = _ocr_image_bytes(file_path.read_bytes())
    return [LCDocument(page_content=text, metadata={"ocr": True})]


def _load_pdf(file_path: pathlib.Path) -> list[LCDocument]:
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    docs: list[LCDocument] = []

    ocr_pages: list[int] = []
    for page_num, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if len(text) < MIN_TEXT_CHARS:
            ocr_pages.append(page_num)
        else:
            docs.append(LCDocument(page_content=text, metadata={"page": page_num + 1}))

    if ocr_pages:
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(str(file_path))
            for page_num in ocr_pages:
                if page_num >= len(images):
                    continue
                buf = io.BytesIO()
                images[page_num].save(buf, format="PNG")
                text = _ocr_image_bytes(buf.getvalue())
                if text.strip():
                    docs.append(LCDocument(page_content=text, metadata={"page": page_num + 1, "ocr": True}))
        except Exception:
            # Poppler/pdf2image unavailable or conversion failed — skip OCR fallback,
            # keep whatever text-extractable pages were found.
            pass

    return docs


def load_documents_for_file(file_path: pathlib.Path, file_hash: str) -> list[LCDocument]:
    suffix = file_path.suffix.lower()

    if suffix == ".docx":
        docs = Docx2txtLoader(str(file_path)).load()
    elif suffix == ".pdf":
        docs = _load_pdf(file_path)
    elif suffix in {".jpg", ".jpeg", ".png"}:
        docs = _load_image(file_path)
    else:
        text = file_path.read_text(encoding="utf-8")
        docs = [LCDocument(page_content=text, metadata={})]

    if not docs:
        return []

    openapi_metadata = extract_openapi_metadata(file_path)
    title = openapi_metadata.get("api_title") or file_path.stem
    base_metadata = {
        "source": file_path.name,
        "title": title,
        "file_hash": file_hash,
    }
    base_metadata.update(openapi_metadata)

    loaded_docs = []
    for doc in docs:
        metadata = dict(base_metadata)
        if isinstance(doc.metadata, dict):
            metadata.update(doc.metadata)
        metadata.setdefault("title", title)
        loaded_docs.append(LCDocument(page_content=doc.page_content, metadata=metadata))

    return loaded_docs


def delete_chunks_for_source(vectorstore, source_name: str):
    try:
        result = vectorstore.get(where={"source": source_name})
        ids = result.get("ids", []) if isinstance(result, dict) else []
    except Exception:
        try:
            result = vectorstore._collection.get(where={"source": source_name})
            ids = result.get("ids", []) if isinstance(result, dict) else []
        except Exception:
            ids = []

    if ids:
        vectorstore.delete(ids=ids)
