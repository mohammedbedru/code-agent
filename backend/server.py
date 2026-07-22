import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from . import agent as agent_module
from . import ollama_client

app = FastAPI(title="Code Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    workspace: str
    message: str
    history: list = []
    model: str = "gemma4:12b"
    settings: dict = {}


class SettingsRequest(BaseModel):
    model: str = "gemma4:12b"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/models")
def get_models():
    return {"models": ollama_client.list_models()}


@app.post("/chat")
def chat(req: ChatRequest):
    def event_stream():
        for event in agent_module.run_agent(
            workspace=req.workspace,
            user_message=req.message,
            history=req.history,
            model=req.model,
            settings=req.settings,
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
