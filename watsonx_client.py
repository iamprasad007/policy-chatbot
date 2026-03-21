from langchain_ibm import WatsonxLLM
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os

# ── 1. Load documents ─────────────────────────────────────────────────────────
loaders = [
    Docx2txtLoader("/app/policies_docx/HR_policy.docx"),
    Docx2txtLoader("/app/policies_docx/Leave_policy.docx"),
    Docx2txtLoader("/app/policies_docx/Insurance_policy.docx"),
    Docx2txtLoader("/app/policies_docx/Travel_policy.docx"),
]
docs = []
for loader in loaders:
    docs.extend(loader.load())

# ── 2. Chunk ──────────────────────────────────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# ── 3. Embed & store ──────────────────────────────────────────────────────────
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# ── 4. LLM ────────────────────────────────────────────────────────────────────
llm = WatsonxLLM(
    model_id="meta-llama/llama-3-3-70b-instruct",
    url=f"https://{os.environ['IBM_REGION']}.ml.cloud.ibm.com",
    apikey=os.environ["IBM_API_KEY"],
    project_id=os.environ["PROJECT_ID"],
    params={"max_new_tokens": 500, "temperature": 0.0}
)

# ── 5. Prompt ─────────────────────────────────────────────────────────────────
prompt = PromptTemplate.from_template("""
You are a helpful HR assistant.
Use ONLY the context below to answer the question.
Give a direct, concise answer based strictly on the context.

Context:
{context}

Question: {question}

Answer:""")

# ── 6. RAG chain (modern LCEL style) ─────────────────────────────────────────
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# ── 7. Answer ─────────────────────────────────────────────────────────────────
def generate_answer(question):
    # Check retrieval
    retrieved = retriever.invoke(question)
    print("RETRIEVED CHUNKS:", len(retrieved))
    for doc in retrieved:
        print("  →", doc.page_content[:100])

    answer = rag_chain.invoke(question)
    return answer