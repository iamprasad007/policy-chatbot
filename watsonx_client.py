import os
import pathlib
import hashlib
import json

from langchain_ibm import ChatWatsonx
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# ── Configuration ─────────────────────────────────────────────────────────────
POLICY_DIR   = pathlib.Path("/app/policies_docx")  # folder to watch for .docx files
CHROMA_DIR   = "/app/chroma_db"                    # persistent vector store on disk
TRACKER_FILE = "/app/chroma_db/indexed_files.json" # tracks which files are indexed & their hash


# ── Step 1: Embedding model ───────────────────────────────────────────────────
# Loaded once at startup — used for both indexing and querying
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


# ── Step 2: Text splitter ─────────────────────────────────────────────────────
# Splits documents into overlapping chunks for better retrieval coverage
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,   # larger chunks preserve endpoint definitions better
    chunk_overlap=150  # broader overlap keeps related API details together
)


# ── Step 3: File hash helper ──────────────────────────────────────────────────
# MD5 hash of file bytes — used to detect if a file has changed since last index
def get_file_hash(filepath: pathlib.Path) -> str:
    return hashlib.md5(filepath.read_bytes()).hexdigest()


# ── Step 4: Tracker helpers ───────────────────────────────────────────────────
# Tracker is a JSON file that stores {filename: hash} of all indexed documents
# Allows us to skip unchanged files on restart and only process new/modified ones

def load_tracker() -> dict:
    if pathlib.Path(TRACKER_FILE).exists():
        return json.loads(pathlib.Path(TRACKER_FILE).read_text())
    return {}

def save_tracker(tracker: dict):
    pathlib.Path(TRACKER_FILE).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(TRACKER_FILE).write_text(json.dumps(tracker))


def extract_openapi_metadata(file_path: pathlib.Path) -> dict:
    if file_path.suffix.lower() not in {".json", ".yaml", ".yml"}:
        return {}

    try:
        text = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() == ".json":
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


def load_documents_for_file(file_path: pathlib.Path, file_hash: str) -> list[Document]:
    if file_path.suffix.lower() == ".docx":
        docs = Docx2txtLoader(str(file_path)).load()
    else:
        text = file_path.read_text(encoding="utf-8")
        docs = [Document(page_content=text, metadata={})]

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
        loaded_docs.append(Document(page_content=doc.page_content, metadata=metadata))

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


# ── Step 5: Smart document indexer ───────────────────────────────────────────
# Connects to persistent ChromaDB on disk
# Scans POLICY_DIR for supported API/document files
# Only chunks + embeds + stores files that are new or have changed
# Skips unchanged files — they're already in ChromaDB
def build_retriever():
    # Connect to existing ChromaDB or create a new one on first run
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )

    tracker = load_tracker()
    new_files_indexed = 0
    supported_suffixes = {".docx", ".json", ".yaml", ".yml", ".md", ".txt"}
    current_files = {f.name for f in POLICY_DIR.iterdir() if f.is_file() and f.suffix.lower() in supported_suffixes}

    for f in sorted(POLICY_DIR.iterdir()):
        if not f.is_file() or f.suffix.lower() not in supported_suffixes:
            continue

        file_hash = get_file_hash(f)

        # Skip if this file was already indexed with same content
        if tracker.get(f.name) == file_hash:
            print(f"  Skipping (unchanged): {f.name}")
            continue

        # New or modified file — delete old vectors, load, chunk, embed and store
        print(f"  Indexing: {f.name}")
        delete_chunks_for_source(vectorstore, f.name)
        docs = load_documents_for_file(f, file_hash)
        chunks = splitter.split_documents(docs)

        # Tag each chunk with its source filename and chunk metadata for later reference
        for idx, chunk in enumerate(chunks):
            chunk.metadata["source"] = f.name
            chunk.metadata["title"] = chunk.metadata.get("title") or f.stem
            chunk.metadata["file_hash"] = file_hash
            chunk.metadata["chunk_index"] = idx

        vectorstore.add_documents(chunks)

        # Record this file as indexed with its current hash
        tracker[f.name] = file_hash
        new_files_indexed += 1

    for tracked_name in list(tracker.keys()):
        if tracked_name not in current_files:
            print(f"  Removing deleted file: {tracked_name}")
            delete_chunks_for_source(vectorstore, tracked_name)
            del tracker[tracked_name]

    save_tracker(tracker)

    if new_files_indexed == 0:
        print("  No new documents — loaded from existing index")
    else:
        print(f"  {new_files_indexed} document(s) indexed successfully")

    # Return retriever that fetches top 5 most relevant chunks per query
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.7}
    )


