import os
import pathlib
import hashlib
import json

from langchain_ibm import ChatWatsonx
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

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
    chunk_size=500,   # ~500 chars per chunk
    chunk_overlap=50  # 50 char overlap so context isn't lost at chunk boundaries
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


# ── Step 5: Smart document indexer ───────────────────────────────────────────
# Connects to persistent ChromaDB on disk
# Scans POLICY_DIR for .docx files
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

    for f in POLICY_DIR.glob("*.docx"):
        file_hash = get_file_hash(f)

        # Skip if this file was already indexed with same content
        if tracker.get(f.name) == file_hash:
            print(f"  Skipping (unchanged): {f.name}")
            continue

        # New or modified file — load, chunk, embed and store
        print(f"  Indexing: {f.name}")
        docs = Docx2txtLoader(str(f)).load()
        chunks = splitter.split_documents(docs)

        # Tag each chunk with its source filename for later reference
        for chunk in chunks:
            chunk.metadata["source"] = f.name

        vectorstore.add_documents(chunks)

        # Record this file as indexed with its current hash
        tracker[f.name] = file_hash
        new_files_indexed += 1

    save_tracker(tracker)

    if new_files_indexed == 0:
        print("  No new documents — loaded from existing index")
    else:
        print(f"  {new_files_indexed} document(s) indexed successfully")

    # Return retriever that fetches top 3 most relevant chunks per query
    return vectorstore.as_retriever(search_kwargs={"k": 3})


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
    model_id="meta-llama/llama-3-3-70b-instruct",
    url=f"https://{os.environ['IBM_REGION']}.ml.cloud.ibm.com",
    apikey=os.environ["IBM_API_KEY"],
    project_id=os.environ["PROJECT_ID"],
    params={"max_new_tokens": 150, "temperature": 0.0}
)


# ── Step 8: Prompt template ───────────────────────────────────────────────────
# System message constrains the model to only use provided context
# Human message injects retrieved chunks + user question
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful HR assistant.
Answer using ONLY the context provided.
Be direct and concise — maximum 3 sentences.
Do not explain your reasoning or rewrite your answer.
If the answer is not in the context, say: I cannot find that information in the policy documents."""),
    ("human", """Context:
{context}

Question: {question}""")
])


# ── Step 9: Format retrieved chunks into a single string ─────────────────────
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


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
    # Retrieve top 3 relevant chunks from ChromaDB
    retrieved = retriever.invoke(question)

    # Debug — shows which chunks were used
    print(f"RETRIEVED CHUNKS: {len(retrieved)}")
    for doc in retrieved:
        print(f"  → [{doc.metadata.get('source', 'unknown')}]: {doc.page_content[:100]}")

    # Extract unique source filenames
    sources = list(set(
        doc.metadata.get("source", "unknown") for doc in retrieved
    ))

    # Run the full RAG chain
    answer = rag_chain.invoke(question)

    return answer, sources