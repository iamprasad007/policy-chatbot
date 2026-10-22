"""Per-project retriever + RAG chain, generalized from the original
watsonx_client.py (which had one global retriever/chain for a single tenant).

Chains are cached in-memory per project_id and rebuilt on reload or config change.
"""
from datetime import datetime, timezone

from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document as DocumentRow
from app.models.rag_config import RagConfig
from app.services import ingestion
from app.services.llm_factory import get_chat_model

settings = get_settings()

# Loaded once at process startup — shared across all projects, only the
# persist_directory differs per project.
_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant.
Answer using ONLY the retrieved context — maximum 3 sentences.
Never invent facts that are not present in the context.
Cite the document name when possible.
If the information is not in the context, reply exactly: I couldn't find that information in the documentation.
"""

_CHAIN_CACHE: dict[int, dict] = {}


def invalidate(project_id: int) -> None:
    _CHAIN_CACHE.pop(project_id, None)


def get_vectorstore(project_id: int) -> Chroma:
    return Chroma(persist_directory=str(settings.chroma_dir(str(project_id))), embedding_function=_embeddings)


def _format_docs(docs) -> str:
    formatted = []
    for doc in docs:
        metadata = doc.metadata or {}
        title = metadata.get("title") or metadata.get("source") or "Document"
        api_title = metadata.get("api_title")
        path = metadata.get("path")
        http_method = metadata.get("http_method")

        if metadata.get("source") or metadata.get("title") or metadata.get("api_title") or metadata.get("path") or metadata.get("http_method"):
            lines = [f"Document: {title}"]
            if api_title:
                lines.append(f"API:\n{api_title}")
            if path or http_method:
                endpoint = f"{http_method.upper()} {path}".strip() if http_method else path
                lines.append(f"Endpoint:\n{endpoint}")
            lines.append("Content:")
            lines.append(doc.page_content)
            formatted.append("\n\n".join(lines))
        else:
            formatted.append(doc.page_content)

    return "\n\n".join(formatted)


def reindex_project(project_id: int, config: RagConfig, db: Session) -> tuple[int, int, list[str]]:
    """Scans the project's uploads dir, indexes new/changed files, drops removed ones.
    Returns (indexed_count, removed_count, error_messages)."""
    uploads_dir = settings.uploads_dir(str(project_id))
    uploads_dir.mkdir(parents=True, exist_ok=True)

    vectorstore = get_vectorstore(project_id)
    splitter = RecursiveCharacterTextSplitter(chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)

    existing_rows = {row.filename: row for row in db.query(DocumentRow).filter(DocumentRow.project_id == project_id)}
    current_files = {
        f.name: f
        for f in uploads_dir.iterdir()
        if f.is_file() and f.suffix.lower() in ingestion.SUPPORTED_SUFFIXES
    }

    indexed_count = 0
    errors: list[str] = []

    for filename, file_path in current_files.items():
        file_hash = ingestion.get_file_hash(file_path)
        row = existing_rows.get(filename)

        if row and row.file_hash == file_hash and row.status == "indexed":
            continue  # unchanged — skip re-embedding

        ingestion.delete_chunks_for_source(vectorstore, filename)

        try:
            docs = ingestion.load_documents_for_file(file_path, file_hash)
            chunks = splitter.split_documents(docs)
            for idx, chunk in enumerate(chunks):
                chunk.metadata["source"] = filename
                chunk.metadata["title"] = chunk.metadata.get("title") or file_path.stem
                chunk.metadata["file_hash"] = file_hash
                chunk.metadata["chunk_index"] = idx
            if chunks:
                vectorstore.add_documents(chunks)

            if row is None:
                row = DocumentRow(project_id=project_id, filename=filename, file_hash=file_hash)
                db.add(row)
            row.file_hash = file_hash
            row.status = "indexed"
            row.error_message = None
            row.indexed_at = datetime.now(timezone.utc)
            indexed_count += 1
        except Exception as exc:
            error_msg = f"{filename}: {exc}"
            errors.append(error_msg)
            if row is None:
                row = DocumentRow(project_id=project_id, filename=filename, file_hash=file_hash)
                db.add(row)
            row.file_hash = file_hash
            row.status = "error"
            row.error_message = str(exc)

    removed_count = 0
    for filename, row in list(existing_rows.items()):
        if filename not in current_files:
            ingestion.delete_chunks_for_source(vectorstore, filename)
            db.delete(row)
            removed_count += 1

    db.commit()
    invalidate(project_id)
    return indexed_count, removed_count, errors


def _build_chain(project_id: int, config: RagConfig):
    vectorstore = get_vectorstore(project_id)
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": config.search_k, "fetch_k": config.fetch_k, "lambda_mult": config.lambda_mult},
    )

    llm = get_chat_model(config)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", config.system_prompt or DEFAULT_SYSTEM_PROMPT),
            ("human", "Context:\n{context}\n\nQuestion: {question}"),
        ]
    )

    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return retriever, chain


def _get_or_build(project_id: int, config: RagConfig) -> dict:
    cached = _CHAIN_CACHE.get(project_id)
    if cached is not None:
        return cached

    retriever, chain = _build_chain(project_id, config)
    entry = {"retriever": retriever, "chain": chain}
    _CHAIN_CACHE[project_id] = entry
    return entry


def generate_answer(project_id: int, config: RagConfig, question: str) -> tuple[str, list[str]]:
    entry = _get_or_build(project_id, config)
    retrieved = entry["retriever"].invoke(question)
    sources = sorted({doc.metadata.get("source", "unknown") for doc in retrieved})
    answer = entry["chain"].invoke(question)
    return answer, sources
