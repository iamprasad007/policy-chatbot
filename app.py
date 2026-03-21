from fastapi import FastAPI, Request
from pydantic import BaseModel
from watsonx_client import generate_answer

app = FastAPI()

class ChatRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"status": "Policy Chatbot running"}


# @app.post("/chatbot")
# async def chatbot(req: ChatRequest):
#     print("User message:", req.text)
#     answer = generate_answer(req.text)
#     print("Answer:", answer)
#     return {"response": answer}

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

    answer = generate_answer(question)

    print("ANSWER:", answer)

    return {"response": answer}
