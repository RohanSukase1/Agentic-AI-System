import json
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from orchestrator import Orchestrator
from models import PromptRequest
from utils.llm import chat
from agents.planner_agent import create_plan

orchestrator = Orchestrator()

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="Agentic AI System",
    version="2.0"
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------
# Test LLM
# ----------------------------------------------------

@app.post("/test")
async def test(request: PromptRequest):

    response = await chat(
        "You are a helpful assistant.",
        request.prompt
    )

    return {
        "response": response
    }


# ----------------------------------------------------
# Planning Endpoint
# ----------------------------------------------------

@app.post("/plan")
async def plan(request: PromptRequest):

    execution_plan = await create_plan(
        request.prompt
    )

    return execution_plan


# ----------------------------------------------------
# Normal Execution
# ----------------------------------------------------

@app.post("/execute")
async def execute(request: PromptRequest):

    return await orchestrator.execute(
        request.prompt,
        request.quality
    )


# ----------------------------------------------------
# Streaming Execution (SSE)
# ----------------------------------------------------

@app.get("/execute/stream")
async def execute_stream(prompt: str, quality: int = 5):

    async def event_generator():

        async for event in orchestrator.execute_stream(
            prompt,
            quality
        ):

            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ----------------------------------------------------
# Static Frontend
# MUST be last — routes defined above take priority.
# Uses absolute path so it works both locally and on Railway.
# ----------------------------------------------------

app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")