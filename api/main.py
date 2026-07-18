#!/data/data/com.termux/files/usr/bin/python3
"""
main.py — FastAPI application for Team B v1.3.0.
Features: 
- Health & router status, task batching, streaming generation with llama.cpp (llama-server)
- Multi-agent system with sub-agents (skills, memory, heartbeat, soul, tools)
- Universal Remote Control for zero-shot planning and execution
- MCP server integration with isolated connection pools
- Background task scheduler with lazy loading
Uses Qwen2.5-0.5b-instruct-q4_k_m.gguf model for optimized performance.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import json
import time
import asyncio
from collections import deque
from typing import Optional

from core.config import settings
from api.endpoints import agents as agents_router

app = FastAPI(
    title="Team B AI-Agent System",
    version="1.3.0",
    description="DDD AI‑Agent Task Execution & Coordination System with llama.cpp and Multi-Agent Architecture",
)

# Include routers
app.include_router(agents_router.router, prefix="/api/v1", tags=["agents"])

# Model configuration for llama.cpp (llama-server)
LLAMA_SERVER_URL = f"http://{settings.LLAMA_SERVER_HOST}:{settings.LLAMA_SERVER_PORT}"
DEFAULT_MODEL = settings.LLAMA_MODEL

MODEL_TASK_MAP: dict[str, list[str]] = {
    "qwen2.5-0.5b-instruct": [
        "code_generation",
        "refactoring",
        "bug_fix",
        "planning",
        "architecture",
        "review",
        "translation",
        "quick_cmd",
        "classification",
        "boilerplate",
        "file_ops",
        "summary",
        "chat",
        "qa",
    ],
}

BATCH_WINDOW: float = 30.0
task_queue: deque[dict] = deque()
last_batch_time: float = time.time()


def _best_model(task_type: str) -> str:
    """Return the best model for a given task type."""
    return DEFAULT_MODEL


async def _process_batch() -> None:
    """Process batched tasks from the queue."""
    global last_batch_time
    while True:
        elapsed = time.time() - last_batch_time
        if elapsed >= BATCH_WINDOW and task_queue:
            groups: dict[str, list[dict]] = {}
            while task_queue:
                task = task_queue.popleft()
                model = _best_model(task["type"])
                groups.setdefault(model, []).append(task)
            for model, tasks in groups.items():
                print(f"[BATCH] {model} ← {len(tasks)} tasks")
            last_batch_time = time.time()
        await asyncio.sleep(2)


@app.on_event("startup")
async def _startup() -> None:
    """Initialize background tasks on startup."""
    asyncio.create_task(_process_batch())


AGENTS: list[dict[str, str]] = [
    {"name": "qwen-coder", "status": "online"},  # Qwen2.5-0.5b-instruct (All tasks)
    {"name": "qwen-fast", "status": "online"},  # Qwen2.5-0.5b-instruct (Quick tasks)
]


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "1.2.0"}


@app.get("/router/status")
async def router_status() -> dict[str, list[dict[str, str]]]:
    """Get router/agent status."""
    return {"agents": AGENTS}


@app.post("/router/reassign")
async def router_reassign() -> JSONResponse:
    """Reassign tasks to agents."""
    return JSONResponse(content={"ok": True, "reassigned": True})


@app.post("/tasks/retry_failed")
async def retry_failed() -> dict[str, int]:
    """Retry failed tasks."""
    return {"retried": 0}


@app.post("/task")
async def submit_task(task_type: str, payload: str) -> dict[str, int]:
    """Submit a task to the queue."""
    task_queue.append({"type": task_type, "payload": payload, "arrived": time.time()})
    return {"queued": len(task_queue)}


@app.post("/generate")
async def generate(prompt: str, model: str = DEFAULT_MODEL):
    """Generate text using llama-server (llama.cpp) with streaming support."""
    async def _stream():
        # llama-server /completion endpoint format
        payload = {
            "prompt": prompt,
            "n_predict": 1024,
            "temperature": 0.3,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "stream": True,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{LLAMA_SERVER_URL}/completion",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or line.startswith("data: "):
                            # Parse SSE format: data: {...}
                            if line.startswith("data: "):
                                line = line[6:]  # Remove "data: " prefix
                            if line.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(line)
                                token: str = chunk.get("content", "")
                                if token:
                                    yield token
                                if chunk.get("stop", False) or chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
            except Exception as exc:
                yield f"\n[Error: {exc}]"

    return StreamingResponse(_stream(), media_type="text/plain")


@app.get("/models")
async def list_models() -> dict[str, list[str]]:
    """List available models."""
    return {"models": [DEFAULT_MODEL]}
