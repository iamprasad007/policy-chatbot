from fastapi import FastAPI, Request
from pydantic import BaseModel
from watsonx_client import generate_answer, reload_documents

app = FastAPI()

class ChatRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"status": "Policy Chatbot running"}


@app.post("/chatbot")
async def chatbot(request: Request):
    print("REQUEST RECEIVED")

    body = await request.json()
    print("RAW BODY:", body)

    question = body.get("text")

    # Watsonx Assistant sends parameters as arrays
    if isinstance(question, list):
        question = question[0]

    print("QUESTION:", question)

    # generate_answer now returns (answer, sources)
    answer, sources = generate_answer(question)

    print("ANSWER:", answer)
    print("SOURCES:", sources)

    return {"response": answer, "sources": sources}


# Drop a new .docx into policies_docx/ then hit this endpoint
# No rebuild or restart needed
@app.post("/admin/reload")
def reload():
    reload_documents()
    return {"status": "reloaded"}