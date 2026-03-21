import requests
import os
import chromadb
from chromadb.utils import embedding_functions
from docx import Document
import pathlib

API_KEY = os.environ.get("IBM_API_KEY")
PROJECT_ID = os.environ.get("PROJECT_ID")
REGION = os.environ.get("IBM_REGION")

# ── Load & index policy docs at startup ───────────────────────────────────────
chroma_client = chromadb.Client()  # in-memory, no server needed

collection = chroma_client.create_collection(
    name="policies",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"  # small, fast, free
    )
)

def load_policies():
    policy_dir = pathlib.Path("/app/policies_docx")
    for f in policy_dir.glob("*.docx"):
        doc = Document(f)
        full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        # Simple chunking — split into ~500 char chunks with overlap
        chunk_size = 500
        overlap = 50
        chunks = []
        start = 0
        while start < len(full_text):
            end = start + chunk_size
            chunks.append(full_text[start:end])
            start += chunk_size - overlap

        collection.add(
            documents=chunks,
            ids=[f"{f.stem}_chunk_{i}" for i in range(len(chunks))]
        )
        print(f"Indexed {len(chunks)} chunks from {f.name}")

load_policies()


# ── Retrieve relevant chunks ──────────────────────────────────────────────────
def retrieve_context(question):
    results = collection.query(
        query_texts=[question],
        n_results=3
    )
    chunks = results["documents"][0]  # top 3 matching chunks
    context = "\n\n".join(chunks)
    print("Retrieved context:", context[:300], "...")
    return context


# ── IAM token ─────────────────────────────────────────────────────────────────
def get_access_token():
    response = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "apikey": API_KEY,
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey"
        }
    )
    return response.json()["access_token"]


# ── Generate answer ───────────────────────────────────────────────────────────
def generate_answer(question):
    context = retrieve_context(question)
    token = get_access_token()

    url = f"https://{REGION}.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    prompt = f"""You are a helpful HR assistant.
Answer the question using ONLY the policy excerpts below.
If the answer is not in the excerpts, say: "I cannot find that information in the policy documents."
Do NOT invent rules, numbers, or procedures not explicitly stated.

=== POLICY EXCERPTS ===
{context}
=== END ===

Question: {question}
Answer:"""

    payload = {
        "model_id": "meta-llama/llama-3-3-70b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.0,
        "project_id": PROJECT_ID
    }

    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    print("PROMPT TOKENS:", result.get("usage", {}).get("prompt_tokens"))

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return "I'm sorry, I was unable to find an answer in the policy documents."