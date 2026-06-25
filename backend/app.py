from fastapi import FastAPI
from models import PromptRequest
from utils.llm import chat

app = FastAPI(
    title="Agentic AI System",
    version="1.0"
)


@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "Agentic AI System Backend"
    }


@app.post("/test")
async def test_llm(request: PromptRequest):
    response = await chat(request.prompt)

    return {
        "response": response
    }