# ── Step 6: Build retriever at startup ───────────────────────────────────────
# Runs once when the container starts
# Fast on subsequent restarts if no documents changed
print("Loading document index...")
retriever = build_retriever()
print("Index ready.")


# ── Step 7: LLM setup ────────────────────────────────────────────────────────
# ChatWatsonx is the chat variant — stops cleanly after one response
# Temperature 0.0 = deterministic, no creativity, strictly factual
llm = ChatWatsonx(
    model_id="ibm-granite/granite-4.0-h-small",
    url=f"https://{os.environ['IBM_REGION']}.ml.cloud.ibm.com",
    apikey=os.environ["IBM_API_KEY"],
    project_id=os.environ["PROJECT_ID"],
    params={"max_new_tokens": 150, "temperature": 0.0}
)


# ── Step 8: Prompt template ───────────────────────────────────────────────────
# System message constrains the model to only use provided context
# Human message injects retrieved chunks + user question
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful API assistant.
Answer using ONLY the retrieved context — maximum 3 sentences.
Never invent endpoints, HTTP methods, request or response schemas, OAuth scopes, or headers.
Cite the document name when possible.
If the information is not in the context, reply exactly: I couldn't find that information in the documentation.
"""),
    ("human", """Context:
{context}

Question: {question}""")
])


# ── Step 9: Format retrieved chunks into a single string ─────────────────────
def format_docs(docs):
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


# ── Step 10: RAG chain (LCEL pipe style) ─────────────────────────────────────
# Flow:
#   question → retriever fetches top 3 chunks → format_docs joins them
#            → injected into prompt alongside question
#            → LLM generates answer
#            → StrOutputParser extracts plain text from response
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)


# ── Step 11: Reload helper ────────────────────────────────────────────────────
# Called by POST /admin/reload endpoint in app.py
# Re-scans the policy folder and indexes any new or changed documents
# Does NOT re-process unchanged files
def reload_documents():
    global retriever, rag_chain
    print("Reloading documents...")
    retriever = build_retriever()
    # Rebuild chain with updated retriever
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    print("Reload complete.")


# ── Step 12: Main answer function ────────────────────────────────────────────
# Called by POST /chatbot in app.py
# Retrieves relevant chunks, prints debug info, returns LLM answer + sources
def generate_answer(question: str) -> tuple[str, list[str]]:
    # Retrieve relevant chunks from ChromaDB
    retrieved = retriever.invoke(question)

    # Debug — shows which chunks were used
    print(f"RETRIEVED CHUNKS: {len(retrieved)}")
    for doc in retrieved:
        metadata = doc.metadata or {}
        print(
            "  → "
            f"[{metadata.get('source', 'unknown')}] "
            f"title={metadata.get('title', 'unknown')} "
            f"api_title={metadata.get('api_title', '-')} "
            f"path={metadata.get('path', '-')} "
            f"method={metadata.get('http_method', '-')} "
            f"chunk_index={metadata.get('chunk_index', '-') }"
        )

    # Extract unique source filenames
    sources = list(set(
        doc.metadata.get("source", "unknown") for doc in retrieved
    ))

    # Run the full RAG chain
    answer = rag_chain.invoke(question)

    return answer, sources