import json
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from orchestrator import Orchestrator
from models import PromptRequest
from utils.llm import chat
from agents.planner_agent import create_plan

orchestrator = Orchestrator()

app = FastAPI(
    title="Agentic AI System",
    version="2.0"
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# REMOVED: GET / was blocking the static file mount.
# The static mount below now serves index.html at /
# ----------------------------------------------------


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
# FIX: Changed POST -> GET with query params.
# EventSource in the browser only supports GET requests
# and cannot send a request body.
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
# Serves static/index.html at http://localhost:8000/
# ----------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")